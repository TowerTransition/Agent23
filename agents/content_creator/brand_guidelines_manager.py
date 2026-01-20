"""
Brand Guidelines Manager - Focused on TRAINED domains and platform guidelines.

This manager focuses on the key domains the bot was trained on:
- Assisted Living
- Foreclosures
- Trading Futures

Platform guidelines (Facebook, Twitter, Instagram, LinkedIn) are kept active.
Other guidelines remain dormant (not used in code).
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# CHANGE WITH EXPLANATION:
# These domain names must match the domains you trained on.
# Also include "aliases" (handled in get_brand_voice) so different input labels
# still map to the correct trained voice.
DOMAIN_BRAND_VOICE = {
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
            "Safety, routines, and compassionate care",
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
            "Offer service availability + next step (consultation / intake) without promising outcomes"
        ],
        "key_themes": [
            "Uncertainty tolerance enables action",
            "Staying grounded during pressure",
            "Organizing documents and timelines (non-advice framing)",
            "Exploring options with qualified professionals",
            "Empowerment and emotional steadiness"
        ]
    },
    "Trading Futures": {
        "tone": "Analytical, risk-first, disciplined, and process-driven",
        "traits": [
            "Emphasize rules, risk management, and consistency",
            "Avoid profit promises or hype language",
            "Use correct trading terminology (drawdown, R:R, execution, slippage) when needed",
            "Focus on process over outcomes",
            "Encourage journaling, backtesting, and controlled sizing"
        ],
        "key_themes": [
            "Risk management and preservation",
            "Consistency and rule adherence",
            "Execution quality and discipline",
            "Review loops (journal, stats, screenshots)",
            "Avoiding emotional decision-making"
        ]
    },
    "General": {
        "tone": "Clear, practical, and grounded",
        "traits": [
            "Speak to real problems and real people",
            "Avoid exaggerated claims",
            "Keep it actionable and respectful"
        ],
        "key_themes": [
            "Clarity, structure, next steps"
        ]
    }
}

# CHANGE WITH EXPLANATION:
# Keep these platform rules, but remove the default "AI trending topic" angle.
# Your bot is domain-trained; platform guidance should shape formatting, not topic selection.
PLATFORM_GUIDELINES = {
    "twitter": {
        "tone": "Brief, direct, and punchy",
        "hashtags": ["#AssistedLiving", "#ForeclosureHelp", "#FuturesTrading", "#RiskManagement"],
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

# CHANGE WITH EXPLANATION:
# These requirements should match your trained content style and reduce validation failures.
CONTENT_REQUIREMENTS = [
    "Stay within the trained domains: Assisted Living, Foreclosures, or Futures Trading",
    "Do not give legal advice, financial advice, or medical advice",
    "Use calming, grounded language that reduces overwhelm",
    "Focus on acceptance + next-step orientation (clarity enables action)",
    "Avoid promises or guaranteed outcomes",
    "Use domain terminology only when it improves clarity",
    "End with an empowering line and brand footer when attribution is enabled"
]

# Prohibited content (active)
PROHIBITED_CONTENT = [
    "Political statements",
    "Religious references",
    "Criticism of other brands or products",
    "Guaranteed outcomes (e.g., 'we will stop foreclosure')",
    "Overly technical jargon without explanation",
    "Fear-mongering",
    "Speculative claims about capabilities or results"
]


class BrandGuidelinesManager:
    """
    Manages brand guidelines focused on trained domains and platform guidelines.

    Active features:
    - Domain-specific brand voice (Assisted Living, Foreclosures, Trading Futures)
    - Platform guidelines (Facebook, Twitter, Instagram, LinkedIn)
    - Content requirements and prohibited content

    Dormant features (not used in code):
    - Visual style
    - Product features
    - Target audience
    - Product mentions
    """

    def __init__(self, guidelines_path: Optional[str] = None):
        """
        Initialize the BrandGuidelinesManager.

        Args:
            guidelines_path: Path to JSON file (optional - uses defaults if not provided)
        """
        self.logger = logging.getLogger(__name__)
        self.guidelines = None

        # Load guidelines if path is provided
        if guidelines_path:
            if not self.load_guidelines(guidelines_path):
                # Fall back to defaults if load failed
                self.guidelines = self._get_default_guidelines()
                self.logger.info("Failed to load guidelines from file, using default trained-domain brand guidelines")
        else:
            # Use default trained-domain guidelines
            self.guidelines = self._get_default_guidelines()
            self.logger.info("Using default trained-domain brand guidelines")

    def load_guidelines(self, guidelines_path: str) -> bool:
        """
        Load brand guidelines from a JSON file.

        Args:
            guidelines_path: Path to the JSON file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(guidelines_path):
                self.logger.warning("Guidelines file not found: %s", guidelines_path)
                return False

            with open(guidelines_path, 'r') as f:
                self.guidelines = json.load(f)

            self.logger.info("Successfully loaded brand guidelines from %s", guidelines_path)
            return True

        except json.JSONDecodeError:
            self.logger.error("Invalid JSON format in guidelines file: %s", guidelines_path)
            return False

        except Exception as e:
            self.logger.error("Error loading guidelines: %s", str(e))
            return False

    def get_guidelines(self) -> Dict[str, Any]:
        """
        Get the full brand guidelines.

        Returns:
            Dictionary containing all brand guidelines
        """
        if not self.guidelines:
            return self._get_default_guidelines()

        return self.guidelines

    # CHANGE WITH EXPLANATION:
    # Normalize domain inputs so upstream callers can pass variants and still hit trained voices.
    def _normalize_domain(self, domain: str) -> str:
        """
        Normalize domain name to match trained domain names.

        Args:
            domain: Domain name (may be variant/alias)

        Returns:
            Normalized domain name matching trained domains
        """
        if not domain:
            return "General"

        d = domain.strip().lower()

        aliases = {
            "assisted living": "Assisted Living",
            "assisted_living": "Assisted Living",
            "senior care": "Assisted Living",
            "care homes": "Assisted Living",
            "foreclosure": "Foreclosures",
            "foreclosures": "Foreclosures",
            "foreclosure help": "Foreclosures",
            "trading": "Trading Futures",
            "futures": "Trading Futures",
            "futures trading": "Trading Futures",
            "trading futures": "Trading Futures",
            "finance & trading": "Trading Futures",
        }

        return aliases.get(d, domain)

    def get_brand_voice(self, domain: Optional[str] = None) -> Dict[str, Any]:
        """
        Get brand voice guidelines for a specific domain.

        Args:
            domain: Domain name (Assisted Living, Foreclosures, Trading Futures)
                   If None, returns General brand voice
                   Accepts aliases which are normalized automatically

        Returns:
            Dictionary containing brand voice information for the domain
        """
        if not domain:
            domain = "General"

        # Normalize domain to handle aliases
        domain = self._normalize_domain(domain)

        # Get domain-specific voice or fallback to General
        domain_voice = DOMAIN_BRAND_VOICE.get(domain, DOMAIN_BRAND_VOICE["General"])

        # If guidelines loaded from file, merge with defaults
        if self.guidelines and "voice" in self.guidelines:
            file_voice = self.guidelines.get("voice", {})
            if isinstance(file_voice, dict) and domain in file_voice:
                # Merge file voice with defaults
                merged = domain_voice.copy()
                merged.update(file_voice[domain])
                return merged

        return domain_voice

    def get_content_requirements(self) -> List[str]:
        """
        Get the content requirements guidelines.

        Returns:
            List of content requirements
        """
        if self.guidelines and "content_requirements" in self.guidelines:
            return self.guidelines.get("content_requirements", CONTENT_REQUIREMENTS)

        return CONTENT_REQUIREMENTS

    def get_prohibited_content(self) -> List[str]:
        """
        Get the prohibited content guidelines.

        Returns:
            List of prohibited content types
        """
        if self.guidelines and "prohibited_content" in self.guidelines:
            return self.guidelines.get("prohibited_content", PROHIBITED_CONTENT)

        return PROHIBITED_CONTENT

    def get_platform_guidelines(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific guidelines (ACTIVE - used in code).

        Args:
            platform: Platform name (twitter, instagram, linkedin, facebook)

        Returns:
            Dictionary containing platform-specific guidelines
        """
        platform_key = platform.lower()

        # Get from file if loaded, otherwise use defaults
        if self.guidelines and "platforms" in self.guidelines:
            platforms = self.guidelines.get("platforms", {})
            file_platform = platforms.get(platform_key, {})
            # Merge with defaults
            default_platform = PLATFORM_GUIDELINES.get(platform_key, {})
            merged = default_platform.copy()
            merged.update(file_platform)
            return merged

        return PLATFORM_GUIDELINES.get(platform_key, {})

    def get_attribution(self) -> Dict[str, Any]:
        """
        Get attribution configuration (footer).

        Returns:
            Dictionary containing attribution settings
        """
        if self.guidelines and "attribution" in self.guidelines:
            return self.guidelines.get("attribution", {})

        return {
            "enabled": True,
            "style": "subtle",
            "default_line": "- Elevare by Amaziah",
            "long_form": "Insights from Elevare by Amaziah, building real-world systems with AI."
        }

    # DORMANT METHODS - These exist for backward compatibility but are not used in code
    # They return empty/default values to avoid breaking existing code

    def get_visual_style(self) -> Dict[str, Any]:
        """
        Get visual style guidelines (DORMANT - not used in code).

        Returns:
            Empty dict (dormant feature)
        """
        return {}

    def get_product_mentions(self) -> Dict[str, Any]:
        """
        Get product mention requirements (DORMANT - not used in code).

        Returns:
            Empty dict (dormant feature)
        """
        return {}

    def get_target_audience(self) -> Dict[str, Any]:
        """
        Get target audience information (DORMANT - not used in code).

        Returns:
            Empty dict (dormant feature)
        """
        return {}

    def get_product_features(self) -> List[Dict[str, Any]]:
        """
        Get product features information (DORMANT - not used in code).

        Returns:
            Empty list (dormant feature)
        """
        return []

    def _get_default_guidelines(self) -> Dict[str, Any]:
        """
        Create default brand guidelines focused on trained domains.

        Returns:
            Dictionary containing default guidelines
        """
        return {
            "brand_name": "Elevare by Amaziah",
            "attribution": {
                "enabled": True,
                "style": "subtle",
                "default_line": "- Elevare by Amaziah",
                "long_form": "Insights from Elevare by Amaziah, building real-world systems with AI."
            },
            "voice": DOMAIN_BRAND_VOICE,
            "content_requirements": CONTENT_REQUIREMENTS,
            "prohibited_content": PROHIBITED_CONTENT,
            "platforms": PLATFORM_GUIDELINES,
            # Dormant fields (not used in code, but kept for compatibility)
            "visual_style": {},
            "product_mentions": {},
            "target_audience": {},
            "product_features": []
        }
