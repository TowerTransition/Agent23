"""
Text Generator - Simplified module optimized for fine-tuned PEFT models.

TWO MODES:
1) Direct PEFT model (PREFERRED): Minimal prompts, trusts fine-tuned model output
2) HTTP endpoint (fallback): More aggressive cleaning for non-fine-tuned models

DESIGN PRINCIPLES:
- Fine-tuned model: Ultra-minimal prompts, minimal post-processing (trust the training)
- HTTP endpoint: More detailed prompts, aggressive cleaning (don't trust as much)
- Footer/hashtags: Always added in code (never by model)
- Validation: Always enforced (one question, platform length limits)

ENV VARS:
- PEFT_ADAPTER_PATH -> Uses fine-tuned model directly (preferred)
- BASE_MODEL_NAME -> Base model for PEFT (default: TinyLlama/TinyLlama-1.1B-Chat-v1.0)
- LOCAL_LLM_ENDPOINT -> HTTP endpoint fallback (OpenAI-compatible)
- LOCAL_LLM_MODEL -> Model name for HTTP endpoint (default: tinyllama)
- ALLOW_DEFAULT_LLM_ENDPOINT -> Allow default localhost:11434 (default: false)

OUTPUT:
- dict: {"platform":..., "text":..., "hashtags":[...], "meta":{...}}
- For instagram also returns: {"caption":...} and meta.requires_image=True
"""

import logging
import os
import json
import re
import time
from typing import Dict, Any, Optional, List

import requests

# Optional imports for PEFT model loading
try:
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
    PEFT_AVAILABLE = True
except ImportError:
    PEFT_AVAILABLE = False


logger = logging.getLogger("TextGenerator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# ---- Brand footer (ONLY handled in code) ----
# These MUST match exactly what the model was trained on
SIGNATURE = "— Elevare by Amaziah"
# Training data uses this exact tagline BEFORE the signature
TAGLINE = "Real-world systems. Real clarity."
# Legacy line - kept for backward compatibility during extraction
INSIGHTS_LINE = "Insights from Elevare by Amaziah, building real-world systems with AI."

# Import validation utilities
from .validation_utils import (
    extract_body as extract_body_result,
    ensure_ends_with_statement,
    ensure_exactly_one_question_at_end,  # Deprecated - now calls ensure_ends_with_statement
    split_sentences,
    get_sentence_count_range,
    BodyExtractionResult,
    TAGLINE as VALIDATION_TAGLINE
)

# Backward compatibility: simple extract_body function
def extract_body(post_text: str) -> str:
    """
    Extract the body text from a post by removing hashtags and footer.
    Backward compatibility wrapper around validation_utils.extract_body.
    
    Args:
        post_text: Full post text including footer and hashtags
        
    Returns:
        Clean body text without footer or hashtags
    """
    result = extract_body_result(post_text)
    return result.body


class TextGenerator:
    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        local_llm_endpoint: Optional[str] = None,
        timeout_s: int = 120,
        brand_manager: Optional[Any] = None  # Deprecated - kept for compatibility
    ):
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_s = timeout_s

        # Model selection
        self.model = os.environ.get("LOCAL_LLM_MODEL") or model or "tinyllama"

        # Direct PEFT model mode (preferred if you have it)
        self.peft_adapter_path = os.environ.get("PEFT_ADAPTER_PATH")
        self.base_model_name = os.environ.get("BASE_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

        self.use_direct_model = False
        self.model_obj = None
        self.tokenizer = None

        if self.peft_adapter_path:
            if not PEFT_AVAILABLE:
                logger.warning("PEFT_ADAPTER_PATH set, but peft/transformers/torch not installed. Falling back to HTTP mode.")
            else:
                try:
                    self._load_peft_model()
                    self.use_direct_model = True
                    logger.info("TextGenerator running in DIRECT MODEL mode (PEFT).")
                except Exception as e:
                    logger.warning("PEFT load failed (%s). Falling back to HTTP mode.", e)

        # HTTP endpoint mode
        self.api_key = api_key or os.environ.get("LOCAL_LLM_API_KEY")
        self.local_llm_endpoint = local_llm_endpoint or os.environ.get("LOCAL_LLM_ENDPOINT")

        if not self.use_direct_model:
            if not self.local_llm_endpoint:
                allow_default = os.environ.get("ALLOW_DEFAULT_LLM_ENDPOINT", "").lower() in ("true", "1", "yes")
                if allow_default:
                    self.local_llm_endpoint = "http://localhost:11434/v1/chat/completions"
                    logger.warning("LOCAL_LLM_ENDPOINT not set; using default: %s", self.local_llm_endpoint)
                else:
                    raise ValueError(
                        "Need PEFT_ADAPTER_PATH (direct model) OR LOCAL_LLM_ENDPOINT (HTTP). "
                        "To allow default endpoint, set ALLOW_DEFAULT_LLM_ENDPOINT=true."
                    )
            logger.info("TextGenerator running in HTTP mode. endpoint=%s model=%s", self.local_llm_endpoint, self.model)

    # -------------------------
    # Public API
    # -------------------------
    def generate_text(
        self,
        context: Dict[str, Any],
        platform: str,
        max_length: int = 400,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generates a finished post for the platform.
        - Validates "exactly one question" on BODY ONLY
        - Appends footer in code
        - Ensures hashtags in code (model optional)
        """
        platform_key = (platform or "facebook").strip().lower()
        temp = temperature if temperature is not None else self.temperature

        # Store domain for sanitizer
        lens_plan = context.get("lens_plan") or {}
        domain = context.get("domain") or lens_plan.get("domain") or ""
        self._current_domain = domain

        # 1) Build minimal prompt that matches your trained format expectation
        prompt = self._build_minimal_prompt(context, platform_key)

        # 2) Call model (retry)
        last_err = None
        for attempt in range(1, self.max_retries + 2):
            try:
                raw = self._call_model(platform_key, prompt, max_tokens=max_length, temperature=temp)
                
                # For fine-tuned model (PEFT), trust it more - minimal processing
                if self.use_direct_model:
                    body = self._minimal_clean_for_finetuned(raw)
                else:
                    # HTTP endpoint mode - more aggressive cleaning needed
                    body = self._clean_model_output(raw)
                    body = self._post_process_content(body)
                    body = self._sanitize_prompt_echo(body)
                
                if not body.strip():
                    raise ValueError("Model returned empty text after cleaning")

                # Always validate structure (sentence count, ends with statement)
                body = self._enforce_sentence_count_and_format(body, platform_key)

                # 3) Footer AFTER validation (prevents footer breaking question rule)
                final_text = self._append_footer(body, platform_key)

                # 4) Hashtags AFTER footer (so they never interfere with question rule)
                tags = self._ensure_hashtags(context, platform_key)
                if tags:
                    final_text = final_text.rstrip() + "\n\n" + " ".join(tags)

                result = {
                    "platform": platform_key,
                    "text": final_text,
                    "hashtags": [t.lstrip("#") for t in tags],
                    "meta": {
                        "used_direct_model": self.use_direct_model,
                        "requires_image": platform_key == "instagram",
                    },
                }

                # Instagram convention - keep both text and caption
                if platform_key == "instagram":
                    result["caption"] = result["text"]

                return result

            except Exception as e:
                last_err = str(e)
                logger.warning("Generation failed attempt %d/%d: %s", attempt, self.max_retries + 1, last_err)
                time.sleep(min(2 ** attempt, 8))

        raise ValueError(f"Failed to generate text after retries. Last error: {last_err}")

    # -------------------------
    # Prompting
    # -------------------------
    def _get_training_example(self, domain: str) -> str:
        """
        Get a training example for the domain to use as few-shot example.
        Format matches EXACTLY what the model was trained on.

        Training data structure:
        - Opening thesis statement
        - Problem/context (1-2 sentences)
        - "AI supports/helps by..." sentence
        - Closing benefit statement
        - "Real-world systems. Real clarity." tagline
        - "— Elevare by Amaziah" signature
        - Exactly 4 hashtags

        NO QUESTIONS - all posts end with declarative statements.
        """
        domain_lower = (domain or "").lower()

        # Examples copied directly from training data (train.jsonl)
        examples = {
            "foreclosure": """Foreclosure involves many moving parts.

When information isn't coordinated, small details fall through the cracks and stress compounds.

AI supports clarity by coordinating information—helping people see how pieces relate without stepping into legal guidance.

Coordination reduces avoidable errors.

Real-world systems. Real clarity.
— Elevare by Amaziah

#RealWorldAI #HousingStability #ProcessClarity #SystemDesign""",

            "trading": """Fast markets challenge focus.

When speed increases, skipped steps and emotional reactions become more likely.

AI supports focus by reinforcing structure and reducing noise—without giving trading advice.

Focused execution supports disciplined trading.

Real-world systems. Real clarity.
— Elevare by Amaziah

#TradingSystems #ExecutionFocus #RiskDiscipline #RealWorldAI""",

            "assisted": """Confidence grows with clarity.

When families don't understand environments and care models, uncertainty rises.

AI supports clarity by organizing information and simplifying comparisons—without offering placement advice.

Clear understanding supports confident decisions.

Real-world systems. Real clarity.
— Elevare by Amaziah

#ResidentMatching #CareDecisions #ClarityMatters #RealWorldAI"""
        }

        # Match domain
        if "foreclosure" in domain_lower:
            return examples["foreclosure"]
        elif "trading" in domain_lower:
            return examples["trading"]
        elif "assisted" in domain_lower or "care" in domain_lower:
            return examples["assisted"]

        # Default to foreclosure example
        return examples["foreclosure"]

    def _build_minimal_prompt(self, context: Dict[str, Any], platform: str) -> str:
        """
        Build minimal prompt for fine-tuned model.
        Since model is fine-tuned, we can be very minimal - just provide context.

        Training data format (what the model learned):
        - 4-6 sentences
        - NO questions - ends with statement
        - "AI supports/helps by..." phrasing
        - Tagline + signature at end
        """
        # Get domain for example selection (only if using HTTP mode)
        domain = context.get("domain") or ""
        lens = context.get("lens_plan") or {}
        if not domain:
            domain = lens.get("domain") or ""

        # Get title/description from context or lens_plan
        title = context.get("title") or ""
        desc = context.get("description") or ""

        if not title:
            title = (lens.get("title") or lens.get("context") or "AI in real-world workflows").strip()
        if not desc:
            desc = (lens.get("description") or "").strip()

        if not title:
            title = "AI in real-world workflows"

        # For fine-tuned model: use training format labels only.
        # The model was trained on CONTEXT/PROBLEM/AI_SUPPORT/REINFORCEMENT.
        # No instructional English — it gets echoed verbatim in output.
        if self.use_direct_model:
            parts = [f"CONTEXT: {title}"]
            if desc:
                parts.append(f"PROBLEM: {desc}")
            parts.append("AI_SUPPORT:")
            return "\n".join(parts)

        # For HTTP endpoint (not fine-tuned): include example
        parts = []
        parts.append("Generate a post in this EXACT format (note: ends with STATEMENT, not question):")
        parts.append("")
        parts.append(self._get_training_example(domain))
        parts.append("")
        parts.append("---")
        parts.append("Now generate a similar post for this topic:")
        parts.append(f"Topic: {title}")
        if desc:
            parts.append(f"Context: {desc}")

        # Get decision/constraint/risk_owner from lens_plan (optional)
        decision = (lens.get("decision") or "").strip()
        constraint = (lens.get("constraint") or "").strip()
        risk_owner = (lens.get("risk_owner") or "").strip()

        if decision:
            parts.append(f"Decision: {decision}")
        if constraint:
            parts.append(f"Constraint: {constraint}")
        if risk_owner:
            parts.append(f"Risk owner: {risk_owner}")

        # Platform-specific instruction (minimal)
        parts.append("")
        parts.append(self._style_line(platform))
        parts.append("Do NOT end with a question. End with a declarative statement.")

        return "\n".join([p for p in parts if p])

    def _style_line(self, platform: str) -> str:
        """
        Platform-specific style hints for HTTP mode.
        NOTE: Training data shows NO questions - all posts end with statements.
        """
        if platform in ("twitter", "x"):
            return "Write 2-4 short sentences, max 270 characters. End with a statement."
        if platform == "linkedin":
            return "Write 4-8 sentences, 1-2 short paragraphs. End with a statement."
        if platform == "instagram":
            return "Write 3-5 short sentences. End with a statement."
        # Facebook and default - matches training data exactly
        return "Write 4-6 sentences. End with a statement."

    def _system_message(self, platform: str) -> str:
        # For fine-tuned model: identity only, no instructions.
        # The model echoes any instructional text. The training format
        # (CONTEXT/PROBLEM/AI_SUPPORT/REINFORCEMENT) drives structure instead.
        if self.use_direct_model:
            return "You are Elevare by Amaziah."

        # For HTTP endpoint (not fine-tuned): more detailed instructions
        # NOTE: Training data shows NO questions - all posts end with statements
        if platform == "facebook":
            return (
                "Write a Facebook post. Output only the post text. "
                "4-6 sentences. End with a declarative statement (NOT a question). "
                "No politics, religion, or exaggerated claims."
            )

        # For other platforms, use lean messages
        base = (
            "You write finished social posts only. "
            "No labels, no headings, no bullet lists, no meta-commentary. "
            "No politics or religion. Avoid exaggerated claims. "
            "Frame AI as decision support/prioritization, not replacement. "
            "End with a declarative statement, NOT a question."
        )
        if platform in ("twitter", "x"):
            return base + " Keep within 270 characters."
        return base

    # -------------------------
    # Model calling
    # -------------------------
    def _call_model(self, platform: str, user_prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Call the model (direct PEFT or HTTP endpoint).
        When using fine-tuned model (PEFT), NEVER falls back to Ollama.
        """
        system_msg = self._system_message(platform)

        if self.use_direct_model:
            # Use fine-tuned PEFT model directly - no fallback to Ollama
            return self._call_direct_model(system_msg, user_prompt, max_tokens, temperature)

        # HTTP endpoint mode (only used when PEFT is not available)
        return self._call_http(system_msg, user_prompt, max_tokens, temperature)

    def _call_http(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float) -> str:
        """
        Call HTTP endpoint (OpenAI-compatible or Ollama).
        NOTE: This should NEVER be called when use_direct_model=True.
        Only use this for HTTP endpoint mode.
        """
        if self.use_direct_model:
            raise RuntimeError("Direct model mode is enabled. Use _call_direct_model instead of _call_http.")
        
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "n": 1,
        }

        try:
            resp = requests.post(self.local_llm_endpoint, json=payload, headers=headers, timeout=self.timeout_s)
            if resp.status_code == 404:
                # Ollama fallback (only in HTTP mode, not for fine-tuned model)
                logger.info("OpenAI-compatible endpoint returned 404. Trying Ollama /api/generate fallback.")
                return self._call_ollama_generate(system_msg, user_msg, max_tokens, temperature)
            resp.raise_for_status()
            data = resp.json()
            return (data["choices"][0]["message"]["content"] or "").strip()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            # Try Ollama as a second chance for connection/timeout errors (common in local setups)
            # BUT ONLY if we're in HTTP mode (not using fine-tuned model)
            logger.warning("HTTP endpoint connection/timeout error (%s). Trying Ollama /api/generate fallback.", e)
            return self._call_ollama_generate(system_msg, user_msg, max_tokens, temperature)
        except requests.exceptions.RequestException as e:
            # Other request errors (auth, server errors, etc.) should not fall back to Ollama
            logger.error("HTTP endpoint request error (%s): %s", type(e).__name__, str(e))
            raise

    def _call_ollama_generate(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float) -> str:
        endpoint = self._convert_to_ollama_generate_endpoint(self.local_llm_endpoint)
        full_prompt = f"{system_msg}\n\n{user_msg}".strip()

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        resp = requests.post(endpoint, json=payload, headers={"Content-Type": "application/json"}, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        return (data.get("response") or "").strip()

    @staticmethod
    def _convert_to_ollama_generate_endpoint(endpoint: str) -> str:
        if not endpoint:
            return "http://localhost:11434/api/generate"
        if "/v1/chat/completions" in endpoint:
            return endpoint.replace("/v1/chat/completions", "/api/generate")
        if endpoint.endswith("/api/generate"):
            return endpoint
        return endpoint.rstrip("/") + "/api/generate"

    # -------------------------
    # Direct model (PEFT)
    # -------------------------
    def _load_peft_model(self) -> None:
        if not PEFT_AVAILABLE:
            raise ImportError("Install: pip install peft transformers torch")

        if not os.path.exists(self.peft_adapter_path):
            raise FileNotFoundError(f"PEFT_ADAPTER_PATH not found: {self.peft_adapter_path}")

        logger.info("Loading base model: %s", self.base_model_name)
        # Read device_map from environment variable, with smart defaults
        device_map_setting = os.environ.get("PEFT_DEVICE_MAP")
        if device_map_setting:
            # Parse string values
            if device_map_setting.lower() == "auto":
                device_map = "auto" if torch.cuda.is_available() else None
            elif device_map_setting.lower() == "cpu":
                device_map = None
            elif device_map_setting.lower() == "cuda":
                device_map = "auto" if torch.cuda.is_available() else None
            else:
                # Could be a JSON dict string, but for simplicity, default to auto/cpu logic
                device_map = "auto" if torch.cuda.is_available() else None
                logger.warning("PEFT_DEVICE_MAP value '%s' not recognized, using default", device_map_setting)
        else:
            # Default behavior: auto if CUDA available, else None (CPU)
            device_map = "auto" if torch.cuda.is_available() else None
        
        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map=device_map,
            low_cpu_mem_usage=True,
        )

        logger.info("Loading adapter: %s", self.peft_adapter_path)
        self.model_obj = PeftModel.from_pretrained(base, self.peft_adapter_path)
        self.model_obj.eval()

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def _call_direct_model(self, system_msg: str, user_msg: str, max_tokens: int, temperature: float) -> str:
        if not self.model_obj or not self.tokenizer:
            raise RuntimeError("Direct model not loaded.")

        messages = [{"role": "system", "content": system_msg}, {"role": "user", "content": user_msg}]
        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

        inputs = self.tokenizer(prompt, return_tensors="pt")
        if torch.cuda.is_available():
            inputs = {k: v.cuda() for k, v in inputs.items()}

        do_sample = temperature > 0.0
        with torch.no_grad():
            out = self.model_obj.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature if do_sample else None,
                do_sample=do_sample,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        # Decode only the new tokens (skip the prompt)
        generated = self.tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
        return generated.strip()

    # -------------------------
    # Post-processing
    # -------------------------
    def _clean_model_output(self, raw: str) -> str:
        """
        Remove labels, meta-commentary, and instruction echoes.
        Used for HTTP endpoint mode (not fine-tuned models).
        """
        text = raw.strip()

        # Remove common label prefixes
        label_patterns = [
            r"^(CONTEXT|PROBLEM|AI SUPPORT|REINFORCEMENT|FOOTER|HASHTAGS|Title|Post|Content|Facebook Post|Twitter Post|Instagram Post|LinkedIn Post)[:.]\s*",
            r"^(START WITH|Start with|Start by reproducing|End with|END WITH)[:.]\s*",
            r"^(No headings|no headings|No labels|no labels|No bullets|no bullets|No meta-commentary|no meta-commentary)\b[^.!?]*[.!?]?",
        ]

        for pattern in label_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE | re.MULTILINE)

        # Remove instruction-like lines
        instruction_patterns = [
            r"^.*(4[-–]6 complete sentences?\.?\s*End with exactly (ONE|one) question mark\.?).*$",
            r"^.*(Write \d+[-–]\d+ sentences?\.?\s*End with exactly one question\.?).*$",
            r"^.*(Final Facebook post\.|Final post\.).*$",
        ]

        lines = text.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # Skip lines that are pure instructions
            is_instruction = any(re.search(pat, line, re.IGNORECASE) for pat in instruction_patterns)
            if not is_instruction:
                cleaned_lines.append(line)

        text = "\n".join(cleaned_lines).strip()

        # Remove duplicate phrases (simple regex)
        text = re.sub(r'\b(\w+(?:\s+\w+){1,4})\s+\1\b', r'\1', text, flags=re.IGNORECASE)

        # Remove incomplete sentences (ending with dash or cut-off)
        sentences = re.split(r'([.!?]+)', text)
        complete = []
        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else "")
            sent = sent.strip()
            if sent and len(sent) > 10 and not re.search(r'\w+[-–]\s*[?!.]?$', sent):
                complete.append(sent)
        
        # Check for trailing fragment (odd number of splits means last fragment has no punctuation)
        if len(sentences) % 2 == 1:
            last_fragment = sentences[-1].strip()
            if last_fragment and len(last_fragment) > 10 and not re.search(r'\w+[-–]\s*[?!.]?$', last_fragment):
                complete.append(last_fragment)
        
        if complete:
            text = " ".join(complete)

        return text.strip()

    def _minimal_clean_for_finetuned(self, text: str) -> str:
        """
        Minimal cleanup for fine-tuned model output.
        Trust the model - only remove obvious artifacts and prompt echoes.
        """
        text = text.strip()
        
        # Remove obvious markers that shouldn't be in output
        text = re.sub(r'(?i)\bEND\b', '', text)
        text = re.sub(r'(?m)^\s*(CONTEXT|PROBLEM|AI_SUPPORT|REINFORCEMENT|FOOTER|HASHTAGS)[:.]\s*', '', text)
        
        # Remove prompt instruction echoes (model sometimes copies these)
        instruction_patterns = [
            r'(?i)\bWrite\s+\d+[-–]\d+\s+sentences?[^.!?]*[.!?]?',
            r'(?i)\bWrite\s+\d+\s+short\s+sentences?[^.!?]*[.!?]?',
            r'(?i)\bend\s+with\s+exactly\s+one\s+question[^.!?]*[.!?]?',
            r'(?i)\bwith\s+(?:exact(?:ly)?\s+)?one\s+question[^.!?]*[.!?]?',
            r'(?i)\bWrite\s+one\s+short\s+post[^.!?]*[.!?]?',
            r'(?i)\bmax\s+\d+\s+characters?[^.!?]*[.!?]?',
            r'(?i)\b\d+[-–]\d+\s+sentences?\.?\s*',  # Catches standalone "4-6 sentences."
            # Remove instruction echoes about answering questions
            r'(?i)How\s+can\s+you\s+answering\s+this\s+question[^.!?]*[.!?]?',
            r'(?i)answering\s+this\s+question[^.!?]*[.!?]?',
            r'(?i)Then\s+continue\s+with[^.!?]*[.!?]?',
            r'(?i)following\s+the\s+\w+\s+format[^.!?]*[.!?]?',
            r'(?i)A\s+clear\s+question\s+at\s+the\s+of\s+this\s+process[^.!?]*[.!?]?',
            r'(?i)helps\s+ensure\s+clarity\s+and\s+accuracy[^.!?]*[.!?]?',
            # Catch any sentence containing both "answering" and "question" (instruction echo)
            r'(?i)[^.!?]*answering[^.!?]*question[^.!?]*[.!?]',
            # Catch continuation instructions
            r'(?i)[^.!?]*continue\s+with\s+the\s+complete[^.!?]*[.!?]',
            r'(?i)[^.!?]*complete\s+post\s+following[^.!?]*[.!?]',
            # Additional patterns from test results
            r'(?i)^\s*—\s*\d+[-–]\d+\s+sentences?\s+max\s*$',
            r'(?i)^\s*—\s*End\s+with\s+question\.\s*$',
            r'(?i)^\s*—\s*Exactly\s+one\s+complete\s+thought\.\s*$',
            r'(?i)End\s+with\s+this\s+question:\s*',
            r'(?i)End\s+with\s*[—:]\s*',  # "End with:" or "End with—"
            r'(?i)^\s*END\b',  # Standalone END (word boundary)
            r'(?i)^\s*—\s*End\.?\s*$',  # "— End" or "— End."
            r'(?i)^\s*End\.?\s*$',  # Standalone "End" or "End."
            r'(?i)^\s*\d+[-–]\d+\s+sentences?\.?\s*$',  # Standalone "4-6 sentences."
            r'(?im)^\s*Question[:.!]?\s*$',
            r'(?i)^\s*Answer:\s*',  # "Answer:" label
            r'(?i)^\s*Response:\s*',  # "Response:" label
            r'(?i)^\s*—\s*Q\.\s*',  # "— Q." pattern
            r'(?i)^\s*–\s*Q\.\s*',  # "– Q." pattern (different dash)
            r'(?i)Follow\s+by\s+posting\.?\s*$',  # "Follow by posting"
            r'(?i)^\s*Four-step\s+approach\.?\s*$',  # "Four-step approach"
            r'(?i)^\s*A\s+system\s+that\s+follows\s+these\s+four\s+steps:\s*$',  # "A system that follows these four steps:"
            # Prompt phrases that can leak from system message / user prompt
            r'(?i)\bWrite\s+a\s+(?:Facebook|Twitter|LinkedIn|Instagram|social\s+media)\s+post[^.!?]*[.!?]?',
            r'(?i)\bWrite\s+a\s+post\s+in\s+the\s+[^.!?]*[.!?]?',
            r'(?i)\bas\s+you\s+were\s+trained\s+on[^.!?]*[.!?]?',
            # Imperative instruction sentences the model generates
            # "ask this question:" label must be stripped BEFORE the "Then, [verb]"
            # pattern, otherwise "Then, ask ... question: How...?" strips the question too
            r'(?i)(?:Then,?\s+)?ask\s+this\s+question:\s*',
            r'(?i)\bStart\s+by\s+\w+[^.!?]*[.!?]',
            r'(?i)\bThen,?\s+(?:establish|define|set|provide|create|build|ensure|follow|apply|begin|start|use|make|prepare|organize|identify|maintain|track|update|verify|review|send|share|implement)[^.!?]*[.!?]',
        ]
        for pattern in instruction_patterns:
            text = re.sub(pattern, '', text)
        
        # Remove label prefixes that might leak from prompt (Decision:, Constraint:, Risk owner:, Question:, Real-world example:)
        # Also remove CONTEXT: and PROBLEM: labels (keep content)
        text = re.sub(r'(?m)^\s*(Decision|Constraint|Risk owner|Risk Owner|Question|Real-world example|Real world example|CONTEXT|PROBLEM|AI_SUPPORT|REINFORCEMENT)[:.]\s*', '', text, flags=re.IGNORECASE)
        
        # Remove standalone constraint/risk owner/question/example lines (if model copied them)
        text = re.sub(r'(?m)^\s*Constraint:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Risk owner:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Decision:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Question:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Answer:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Response:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Real-world example:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?m)^\s*Real world example:\s*[^\n]+\n?', '', text, flags=re.IGNORECASE)
        
        # Remove instruction-like phrases (but keep the actual question/answer content)
        # Remove labels with dashes first
        text = re.sub(r'(?i)^\s*—\s*Question:\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*—\s*Answer:\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*—\s*Response:\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*—\s*Q\.\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*–\s*Q\.\s*', '', text, flags=re.MULTILINE)
        # Remove standalone labels (without dashes) - these should already be removed above, but double-check
        text = re.sub(r'(?i)^\s*Question:\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*Answer:\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*Response:\s*', '', text, flags=re.MULTILINE)
        # Remove instruction phrases
        text = re.sub(r'(?i)Follow\s+by\s+posting\.?\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*Four-step\s+approach\.?\s*$', '', text, flags=re.MULTILINE)
        text = re.sub(r'(?i)^\s*A\s+system\s+that\s+follows\s+these\s+four\s+steps:\s*$', '', text, flags=re.MULTILINE)
        
        # Remove numbered list items that are clearly instruction format
        # Remove lines like "1. Tracking of documents" if they follow instruction patterns
        text = re.sub(r'(?i)^\s*\d+\.\s+(Tracking|Providing|Automating|Aligning|Identifying|Maintaining)\s+', '', text, flags=re.MULTILINE)
        
        # Remove brand artifacts and unwanted mentions
        text = re.sub(r'\bclearlyai™?\b', '', text, flags=re.IGNORECASE)
        # Remove trailing attribution patterns like "— foreclosure process coordination by clearlyai™?"
        text = re.sub(r'\s*—\s*[^?]+\s+by\s+[^?]+\?', '', text, flags=re.IGNORECASE)
        # Remove wrong signature formats like "— Topic by Elevare by Amaziah" or "— Topic by Elevare"
        text = re.sub(r'—\s+[^—]+?\s+by\s+Elevare\s+by\s+Amaziah', '', text, flags=re.IGNORECASE)
        text = re.sub(r'—\s+[^—]+?\s+by\s+Elevare(?!\s+by\s+Amaziah)', '', text, flags=re.IGNORECASE)
        # Remove wrong brand mentions like "— Cogora"
        text = re.sub(r'—\s+Cogora\s*$', '', text, flags=re.IGNORECASE | re.MULTILINE)
        # Remove repetitive dash patterns (like "— When clarity is clear...") but keep signature "— Elevare by Amaziah"
        text = re.sub(r'^\s*—\s+(?!Elevare\s+by\s+Amaziah)([^—\n]+)$', r'\1', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # Remove entire sentences that are clearly instruction echoes
        # Split by sentence boundaries and filter
        sentence_pattern = r'([^.!?]+[.!?]+)'
        sentences = re.findall(sentence_pattern, text)
        remaining_text = re.sub(sentence_pattern, '', text)  # Text that doesn't match sentence pattern
        
        instruction_indicators = [
            r'answering\s+this\s+question',
            r'continue\s+with\s+the\s+complete',
            r'complete\s+post\s+following',
            r'following\s+the\s+\w+\s+format',
            r'clear\s+question\s+at\s+the\s+of',
            r'helps\s+ensure\s+clarity\s+and\s+accuracy',
            r'end\s+with\s+this\s+question',
            r'end\s+with\s+question',
            r'^\s*—\s*[^—]*\s+by\s+Elevare',  # Wrong signature format like "— Topic by Elevare"
            r'Now\s+generate\s+a\s+similar\s+post\s+for:',  # Echo from training example prompt
            r'^\s*—\s*End\.?\s*$',  # "— End" or "— End."
            r'^\s*End\.?\s*$',  # Standalone "End" or "End."
        ]
        
        cleaned_sentences = []
        for sentence in sentences:
            is_instruction = any(re.search(pattern, sentence, re.IGNORECASE) for pattern in instruction_indicators)
            if not is_instruction:
                cleaned_sentences.append(sentence)
        
        text = ''.join(cleaned_sentences) + remaining_text
        
        # Normalize whitespace (but preserve paragraph breaks)
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\n{3,}', '\n\n', text)  # Multiple newlines to double
        
        return text.strip()
    
    def _fix_incomplete_sentences(self, text: str) -> str:
        """
        Fix incomplete sentences like "AI clarity." -> "AI provides clarity."
        """
        # Split into sentences
        sentences = split_sentences(text)
        fixed_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for incomplete patterns
            # Pattern: "AI clarity." or "AI communication." -> "AI provides clarity."
            incomplete_pattern = re.match(r'^AI\s+(clarity|communication|coordination|focus|support|guidance|information|updates|decisions|options)\.?$', sentence, re.IGNORECASE)
            if incomplete_pattern:
                noun = incomplete_pattern.group(1).lower()
                # Convert to complete sentence
                if noun == "clarity":
                    sentence = "AI provides clarity."
                elif noun == "communication":
                    sentence = "AI enables communication."
                elif noun == "coordination":
                    sentence = "AI supports coordination."
                elif noun == "focus":
                    sentence = "AI helps maintain focus."
                elif noun == "support":
                    sentence = "AI provides support."
                elif noun == "guidance":
                    sentence = "AI offers guidance."
                elif noun == "information":
                    sentence = "AI organizes information."
                elif noun == "updates":
                    sentence = "AI delivers updates."
                elif noun == "decisions":
                    sentence = "AI supports decisions."
                elif noun == "options":
                    sentence = "AI presents options."
            
            # Pattern: "Families understand care options." - this is actually complete, keep it
            # Pattern: "X understand Y" - complete sentence
            
            fixed_sentences.append(sentence)
        
        return " ".join(fixed_sentences)
    
    def _post_process_content(self, text: str) -> str:
        """
        Post-processing for HTTP endpoint mode (not fine-tuned).
        More aggressive cleaning needed for non-fine-tuned models.
        """
        # Import sanitizer (simple version)
        try:
            from .sanitizer import sanitize_post
            # Get domain from stored context if available
            domain = getattr(self, '_current_domain', None)
            return sanitize_post(text, domain=domain)
        except ImportError:
            # Fallback to basic cleanup if sanitizer not available
            text = text.strip()
            text = re.sub(r'(?i)\bEND\b', '', text)
            text = re.sub(r'(?m)^\s*\d+\.\s+.*$', '', text)
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n{3,}', '\n\n', text)
            return text.strip()

    def _sanitize_prompt_echo(self, text: str) -> str:
        """
        Remove prompt echoes and instruction artifacts.
        """
        # Remove common prompt echo patterns
        instruction_phrases_to_remove = [
            r'\b(Start by reproducing)[:.]\s*',
            r'\b(Write a finished Facebook post)[:.]\s*',
            r'\b(Output only the post text)[:.]\s*',
            r'\b(Do not include)[:.]\s*',
            r'\bSTART HERE\s*',
            r'\(?\s*not repeat beginning text\s*\)?',
            r'\(?\s*not repeat\s+beginning\s+text\s*\)?',
            r'\bQuestion:\s*',
            r'\(?\s*not\s+repeat\s+beginning\s+text\s*\)?',
            r'\bfollow these natural sentences\b',
            r'\bwith one question\b',
            r'\bContinue with steps until complete\b',
            r'\bBe clear responsibility\b',
            r'\bFollow established process\b',
            r'\bfollow these\s+natural\s+sentences\b',
            r'\bcontinue\s+with\s+steps\b',
            r'\buntil\s+complete\b',
        ]
        
        for pattern in instruction_phrases_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Remove parenthetical instruction echoes more aggressively
        text = re.sub(r'\([^)]*(?:not|repeat|beginning|text|start|here|natural|sentences|question|steps|complete|process)[^)]*\)', '', text, flags=re.IGNORECASE)
        
        # Remove instruction-like sentence fragments
        # Patterns that look like meta-instructions rather than content
        instruction_sentences = [
            r'\bfollow\s+these\s+[^.]*\.',
            r'\bwith\s+one\s+question\s*\.',
            r'\bcontinue\s+with\s+[^.]*\.',
            r'\bbe\s+clear\s+[^.]*\.',
            r'\bfollow\s+established\s+[^.]*\.',
        ]
        
        for pattern in instruction_sentences:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and periods that might result
        text = re.sub(r'\.\s*\.', '.', text)  # Remove double periods
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s+\.', '.', text)  # Remove space before period
        
        return text.strip()
    
    def _fix_incomplete_sentences(self, text: str) -> str:
        """
        Fix incomplete sentences like "AI clarity." -> "AI provides clarity."
        """
        # Split into sentences
        sentences = split_sentences(text)
        fixed_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Check for incomplete patterns
            # Pattern: "AI clarity." or "AI communication." -> "AI provides clarity."
            incomplete_pattern = re.match(r'^AI\s+(clarity|communication|coordination|focus|support|guidance|information|updates|decisions|options)\.?$', sentence, re.IGNORECASE)
            if incomplete_pattern:
                noun = incomplete_pattern.group(1).lower()
                # Convert to complete sentence
                if noun == "clarity":
                    sentence = "AI provides clarity."
                elif noun == "communication":
                    sentence = "AI enables communication."
                elif noun == "coordination":
                    sentence = "AI supports coordination."
                elif noun == "focus":
                    sentence = "AI helps maintain focus."
                elif noun == "support":
                    sentence = "AI provides support."
                elif noun == "guidance":
                    sentence = "AI offers guidance."
                elif noun == "information":
                    sentence = "AI organizes information."
                elif noun == "updates":
                    sentence = "AI delivers updates."
                elif noun == "decisions":
                    sentence = "AI supports decisions."
                elif noun == "options":
                    sentence = "AI presents options."
            
            fixed_sentences.append(sentence)
        
        return " ".join(fixed_sentences)
    
    def _enforce_sentence_count_and_format(self, body: str, platform: str) -> str:
        """
        Ensure body matches training data format:
        - 4-6 sentences (varies slightly by platform)
        - Ends with a STATEMENT (not a question)
        - Fixes incomplete sentences
        """
        # Fix incomplete sentences first (like "AI clarity." -> "AI provides clarity.")
        body = self._fix_incomplete_sentences(body)

        # Extract clean body (removes footer/hashtags) using validation utils
        extracted = extract_body_result(body)
        body_clean = extracted.body

        # Ensure ends with statement (training data has NO questions)
        body_clean = ensure_ends_with_statement(body_clean)

        # Get platform-specific sentence count range
        min_sentences, max_sentences = get_sentence_count_range(platform)

        # Enforce sentence count by platform
        sentences = split_sentences(body_clean)

        if len(sentences) > max_sentences:
            # Trim to max, ensure ends with period
            body_clean = " ".join(sentences[:max_sentences])
            if not body_clean.endswith("."):
                body_clean = body_clean.rstrip(".,!?") + "."
            logger.info("Trimmed post from %d to %d sentences for %s", len(sentences), max_sentences, platform)
        elif len(sentences) < min_sentences:
            # Too short - log warning but don't fail (trust the model)
            logger.warning("%s post has only %d sentences (target: %d-%d)", platform, len(sentences), min_sentences, max_sentences)

        # Final check: ensure ends with period, not question mark
        if body_clean.endswith("?"):
            body_clean = body_clean.rstrip("?") + "."

        return body_clean.strip()

    # Keep old name for backward compatibility
    def _enforce_one_question_and_length(self, body: str, platform: str) -> str:
        """DEPRECATED: Use _enforce_sentence_count_and_format instead."""
        return self._enforce_sentence_count_and_format(body, platform)

    def _append_footer(self, body: str, platform: str) -> str:
        """
        Append footer in code (never ask model to do it).
        Footer format matches training data exactly:

        [body text]

        Real-world systems. Real clarity.
        — Elevare by Amaziah
        """
        # Remove any existing footer if model accidentally added it
        if SIGNATURE in body:
            body = body.split(SIGNATURE)[0].strip()
        if INSIGHTS_LINE in body:
            body = body.split(INSIGHTS_LINE)[0].strip()
        if TAGLINE in body:
            body = body.split(TAGLINE)[0].strip()

        # Remove partial footer text from training examples
        if "Real-world systems. Real clarity." in body:
            body = body.split("Real-world systems. Real clarity.")[0].strip()

        # Append footer in EXACT training data format
        # Training format: tagline on its own line, then signature
        footer = f"\n\n{TAGLINE}\n{SIGNATURE}"
        return body + footer

    def _ensure_hashtags(self, context: Dict[str, Any], platform: str) -> List[str]:
        """
        Generate/ensure EXACTLY 4 hashtags (matches training data).
        Training data shows exactly 4 hashtags on every post.
        """
        hashtags = []

        # Try to get hashtags from context directly
        hashtags = context.get("hashtags", []) or []

        # If no hashtags provided, determine from domain (from lens_plan or context)
        if not hashtags:
            domain = ""
            # Check lens_plan first (most reliable)
            lens_plan = context.get("lens_plan") or {}
            domain = (lens_plan.get("domain") or "").lower()

            # Fall back to context domain if lens_plan doesn't have it
            if not domain:
                domain = (context.get("domain") or "").lower()

            # Domain-based hashtags (aligned with training data patterns)
            # Training data hashtags follow pattern: #DomainSpecific #ConceptName #ClarityMatters #RealWorldAI
            if "foreclosure" in domain:
                hashtags = ["#RealWorldAI", "#HousingStability", "#ProcessClarity", "#SystemDesign"]
            elif "assisted living" in domain or "assisted" in domain or "care" in domain or "senior" in domain:
                hashtags = ["#CareOperations", "#ResidentMatching", "#ClarityMatters", "#RealWorldAI"]
            elif "trading" in domain or "futures" in domain:
                hashtags = ["#TradingSystems", "#ExecutionFocus", "#RiskDiscipline", "#RealWorldAI"]
            else:
                # Default hashtags (aligned with training data)
                hashtags = ["#RealWorldAI", "#SystemDesign", "#ProcessClarity", "#ClarityMatters"]

        # CRITICAL: Training data shows EXACTLY 4 hashtags
        # Enforce exactly 4 hashtags regardless of platform
        HASHTAG_COUNT = 4

        if len(hashtags) > HASHTAG_COUNT:
            hashtags = hashtags[:HASHTAG_COUNT]
        elif len(hashtags) < HASHTAG_COUNT:
            # Pad with default hashtags if needed
            default_fillers = ["#RealWorldAI", "#SystemDesign", "#ClarityMatters", "#ProcessClarity"]
            for filler in default_fillers:
                if len(hashtags) >= HASHTAG_COUNT:
                    break
                if filler not in hashtags and f"#{filler.lstrip('#')}" not in hashtags:
                    hashtags.append(filler)

        # Ensure all have # prefix
        return [f"#{tag.lstrip('#')}" for tag in hashtags[:HASHTAG_COUNT] if tag]

    # -------------------------
    # Image prompt (kept for compatibility)
    # -------------------------
    def generate_image_prompt(
        self,
        context: Dict[str, Any],
        platform: str,
        brand_guidelines: Dict[str, Any] = None  # Deprecated - kept for compatibility
    ) -> str:
        """
        Generate an image prompt based on context (not trend data).
        The fine-tuned model generates content, so we use context directly.
        """
        # Get title/description from context or lens_plan (not trend)
        title = context.get("title") or ""
        desc = context.get("description") or ""
        
        # Check lens_plan for context info
        lens = context.get("lens_plan") or {}
        if not title:
            title = (lens.get("title") or lens.get("context") or "AI technology").strip()
        if not desc:
            desc = (lens.get("description") or "").strip()

        prompt_parts = []
        prompt_parts.append(f"Modern illustration showing {title}")
        if desc:
            prompt_parts.append(f"depicting {desc}")

        image_prompt = ", ".join(prompt_parts)
        image_prompt += ", high quality, professional, clean design"

        return image_prompt
