"""
ContentCreatorAgent module for generating platform-specific social media content.

This module contains the ContentCreatorAgent class which handles the generation
of content for various social media platforms.

NOTE:
- This agent can still accept "trend_data" for backward compatibility, but it is
  treated as general topic/context input (not necessarily "trending").
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from .text_generator import TextGenerator
from .image_generator import ImageGenerator
from .platform_formatter import PlatformFormatter
from .content_moderator import ContentModerator
from .expert_lens_manager import ExpertLensManager
from .domain_classifier import DomainClassifier


class ContentCreatorAgent:
    """
    Agent for creating platform-specific social media content.

    This agent generates content for various social media platforms using a text generator
    (and optional image generator) while ensuring content adheres to platform constraints.

    Changes made:
    1) Default `use_expert_lens` is now False for determinism/stability.
    2) PEFT domain mapping is tightened: healthcare ≠ assisted living (only LTC/senior-care maps).
    3) Trend rewriting is disabled by default; opt-in via env var ENABLE_TREND_REWRITE=1.
    """

    def __init__(
        self,
        brand_guidelines_path: str = None,
        llm_api_key: str = None,
        stability_api_key: str = None,
        image_generation_enabled: bool = True,
        custom_filter_words: List[str] = None,
        cache_dir: str = "cache"
    ):
        self.logger = logging.getLogger(__name__)

        # Set API keys
        self.llm_api_key = llm_api_key or os.environ.get("LOCAL_LLM_API_KEY")
        self.stability_api_key = stability_api_key or os.environ.get("STABILITY_API_KEY")

        # Initialize components
        peft_adapter_path = os.environ.get("PEFT_ADAPTER_PATH")

        # Only require LOCAL_LLM_ENDPOINT if PEFT adapter is not available
        local_llm_endpoint = None
        if not peft_adapter_path:
            local_llm_endpoint = os.environ.get("LOCAL_LLM_ENDPOINT")
            if not local_llm_endpoint:
                allow_default = os.environ.get("ALLOW_DEFAULT_LLM_ENDPOINT", "").lower() in ("true", "1", "yes")
                if allow_default:
                    default_endpoint = "http://localhost:11434/v1/chat/completions"
                    self.logger.warning("LOCAL_LLM_ENDPOINT not found. Using default endpoint: %s", default_endpoint)
                    self.logger.info("To disable default endpoint behavior, unset ALLOW_DEFAULT_LLM_ENDPOINT")
                    local_llm_endpoint = default_endpoint
                else:
                    raise ValueError(
                        "LOCAL_LLM_ENDPOINT or PEFT_ADAPTER_PATH environment variable is required. "
                        "Set LOCAL_LLM_ENDPOINT to your local LLM endpoint URL (e.g., http://localhost:11434/v1/chat/completions), "
                        "or set PEFT_ADAPTER_PATH for direct model loading. "
                        "To allow default endpoint, set ALLOW_DEFAULT_LLM_ENDPOINT=true"
                    )
        else:
            self.logger.info("PEFT_ADAPTER_PATH detected. Will use direct model loading (offline mode)")

        self.text_generator = TextGenerator(
            brand_manager=None,  # No brand guidelines - model is pretrained
            api_key=self.llm_api_key,
            local_llm_endpoint=local_llm_endpoint
        )

        self.image_gen_enabled = image_generation_enabled

        if self.image_gen_enabled:
            if not self.stability_api_key:
                self.logger.warning("Image generation enabled but no Stability API key provided.")
                self.image_gen_enabled = False
            else:
                self.image_generator = ImageGenerator(
                    enabled=True,
                    output_dir=cache_dir if cache_dir else "generated_images"
                )

        # Initialize platform formatter (no brand guidelines - model is pretrained)
        self.platform_formatter = PlatformFormatter(brand_guidelines=None)

        # Initialize content moderator (will auto-detect local LLM usage)
        self.content_moderator = ContentModerator(custom_filter_words=custom_filter_words)

        # Store cache directory
        self.cache_dir = cache_dir

        # Create cache directory if it doesn't exist (before initializing ExpertLensManager)
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)

        # Initialize expert lens manager for autonomous lens selection
        state_path = os.path.join(cache_dir, "content_state.json") if cache_dir else "content_state.json"
        self.lens_manager = ExpertLensManager(state_path=state_path)

        # Initialize domain classifier to map topics to domains
        self.domain_classifier = DomainClassifier()

        # PEFT adapter trained domains (ONLY these three domains were trained)
        self.peft_trained_domains = ["FORECLOSURE", "TRADING", "ASSISTED_LIVING"]
        self.peft_adapter_path = os.environ.get("PEFT_ADAPTER_PATH")

    def generate_content_for_platform(
        self,
        platform: str,
        trend_data: Dict[str, Any],
        product_info: Optional[Dict[str, Any]] = None,
        use_expert_lens: bool = False,  # CHANGED: default False for determinism
        trend_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Generate content for a specific platform.
        Note: `trend_data` is treated as general topic/context input (backward compatible name).
        """
        self.logger.info(f"Generating content for {platform} about '{trend_data.get('title', 'unknown topic')}'")

        if platform not in ["twitter", "instagram", "linkedin", "facebook"]:
            self.logger.error(f"Unsupported platform: {platform}")
            return {"error": f"Unsupported platform: {platform}"}

        # Optional: expert lens plan
        lens_plan = None
        if use_expert_lens:
            try:
                if trend_candidates is None:
                    # Auto-classify if domain/category missing
                    if not trend_data.get("domain") and not trend_data.get("category"):
                        trend_text = trend_data.get("title", "")
                        description = trend_data.get("description", "")
                        domain, confidence = self.domain_classifier.classify(trend_text, description)
                        new_trend = trend_data.copy()
                        new_trend["domain"] = domain
                        new_trend["domain_confidence"] = confidence
                        trend_data = new_trend
                        self.logger.info(f"Auto-classified '{trend_text}' as domain '{domain}' (confidence: {confidence:.2f})")

                    # If using PEFT adapter, map domain (and optionally rewrite text) BEFORE prompt construction
                    if self.peft_adapter_path:
                        original_domain = trend_data.get("domain", "General")
                        original_title = trend_data.get("title", "")
                        mapped_domain, rewritten_title = self._map_domain_and_rewrite_trend(original_domain, original_title)

                        # Apply mapping (always). Apply rewriting only if it actually changed.
                        if mapped_domain != original_domain or rewritten_title != original_title:
                            trend_data = trend_data.copy()
                            trend_data["domain"] = mapped_domain
                            if rewritten_title != original_title:
                                trend_data["title"] = rewritten_title
                                self.logger.info(f"PEFT adapter: rewritten topic '{original_title}' -> '{rewritten_title}'")
                            self.logger.info(f"PEFT adapter: mapped domain '{original_domain}' -> '{mapped_domain}'")

                    trend_candidates = [{
                        "trend": trend_data.get("title", "Topic"),
                        "title": trend_data.get("title", "Topic"),
                        "description": trend_data.get("description", ""),
                        "domain": trend_data.get("domain", "General"),
                        "hashtags": trend_data.get("hashtags", []),
                        "score": trend_data.get("score", 0.8)
                    }]
                else:
                    trend_candidates = self.domain_classifier.classify_candidates(trend_candidates)

                    if self.peft_adapter_path:
                        # Make shallow copies to avoid mutating caller-owned dictionaries
                        updated_candidates = []
                        for candidate in trend_candidates:
                            new_candidate = candidate.copy()
                            original_domain = new_candidate.get("domain", "General")
                            original_title = new_candidate.get("title", "")
                            mapped_domain, rewritten_title = self._map_domain_and_rewrite_trend(original_domain, original_title)

                            if mapped_domain != original_domain:
                                new_candidate["domain"] = mapped_domain
                                self.logger.info(f"PEFT adapter: mapped candidate domain '{original_domain}' -> '{mapped_domain}'")
                            if rewritten_title != original_title:
                                new_candidate["title"] = rewritten_title
                                new_candidate["trend"] = rewritten_title
                                self.logger.info(f"PEFT adapter: rewritten candidate title '{original_title}' -> '{rewritten_title}'")
                            updated_candidates.append(new_candidate)
                        trend_candidates = updated_candidates

                lens_plan = self.lens_manager.pick_plan(candidates=trend_candidates, platform=platform)
                lens_domain = lens_plan.get("domain", trend_data.get("domain", "General"))
                # Use "title" (new) or "trend" (backward compatibility)
                lens_title = lens_plan.get("title") or lens_plan.get("trend") or trend_data.get("title", "")

                if self.peft_adapter_path:
                    original_lens_domain = lens_domain
                    original_lens_title = lens_title
                    lens_domain, rewritten_lens_title = self._map_domain_and_rewrite_trend(lens_domain, lens_title)

                    if lens_domain != original_lens_domain:
                        lens_plan["domain"] = lens_domain
                        self.logger.info(f"PEFT adapter: mapped lens domain '{original_lens_domain}' -> '{lens_domain}'")
                    if rewritten_lens_title != original_lens_title:
                        lens_plan["title"] = rewritten_lens_title
                        self.logger.info(f"PEFT adapter: rewritten lens title '{original_lens_title}' -> '{rewritten_lens_title}'")

                self.logger.info(
                    f"Selected lens: {lens_plan.get('lens')} for topic: {lens_title} (domain: {lens_plan.get('domain')})"
                )

                if lens_title != trend_data.get("title"):
                    trend_data = {
                        **trend_data,
                        "title": lens_title,
                        "description": lens_plan.get("description") or lens_plan.get("trend_description") or trend_data.get("description", ""),
                        "hashtags": lens_plan.get("hashtags", trend_data.get("hashtags", [])),
                        "domain": lens_domain
                    }

            except Exception as e:
                self.logger.warning(f"Error in expert lens selection: {e}. Continuing without lens system.")
                lens_plan = None

        # Prepare the context for text generation
        context = {
            "platform": platform,
            "trend": trend_data,
            "product_info": product_info or {},
            "timestamp": datetime.now().isoformat(),
            "lens_plan": lens_plan
        }

        # Generate text content
        try:
            text_content = self.text_generator.generate_text(
                context=context,
                platform=platform
            )
        except Exception as e:
            self.logger.error(f"Error generating text for {platform}: {str(e)}")
            return {"error": f"Text generation failed: {str(e)}"}

        # Extract the actual text content for moderation (handles both "text" and "caption" keys)
        content_to_check = text_content.get("text", "") or text_content.get("caption", "")
        if not content_to_check or not content_to_check.strip():
            self.logger.error(f"No text content found for {platform} - content generation failed")
            return {"error": "Content generation failed: No text content was generated"}

        moderation_result = self.content_moderator.check_content(content_to_check)

        if not isinstance(moderation_result, dict) or "is_appropriate" not in moderation_result:
            self.logger.error(f"Unexpected moderation result format: {moderation_result}")
            return {"error": "Content moderation check failed: Invalid moderation result format"}

        if not moderation_result.get("is_appropriate", True):
            reason = moderation_result.get("reason", "Unknown moderation issue")
            self.logger.warning(f"Content for {platform} flagged by moderation: {reason}")
            return {"error": f"Content moderation failed: {reason}"}

        # Format content for platform
        formatted_content = self.platform_formatter.format_for_platform(
            content=text_content,
            platform=platform
        )

        # Add hashtags from trend data
        hashtags = trend_data.get("hashtags", [])
        if hashtags:
            formatted_content["hashtags"] = hashtags

            if platform in ("twitter", "instagram"):
                hashtag_text = " ".join([f"#{tag}" for tag in hashtags])

                if platform == "twitter" and "text" in formatted_content:
                    formatted_content["text"] = formatted_content["text"] + "\n\n" + hashtag_text
                elif platform == "instagram" and "caption" in formatted_content:
                    formatted_content["caption"] = formatted_content["caption"] + "\n\n" + hashtag_text

        # Generate image if enabled
        if self.image_gen_enabled:
            try:
                image_prompt = self.text_generator.generate_image_prompt(
                    context=context,
                    platform=platform,
                    brand_guidelines={}
                )

                image_data = self.image_generator.generate_image(
                    prompt=image_prompt,
                    platform=platform,
                    trend_title=trend_data.get("title", "topic")
                )

                formatted_content["image"] = image_data

            except Exception as e:
                self.logger.error(f"Error generating image for {platform}: {str(e)}")
                formatted_content["image_error"] = str(e)

        return formatted_content

    def generate_multi_platform_content(
        self,
        trend_data: Dict[str, Any],
        platforms: Optional[List[str]] = None,
        product_info: Optional[Dict[str, Any]] = None,
        use_expert_lens: bool = False,  # CHANGED: default False for determinism
        trend_candidates: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Generate content for multiple platforms using expert lens system.
        """
        if platforms is None:
            platforms = ["twitter", "instagram", "linkedin"]

        self.logger.info(f"Generating content for {len(platforms)} platforms: {', '.join(platforms)}")

        results = {}
        for platform in platforms:
            results[platform] = self.generate_content_for_platform(
                platform=platform,
                trend_data=trend_data,
                product_info=product_info,
                use_expert_lens=use_expert_lens,
                trend_candidates=trend_candidates
            )

        return results

    def validate_trend_data(self, trend_data: Dict[str, Any]) -> bool:
        required_fields = ["title"]
        for field in required_fields:
            if field not in trend_data:
                self.logger.error(f"Missing required field in trend data: {field}")
                return False
        return True

    def _map_to_peft_domain(self, domain: str) -> str:
        """
        Map domain to one of the PEFT adapter trained domains.
        Returns one of: FORECLOSURE, TRADING, ASSISTED_LIVING
        """
        if not domain:
            return "TRADING"  # default (kept as-is to avoid breaking behavior)

        domain_upper = domain.upper()

        if domain_upper in self.peft_trained_domains:
            return domain_upper

        domain_lower = domain.lower()

        # CHANGED: Only long-term care / senior-care keywords map to ASSISTED_LIVING (healthcare ≠ assisted living)
        if any(keyword in domain_lower for keyword in [
            "assisted living", "senior", "elder", "aging", "caregiver", "caregiving",
            "memory care", "nursing home", "long term care", "long-term care", "ltc", "resident"
        ]):
            return "ASSISTED_LIVING"

        # Finance/Markets -> TRADING
        if any(keyword in domain_lower for keyword in [
            "finance", "trading", "market", "stock", "investment", "bank", "financial", "futures", "prop"
        ]):
            return "TRADING"

        # Housing/Mortgage -> FORECLOSURE
        if any(keyword in domain_lower for keyword in [
            "housing", "mortgage", "real estate", "property", "foreclosure", "home", "homeowner"
        ]):
            return "FORECLOSURE"

        return "TRADING"

    def _map_domain_and_rewrite_trend(self, trend_domain: str, trend_text: str) -> tuple[str, str]:
        """
        Map domain to PEFT trained domain and (optionally) rewrite trend text into domain vocabulary.

        CHANGED:
        - Domain mapping remains ON (needed for trained domain gating).
        - Text rewriting is OFF by default (ENABLE_TREND_REWRITE=1 to opt-in).
        """
        import re

        mapped_domain = self._map_to_peft_domain(trend_domain)
        rewritten_text = trend_text

        enable_rewrite = os.getenv("ENABLE_TREND_REWRITE", "0") == "1"
        if enable_rewrite:
            if mapped_domain == "ASSISTED_LIVING":
                rewritten_text = re.sub(r'\b(Healthcare|Medical|Health Care|healthcare|medical|health care)\b',
                                        'assisted living', rewritten_text, flags=re.I)
                rewritten_text = re.sub(r'\b(patient|patients|clinical|hospital|clinic|doctor|physician)\b',
                                        'resident', rewritten_text, flags=re.I)
                rewritten_text = re.sub(r'\b(treatment|therapy|diagnosis)\b',
                                        'care', rewritten_text, flags=re.I)

            elif mapped_domain == "TRADING":
                rewritten_text = re.sub(r'\b(finance|financial|banking|investment|investing)\b',
                                        'trading', rewritten_text, flags=re.I)

            elif mapped_domain == "FORECLOSURE":
                rewritten_text = re.sub(r'\b(housing|real estate|property|mortgage|homeowner|homeowners)\b',
                                        'foreclosure', rewritten_text, flags=re.I)
                rewritten_text = re.sub(r'\b(home|house|residence)\b',
                                        'property', rewritten_text, flags=re.I)

        if os.getenv("DEBUG_GENERATION", "0") == "1":
            if mapped_domain != (trend_domain or "").upper() or rewritten_text != trend_text:
                print(f"\n=== DOMAIN MAPPING ===")
                print(f"Original domain: {trend_domain}")
                print(f"Mapped domain: {mapped_domain}")
                print(f"Original topic:  {trend_text}")
                print(f"Rewritten topic: {rewritten_text}")
                print(f"=== END MAPPING ===\n")

        return mapped_domain, rewritten_text

    def save_content_to_file(
        self,
        content: Dict[str, Any],
        filename: str = None,
        output_dir: str = "output"
    ) -> str:
        os.makedirs(output_dir, exist_ok=True)

        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            platform = content.get("platform", "content")
            filename = f"{platform}_{timestamp}.json"

        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w') as f:
            json.dump(content, f, indent=2)

        self.logger.info(f"Content saved to {filepath}")
        return filepath
