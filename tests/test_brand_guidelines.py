"""
Unit tests for brand_guidelines.py (BrandGuidelinesManager).

Tests cover:
- Initialization (with/without file path)
- File loading (success, failure, invalid JSON)
- Domain normalization and aliases
- Brand voice retrieval
- Platform-specific guidelines
- Content requirements and prohibited content
- Visual style and product mentions
"""

import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import patch

# Add parent directory to path to import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.brand_guidelines import (
    BrandGuidelinesManager,
    DEFAULT_DOMAIN_VOICE,
    DEFAULT_PLATFORM_GUIDELINES,
    DEFAULT_CONTENT_REQUIREMENTS,
    DEFAULT_PROHIBITED_CONTENT
)


class TestBrandGuidelines(unittest.TestCase):
    """Test suite for brand_guidelines.py BrandGuidelinesManager."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        self.manager = None

    def tearDown(self):
        """Clean up after tests."""
        if self.manager:
            del self.manager
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # ==================== Initialization Tests ====================

    def test_init_without_path(self):
        """Test initialization without file path uses defaults."""
        manager = BrandGuidelinesManager()
        self.assertIsNotNone(manager.guidelines)
        self.assertEqual(manager.guidelines["brand_name"], "Elevare by Amaziah")
        self.assertIn("voice", manager.guidelines)
        self.assertIn("platforms", manager.guidelines)

    def test_init_with_valid_path(self):
        """Test initialization with valid file path."""
        test_file = os.path.join(self.test_dir, "test_guidelines.json")
        test_data = {
            "brand_name": "Test Brand",
            "attribution": {"enabled": True}
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        manager = BrandGuidelinesManager(guidelines_path=test_file)
        self.assertEqual(manager.guidelines["brand_name"], "Test Brand")

    def test_init_with_invalid_path_falls_back_to_defaults(self):
        """Test initialization with non-existent file falls back to defaults."""
        invalid_path = os.path.join(self.test_dir, "nonexistent.json")
        manager = BrandGuidelinesManager(guidelines_path=invalid_path)
        self.assertEqual(manager.guidelines["brand_name"], "Elevare by Amaziah")

    def test_init_with_invalid_json_falls_back_to_defaults(self):
        """Test initialization with invalid JSON falls back to defaults."""
        test_file = os.path.join(self.test_dir, "invalid.json")
        with open(test_file, 'w') as f:
            f.write("This is not valid JSON {")

        manager = BrandGuidelinesManager(guidelines_path=test_file)
        self.assertEqual(manager.guidelines["brand_name"], "Elevare by Amaziah")

    # ==================== File Loading Tests ====================

    def test_load_guidelines_success(self):
        """Test successful loading of guidelines from file."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {
            "brand_name": "Loaded Brand",
            "content_requirements": ["Requirement 1", "Requirement 2"]
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        result = manager.load_guidelines(test_file)
        self.assertTrue(result)
        self.assertEqual(manager.guidelines["brand_name"], "Loaded Brand")

    def test_load_guidelines_file_not_found(self):
        """Test loading guidelines when file doesn't exist."""
        manager = BrandGuidelinesManager()
        invalid_path = os.path.join(self.test_dir, "nonexistent.json")
        result = manager.load_guidelines(invalid_path)
        self.assertFalse(result)

    def test_load_guidelines_invalid_json(self):
        """Test loading guidelines with invalid JSON."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "invalid.json")
        with open(test_file, 'w') as f:
            f.write("Invalid JSON content {")

        result = manager.load_guidelines(test_file)
        self.assertFalse(result)

    def test_load_guidelines_exception_handling(self):
        """Test loading guidelines with general exception."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        
        with patch('builtins.open', side_effect=PermissionError("Permission denied")):
            result = manager.load_guidelines(test_file)
            self.assertFalse(result)

    # ==================== Domain Normalization Tests ====================

    def test_normalize_domain_assisted_living_aliases(self):
        """Test normalization of Assisted Living aliases."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain("assisted living"), "Assisted Living")
        self.assertEqual(manager._normalize_domain("assisted_living"), "Assisted Living")
        self.assertEqual(manager._normalize_domain("senior care"), "Assisted Living")

    def test_normalize_domain_foreclosures_aliases(self):
        """Test normalization of Foreclosures aliases."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain("foreclosure"), "Foreclosures")
        self.assertEqual(manager._normalize_domain("foreclosures"), "Foreclosures")

    def test_normalize_domain_trading_futures_aliases(self):
        """Test normalization of Trading Futures aliases."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain("trading"), "Trading Futures")
        self.assertEqual(manager._normalize_domain("futures"), "Trading Futures")
        self.assertEqual(manager._normalize_domain("futures trading"), "Trading Futures")
        self.assertEqual(manager._normalize_domain("trading futures"), "Trading Futures")

    def test_normalize_domain_none_or_empty(self):
        """Test normalization with None or empty string."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain(None), "General")
        self.assertEqual(manager._normalize_domain(""), "General")

    def test_normalize_domain_unknown_domain_uses_title_case(self):
        """Test normalization with unknown domain uses title case fallback."""
        manager = BrandGuidelinesManager()
        # This version uses .title() as fallback
        self.assertEqual(manager._normalize_domain("unknown domain"), "Unknown Domain")
        self.assertEqual(manager._normalize_domain("test case"), "Test Case")

    def test_normalize_domain_case_insensitive(self):
        """Test normalization is case insensitive."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain("ASSISTED LIVING"), "Assisted Living")
        self.assertEqual(manager._normalize_domain("Assisted Living"), "Assisted Living")

    def test_normalize_domain_strips_whitespace(self):
        """Test normalization strips whitespace."""
        manager = BrandGuidelinesManager()
        self.assertEqual(manager._normalize_domain("  assisted living  "), "Assisted Living")
        self.assertEqual(manager._normalize_domain("\tforeclosure\n"), "Foreclosures")

    # ==================== Brand Voice Tests ====================

    def test_get_brand_voice_assisted_living(self):
        """Test getting brand voice for Assisted Living."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("Assisted Living")
        self.assertIn("tone", voice)
        self.assertIn("traits", voice)
        self.assertIn("key_themes", voice)
        self.assertEqual(voice["tone"], "Warm, grounded, supportive, and community-oriented")

    def test_get_brand_voice_foreclosures(self):
        """Test getting brand voice for Foreclosures."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("Foreclosures")
        self.assertIn("tone", voice)
        self.assertEqual(voice["tone"], "Empathetic, steady, non-judgmental, and empowering")

    def test_get_brand_voice_trading_futures(self):
        """Test getting brand voice for Trading Futures."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("Trading Futures")
        self.assertIn("tone", voice)
        self.assertEqual(voice["tone"], "Analytical, risk-first, disciplined, and process-driven")

    def test_get_brand_voice_general(self):
        """Test getting brand voice for General domain."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("General")
        self.assertIn("tone", voice)
        self.assertEqual(voice["tone"], "Clear, practical, and grounded")

    def test_get_brand_voice_none_returns_general(self):
        """Test getting brand voice with None returns General."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice(None)
        self.assertEqual(voice["tone"], "Clear, practical, and grounded")

    def test_get_brand_voice_with_alias(self):
        """Test getting brand voice with alias."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("assisted living")
        self.assertEqual(voice["tone"], "Warm, grounded, supportive, and community-oriented")

    def test_get_brand_voice_unknown_domain_falls_back_to_general(self):
        """Test getting brand voice for unknown domain falls back to General."""
        manager = BrandGuidelinesManager()
        voice = manager.get_brand_voice("Unknown Domain")
        self.assertEqual(voice["tone"], "Clear, practical, and grounded")

    def test_get_brand_voice_from_file_guidelines(self):
        """Test brand voice from file guidelines."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {
            "voice": {
                "Assisted Living": {
                    "tone": "Custom Tone",
                    "traits": ["Custom trait"]
                }
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        voice = manager.get_brand_voice("Assisted Living")
        self.assertEqual(voice["tone"], "Custom Tone")
        self.assertEqual(voice["traits"], ["Custom trait"])

    # ==================== Content Requirements Tests ====================

    def test_get_content_requirements_default(self):
        """Test getting default content requirements."""
        manager = BrandGuidelinesManager()
        requirements = manager.get_content_requirements()
        self.assertIsInstance(requirements, list)
        self.assertGreater(len(requirements), 0)
        self.assertEqual(requirements, DEFAULT_CONTENT_REQUIREMENTS)

    def test_get_content_requirements_from_file(self):
        """Test getting content requirements from file."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        custom_requirements = ["Custom requirement 1", "Custom requirement 2"]
        test_data = {"content_requirements": custom_requirements}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        requirements = manager.get_content_requirements()
        self.assertEqual(requirements, custom_requirements)

    def test_get_content_requirements_invalid_type_returns_default(self):
        """Test getting content requirements with invalid type returns default."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {"content_requirements": "not a list"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        requirements = manager.get_content_requirements()
        self.assertEqual(requirements, DEFAULT_CONTENT_REQUIREMENTS)

    # ==================== Prohibited Content Tests ====================

    def test_get_prohibited_content_default(self):
        """Test getting default prohibited content."""
        manager = BrandGuidelinesManager()
        prohibited = manager.get_prohibited_content()
        self.assertIsInstance(prohibited, list)
        self.assertGreater(len(prohibited), 0)
        self.assertEqual(prohibited, DEFAULT_PROHIBITED_CONTENT)

    def test_get_prohibited_content_from_file(self):
        """Test getting prohibited content from file."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        custom_prohibited = ["Custom prohibited 1", "Custom prohibited 2"]
        test_data = {"prohibited_content": custom_prohibited}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        prohibited = manager.get_prohibited_content()
        self.assertEqual(prohibited, custom_prohibited)

    def test_get_prohibited_content_uses_prohibited_key(self):
        """Test getting prohibited content uses 'prohibited' key as fallback."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        custom_prohibited = ["Using prohibited key"]
        test_data = {"prohibited": custom_prohibited}  # Note: "prohibited" not "prohibited_content"
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        prohibited = manager.get_prohibited_content()
        self.assertEqual(prohibited, custom_prohibited)

    def test_get_prohibited_content_invalid_type_returns_default(self):
        """Test getting prohibited content with invalid type returns default."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {"prohibited_content": "not a list"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        prohibited = manager.get_prohibited_content()
        self.assertEqual(prohibited, DEFAULT_PROHIBITED_CONTENT)

    # ==================== Platform Guidelines Tests ====================

    def test_get_platform_specific_guidelines_twitter(self):
        """Test getting Twitter platform guidelines."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines("twitter")
        self.assertIn("tone", guidelines)
        self.assertIn("max_length", guidelines)
        self.assertEqual(guidelines["max_length"], 280)

    def test_get_platform_specific_guidelines_instagram(self):
        """Test getting Instagram platform guidelines."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines("instagram")
        self.assertIn("tone", guidelines)
        self.assertEqual(guidelines["max_length"], 2200)

    def test_get_platform_specific_guidelines_linkedin(self):
        """Test getting LinkedIn platform guidelines."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines("linkedin")
        self.assertIn("tone", guidelines)
        self.assertEqual(guidelines["max_length"], 3000)

    def test_get_platform_specific_guidelines_facebook(self):
        """Test getting Facebook platform guidelines."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines("facebook")
        self.assertIn("tone", guidelines)
        self.assertEqual(guidelines["max_length"], 5000)

    def test_get_platform_specific_guidelines_case_insensitive(self):
        """Test platform guidelines are case insensitive."""
        manager = BrandGuidelinesManager()
        lower = manager.get_platform_specific_guidelines("twitter")
        upper = manager.get_platform_specific_guidelines("TWITTER")
        mixed = manager.get_platform_specific_guidelines("Twitter")
        self.assertEqual(lower, upper)
        self.assertEqual(lower, mixed)

    def test_get_platform_specific_guidelines_unknown_platform(self):
        """Test getting guidelines for unknown platform returns empty dict."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines("unknown_platform")
        self.assertEqual(guidelines, {})

    def test_get_platform_specific_guidelines_none_platform(self):
        """Test getting guidelines with None platform."""
        manager = BrandGuidelinesManager()
        guidelines = manager.get_platform_specific_guidelines(None)
        self.assertEqual(guidelines, {})

    def test_get_platform_specific_guidelines_merges_with_file(self):
        """Test platform guidelines merge with file guidelines."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {
            "platforms": {
                "twitter": {
                    "max_length": 500,
                    "new_field": "New Value"
                }
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        guidelines = manager.get_platform_specific_guidelines("twitter")
        self.assertEqual(guidelines["max_length"], 500)  # File overrides default
        self.assertIn("tone", guidelines)  # Default fields still present
        self.assertEqual(guidelines["new_field"], "New Value")  # New field added

    # ==================== Visual Style Tests ====================

    def test_get_visual_style_default_returns_empty_dict(self):
        """Test get_visual_style returns empty dict by default."""
        manager = BrandGuidelinesManager()
        result = manager.get_visual_style()
        self.assertEqual(result, {})

    def test_get_visual_style_from_file(self):
        """Test get_visual_style from file."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {
            "visual_style": {
                "colors": ["#FF0000", "#00FF00"],
                "description": "Test style"
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        result = manager.get_visual_style()
        self.assertEqual(result["colors"], ["#FF0000", "#00FF00"])
        self.assertEqual(result["description"], "Test style")

    def test_get_visual_style_invalid_type_returns_empty_dict(self):
        """Test get_visual_style with invalid type returns empty dict."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {"visual_style": "not a dict"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        result = manager.get_visual_style()
        self.assertEqual(result, {})

    # ==================== Product Mentions Tests ====================

    def test_get_product_mention_requirements_default_returns_empty_dict(self):
        """Test get_product_mention_requirements returns empty dict by default."""
        manager = BrandGuidelinesManager()
        result = manager.get_product_mention_requirements()
        self.assertEqual(result, {})

    def test_get_product_mention_requirements_from_file(self):
        """Test get_product_mention_requirements from file."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {
            "product_mentions": {
                "first_mention": "Test Product",
                "emphasis": "Test emphasis"
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        result = manager.get_product_mention_requirements()
        self.assertEqual(result["first_mention"], "Test Product")
        self.assertEqual(result["emphasis"], "Test emphasis")

    def test_get_product_mention_requirements_invalid_type_returns_empty_dict(self):
        """Test get_product_mention_requirements with invalid type returns empty dict."""
        manager = BrandGuidelinesManager()
        test_file = os.path.join(self.test_dir, "test.json")
        test_data = {"product_mentions": "not a dict"}
        with open(test_file, 'w') as f:
            json.dump(test_data, f)
        manager.load_guidelines(test_file)

        result = manager.get_product_mention_requirements()
        self.assertEqual(result, {})

    # ==================== Integration Tests ====================

    def test_full_workflow_with_file(self):
        """Test complete workflow with file loading."""
        test_file = os.path.join(self.test_dir, "full_test.json")
        test_data = {
            "brand_name": "Test Brand",
            "voice": {
                "Assisted Living": {
                    "tone": "Custom Tone"
                }
            },
            "content_requirements": ["Custom 1", "Custom 2"],
            "platforms": {
                "twitter": {
                    "max_length": 500
                }
            }
        }
        with open(test_file, 'w') as f:
            json.dump(test_data, f)

        manager = BrandGuidelinesManager(guidelines_path=test_file)
        
        # Test all methods work together
        self.assertEqual(manager.guidelines["brand_name"], "Test Brand")
        voice = manager.get_brand_voice("Assisted Living")
        self.assertEqual(voice["tone"], "Custom Tone")
        self.assertEqual(len(manager.get_content_requirements()), 2)
        twitter = manager.get_platform_specific_guidelines("twitter")
        self.assertEqual(twitter["max_length"], 500)


if __name__ == '__main__':
    unittest.main()
