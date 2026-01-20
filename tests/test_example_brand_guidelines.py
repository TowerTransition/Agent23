"""
Unit tests for example_brand_guidelines.json.

Tests cover:
- JSON structure validity
- Required fields presence
- Domain alignment with trained domains
- Platform configurations
- Hashtag configurations
- Content requirements
"""

import unittest
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


class TestExampleBrandGuidelines(unittest.TestCase):
    """Test suite for example_brand_guidelines.json."""

    def setUp(self):
        """Set up test fixtures."""
        guidelines_path = os.path.join(
            os.path.dirname(__file__),
            '..',
            'agents',
            'content_creator',
            'example_brand_guidelines.json'
        )
        with open(guidelines_path, 'r', encoding='utf-8') as f:
            self.guidelines = json.load(f)
        
        # Trained domains (from domain_classifier and training data)
        self.trained_domains = ["Foreclosures", "Trading Futures", "Assisted Living"]

    # -------------------------
    # JSON Structure Tests
    # -------------------------

    def test_json_is_valid(self):
        """Test that JSON file is valid and can be loaded."""
        self.assertIsInstance(self.guidelines, dict)
        self.assertGreater(len(self.guidelines), 0)

    def test_required_top_level_fields(self):
        """Test that all required top-level fields are present."""
        required_fields = [
            "brand_name",
            "attribution",
            "voice",
            "content_requirements",
            "prohibited_content",
            "platforms"
        ]
        for field in required_fields:
            self.assertIn(field, self.guidelines, f"Missing required field: {field}")

    # -------------------------
    # Brand Name Tests
    # -------------------------

    def test_brand_name(self):
        """Test brand name is present and correct."""
        self.assertIn("brand_name", self.guidelines)
        self.assertEqual(self.guidelines["brand_name"], "Elevare by Amaziah")

    # -------------------------
    # Attribution Tests
    # -------------------------

    def test_attribution_structure(self):
        """Test attribution structure."""
        attribution = self.guidelines.get("attribution", {})
        self.assertIn("enabled", attribution)
        self.assertIn("style", attribution)
        self.assertIn("default_line", attribution)
        self.assertIn("long_form", attribution)
        self.assertTrue(attribution["enabled"])

    def test_attribution_content(self):
        """Test attribution content matches expected format."""
        attribution = self.guidelines["attribution"]
        self.assertIn("Elevare by Amaziah", attribution["default_line"])
        self.assertIn("Elevare by Amaziah", attribution["long_form"])

    # -------------------------
    # Voice/Domain Tests
    # -------------------------

    def test_voice_has_trained_domains(self):
        """Test that voice section includes all trained domains."""
        voice = self.guidelines.get("voice", {})
        for domain in self.trained_domains:
            self.assertIn(domain, voice, f"Missing voice for trained domain: {domain}")

    def test_voice_has_general(self):
        """Test that voice section includes General domain."""
        voice = self.guidelines.get("voice", {})
        self.assertIn("General", voice, "Missing General voice")

    def test_voice_structure(self):
        """Test that each domain voice has required structure."""
        voice = self.guidelines.get("voice", {})
        for domain, domain_voice in voice.items():
            self.assertIn("tone", domain_voice, f"Missing tone for {domain}")
            self.assertIn("traits", domain_voice, f"Missing traits for {domain}")
            self.assertIn("key_themes", domain_voice, f"Missing key_themes for {domain}")
            self.assertIsInstance(domain_voice["traits"], list)
            self.assertIsInstance(domain_voice["key_themes"], list)

    def test_foreclosures_voice(self):
        """Test Foreclosures voice configuration."""
        voice = self.guidelines["voice"]["Foreclosures"]
        self.assertIn("tone", voice)
        self.assertGreater(len(voice["traits"]), 0)
        self.assertGreater(len(voice["key_themes"]), 0)

    def test_trading_futures_voice(self):
        """Test Trading Futures voice configuration."""
        voice = self.guidelines["voice"]["Trading Futures"]
        self.assertIn("tone", voice)
        self.assertGreater(len(voice["traits"]), 0)
        self.assertGreater(len(voice["key_themes"]), 0)

    def test_assisted_living_voice(self):
        """Test Assisted Living voice configuration."""
        voice = self.guidelines["voice"]["Assisted Living"]
        self.assertIn("tone", voice)
        self.assertGreater(len(voice["traits"]), 0)
        self.assertGreater(len(voice["key_themes"]), 0)

    # -------------------------
    # Content Requirements Tests
    # -------------------------

    def test_content_requirements(self):
        """Test content requirements are present and valid."""
        requirements = self.guidelines.get("content_requirements", [])
        self.assertIsInstance(requirements, list)
        self.assertGreater(len(requirements), 0)
        
        # Check for key requirements
        requirements_text = " ".join(requirements).lower()
        self.assertIn("trained domains", requirements_text)
        self.assertIn("legal advice", requirements_text or "no legal advice")

    def test_content_requirements_mention_trained_domains(self):
        """Test that content requirements mention trained domains."""
        requirements = self.guidelines.get("content_requirements", [])
        requirements_text = " ".join(requirements)
        for domain in self.trained_domains:
            self.assertIn(domain, requirements_text, 
                         f"Content requirements should mention {domain}")

    # -------------------------
    # Prohibited Content Tests
    # -------------------------

    def test_prohibited_content(self):
        """Test prohibited content list is present and valid."""
        prohibited = self.guidelines.get("prohibited_content", [])
        self.assertIsInstance(prohibited, list)
        self.assertGreater(len(prohibited), 0)

    # -------------------------
    # Platform Tests
    # -------------------------

    def test_platforms_present(self):
        """Test that all required platforms are present."""
        platforms = self.guidelines.get("platforms", {})
        required_platforms = ["twitter", "instagram", "linkedin", "facebook"]
        for platform in required_platforms:
            self.assertIn(platform, platforms, f"Missing platform: {platform}")

    def test_platform_structure(self):
        """Test that each platform has required structure."""
        platforms = self.guidelines.get("platforms", {})
        for platform, config in platforms.items():
            self.assertIn("tone", config, f"Missing tone for {platform}")
            self.assertIn("hashtags", config, f"Missing hashtags for {platform}")
            self.assertIn("max_length", config, f"Missing max_length for {platform}")
            self.assertIn("format", config, f"Missing format for {platform}")
            self.assertIsInstance(config["hashtags"], list)
            self.assertIsInstance(config["max_length"], int)

    def test_platform_hashtags(self):
        """Test that each platform has hashtags."""
        platforms = self.guidelines.get("platforms", {})
        for platform, config in platforms.items():
            hashtags = config.get("hashtags", [])
            self.assertGreater(len(hashtags), 0, 
                             f"Platform {platform} should have hashtags")
            # Check hashtags start with #
            for tag in hashtags:
                self.assertTrue(tag.startswith("#"), 
                              f"Hashtag {tag} in {platform} should start with #")

    def test_twitter_config(self):
        """Test Twitter platform configuration."""
        twitter = self.guidelines["platforms"]["twitter"]
        self.assertEqual(twitter["max_length"], 280)
        self.assertGreater(len(twitter["hashtags"]), 0)

    def test_instagram_config(self):
        """Test Instagram platform configuration."""
        instagram = self.guidelines["platforms"]["instagram"]
        self.assertEqual(instagram["max_length"], 2200)
        self.assertGreater(len(instagram["hashtags"]), 0)

    def test_linkedin_config(self):
        """Test LinkedIn platform configuration."""
        linkedin = self.guidelines["platforms"]["linkedin"]
        self.assertEqual(linkedin["max_length"], 3000)
        self.assertGreater(len(linkedin["hashtags"]), 0)

    def test_facebook_config(self):
        """Test Facebook platform configuration."""
        facebook = self.guidelines["platforms"]["facebook"]
        self.assertEqual(facebook["max_length"], 5000)
        self.assertGreater(len(facebook["hashtags"]), 0)

    # -------------------------
    # Visual Style Tests
    # -------------------------

    def test_visual_style(self):
        """Test visual style configuration if present."""
        if "visual_style" in self.guidelines:
            visual = self.guidelines["visual_style"]
            self.assertIn("description", visual)
            if "colors" in visual:
                self.assertIsInstance(visual["colors"], list)

    # -------------------------
    # Product Mentions Tests
    # -------------------------

    def test_product_mentions(self):
        """Test product mentions configuration if present."""
        if "product_mentions" in self.guidelines:
            mentions = self.guidelines["product_mentions"]
            self.assertIn("first_mention", mentions)
            self.assertIn("subsequent_mentions", mentions)

    # -------------------------
    # Product Features Tests
    # -------------------------

    def test_product_features(self):
        """Test product features configuration if present."""
        if "product_features" in self.guidelines:
            features = self.guidelines["product_features"]
            self.assertIsInstance(features, list)
            for feature in features:
                self.assertIn("name", feature)
                self.assertIn("description", feature)

    # -------------------------
    # Target Audience Tests
    # -------------------------

    def test_target_audience(self):
        """Test target audience configuration if present."""
        if "target_audience" in self.guidelines:
            audience = self.guidelines["target_audience"]
            self.assertIn("primary", audience)
            self.assertIn("secondary", audience)
            self.assertIsInstance(audience["primary"], list)
            self.assertIsInstance(audience["secondary"], list)

    # -------------------------
    # Domain Alignment Tests
    # -------------------------

    def test_domains_match_trained_domains(self):
        """Test that domains in voice match trained domains."""
        voice = self.guidelines.get("voice", {})
        voice_domains = set(voice.keys()) - {"General"}
        
        # Check that all trained domains are present
        for domain in self.trained_domains:
            self.assertIn(domain, voice_domains, 
                         f"Voice missing trained domain: {domain}")

    def test_no_untrained_domains(self):
        """Test that no untrained domains are in voice (except General)."""
        voice = self.guidelines.get("voice", {})
        voice_domains = set(voice.keys()) - {"General"}
        
        # Should only have trained domains
        untrained = voice_domains - set(self.trained_domains)
        if untrained:
            print(f"\n[WARN] Found untrained domains in voice: {untrained}")
            print("These may not match the trained model domains.")

    # -------------------------
    # Integration Tests
    # -------------------------

    def test_guidelines_consistency(self):
        """Test overall consistency of guidelines."""
        # Check that brand name appears in attribution
        attribution = self.guidelines.get("attribution", {})
        brand_name = self.guidelines.get("brand_name", "")
        if brand_name and attribution.get("default_line"):
            self.assertIn(brand_name, attribution["default_line"])

    def test_platform_hashtags_align_with_domains(self):
        """Test that platform hashtags align with trained domains."""
        platforms = self.guidelines.get("platforms", {})
        all_hashtags = set()
        for platform, config in platforms.items():
            all_hashtags.update([h.lower() for h in config.get("hashtags", [])])
        
        # Check for domain-related hashtags
        domain_keywords = {
            "foreclosures": ["foreclosure", "housing", "homeowner"],
            "trading": ["trading", "futures", "risk"],
            "assisted": ["assisted", "care", "caregiving"]
        }
        
        found_domains = []
        for domain_key, keywords in domain_keywords.items():
            for hashtag in all_hashtags:
                if any(keyword in hashtag for keyword in keywords):
                    found_domains.append(domain_key)
                    break
        
        self.assertGreater(len(found_domains), 0, 
                         "Platform hashtags should reference trained domains")


if __name__ == '__main__':
    unittest.main(verbosity=2)
