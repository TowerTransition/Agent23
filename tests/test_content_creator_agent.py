"""
Unit tests for ContentCreatorAgent.

Tests cover:
- Initialization (with/without various parameters)
- Content generation for platforms
- Multi-platform content generation
- Domain mapping and trend rewriting
- Trend data validation
- File saving
- Error handling
"""

import unittest
import os
import json
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

# Add parent directory to path to import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.content_creator_agent import ContentCreatorAgent


class TestContentCreatorAgent(unittest.TestCase):
    """Test suite for ContentCreatorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = tempfile.mkdtemp()
        # Set required environment variables for tests
        os.environ["PEFT_ADAPTER_PATH"] = "/test/path/to/adapter"
        # Clear any conflicting env vars
        if "LOCAL_LLM_ENDPOINT" in os.environ:
            del os.environ["LOCAL_LLM_ENDPOINT"]

    def tearDown(self):
        """Clean up after tests."""
        # Clean up environment variables
        if "PEFT_ADAPTER_PATH" in os.environ:
            del os.environ["PEFT_ADAPTER_PATH"]
        if "ENABLE_TREND_REWRITE" in os.environ:
            del os.environ["ENABLE_TREND_REWRITE"]
        if "DEBUG_GENERATION" in os.environ:
            del os.environ["DEBUG_GENERATION"]
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # ==================== Initialization Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_init_with_peft_adapter(self, mock_domain_classifier, mock_lens_manager,
                                     mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test initialization with PEFT adapter path."""
        agent = ContentCreatorAgent()
        self.assertIsNotNone(agent.text_generator)
        self.assertIsNotNone(agent.domain_classifier)
        self.assertIsNotNone(agent.lens_manager)
        mock_text_gen.assert_called_once()

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_init_without_peft_requires_endpoint(self, mock_domain_classifier, mock_lens_manager,
                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test initialization without PEFT adapter requires endpoint."""
        if "PEFT_ADAPTER_PATH" in os.environ:
            del os.environ["PEFT_ADAPTER_PATH"]
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        agent = ContentCreatorAgent()
        self.assertIsNotNone(agent.text_generator)
        mock_text_gen.assert_called_once()

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_init_with_image_generation_disabled(self, mock_domain_classifier, mock_lens_manager,
                                                  mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test initialization with image generation disabled."""
        agent = ContentCreatorAgent(image_generation_enabled=False)
        self.assertFalse(agent.image_gen_enabled)
        mock_image_gen.assert_not_called()

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_init_with_custom_cache_dir(self, mock_domain_classifier, mock_lens_manager,
                                         mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test initialization with custom cache directory."""
        cache_dir = os.path.join(self.test_dir, "custom_cache")
        agent = ContentCreatorAgent(cache_dir=cache_dir)
        self.assertEqual(agent.cache_dir, cache_dir)
        self.assertTrue(os.path.exists(cache_dir))

    # ==================== Trend Data Validation Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_validate_trend_data_valid(self, mock_domain_classifier, mock_lens_manager,
                                       mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test trend data validation with valid data."""
        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        self.assertTrue(agent.validate_trend_data(trend_data))

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_validate_trend_data_missing_title(self, mock_domain_classifier, mock_lens_manager,
                                                mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test trend data validation with missing title."""
        agent = ContentCreatorAgent()
        trend_data = {"description": "Test description"}
        self.assertFalse(agent.validate_trend_data(trend_data))

    # ==================== Domain Mapping Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_to_peft_domain_assisted_living(self, mock_domain_classifier, mock_lens_manager,
                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping to ASSISTED_LIVING."""
        agent = ContentCreatorAgent()
        self.assertEqual(agent._map_to_peft_domain("assisted living"), "ASSISTED_LIVING")
        self.assertEqual(agent._map_to_peft_domain("senior care"), "ASSISTED_LIVING")
        self.assertEqual(agent._map_to_peft_domain("elder care"), "ASSISTED_LIVING")
        self.assertEqual(agent._map_to_peft_domain("long term care"), "ASSISTED_LIVING")

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_to_peft_domain_trading(self, mock_domain_classifier, mock_lens_manager,
                                        mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping to TRADING."""
        agent = ContentCreatorAgent()
        self.assertEqual(agent._map_to_peft_domain("finance"), "TRADING")
        self.assertEqual(agent._map_to_peft_domain("trading"), "TRADING")
        self.assertEqual(agent._map_to_peft_domain("market"), "TRADING")
        self.assertEqual(agent._map_to_peft_domain("investment"), "TRADING")

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_to_peft_domain_foreclosure(self, mock_domain_classifier, mock_lens_manager,
                                            mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping to FORECLOSURE."""
        agent = ContentCreatorAgent()
        self.assertEqual(agent._map_to_peft_domain("housing"), "FORECLOSURE")
        self.assertEqual(agent._map_to_peft_domain("mortgage"), "FORECLOSURE")
        self.assertEqual(agent._map_to_peft_domain("real estate"), "FORECLOSURE")
        self.assertEqual(agent._map_to_peft_domain("foreclosure"), "FORECLOSURE")

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_to_peft_domain_default(self, mock_domain_classifier, mock_lens_manager,
                                        mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping defaults to TRADING."""
        agent = ContentCreatorAgent()
        self.assertEqual(agent._map_to_peft_domain(""), "TRADING")
        self.assertEqual(agent._map_to_peft_domain("unknown domain"), "TRADING")

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_to_peft_domain_case_insensitive(self, mock_domain_classifier, mock_lens_manager,
                                                  mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping is case insensitive."""
        agent = ContentCreatorAgent()
        self.assertEqual(agent._map_to_peft_domain("ASSISTED LIVING"), "ASSISTED_LIVING")
        self.assertEqual(agent._map_to_peft_domain("Assisted Living"), "ASSISTED_LIVING")
        self.assertEqual(agent._map_to_peft_domain("TRADING"), "TRADING")

    # ==================== Domain and Trend Rewriting Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_domain_and_rewrite_trend_no_rewrite(self, mock_domain_classifier, mock_lens_manager,
                                                      mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping without text rewriting (default)."""
        agent = ContentCreatorAgent()
        # Use "assisted living" which maps to ASSISTED_LIVING
        domain, text = agent._map_domain_and_rewrite_trend("assisted living", "Senior care trends")
        self.assertEqual(domain, "ASSISTED_LIVING")  # Domain is mapped
        self.assertEqual(text, "Senior care trends")  # Text is NOT rewritten (default)

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_map_domain_and_rewrite_trend_with_rewrite_enabled(self, mock_domain_classifier, mock_lens_manager,
                                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test domain mapping with text rewriting enabled."""
        os.environ["ENABLE_TREND_REWRITE"] = "1"
        agent = ContentCreatorAgent()
        # Use text that contains words that will be rewritten
        domain, text = agent._map_domain_and_rewrite_trend("assisted living", "Healthcare trends for patients")
        self.assertEqual(domain, "ASSISTED_LIVING")
        # Check that rewriting happened (Healthcare -> assisted living, patients -> resident)
        self.assertIn("assisted living", text.lower())
        self.assertIn("resident", text.lower())  # "patients" should be rewritten to "resident"

    # ==================== Content Generation Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_unsupported(self, mock_domain_classifier, mock_lens_manager,
                                                        mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test content generation for unsupported platform."""
        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        result = agent.generate_content_for_platform("unsupported", trend_data)
        self.assertIn("error", result)
        self.assertIn("Unsupported platform", result["error"])

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_success(self, mock_domain_classifier, mock_lens_manager,
                                                    mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test successful content generation."""
        # Setup mocks
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": True}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter_instance.format_for_platform.return_value = {"text": "Formatted content"}
        mock_formatter.return_value = mock_formatter_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        result = agent.generate_content_for_platform("twitter", trend_data)

        self.assertNotIn("error", result)
        mock_text_gen_instance.generate_text.assert_called_once()
        mock_moderator_instance.check_content.assert_called_once()
        mock_formatter_instance.format_for_platform.assert_called_once()

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_text_generation_error(self, mock_domain_classifier, mock_lens_manager,
                                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test content generation with text generation error."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.side_effect = Exception("Generation failed")
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator.return_value = mock_moderator_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        result = agent.generate_content_for_platform("twitter", trend_data)

        self.assertIn("error", result)
        self.assertIn("Text generation failed", result["error"])

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_moderation_failed(self, mock_domain_classifier, mock_lens_manager,
                                                              mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test content generation with moderation failure."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": False, "reason": "Inappropriate"}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter.return_value = mock_formatter_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        result = agent.generate_content_for_platform("twitter", trend_data)

        self.assertIn("error", result)
        self.assertIn("Content moderation failed", result["error"])

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_with_hashtags(self, mock_domain_classifier, mock_lens_manager,
                                                         mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test content generation with hashtags."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": True}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter_instance.format_for_platform.return_value = {"text": "Formatted content"}
        mock_formatter.return_value = mock_formatter_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic", "hashtags": ["test", "content"]}
        result = agent.generate_content_for_platform("twitter", trend_data)

        self.assertIn("hashtags", result)
        self.assertEqual(result["hashtags"], ["test", "content"])

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_content_for_platform_with_expert_lens(self, mock_domain_classifier, mock_lens_manager,
                                                              mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test content generation with expert lens enabled."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": True}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter_instance.format_for_platform.return_value = {"text": "Formatted content"}
        mock_formatter.return_value = mock_formatter_instance

        mock_lens_manager_instance = Mock()
        mock_lens_manager_instance.pick_plan.return_value = {
            "lens": "Test Lens",
            "trend": "Test Trend",
            "domain": "TRADING"
        }
        mock_lens_manager.return_value = mock_lens_manager_instance

        mock_domain_classifier_instance = Mock()
        mock_domain_classifier_instance.classify_trend.return_value = ("TRADING", 0.9)
        mock_domain_classifier.return_value = mock_domain_classifier_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        result = agent.generate_content_for_platform("twitter", trend_data, use_expert_lens=True)

        self.assertNotIn("error", result)
        mock_lens_manager_instance.pick_plan.assert_called_once()

    # ==================== Multi-Platform Content Generation Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_multi_platform_content_default_platforms(self, mock_domain_classifier, mock_lens_manager,
                                                                mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test multi-platform content generation with default platforms."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": True}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter_instance.format_for_platform.return_value = {"text": "Formatted content"}
        mock_formatter.return_value = mock_formatter_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        results = agent.generate_multi_platform_content(trend_data)

        self.assertIn("twitter", results)
        self.assertIn("instagram", results)
        self.assertIn("linkedin", results)
        self.assertEqual(len(results), 3)

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_generate_multi_platform_content_custom_platforms(self, mock_domain_classifier, mock_lens_manager,
                                                              mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test multi-platform content generation with custom platforms."""
        mock_text_gen_instance = Mock()
        mock_text_gen_instance.generate_text.return_value = {"text": "Generated content"}
        mock_text_gen.return_value = mock_text_gen_instance

        mock_moderator_instance = Mock()
        mock_moderator_instance.check_content.return_value = {"is_appropriate": True}
        mock_moderator.return_value = mock_moderator_instance

        mock_formatter_instance = Mock()
        mock_formatter_instance.format_for_platform.return_value = {"text": "Formatted content"}
        mock_formatter.return_value = mock_formatter_instance

        agent = ContentCreatorAgent()
        trend_data = {"title": "Test Topic"}
        platforms = ["twitter", "facebook"]
        results = agent.generate_multi_platform_content(trend_data, platforms=platforms)

        self.assertIn("twitter", results)
        self.assertIn("facebook", results)
        self.assertEqual(len(results), 2)

    # ==================== File Saving Tests ====================

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_save_content_to_file_with_filename(self, mock_domain_classifier, mock_lens_manager,
                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test saving content to file with specified filename."""
        agent = ContentCreatorAgent()
        content = {"text": "Test content", "platform": "twitter"}
        output_dir = os.path.join(self.test_dir, "output")
        filepath = agent.save_content_to_file(content, filename="test.json", output_dir=output_dir)

        self.assertTrue(os.path.exists(filepath))
        self.assertEqual(os.path.basename(filepath), "test.json")
        
        with open(filepath, 'r') as f:
            saved_content = json.load(f)
        self.assertEqual(saved_content["text"], "Test content")

    @patch('agents.content_creator.content_creator_agent.TextGenerator')
    @patch('agents.content_creator.content_creator_agent.ImageGenerator')
    @patch('agents.content_creator.content_creator_agent.PlatformFormatter')
    @patch('agents.content_creator.content_creator_agent.ContentModerator')
    @patch('agents.content_creator.content_creator_agent.ExpertLensManager')
    @patch('agents.content_creator.content_creator_agent.DomainClassifier')
    def test_save_content_to_file_auto_filename(self, mock_domain_classifier, mock_lens_manager,
                                                 mock_moderator, mock_formatter, mock_image_gen, mock_text_gen):
        """Test saving content to file with auto-generated filename."""
        agent = ContentCreatorAgent()
        content = {"text": "Test content", "platform": "twitter"}
        output_dir = os.path.join(self.test_dir, "output")
        filepath = agent.save_content_to_file(content, output_dir=output_dir)

        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.startswith(os.path.join(output_dir, "twitter_")))
        self.assertTrue(filepath.endswith(".json"))


if __name__ == '__main__':
    unittest.main()
