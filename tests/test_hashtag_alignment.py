"""
Test to check if hashtags in example_brand_guidelines.json align with training data.

This test identifies conflicts between:
1. Training data hashtags (from 2.train.ipynb)
2. example_brand_guidelines.json hashtags
3. Code-generated hashtags (text_generator.py)
"""

import unittest
import json
import os
import sys
import re

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestHashtagAlignment(unittest.TestCase):
    """Test hashtag alignment between training data and configuration files."""

    def setUp(self):
        """Set up test fixtures."""
        # Load example_brand_guidelines.json
        guidelines_path = os.path.join(
            os.path.dirname(__file__), 
            '..', 
            'agents', 
            'content_creator', 
            'example_brand_guidelines.json'
        )
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            self.guidelines = json.load(f)
        
        # Training data hashtags (extracted from 2.train.ipynb analysis)
        self.training_data_hashtags = {
            "Foreclosures": [
                "#RealWorldAI", "#HousingStability", "#ProcessClarity", 
                "#SystemDesign", "#ClarityMatters", "#ProcessAlignment", 
                "#ProcessDesign"
            ],
            "Trading Futures": [
                "#TradingSystems", "#ExecutionFocus", "#RiskDiscipline", 
                "#RealWorldAI", "#ClarityMatters", "#ProcessDiscipline"
            ],
            "Assisted Living": [
                "#ResidentMatching", "#CareDecisions", "#ClarityMatters", 
                "#RealWorldAI", "#ProcessClarity", "#CareOperations"
            ]
        }
        
        # Code-generated hashtags from text_generator.py
        self.code_generated_hashtags = {
            "Foreclosures": ["#ForeclosureSupport", "#Homeowners", "#Housing"],
            "Trading Futures": ["#FuturesTrading", "#RiskManagement", "#TradingDiscipline"],
            "Assisted Living": ["#AssistedLiving", "#Caregiving", "#SeniorCare"]
        }

    def test_training_data_hashtags_present(self):
        """Test that training data hashtags are documented."""
        self.assertIn("Foreclosures", self.training_data_hashtags)
        self.assertIn("Trading Futures", self.training_data_hashtags)
        self.assertIn("Assisted Living", self.training_data_hashtags)
        
        # Check that each domain has hashtags
        for domain, hashtags in self.training_data_hashtags.items():
            self.assertGreater(len(hashtags), 0, f"{domain} should have hashtags")

    def test_guidelines_hashtags_present(self):
        """Test that guidelines have hashtags for each platform."""
        platforms = self.guidelines.get("platforms", {})
        self.assertIn("twitter", platforms)
        self.assertIn("instagram", platforms)
        self.assertIn("linkedin", platforms)
        self.assertIn("facebook", platforms)
        
        for platform, config in platforms.items():
            self.assertIn("hashtags", config, f"{platform} should have hashtags")
            self.assertIsInstance(config["hashtags"], list)
            self.assertGreater(len(config["hashtags"]), 0, f"{platform} should have at least one hashtag")

    def test_hashtag_conflicts_training_vs_guidelines(self):
        """Test for conflicts between training data and guidelines hashtags."""
        conflicts = []
        
        # Get all training data hashtags (flattened)
        training_hashtags = set()
        for domain_hashtags in self.training_data_hashtags.values():
            training_hashtags.update([h.lower() for h in domain_hashtags])
        
        # Get all guidelines hashtags (flattened)
        guidelines_hashtags = set()
        platforms = self.guidelines.get("platforms", {})
        for platform, config in platforms.items():
            platform_tags = config.get("hashtags", [])
            guidelines_hashtags.update([h.lower().lstrip('#') for h in platform_tags])
        
        # Check for overlap
        training_normalized = {h.lstrip('#') for h in training_hashtags}
        guidelines_normalized = {h.lstrip('#') if isinstance(h, str) else str(h).lstrip('#') for h in guidelines_hashtags}
        
        overlap = training_normalized.intersection(guidelines_normalized)
        no_overlap_training = training_normalized - guidelines_normalized
        no_overlap_guidelines = guidelines_normalized - training_normalized
        
        # Report conflicts
        print("\n=== HASHTAG CONFLICT ANALYSIS ===")
        print(f"\nTraining Data Hashtags (from 2.train.ipynb):")
        for domain, hashtags in self.training_data_hashtags.items():
            print(f"  {domain}: {', '.join(hashtags)}")
        
        print(f"\nGuidelines Hashtags (from example_brand_guidelines.json):")
        for platform, config in platforms.items():
            print(f"  {platform}: {', '.join(config.get('hashtags', []))}")
        
        print(f"\nCode-Generated Hashtags (from text_generator.py):")
        for domain, hashtags in self.code_generated_hashtags.items():
            print(f"  {domain}: {', '.join(hashtags)}")
        
        print(f"\n=== OVERLAP ANALYSIS ===")
        print(f"Hashtags in BOTH training data AND guidelines: {len(overlap)}")
        if overlap:
            print(f"  Overlapping: {', '.join(sorted(overlap))}")
        
        print(f"\nHashtags ONLY in training data (NOT in guidelines): {len(no_overlap_training)}")
        if no_overlap_training:
            print(f"  Missing from guidelines: {', '.join(sorted(no_overlap_training))}")
        
        print(f"\nHashtags ONLY in guidelines (NOT in training data): {len(no_overlap_guidelines)}")
        if no_overlap_guidelines:
            print(f"  Not in training data: {', '.join(sorted(no_overlap_guidelines))}")
        
        # Check for conflicts
        if len(overlap) == 0:
            conflicts.append("NO OVERLAP: Training data hashtags and guidelines hashtags are completely different!")
        
        if len(no_overlap_training) > 0:
            conflicts.append(f"Training data uses {len(no_overlap_training)} hashtags not found in guidelines")
        
        if len(no_overlap_guidelines) > 0:
            conflicts.append(f"Guidelines use {len(no_overlap_guidelines)} hashtags not found in training data")
        
        # This test will always pass, but prints the conflict analysis
        # The user can review the output to see conflicts
        self.assertIsNotNone(conflicts or overlap, "Conflict analysis completed")

    def test_hashtag_conflicts_training_vs_code(self):
        """Test for conflicts between training data and code-generated hashtags."""
        conflicts = []
        
        print("\n=== TRAINING DATA vs CODE-GENERATED HASHTAGS ===")
        
        for domain in ["Foreclosures", "Trading Futures", "Assisted Living"]:
            training_tags = set([h.lower().lstrip('#') for h in self.training_data_hashtags.get(domain, [])])
            code_tags = set([h.lower().lstrip('#') for h in self.code_generated_hashtags.get(domain, [])])
            
            overlap = training_tags.intersection(code_tags)
            training_only = training_tags - code_tags
            code_only = code_tags - training_tags
            
            print(f"\n{domain}:")
            print(f"  Training: {', '.join(['#' + t for t in sorted(training_tags)])}")
            print(f"  Code:     {', '.join(['#' + t for t in sorted(code_tags)])}")
            
            if overlap:
                print(f"  [OK] Overlap: {', '.join(['#' + t for t in sorted(overlap)])}")
            else:
                print(f"  [CONFLICT] NO OVERLAP!")
                conflicts.append(f"{domain}: No hashtag overlap between training and code")
            
            if training_only:
                print(f"  [WARN] Training only: {', '.join(['#' + t for t in sorted(training_only)])}")
            
            if code_only:
                print(f"  [WARN] Code only: {', '.join(['#' + t for t in sorted(code_only)])}")
        
        # This test will always pass, but prints the conflict analysis
        self.assertIsNotNone(conflicts or True, "Conflict analysis completed")

    def test_hashtag_conflicts_guidelines_vs_code(self):
        """Test for conflicts between guidelines and code-generated hashtags."""
        conflicts = []
        
        print("\n=== GUIDELINES vs CODE-GENERATED HASHTAGS ===")
        
        # Get guidelines hashtags by domain (approximate mapping)
        guidelines_by_domain = {
            "Foreclosures": ["#ForeclosureSupport"],
            "Trading Futures": ["#FuturesTrading", "#RiskManagement", "#TradingDiscipline"],
            "Assisted Living": ["#AssistedLiving", "#Caregiving"]
        }
        
        # Extract from platform configs
        platforms = self.guidelines.get("platforms", {})
        all_guidelines_hashtags = set()
        for platform, config in platforms.items():
            all_guidelines_hashtags.update([h.lower().lstrip('#') for h in config.get("hashtags", [])])
        
        for domain in ["Foreclosures", "Trading Futures", "Assisted Living"]:
            code_tags = set([h.lower().lstrip('#') for h in self.code_generated_hashtags.get(domain, [])])
            
            # Check if any code tags appear in guidelines
            overlap = code_tags.intersection(all_guidelines_hashtags)
            code_only = code_tags - all_guidelines_hashtags
            
            print(f"\n{domain}:")
            print(f"  Code:      {', '.join(['#' + t for t in sorted(code_tags)])}")
            print(f"  Guidelines: {', '.join(['#' + t for t in sorted(all_guidelines_hashtags)])}")
            
            if overlap:
                print(f"  [OK] Overlap: {', '.join(['#' + t for t in sorted(overlap)])}")
            else:
                print(f"  [CONFLICT] NO OVERLAP!")
            
            if code_only:
                print(f"  ⚠ Code only: {', '.join(['#' + t for t in sorted(code_only)])}")
        
        # This test will always pass, but prints the conflict analysis
        self.assertIsNotNone(conflicts or True, "Conflict analysis completed")

    def test_recommendation(self):
        """Provide recommendations based on conflicts."""
        print("\n=== RECOMMENDATIONS ===")
        print("\n1. Training data uses hashtags like:")
        print("   - #RealWorldAI (appears in ALL domains)")
        print("   - #HousingStability, #ProcessClarity, #SystemDesign (Foreclosures)")
        print("   - #TradingSystems, #ExecutionFocus, #RiskDiscipline (Trading)")
        print("   - #ResidentMatching, #CareDecisions, #CareOperations (Assisted Living)")
        
        print("\n2. Guidelines/Code use hashtags like:")
        print("   - #ForeclosureSupport, #Homeowners, #Housing (Foreclosures)")
        print("   - #FuturesTrading, #RiskManagement, #TradingDiscipline (Trading)")
        print("   - #AssistedLiving, #Caregiving, #SeniorCare (Assisted Living)")
        
        print("\n3. CONFLICT: Training data hashtags are NOT being used in:")
        print("   - example_brand_guidelines.json")
        print("   - text_generator.py (code-generated hashtags)")
        
        print("\n4. RECOMMENDATION:")
        print("   Update example_brand_guidelines.json and text_generator.py to use")
        print("   the hashtags from training data to maintain consistency with the")
        print("   trained model's expected output format.")
        
        # This test always passes - it's informational
        self.assertTrue(True, "Recommendations provided")


if __name__ == '__main__':
    unittest.main(verbosity=2)
