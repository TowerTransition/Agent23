"""
Text Generator - Smaller, cleaner module for generating platform posts via:
1) Direct local model inference (PEFT adapter) OR
2) HTTP endpoint (OpenAI-compatible) with Ollama /api/generate fallback.

GOALS (your issues):
- Lean on the trained bot: minimal prompts, no giant brand-guideline blocks.
- Fix footer duplication: footer appended ONLY in code, never required from the model.
- Fix "no hashtags" problem: hashtags are generated/ensured in code (model optional).
- Keep the "exactly one question" rule on BODY ONLY (footer + hashtags come after).

ENV VARS:
- PEFT_ADAPTER_PATH (optional) + BASE_MODEL_NAME (optional) -> direct inference mode
- LOCAL_LLM_ENDPOINT (OpenAI-compatible e.g. http://localhost:11434/v1/chat/completions)
- LOCAL_LLM_MODEL (optional, default: tinyllama)
- LOCAL_LLM_API_KEY (optional)
- DISABLE_JSON_REASONING=true (optional)  # defaults to true in direct-model mode anyway

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
SIGNATURE = "— Elevare by Amaziah"
INSIGHTS_LINE = "Insights from Elevare by Amaziah, building real-world systems with AI."

# Import validation utilities
from .validation_utils import (
    extract_body as extract_body_result,
    ensure_exactly_one_question_at_end,
    split_sentences,
    BodyExtractionResult
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

        # 1) Build minimal prompt that matches your trained format expectation
        prompt = self._build_minimal_prompt(context, platform_key)

        # 2) Call model (retry)
        last_err = None
        for attempt in range(1, self.max_retries + 2):
            try:
                raw = self._call_model(platform_key, prompt, max_tokens=max_length, temperature=temp)
                body = self._clean_model_output(raw)
                body = self._post_process_content(body)
                body = self._sanitize_prompt_echo(body)
                body = self._enforce_one_question_and_length(body, platform_key)

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
    def _build_minimal_prompt(self, context: Dict[str, Any], platform: str) -> str:
        """
        Build minimal prompt for fine-tuned model.
        The model generates content itself - we don't need trend data.
        Uses lens_plan or context directly.
        """
        # Get title/description from context or lens_plan (not trend)
        title = context.get("title") or ""
        desc = context.get("description") or ""
        
        # Check lens_plan for context info
        lens = context.get("lens_plan") or {}
        if not title:
            title = (lens.get("title") or lens.get("context") or "AI in real-world workflows").strip()
        if not desc:
            desc = (lens.get("description") or "").strip()
        
        # If still no title, use a default
        if not title:
            title = "AI in real-world workflows"
        
        # Get decision/constraint/risk_owner from lens_plan
        decision = (lens.get("decision") or "").strip()
        constraint = (lens.get("constraint") or "").strip()
        risk_owner = (lens.get("risk_owner") or "").strip()

        parts = [f"CONTEXT: {title}"]
        if desc:
            parts.append(desc)

        # These are useful "operator" anchors but not big rule blocks.
        # If they're empty, no harm.
        if decision:
            parts.append(f"Decision: {decision}")
        if constraint:
            parts.append(f"Constraint: {constraint}")
        if risk_owner:
            parts.append(f"Risk owner: {risk_owner}")

        # End instruction: short and consistent
        parts.append(self._style_line(platform))

        return "\n".join([p for p in parts if p])

    def _style_line(self, platform: str) -> str:
        if platform in ("twitter", "x"):
            return "Write one short post, max 270 characters, end with exactly one question."
        if platform == "linkedin":
            return "Write 6-10 sentences, 1-2 short paragraphs, end with exactly one question."
        if platform == "instagram":
            return "Write 2-5 short paragraphs, end with exactly one question."
        return "Write 4-6 sentences, end with exactly one question."

    def _system_message(self, platform: str) -> str:
        # Different system messages for direct model (PEFT) vs HTTP endpoint
        if platform == "facebook":
            if self.use_direct_model:
                return (
                    "Write a finished Facebook post as plain text. "
                    "No headings. No lists. No numbered steps. "
                    "Do not include template words like 'END'. "
                    "Do not include hashtags. Do not include any signature or footer. "
                    "Do not mention any brand names other than the content itself. "
                    "Write 4-6 natural sentences and end with exactly one question."
                )
            else:
                return (
                    "Write a Facebook post. Output only the post text. "
                    "4-6 sentences. End with exactly one question. "
                    "No politics, religion, or exaggerated claims."
                )
        
        # For other platforms, use lean messages
        base = (
            "You write finished social posts only. "
            "No labels, no headings, no bullet lists, no meta-commentary. "
            "No politics or religion. Avoid exaggerated claims. "
            "Frame AI as decision support/prioritization, not replacement."
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

    def _post_process_content(self, text: str) -> str:
        """
        Additional post-processing on content.
        """
        # --- PEFT cleanup: strip common adapter template garbage ---
        if self.use_direct_model:
            # remove numbered instruction lines like "4. Start by..."
            text = re.sub(r'(?m)^\s*\d+\.\s+.*$', '', text)

            # remove common template phrases
            text = re.sub(r'(?i)\b4-6 sentences\.?\s*one question\.?\b', '', text)
            text = re.sub(r'(?i)\bformal,\s*confident communication\.?\b', '', text)
            text = re.sub(r'(?i)\bhandoffs\.\s*clear communication\.\b', 'Handoffs require clear communication.', text)

            # remove END markers
            text = re.sub(r'(?i)\bEND\b', '', text)

            # remove any non-Elevare signatures the model emits
            text = re.sub(r'(?m)^—\s*(?!Elevare by Amaziah).*$', '', text)

            # remove hashtags entirely (we will add ours later from extraction logic)
            text = re.sub(r'#\w+', '', text)

            # Remove instruction-like fragments more aggressively
            # Remove standalone instruction words/phrases
            instruction_fragments = [
                r'\bwith\s+one\s+question\b',
                r'\bfollow\s+these\b',
                r'\bcontinue\s+with\b',
                r'\buntil\s+complete\b',
                r'\bbe\s+clear\b',
            ]
            for pattern in instruction_fragments:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)
            
            # Remove tiny stray fragments like "ds" (but preserve common short words)
            # Only remove if it's not a common English word
            common_short_words = {'a', 'i', 'to', 'of', 'in', 'on', 'at', 'is', 'it', 'be', 'as', 'an', 'or', 'if', 'do', 'we', 'he', 'so', 'up', 'go', 'no', 'me', 'my', 'us', 'am', 'ok'}
            words = text.split()
            filtered_words = [w for w in words if not (len(w) <= 2 and w.lower() not in common_short_words and w.islower())]
            text = ' '.join(filtered_words)

            # normalize whitespace/newlines
            text = re.sub(r'\n{3,}', '\n\n', text)
            text = re.sub(r'\s+', ' ', text).strip()
        # --- end PEFT cleanup ---
        
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

    def _enforce_one_question_and_length(self, body: str, platform: str) -> str:
        """
        Ensure body ends with exactly one question and meets length requirements.
        """
        # Extract clean body (removes footer/hashtags) using validation utils
        extracted = extract_body_result(body)
        body_clean = extracted.body

        # Use validation utility to ensure exactly one question at end
        body_clean = ensure_exactly_one_question_at_end(body_clean)

        # Enforce sentence count by platform
        sentences = split_sentences(body_clean)
        if platform in ("twitter", "x"):
            # Twitter: 1-2 sentences max
            if len(sentences) > 2:
                body_clean = " ".join(sentences[:1]).rstrip(".,!") + "?"
        elif platform == "linkedin":
            # LinkedIn: 6-10 sentences
            if len(sentences) > 10:
                body_clean = " ".join(sentences[:9]).rstrip(".,!") + "?"
            elif len(sentences) < 6:
                # Too short, but don't fail - just log
                logger.warning("LinkedIn post has only %d sentences (target: 6-10)", len(sentences))
        elif platform == "instagram":
            # Instagram: 2-5 paragraphs (roughly 2-5 sentences per paragraph)
            if len(sentences) > 25:
                body_clean = " ".join(sentences[:24]).rstrip(".,!") + "?"
        else:
            # Facebook: 4-6 sentences
            if len(sentences) > 6:
                body_clean = " ".join(sentences[:5]).rstrip(".,!") + "?"
            elif len(sentences) < 4:
                # Too short - regenerate
                raise ValueError(f"Body too short: {len(sentences)} sentences (need 4-6). Regenerate.")

        return body_clean.strip()

    def _append_footer(self, body: str, platform: str) -> str:
        """
        Append footer in code (never ask model to do it).
        """
        # Remove any existing footer if model accidentally added it
        if SIGNATURE in body:
            body = body.split(SIGNATURE)[0].strip()
        if INSIGHTS_LINE in body:
            body = body.split(INSIGHTS_LINE)[0].strip()

        # Append footer
        footer = f"\n\n{SIGNATURE}\n{INSIGHTS_LINE}"
        return body + footer

    def _ensure_hashtags(self, context: Dict[str, Any], platform: str) -> List[str]:
        """
        Generate/ensure hashtags in code.
        Uses domain from context or lens_plan, not trend data (fine-tuned model generates content itself).
        """
        hashtags = []
        
        # Try to get hashtags from context directly (not from trend)
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
            
            # Domain-based hashtags (aligned with trained domains)
            if "foreclosure" in domain:
                hashtags = ["#ForeclosureSupport", "#Homeowners", "#Housing", "#ProcessClarity", "#SystemDesign"]
            elif "assisted living" in domain or "assisted" in domain or "senior" in domain:
                hashtags = ["#AssistedLiving", "#Caregiving", "#SeniorCare", "#RealWorldAI", "#SystemDesign"]
            elif "trading" in domain or "futures" in domain:
                hashtags = ["#FuturesTrading", "#RiskManagement", "#TradingDiscipline", "#RealWorldAI", "#SystemDesign"]
            else:
                # Default hashtags (aligned with training data)
                hashtags = ["#RealWorldAI", "#SystemDesign", "#ProcessClarity", "#HousingStability"]

        # Platform-specific limits
        if platform in ("twitter", "x"):
            hashtags = hashtags[:2]  # Max 2 for Twitter
        elif platform == "linkedin":
            hashtags = hashtags[:5]  # Max 5 for LinkedIn
        elif platform == "instagram":
            hashtags = hashtags[:8]  # Max 8 for Instagram
        else:
            hashtags = hashtags[:3]  # Max 3 for Facebook

        # Ensure all have # prefix
        return [f"#{tag.lstrip('#')}" for tag in hashtags if tag]

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
