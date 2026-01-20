"""
Unit tests for PlatformFormatter.

Tests cover:
- Initialization (with/without brand guidelines)
- Platform-specific formatting (Twitter, Instagram, LinkedIn, Facebook)
- Hashtag extraction
- Attribution handling
- Text truncation
- Image aspect ratio handling
- Helper methods
- Error handling
"""

import unittest
from unittest.mock import Mock, patch

# Add parent directory to path to import the module
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.platform_formatter import PlatformFormatter


class TestPlatformFormatter(unittest.TestCase):
    """Test suite for PlatformFormatter."""

    def setUp(self):
        """Set up test fixtures."""
        self.brand_guidelines = {
            "attribution": {
                "enabled": True,
                "default_line": "- Elevare by Amaziah",
                "long_form": "Insights from Elevare by Amaziah, building real-world systems with AI."
            }
        }

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init_without_brand_guidelines(self):
        """Test initialization without brand guidelines."""
        formatter = PlatformFormatter()
        self.assertIsNotNone(formatter)
        self.assertEqual(formatter.brand_guidelines, {})
        self.assertFalse(formatter.attribution_enabled)

    def test_init_with_brand_guidelines(self):
        """Test initialization with brand guidelines."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        self.assertEqual(formatter.brand_guidelines, self.brand_guidelines)
        self.assertTrue(formatter.attribution_enabled)

    def test_init_with_attribution_disabled(self):
        """Test initialization with attribution disabled."""
        guidelines = {
            "attribution": {
                "enabled": False,
                "default_line": "- Elevare by Amaziah"
            }
        }
        formatter = PlatformFormatter(brand_guidelines=guidelines)
        self.assertFalse(formatter.attribution_enabled)

    def test_platform_constraints_initialized(self):
        """Test that platform constraints are initialized."""
        formatter = PlatformFormatter()
        self.assertIn("twitter", formatter.platform_constraints)
        self.assertIn("instagram", formatter.platform_constraints)
        self.assertIn("linkedin", formatter.platform_constraints)
        self.assertIn("facebook", formatter.platform_constraints)

    # -------------------------
    # Twitter Formatting Tests
    # -------------------------

    def test_format_twitter_basic(self):
        """Test basic Twitter formatting."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertEqual(result["text"], "This is a test post")
        self.assertEqual(result["platform"], "twitter")
        self.assertIn("image_ratio", result)

    def test_format_twitter_with_hashtags(self):
        """Test Twitter formatting with hashtags."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test post #Test #Hashtag"}
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertIn("hashtags", result)
        self.assertIn("Test", result["hashtags"])
        self.assertIn("Hashtag", result["hashtags"])

    def test_format_twitter_with_attribution(self):
        """Test Twitter formatting with attribution."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertIn("- Elevare by Amaziah", result["text"])

    def test_format_twitter_truncation(self):
        """Test Twitter text truncation."""
        formatter = PlatformFormatter()
        long_text = "A" * 300  # Exceeds 280 character limit
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertLessEqual(len(result["text"]), 280)
        self.assertIn("...", result["text"])

    def test_format_twitter_truncation_with_attribution(self):
        """Test Twitter truncation preserves attribution."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        long_text = "A" * 300
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "twitter")
        
        # Should preserve attribution even after truncation
        self.assertIn("- Elevare by Amaziah", result["text"])

    # -------------------------
    # Instagram Formatting Tests
    # -------------------------

    def test_format_instagram_basic(self):
        """Test basic Instagram formatting."""
        formatter = PlatformFormatter()
        content = {"caption": "This is a test caption"}
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertEqual(result["caption"], "This is a test caption")
        self.assertEqual(result["platform"], "instagram")
        self.assertEqual(result["image_ratio"], "1:1")

    def test_format_instagram_uses_text_as_caption(self):
        """Test Instagram uses text field if caption not present."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertIn("caption", result)
        self.assertEqual(result["caption"], "This is a test post")

    def test_format_instagram_with_hashtags(self):
        """Test Instagram formatting with hashtags."""
        formatter = PlatformFormatter()
        content = {"caption": "This is a test #Test #Hashtag"}
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertIn("hashtags", result)
        self.assertIn("Test", result["hashtags"])

    def test_format_instagram_with_attribution(self):
        """Test Instagram formatting with attribution."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"caption": "This is a test caption"}
        result = formatter.format_for_platform(content, "instagram")
        
        # Instagram prefers long_form if available
        self.assertIn("Elevare by Amaziah", result["caption"])

    def test_format_instagram_truncation(self):
        """Test Instagram caption truncation."""
        formatter = PlatformFormatter()
        long_text = "A" * 1200  # Exceeds 1000 character limit
        content = {"caption": long_text}
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertLessEqual(len(result["caption"]), 1000)
        self.assertIn("...", result["caption"])

    # -------------------------
    # LinkedIn Formatting Tests
    # -------------------------

    def test_format_linkedin_basic(self):
        """Test basic LinkedIn formatting."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "linkedin")
        
        self.assertEqual(result["text"], "This is a test post")
        self.assertEqual(result["platform"], "linkedin")

    def test_format_linkedin_with_hashtags(self):
        """Test LinkedIn formatting with hashtags."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test #Test #Hashtag"}
        result = formatter.format_for_platform(content, "linkedin")
        
        self.assertIn("hashtags", result)
        self.assertIn("Test", result["hashtags"])

    def test_format_linkedin_with_attribution(self):
        """Test LinkedIn formatting with attribution."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "linkedin")
        
        # LinkedIn prefers long_form if space allows
        self.assertIn("Elevare by Amaziah", result["text"])

    def test_format_linkedin_truncation(self):
        """Test LinkedIn text truncation."""
        formatter = PlatformFormatter()
        long_text = "A" * 1200  # Exceeds 1000 character limit
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "linkedin")
        
        self.assertLessEqual(len(result["text"]), 1000)
        self.assertIn("...", result["text"])

    # -------------------------
    # Facebook Formatting Tests
    # -------------------------

    def test_format_facebook_basic(self):
        """Test basic Facebook formatting."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "facebook")
        
        self.assertEqual(result["text"], "This is a test post")
        self.assertEqual(result["platform"], "facebook")

    def test_format_facebook_with_hashtags(self):
        """Test Facebook formatting with hashtags."""
        formatter = PlatformFormatter()
        content = {"text": "This is a test #Test #Hashtag"}
        result = formatter.format_for_platform(content, "facebook")
        
        self.assertIn("hashtags", result)
        self.assertIn("Test", result["hashtags"])

    def test_format_facebook_with_attribution(self):
        """Test Facebook formatting with attribution."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"text": "This is a test post"}
        result = formatter.format_for_platform(content, "facebook")
        
        # Facebook prefers long_form if space allows
        self.assertIn("Elevare by Amaziah", result["text"])

    def test_format_facebook_truncation(self):
        """Test Facebook text truncation."""
        formatter = PlatformFormatter()
        long_text = "A" * 2500  # Exceeds 2000 character limit
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "facebook")
        
        self.assertLessEqual(len(result["text"]), 2000)
        self.assertIn("...", result["text"])

    # -------------------------
    # Hashtag Extraction Tests
    # -------------------------

    def test_extract_hashtags_single(self):
        """Test extracting single hashtag."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("This is a #test post")
        self.assertEqual(hashtags, ["test"])

    def test_extract_hashtags_multiple(self):
        """Test extracting multiple hashtags."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("This is #test #post #content")
        self.assertEqual(len(hashtags), 3)
        self.assertIn("test", hashtags)
        self.assertIn("post", hashtags)
        self.assertIn("content", hashtags)

    def test_extract_hashtags_duplicates(self):
        """Test that duplicate hashtags are removed."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("This is #test #post #test")
        self.assertEqual(len(hashtags), 2)
        self.assertEqual(hashtags, ["test", "post"])

    def test_extract_hashtags_empty_string(self):
        """Test extracting hashtags from empty string."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("")
        self.assertEqual(hashtags, [])

    def test_extract_hashtags_no_hashtags(self):
        """Test extracting hashtags when none present."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("This is a test post")
        self.assertEqual(hashtags, [])

    def test_extract_hashtags_case_sensitive(self):
        """Test that hashtag extraction preserves case."""
        formatter = PlatformFormatter()
        hashtags = formatter.extract_hashtags("This is #Test #POST")
        self.assertIn("Test", hashtags)
        self.assertIn("POST", hashtags)

    # -------------------------
    # Attribution Tests
    # -------------------------

    def test_attribution_not_duplicated(self):
        """Test that attribution is not duplicated if already present."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"text": "This is a test post\n\n- Elevare by Amaziah"}
        result = formatter.format_for_platform(content, "twitter")
        
        # Count occurrences of attribution
        count = result["text"].count("- Elevare by Amaziah")
        self.assertEqual(count, 1, "Attribution should not be duplicated")

    def test_attribution_long_form_preference(self):
        """Test that long_form is preferred when space allows."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {"text": "Short post"}
        result = formatter.format_for_platform(content, "linkedin")
        
        # LinkedIn should use long_form if space allows
        self.assertIn("Insights from Elevare", result["text"])

    def test_attribution_falls_back_to_default(self):
        """Test that attribution falls back to default_line if long_form too long."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        # Create content that's too long for long_form
        long_text = "A" * 950  # Leaves little room
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "linkedin")
        
        # Should use default_line instead of long_form
        self.assertIn("- Elevare by Amaziah", result["text"])

    # -------------------------
    # Helper Method Tests
    # -------------------------

    def test_get_image_aspect_ratio_twitter(self):
        """Test getting image aspect ratio for Twitter."""
        formatter = PlatformFormatter()
        ratio = formatter.get_image_aspect_ratio("twitter")
        self.assertEqual(ratio, "16:9")

    def test_get_image_aspect_ratio_instagram(self):
        """Test getting image aspect ratio for Instagram."""
        formatter = PlatformFormatter()
        ratio = formatter.get_image_aspect_ratio("instagram")
        self.assertEqual(ratio, "1:1")

    def test_get_image_aspect_ratio_linkedin(self):
        """Test getting image aspect ratio for LinkedIn."""
        formatter = PlatformFormatter()
        ratio = formatter.get_image_aspect_ratio("linkedin")
        self.assertEqual(ratio, "1.91:1")

    def test_get_image_aspect_ratio_facebook(self):
        """Test getting image aspect ratio for Facebook."""
        formatter = PlatformFormatter()
        ratio = formatter.get_image_aspect_ratio("facebook")
        self.assertEqual(ratio, "1.91:1")

    def test_get_image_aspect_ratio_unknown(self):
        """Test getting image aspect ratio for unknown platform."""
        formatter = PlatformFormatter()
        ratio = formatter.get_image_aspect_ratio("unknown")
        self.assertEqual(ratio, "1:1")  # Default

    def test_get_max_hashtags_twitter(self):
        """Test getting max hashtags for Twitter."""
        formatter = PlatformFormatter()
        max_tags = formatter.get_max_hashtags("twitter")
        self.assertEqual(max_tags, 3)

    def test_get_max_hashtags_instagram(self):
        """Test getting max hashtags for Instagram."""
        formatter = PlatformFormatter()
        max_tags = formatter.get_max_hashtags("instagram")
        self.assertEqual(max_tags, 30)

    def test_get_max_hashtags_linkedin(self):
        """Test getting max hashtags for LinkedIn."""
        formatter = PlatformFormatter()
        max_tags = formatter.get_max_hashtags("linkedin")
        self.assertEqual(max_tags, 5)

    def test_get_max_hashtags_facebook(self):
        """Test getting max hashtags for Facebook."""
        formatter = PlatformFormatter()
        max_tags = formatter.get_max_hashtags("facebook")
        self.assertEqual(max_tags, 5)

    def test_get_max_hashtags_unknown(self):
        """Test getting max hashtags for unknown platform."""
        formatter = PlatformFormatter()
        max_tags = formatter.get_max_hashtags("unknown")
        self.assertEqual(max_tags, 3)  # Default

    def test_get_max_length_twitter(self):
        """Test getting max length for Twitter."""
        formatter = PlatformFormatter()
        max_len = formatter.get_max_length("twitter")
        self.assertEqual(max_len, 280)

    def test_get_max_length_instagram(self):
        """Test getting max length for Instagram."""
        formatter = PlatformFormatter()
        max_len = formatter.get_max_length("instagram")
        self.assertEqual(max_len, 1000)

    def test_get_max_length_linkedin(self):
        """Test getting max length for LinkedIn."""
        formatter = PlatformFormatter()
        max_len = formatter.get_max_length("linkedin")
        self.assertEqual(max_len, 1000)

    def test_get_max_length_facebook(self):
        """Test getting max length for Facebook."""
        formatter = PlatformFormatter()
        max_len = formatter.get_max_length("facebook")
        self.assertEqual(max_len, 2000)

    def test_get_max_length_unknown(self):
        """Test getting max length for unknown platform."""
        formatter = PlatformFormatter()
        max_len = formatter.get_max_length("unknown")
        self.assertEqual(max_len, 280)  # Default

    # -------------------------
    # Error Handling Tests
    # -------------------------

    def test_format_unsupported_platform(self):
        """Test formatting for unsupported platform."""
        formatter = PlatformFormatter()
        content = {"text": "Test"}
        result = formatter.format_for_platform(content, "unsupported")
        
        self.assertIn("error", result)
        self.assertIn("Unsupported platform", result["error"])

    # -------------------------
    # Edge Cases Tests
    # -------------------------

    def test_format_empty_content(self):
        """Test formatting empty content."""
        formatter = PlatformFormatter()
        content = {}
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertIn("text", result)
        self.assertEqual(result["text"], "")

    def test_format_content_without_text_or_caption(self):
        """Test formatting content without text or caption."""
        formatter = PlatformFormatter()
        content = {"other_field": "value"}
        result = formatter.format_for_platform(content, "twitter")
        
        # Should handle gracefully
        self.assertIn("text", result)

    def test_format_instagram_no_caption_no_text(self):
        """Test Instagram formatting with no caption or text."""
        formatter = PlatformFormatter()
        content = {}
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertIn("caption", result)
        self.assertEqual(result["caption"], "")

    def test_hashtag_extraction_with_special_chars(self):
        """Test hashtag extraction with special characters."""
        formatter = PlatformFormatter()
        # Hashtags should only contain word characters
        hashtags = formatter.extract_hashtags("This is #test123 #test_123 #test-123")
        # Only alphanumeric and underscore are valid
        self.assertIn("test123", hashtags)
        self.assertIn("test_123", hashtags)
        # test-123 should not match (hyphen not in \w)

    # -------------------------
    # Integration Tests
    # -------------------------

    def test_full_formatting_workflow_twitter(self):
        """Test full formatting workflow for Twitter."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {
            "text": "This is a test post with #hashtag1 and #hashtag2",
            "hashtags": ["hashtag1", "hashtag2"]
        }
        result = formatter.format_for_platform(content, "twitter")
        
        self.assertIn("text", result)
        self.assertIn("hashtags", result)
        self.assertIn("platform", result)
        self.assertEqual(result["platform"], "twitter")
        self.assertIn("image_ratio", result)

    def test_full_formatting_workflow_instagram(self):
        """Test full formatting workflow for Instagram."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        content = {
            "caption": "This is a test caption with #hashtag",
            "hashtags": ["hashtag"]
        }
        result = formatter.format_for_platform(content, "instagram")
        
        self.assertIn("caption", result)
        self.assertIn("hashtags", result)
        self.assertEqual(result["platform"], "instagram")
        self.assertEqual(result["image_ratio"], "1:1")

    def test_attribution_preserved_after_truncation(self):
        """Test that attribution is preserved even after truncation."""
        formatter = PlatformFormatter(brand_guidelines=self.brand_guidelines)
        # Create content that will be truncated
        long_text = "A" * 300  # Exceeds Twitter limit
        content = {"text": long_text}
        result = formatter.format_for_platform(content, "twitter")
        
        # Attribution should still be present
        self.assertIn("- Elevare by Amaziah", result["text"])
        # Total length should be within limit
        self.assertLessEqual(len(result["text"]), 280)


if __name__ == '__main__':
    unittest.main(verbosity=2)
