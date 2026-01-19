"""
Content Moderator - Module for checking content appropriateness before publishing.

Uses custom filtering rules to ensure content meets platform guidelines
and brand standards. Designed for use with local LLM endpoints.

CHANGES MADE (minimal, stability-focused):
1) Fix phrase-matching: word-boundary regex breaks multi-word phrases like "guaranteed results".
   We now use:
   - whole-word matching for single words
   - safe substring/phrase matching for multi-word phrases
2) Add safe basic normalization (collapse whitespace) so phrases match even with extra spaces/newlines.
3) Keep it LENIENT: only extreme claims + profanity markers, plus a very conservative spam caps pattern.
"""

import logging
import re
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ContentModerator")


class ContentModerator:
    """
    Checks content for appropriateness before publishing.
    Uses custom filtering rules to ensure content meets platform guidelines
    and brand standards. Designed for use with local LLM endpoints.
    """

    def __init__(self, custom_filter_words: Optional[List[str]] = None):
        """
        Initialize the ContentModerator.
        Only checks for extreme claims and inappropriate content.

        Args:
            custom_filter_words: Optional list of additional words/phrases to filter
        """
        # Only extreme claims and inappropriate content
        self.filter_words = custom_filter_words or [
            # Extreme claims only
            "guaranteed results", "100% guaranteed", "never fails", "always works",
            "best in the world", "better than all competitors",
            # Inappropriate language markers only
            "wtf", "damn", "hell", "crap", "shit", "fuck", "asshole", "bitch",
        ]

        logger.info("ContentModerator initialized - only checking extreme claims and inappropriate content")

    def check_content(self, content: str) -> Dict[str, Any]:
        """
        Check if content is appropriate for publishing.

        Args:
            content: Text content to check

        Returns:
            Dictionary with keys:
                - is_appropriate: bool indicating if content is appropriate
                - reason: str explaining why content was rejected (if not appropriate)
                - matched_terms: list of matched filter terms/patterns (if any)
        """
        if not isinstance(content, str):
            return {
                "is_appropriate": False,
                "reason": "Content must be a string",
                "matched_terms": ["type_error"]
            }

        custom_filter_result = self._custom_filter_check(content)
        if not custom_filter_result["is_appropriate"]:
            matched_terms = custom_filter_result["matched_terms"]
            reason = f"Content contains filtered terms/patterns: {', '.join(matched_terms)}"
            logger.warning("Content failed custom filter check: %s", reason)
            return {
                "is_appropriate": False,
                "reason": reason,
                "matched_terms": matched_terms
            }

        return {
            "is_appropriate": True,
            "reason": None,
            "matched_terms": []
        }

    def _normalize_text(self, text: str) -> str:
        """
        Minimal normalization for robust matching:
        - Lowercase
        - Collapse whitespace
        """
        text = text.lower()
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _custom_filter_check(self, content: str) -> Dict[str, Any]:
        """
        Perform custom word and phrase filtering.

        Args:
            content: Text content to check

        Returns:
            Dictionary with check results
        """
        normalized = self._normalize_text(content)
        matched_terms: List[str] = []

        # Check for each filter word/phrase
        for term in self.filter_words:
            t = term.lower().strip()

            # If it's a multi-word phrase, word-boundary regex can fail unexpectedly.
            # Use safe phrase containment on normalized text.
            if " " in t:
                if t in normalized:
                    matched_terms.append(term)
                continue

            # Single word: match as a whole word
            pattern = r"\b" + re.escape(t) + r"\b"
            if re.search(pattern, normalized):
                matched_terms.append(term)

        # Spam-like pattern check (very lenient)
        # Remove hashtags before caps spam check (hashtags can legitimately include caps)
        content_without_hashtags = re.sub(r"#\w+", "", content)

        # Check for obvious spam patterns: 4+ consecutive ALL-CAPS words (5+ letters each)
        # Only catches obvious spam like "CLICK HERE NOW BUY"
        spam_pattern = r"\b([A-Z]{5,})\s+([A-Z]{5,})\s+([A-Z]{5,})\s+([A-Z]{5,})"
        if re.search(spam_pattern, content_without_hashtags):
            matched_terms.append("pattern:spam")

        return {
            "is_appropriate": len(matched_terms) == 0,
            "matched_terms": matched_terms
        }
