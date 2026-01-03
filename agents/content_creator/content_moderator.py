"""
Content Moderator - Module for checking content appropriateness before publishing.

Uses custom filtering rules to ensure content meets platform guidelines 
and brand standards. Designed for use with local LLM endpoints.
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
        
        Args:
            custom_filter_words: Optional list of additional words to filter
        """
        # Default list of potentially problematic terms for educational/science content
        self.filter_words = custom_filter_words or [
            # Political terms
            "liberal", "conservative", "republican", "democrat", "leftist", "rightist",
            # Religious terms
            "god", "allah", "jesus", "buddha", "hindu", "christian", "muslim", "jewish",
            # Potentially problematic product terms
            "better than competitors", "best in the world", "guaranteed results",
            # Extreme claims
            "proven", "revolutionary", "groundbreaking", "never before seen",
            # Inappropriate language markers
            "wtf", "damn", "hell", "crap",
        ]
        
        logger.info("ContentModerator initialized with %d filter words (using custom filters only)", 
                   len(self.filter_words))
    
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
        # Run custom filter check
        custom_filter_result = self._custom_filter_check(content)
        if not custom_filter_result["appropriate"]:
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
    
    def _custom_filter_check(self, content: str) -> Dict[str, Any]:
        """
        Perform custom word and phrase filtering.
        
        Args:
            content: Text content to check
            
        Returns:
            Dictionary with check results
        """
        content_lower = content.lower()
        matched_terms = []
        
        # Check for each filter word
        for word in self.filter_words:
            # Use word boundary to match whole words only
            pattern = r'\b' + re.escape(word.lower()) + r'\b'
            if re.search(pattern, content_lower):
                matched_terms.append(word)
        
        # Check for inappropriate patterns
        patterns = {
            "excessive_caps": r'([A-Z]{4,})',  # 4+ capital letters in a row
            "excessive_exclamation": r'(!{3,})',  # 3+ exclamation marks
            "clickbait": r'\b(you won\'t believe|mind blown|shocking|amazing)\b',
            "unprofessional": r'\b(lol|omg|wtf|lmao|rofl)\b'
        }
        
        for name, pattern in patterns.items():
            if re.search(pattern, content, re.IGNORECASE):
                matched_terms.append(f"pattern:{name}")
        
        return {
            "appropriate": len(matched_terms) == 0,
            "matched_terms": matched_terms
        } 