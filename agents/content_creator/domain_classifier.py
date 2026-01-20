"""
Domain Classifier - Maps content/context to specific domains for workflow skeleton matching.

This module analyzes content text and maps it to trained domains (Foreclosures, Trading Futures, Assisted Living)
so that the expert lens system can use the appropriate workflow skeleton.
Aligned with the actual trained model domains.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Domain keywords for classification
# ALIGNED WITH TRAINED DOMAINS: Foreclosures, Trading Futures, Assisted Living
DOMAIN_KEYWORDS = {
    "Foreclosures": {
        "primary": ["foreclosure", "foreclosures", "foreclosure help", "homeowner", "homeowners",
                   "housing", "mortgage", "real estate", "property", "home", "house",
                   "residence", "housing stability", "foreclosure support"],
        "secondary": ["rental", "lease", "tenant", "landlord", "brokerage", "homeowner support"]
    },
    "Trading Futures": {
        "primary": ["trading", "futures", "futures trading", "trading futures", "finance & trading",
                   "trading systems", "risk management", "execution", "slippage", "drawdown",
                   "journaling", "backtesting", "trading strategy", "prop firm", "order flow",
                   "dom", "trading discipline", "execution focus", "capital protection"],
        "secondary": ["finance", "financial", "investment", "portfolio", "options", "crypto", 
                     "forex", "stocks", "banking", "markets", "market"]
    },
    "Assisted Living": {
        "primary": ["assisted living", "assisted_living", "senior care", "care homes",
                   "resident matching", "care decisions", "care operations", "resident",
                   "caregiver", "caregiving", "families", "care options", "care models",
                   "care continuity", "medication management", "staff ratios", "facility visits"],
        "secondary": ["senior", "elder", "aging", "long term care", "long-term care", "ltc",
                     "nursing home", "memory care", "care environment"]
    },
}


class DomainClassifier:
    """
    Classifies content/context into domains based on keyword matching.
    
    Maps content text to trained domains (Foreclosures, Trading Futures, Assisted Living)
    aligned with the trained model domains. Used to select appropriate workflow skeletons.
    """
    
    def __init__(self):
        """Initialize the DomainClassifier."""
        self.logger = logging.getLogger(__name__)
    
    def classify(self, text: str, description: str = "") -> Tuple[str, float]:
        """
        Classify content into a domain based on text analysis.
        
        Args:
            text: The content title or main text
            description: Optional description for additional context
            
        Returns:
            Tuple of (domain_name, confidence_score)
            - domain_name: One of the trained domains (Foreclosures, Trading Futures, Assisted Living), or "General"
            - confidence_score: 0.0 to 1.0 indicating confidence in the classification
        """
        # Combine text for analysis
        combined_text = f"{text} {description}".lower()
        
        domain_scores = {}
        
        # Score each domain based on keyword matches
        for domain, keywords in DOMAIN_KEYWORDS.items():
            score = 0.0
            primary_matches = 0
            secondary_matches = 0
            
            # Check primary keywords (higher weight)
            for keyword in keywords["primary"]:
                # Use word boundary matching for better accuracy
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, combined_text))
                if matches > 0:
                    primary_matches += matches
                    score += matches * 3.0  # Primary keywords worth 3 points each
            
            # Check secondary keywords (lower weight)
            for keyword in keywords["secondary"]:
                pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                matches = len(re.findall(pattern, combined_text))
                if matches > 0:
                    secondary_matches += matches
                    score += matches * 1.0  # Secondary keywords worth 1 point each
            
            if score > 0:
                domain_scores[domain] = {
                    "score": score,
                    "primary_matches": primary_matches,
                    "secondary_matches": secondary_matches
                }
        
        # If no domain matched, return General
        if not domain_scores:
            self.logger.debug(f"No domain keywords matched for content: {text}")
            return ("General", 0.0)
        
        # Find domain with highest score
        best_domain = max(domain_scores.items(), key=lambda x: x[1]["score"])
        domain_name = best_domain[0]
        raw_score = best_domain[1]["score"]
        
        # Calculate confidence (normalize to 0.0-1.0)
        # Higher scores = higher confidence
        # Fix discontinuity: use continuous formula that ensures smooth transition
        # Scores < 3.0: secondary keywords only, map 0->0, 3.0->1.0
        # Scores >= 3.0: at least one primary keyword, maintain high confidence
        # Use single continuous formula: min(1.0, raw_score / 3.0)
        # This ensures: 0->0, 2.9->0.967, 3.0->1.0, 10.0->3.33->1.0 (capped)
        confidence = min(1.0, raw_score / 3.0)
        
        self.logger.info(f"Classified content '{text}' as '{domain_name}' (confidence: {confidence:.2f}, score: {raw_score})")
        
        return (domain_name, confidence)
    
    def classify_trend(self, trend_text: str, description: str = "") -> Tuple[str, float]:
        """
        Classify a trend into a domain (backward compatibility wrapper).
        
        DEPRECATED: Use classify() instead. This method is kept for backward compatibility.
        
        Args:
            trend_text: The content title or main text
            description: Optional description for additional context
            
        Returns:
            Tuple of (domain_name, confidence_score)
        """
        return self.classify(trend_text, description)
    
    def classify_candidates(
        self, 
        candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple content candidates and add domain information.
        
        Args:
            candidates: List of content dictionaries (may or may not have "domain" field)
            
        Returns:
            List of content dictionaries with "domain" and "domain_confidence" fields added
        """
        classified = []
        
        for candidate in candidates:
            # If domain is already provided, use it (but verify it's valid)
            # Still add domain_confidence for consistency with docstring contract
            candidate_domain = candidate.get("domain")
            if candidate_domain and (candidate_domain == "General" or candidate_domain in DOMAIN_KEYWORDS):
                # Ensure domain_confidence is present (use high confidence since domain was pre-provided)
                classified_candidate = {
                    **candidate,
                    "domain_confidence": candidate.get("domain_confidence", 1.0)
                }
                classified.append(classified_candidate)
                continue
            
            # Extract text for classification (from title, context, or lens_plan)
            text = candidate.get("title") or candidate.get("context") or ""
            description = candidate.get("description") or ""
            
            # Check lens_plan for additional context
            lens_plan = candidate.get("lens_plan") or {}
            if not text:
                text = lens_plan.get("title") or lens_plan.get("context") or ""
            if not description:
                description = lens_plan.get("description") or ""
            
            # Classify the content
            domain, confidence = self.classify(text, description)
            
            # Add domain information to candidate
            classified_candidate = {
                **candidate,
                "domain": domain,
                "domain_confidence": confidence
            }
            
            classified.append(classified_candidate)
        
        return classified
    
    def classify_trend_candidates(
        self, 
        trend_candidates: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Classify multiple trend candidates (backward compatibility wrapper).
        
        DEPRECATED: Use classify_candidates() instead. This method is kept for backward compatibility.
        
        Args:
            trend_candidates: List of content dictionaries (may or may not have "domain" field)
            
        Returns:
            List of content dictionaries with "domain" and "domain_confidence" fields added
        """
        return self.classify_candidates(trend_candidates)
    
    def get_domain_keywords(self, domain: str) -> Dict[str, List[str]]:
        """
        Get keywords for a specific domain.
        
        Args:
            domain: Domain name
            
        Returns:
            Dictionary with "primary" and "secondary" keyword lists
        """
        return DOMAIN_KEYWORDS.get(domain, {"primary": [], "secondary": []})
    
    @staticmethod
    def get_available_domains() -> List[str]:
        """
        Get list of available domains.
        
        Returns:
            List of domain names
        """
        return list(DOMAIN_KEYWORDS.keys())
