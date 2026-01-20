"""
Brand Guidelines Manager - Module for loading and managing brand guidelines.

Aligned to TRAINED domains:
- Assisted Living
- Foreclosures
- Trading Futures

Handles loading brand guidelines from JSON files and providing access to specific
guideline elements for content generation.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BrandGuidelinesManager")


DEFAULT_DOMAIN_VOICE: Dict[str, Dict[str, Any]] = {
    "Assisted Living": {
        "tone": "Warm, grounded, supportive, and community-oriented",
        "traits": [
            "Lead with clarity and calm reassurance",
            "Focus on families, caregivers, and practical next steps",
            "Use plain language (avoid clinical jargon unless necessary)",
            "Highlight dignity, safety, and quality of life",
            "No medical advice; encourage professional consultation when needed"
        ],
        "key_themes": [
            "Care options and support navigation",
            "Family decision-making under pressure",
            "Safety and compassionate routines",
            "Trust-building and transparency",
            "Empowerment through clear next steps"
        ]
    },
    "Foreclosures": {
        "tone": "Empathetic, steady, non-judgmental, and empowering",
        "traits": [
            "Acknowledge stress without fear-mongering",
            "Do NOT provide legal advice or specific legal strategy",
            "Focus on acceptance, uncertainty tolerance, and action orientation",
            "Use short, direct sentences that reduce overwhelm",
            "Offer service availability + next step without promising outcomes"
        ],
        "key_themes": [
            "Uncertainty tolerance enables action",
            "Staying grounded during pressure",
            "Organizing documents and timelines (non-advice framing)",
            "Exploring options with qualified professionals",
            "Empowerment and steadiness"
        ]
    },
    "Trading Futures": {
        "tone": "Analytical, risk-first, disciplined, and process-driven",
        "traits": [
            "Emphasize rules, risk management, and consistency",
            "Avoid profit promises or hype language",
            "Use correct trading terminology when it improves clarity",
            "Focus on process over outcomes",
            "Encourage journaling, backtesting, and controlled sizing"
        ],
        "key_themes": [
            "Risk management and preservation",
            "Consistency and rule adherence",
            "Execution quality and discipline",
            "Review loops (journal, stats, screenshots)",
            "Avoiding emotional decisions"
        ]
    },
    "General": {
        "tone": "Clear, practical, and grounded",
        "traits": [
            "Speak to real problems and real people",
            "Avoid exaggerated claims",
            "Keep it actionable and respectful"
        ],
        "key_themes": ["Clarity", "structure", "next steps"]
    }
}

DEFAULT_PLATFORM_GUIDELINES: Dict[str, Dict[str, Any]] = {
    "twitter": {
        "tone": "Brief, direct, and punchy",
        "hashtags": ["#AssistedLiving", "#ForeclosureSupport", "#FuturesTrading", "#RiskManagement"],
        "cta": "Invite a reply or simple engagement",
        "max_length": 280,
        "format": "Single post, 1-2 short sentences"
    },
    "instagram": {
        "tone": "Human, supportive, and story-driven",
        "hashtags": ["#AssistedLiving", "#Caregiving", "#Homeowners", "#TradingDiscipline"],
        "cta": "Encourage saves/shares and profile visits",
        "max_length": 2200,
        "format": "2-5 short paragraphs with line breaks"
    },
    "linkedin": {
        "tone": "Professional, structured, insight-focused",
        "hashtags": ["#AssistedLiving", "#Housing", "#FinancialWellness", "#Trading"],
        "cta": "Encourage thoughtful professional discussion",
        "max_length": 3000,
        "format": "6-10 sentences, 1-2 short paragraphs"
    },
    "facebook": {
        "tone": "Engaging, community-focused, accessible",
        "hashtags": ["#AssistedLiving", "#ForeclosureSupport", "#FuturesTrading", "#Clarity"],
        "cta": "Encourage comments and sharing",
        "focus": "Domain-first: speak to the lived situation, not trends",
        "max_length": 5000,
        "format": "4-6 sentences, ending with one question"
    }
}

DEFAULT_CONTENT_REQUIREMENTS: List[str] = [
    "Stay within the trained domains: Assisted Living, Foreclosures, or Trading Futures",
    "Do not give legal advice, financial advice, or medical advice",
    "Use calming, grounded language that reduces overwhelm",
    "Focus on acceptance + next-step orientation (clarity enables action)",
    "Avoid promises or guaranteed outcomes",
    "Use domain terminology only when it improves clarity",
    "End with an empowering line and brand footer when attribution is enabled"
]

DEFAULT_PROHIBITED_CONTENT: List[str] = [
    "Political statements",
    "Religious references",
    "Criticism of other brands or products",
    "Guaranteed outcomes or promises",
    "Fear-mongering",
    "Speculative claims about capabilities or results"
]


class BrandGuidelinesManager:
    """
    Manages brand guidelines for content generation.
    Loads guidelines from JSON files and provides access to specific elements.
    """

    def __init__(self, guidelines_path: Optional[str] = None):
        self.guidelines: Dict[str, Any] = {}
        if guidelines_path:
            ok = self.load_guidelines(guidelines_path)
            if not ok:
                self.guidelines = self._get_default_guidelines()
                logger.info("Falling back to default trained-domain guidelines (file load failed).")
        else:
            # CHANGE WITH EXPLANATION:
            # Default MUST reflect your training, otherwise the bot generates the wrong style/topics.
            self.guidelines = self._get_default_guidelines()
            logger.info("Using default trained-domain guidelines")

    def load_guidelines(self, guidelines_path: str) -> bool:
        try:
            if not os.path.exists(guidelines_path):
                logger.warning("Guidelines file not found: %s", guidelines_path)
                return False

            with open(guidelines_path, "r") as f:
                self.guidelines = json.load(f)

            logger.info("Successfully loaded brand guidelines from %s", guidelines_path)
            return True

        except json.JSONDecodeError:
            logger.error("Invalid JSON format in guidelines file: %s", guidelines_path)
            return False

        except Exception as e:
            logger.error("Error loading guidelines: %s", str(e))
            return False

    def _normalize_domain(self, domain: Optional[str]) -> str:
        if not domain:
            return "General"
        d = domain.strip().lower()
        aliases = {
            "assisted living": "Assisted Living",
            "assisted_living": "Assisted Living",
            "senior care": "Assisted Living",
            "foreclosure": "Foreclosures",
            "foreclosures": "Foreclosures",
            "trading": "Trading Futures",
            "futures": "Trading Futures",
            "futures trading": "Trading Futures",
            "trading futures": "Trading Futures",
        }
        # Return normalized title-cased fallback if not in aliases
        return aliases.get(d, d.title() if d else "General")

    # CHANGE WITH EXPLANATION:
    # Use a dict return type so downstream prompt builders can reliably reference tone/traits/themes.
    def get_brand_voice(self, domain: Optional[str] = None) -> Dict[str, Any]:
        dom = self._normalize_domain(domain)
        voice = (self.guidelines.get("voice") or {})
        if isinstance(voice, dict) and dom in voice:
            return voice[dom]
        # fallback to defaults
        return DEFAULT_DOMAIN_VOICE.get(dom, DEFAULT_DOMAIN_VOICE["General"])

    def get_content_requirements(self) -> List[str]:
        req = self.guidelines.get("content_requirements")
        if isinstance(req, list):
            return req
        return DEFAULT_CONTENT_REQUIREMENTS

    def get_prohibited_content(self) -> List[str]:
        pro = self.guidelines.get("prohibited_content") or self.guidelines.get("prohibited")
        if isinstance(pro, list):
            return pro
        return DEFAULT_PROHIBITED_CONTENT

    def get_visual_style(self) -> Dict[str, Any]:
        vs = self.guidelines.get("visual_style")
        if isinstance(vs, dict):
            return vs
        return {}

    def get_platform_specific_guidelines(self, platform: str) -> Dict[str, Any]:
        p = (platform or "").lower()
        file_platforms = self.guidelines.get("platforms", {})
        merged = dict(DEFAULT_PLATFORM_GUIDELINES.get(p, {}))
        if isinstance(file_platforms, dict) and isinstance(file_platforms.get(p), dict):
            merged.update(file_platforms[p])
        return merged

    def get_product_mention_requirements(self) -> Dict[str, Any]:
        pm = self.guidelines.get("product_mentions")
        if isinstance(pm, dict):
            return pm
        return {}

    def _get_default_guidelines(self) -> Dict[str, Any]:
        return {
            "brand_name": "Elevare by Amaziah",
            "attribution": {
                "enabled": True,
                "style": "subtle",
                "default_line": "- Elevare by Amaziah",
                "long_form": "Insights from Elevare by Amaziah, building real-world systems with AI."
            },
            "voice": DEFAULT_DOMAIN_VOICE,
            "content_requirements": DEFAULT_CONTENT_REQUIREMENTS,
            "prohibited_content": DEFAULT_PROHIBITED_CONTENT,
            "platforms": DEFAULT_PLATFORM_GUIDELINES,
            "visual_style": {},
            "product_mentions": {}
        }
