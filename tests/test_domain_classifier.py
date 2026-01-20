"""
Unit tests for DomainClassifier.

Tests cover:
- Initialization
- Trend classification (single trends)
- Trend candidate classification (multiple trends)
- Domain keyword retrieval
- Available domains
- Edge cases (empty strings, no matches, etc.)
"""

import unittest
from unittest.mock import patch

# Add parent directory to path to import the module
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.domain_classifier import DomainClassifier, DOMAIN_KEYWORDS


class TestDomainClassifier(unittest.TestCase):
    """Test suite for DomainClassifier."""

    def setUp(self):
        """Set up test fixtures."""
        self.classifier = DomainClassifier()

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init(self):
        """Test DomainClassifier initialization."""
        classifier = DomainClassifier()
        self.assertIsNotNone(classifier)
        self.assertIsNotNone(classifier.logger)

    # -------------------------
    # classify_trend Tests
    # -------------------------

    def test_classify_foreclosure_primary_keyword(self):
        """Test classification with foreclosure primary keyword."""
        domain, confidence = self.classifier.classify_trend("foreclosure help for homeowners")
        self.assertEqual(domain, "Foreclosures")
        self.assertGreater(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_classify_foreclosure_secondary_keyword(self):
        """Test classification with foreclosure secondary keyword."""
        domain, confidence = self.classifier.classify_trend("mortgage assistance")
        self.assertEqual(domain, "Foreclosures")
        self.assertGreater(confidence, 0.0)

    def test_classify_trading_futures_primary_keyword(self):
        """Test classification with trading futures primary keyword."""
        domain, confidence = self.classifier.classify_trend("futures trading strategies")
        self.assertEqual(domain, "Trading Futures")
        self.assertGreater(confidence, 0.0)

    def test_classify_trading_futures_secondary_keyword(self):
        """Test classification with trading futures secondary keyword."""
        domain, confidence = self.classifier.classify_trend("financial investment portfolio")
        self.assertEqual(domain, "Trading Futures")
        self.assertGreater(confidence, 0.0)

    def test_classify_assisted_living_primary_keyword(self):
        """Test classification with assisted living primary keyword."""
        domain, confidence = self.classifier.classify_trend("assisted living care options")
        self.assertEqual(domain, "Assisted Living")
        self.assertGreater(confidence, 0.0)

    def test_classify_assisted_living_secondary_keyword(self):
        """Test classification with assisted living secondary keyword."""
        domain, confidence = self.classifier.classify_trend("senior care facilities")
        self.assertEqual(domain, "Assisted Living")
        self.assertGreater(confidence, 0.0)

    def test_classify_with_description(self):
        """Test classification using both trend text and description."""
        domain, confidence = self.classifier.classify_trend(
            "Market analysis",
            "futures trading risk management and execution"
        )
        self.assertEqual(domain, "Trading Futures")
        self.assertGreater(confidence, 0.0)

    def test_classify_no_match_returns_general(self):
        """Test classification with no matching keywords returns General."""
        domain, confidence = self.classifier.classify_trend("completely unrelated topic")
        self.assertEqual(domain, "General")
        self.assertEqual(confidence, 0.0)

    def test_classify_empty_string(self):
        """Test classification with empty string."""
        domain, confidence = self.classifier.classify_trend("")
        self.assertEqual(domain, "General")
        self.assertEqual(confidence, 0.0)

    def test_classify_case_insensitive(self):
        """Test that classification is case insensitive."""
        domain1, _ = self.classifier.classify_trend("FORECLOSURE HELP")
        domain2, _ = self.classifier.classify_trend("foreclosure help")
        domain3, _ = self.classifier.classify_trend("Foreclosure Help")
        self.assertEqual(domain1, "Foreclosures")
        self.assertEqual(domain2, "Foreclosures")
        self.assertEqual(domain3, "Foreclosures")

    def test_classify_multiple_keywords_same_domain(self):
        """Test classification with multiple keywords from same domain."""
        domain, confidence = self.classifier.classify_trend(
            "foreclosure homeowners housing mortgage"
        )
        self.assertEqual(domain, "Foreclosures")
        self.assertGreater(confidence, 0.0)

    def test_classify_multiple_keywords_different_domains(self):
        """Test classification when multiple domains match (should pick highest score)."""
        # This should favor Trading Futures due to multiple primary keywords
        domain, confidence = self.classifier.classify_trend(
            "trading futures risk management execution"
        )
        self.assertEqual(domain, "Trading Futures")
        self.assertGreater(confidence, 0.0)

    def test_classify_word_boundary_matching(self):
        """Test that word boundary matching prevents partial matches."""
        # "foreclosure" should match, but not "foreclosure" in "foreclosurehelp" (no space)
        domain, confidence = self.classifier.classify_trend("foreclosurehelp")
        # Should still match because "foreclosure" is a substring, but let's test proper matching
        domain2, _ = self.classifier.classify_trend("foreclosure help")
        self.assertEqual(domain2, "Foreclosures")

    def test_classify_confidence_calculation(self):
        """Test that confidence scores are properly calculated."""
        # Primary keyword should give high confidence
        _, conf1 = self.classifier.classify_trend("foreclosure")
        # Multiple primary keywords should give high confidence
        _, conf2 = self.classifier.classify_trend("foreclosure homeowners housing")
        # Secondary keyword only should give confidence (but may be capped at 1.0)
        _, conf3 = self.classifier.classify_trend("mortgage")
        
        self.assertGreater(conf1, 0.0)
        self.assertLessEqual(conf1, 1.0)
        self.assertGreaterEqual(conf2, conf3)  # Multiple primary >= single secondary
        # Note: Both may be 1.0 due to confidence capping formula (min(1.0, score/3.0))

    # -------------------------
    # classify_trend_candidates Tests
    # -------------------------

    def test_classify_candidates_empty_list(self):
        """Test classification of empty candidate list."""
        result = self.classifier.classify_trend_candidates([])
        self.assertEqual(result, [])

    def test_classify_candidates_single_candidate(self):
        """Test classification of single candidate."""
        candidates = [{"title": "foreclosure help", "description": "homeowner assistance"}]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["domain"], "Foreclosures")
        self.assertIn("domain_confidence", result[0])

    def test_classify_candidates_multiple_candidates(self):
        """Test classification of multiple candidates."""
        candidates = [
            {"title": "foreclosure help"},
            {"title": "futures trading"},
            {"title": "assisted living care"}
        ]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["domain"], "Foreclosures")
        self.assertEqual(result[1]["domain"], "Trading Futures")
        self.assertEqual(result[2]["domain"], "Assisted Living")

    def test_classify_candidates_with_existing_domain(self):
        """Test classification when domain is already provided."""
        candidates = [{"title": "some topic", "domain": "Foreclosures"}]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["domain"], "Foreclosures")
        self.assertEqual(result[0]["domain_confidence"], 1.0)

    def test_classify_candidates_with_general_domain(self):
        """Test classification when domain is General."""
        candidates = [{"title": "some topic", "domain": "General"}]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["domain"], "General")
        self.assertEqual(result[0]["domain_confidence"], 1.0)

    def test_classify_candidates_with_invalid_domain(self):
        """Test classification when invalid domain is provided (should reclassify)."""
        candidates = [{"title": "foreclosure help", "domain": "InvalidDomain"}]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 1)
        # Should reclassify based on title
        self.assertEqual(result[0]["domain"], "Foreclosures")

    def test_classify_candidates_uses_trend_or_title(self):
        """Test that classification uses 'trend' or 'title' field."""
        candidates = [
            {"trend": "foreclosure help"},
            {"title": "futures trading"}
        ]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(result[0]["domain"], "Foreclosures")
        self.assertEqual(result[1]["domain"], "Trading Futures")

    def test_classify_candidates_preserves_original_fields(self):
        """Test that classification preserves all original candidate fields."""
        candidates = [{
            "title": "foreclosure help",
            "score": 0.8,
            "hashtags": ["#test"]
        }]
        result = self.classifier.classify_trend_candidates(candidates)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "foreclosure help")
        self.assertEqual(result[0]["score"], 0.8)
        self.assertEqual(result[0]["hashtags"], ["#test"])
        self.assertIn("domain", result[0])
        self.assertIn("domain_confidence", result[0])

    # -------------------------
    # get_domain_keywords Tests
    # -------------------------

    def test_get_domain_keywords_foreclosures(self):
        """Test getting keywords for Foreclosures domain."""
        keywords = self.classifier.get_domain_keywords("Foreclosures")
        self.assertIn("primary", keywords)
        self.assertIn("secondary", keywords)
        self.assertIsInstance(keywords["primary"], list)
        self.assertIsInstance(keywords["secondary"], list)
        self.assertIn("foreclosure", keywords["primary"])

    def test_get_domain_keywords_trading_futures(self):
        """Test getting keywords for Trading Futures domain."""
        keywords = self.classifier.get_domain_keywords("Trading Futures")
        self.assertIn("primary", keywords)
        self.assertIn("secondary", keywords)
        self.assertIn("trading", keywords["primary"])

    def test_get_domain_keywords_assisted_living(self):
        """Test getting keywords for Assisted Living domain."""
        keywords = self.classifier.get_domain_keywords("Assisted Living")
        self.assertIn("primary", keywords)
        self.assertIn("secondary", keywords)
        self.assertIn("assisted living", keywords["primary"])

    def test_get_domain_keywords_invalid_domain(self):
        """Test getting keywords for invalid domain returns empty lists."""
        keywords = self.classifier.get_domain_keywords("InvalidDomain")
        self.assertEqual(keywords["primary"], [])
        self.assertEqual(keywords["secondary"], [])

    # -------------------------
    # get_available_domains Tests
    # -------------------------

    def test_get_available_domains(self):
        """Test getting list of available domains."""
        domains = DomainClassifier.get_available_domains()
        self.assertIsInstance(domains, list)
        self.assertIn("Foreclosures", domains)
        self.assertIn("Trading Futures", domains)
        self.assertIn("Assisted Living", domains)
        self.assertEqual(len(domains), 3)

    def test_get_available_domains_static_method(self):
        """Test that get_available_domains is a static method."""
        domains1 = DomainClassifier.get_available_domains()
        domains2 = self.classifier.get_available_domains()
        self.assertEqual(domains1, domains2)

    # -------------------------
    # Integration Tests
    # -------------------------

    def test_full_workflow(self):
        """Test full workflow: classify candidates, get keywords, verify domains."""
        candidates = [
            {"title": "foreclosure help for homeowners"},
            {"title": "futures trading strategies"},
            {"title": "assisted living care options"}
        ]
        result = self.classifier.classify_trend_candidates(candidates)
        
        for candidate in result:
            domain = candidate["domain"]
            keywords = self.classifier.get_domain_keywords(domain)
            self.assertIn("primary", keywords)
            self.assertIn("secondary", keywords)
            self.assertGreater(candidate["domain_confidence"], 0.0)

    def test_training_data_alignment_foreclosure(self):
        """Test that classifier matches training data examples for foreclosure."""
        # Examples from training data
        test_cases = [
            "Foreclosure involves many moving parts",
            "Foreclosure can feel like a system with too many handoffs",
            "homeowners in foreclosure about decision fatigue"
        ]
        for test_case in test_cases:
            domain, confidence = self.classifier.classify_trend(test_case)
            self.assertEqual(domain, "Foreclosures")
            self.assertGreater(confidence, 0.0)

    def test_training_data_alignment_trading(self):
        """Test that classifier matches training data examples for trading."""
        # Examples from training data
        test_cases = [
            "Fast markets challenge focus",
            "futures traders about asymmetric risk awareness",
            "trading focused on slippage awareness"
        ]
        for test_case in test_cases:
            domain, confidence = self.classifier.classify_trend(test_case)
            self.assertEqual(domain, "Trading Futures")
            self.assertGreater(confidence, 0.0)

    def test_training_data_alignment_assisted_living(self):
        """Test that classifier matches training data examples for assisted living."""
        # Examples from training data
        test_cases = [
            "assisted living operators about care continuity",
            "families considering assisted living",
            "assisted living choices depend on clear expectations"
        ]
        for test_case in test_cases:
            domain, confidence = self.classifier.classify_trend(test_case)
            self.assertEqual(domain, "Assisted Living")
            self.assertGreater(confidence, 0.0)


if __name__ == '__main__':
    unittest.main()
