"""
Unit tests for ImageGenerator.

Tests cover:
- Initialization (with/without API key, enabled/disabled)
- Image generation (success, failure, retries)
- Aspect ratio conversion
- Image response processing
- Error handling
- Retry logic
- Timeout handling
- Directory creation
"""

import unittest
from unittest.mock import Mock, patch, mock_open, MagicMock
import os
import json
import base64
import tempfile
import shutil

# Add parent directory to path to import the module
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.image_generator import ImageGenerator


class TestImageGenerator(unittest.TestCase):
    """Test suite for ImageGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a temporary directory for test output
        self.test_output_dir = tempfile.mkdtemp()
        
        # Mock environment to avoid needing real API key
        self.env_patcher = patch.dict(os.environ, {}, clear=True)
        self.env_patcher.start()

    def tearDown(self):
        """Clean up test fixtures."""
        self.env_patcher.stop()
        # Remove temporary directory
        if os.path.exists(self.test_output_dir):
            shutil.rmtree(self.test_output_dir)

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init_enabled_with_api_key(self):
        """Test initialization with API key and enabled."""
        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
            self.assertTrue(gen.enabled)
            self.assertEqual(gen.api_key, "test_key")
            self.assertEqual(gen.output_dir, self.test_output_dir)

    def test_init_enabled_without_api_key(self):
        """Test initialization enabled but no API key (should disable)."""
        gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
        self.assertFalse(gen.enabled)
        self.assertIsNone(gen.api_key)

    def test_init_disabled(self):
        """Test initialization with disabled flag."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        self.assertFalse(gen.enabled)

    def test_init_creates_output_dir(self):
        """Test that initialization creates output directory."""
        new_dir = os.path.join(self.test_output_dir, "new_images")
        gen = ImageGenerator(enabled=False, output_dir=new_dir)
        self.assertTrue(os.path.exists(new_dir))

    def test_init_defaults(self):
        """Test initialization with default values."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        self.assertEqual(gen.api_host, "https://api.stability.ai")
        self.assertEqual(gen.engine_id, "stable-diffusion-xl-1024-v1-0")
        self.assertEqual(gen.max_retries, 3)
        self.assertEqual(gen.timeout_s, 30)

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        gen = ImageGenerator(
            enabled=False,
            api_host="https://custom.api.com",
            engine_id="custom-engine",
            output_dir=self.test_output_dir,
            max_retries=5,
            timeout_s=60
        )
        self.assertEqual(gen.api_host, "https://custom.api.com")
        self.assertEqual(gen.engine_id, "custom-engine")
        self.assertEqual(gen.max_retries, 5)
        self.assertEqual(gen.timeout_s, 60)

    # -------------------------
    # Image Generation Tests
    # -------------------------

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_success(self, mock_post):
        """Test successful image generation."""
        # Mock successful API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
            result = gen.generate_image("test prompt")

        self.assertNotIn("error", result)
        self.assertIn("filename", result)
        self.assertIn("filepath", result)
        self.assertEqual(result["prompt"], "test prompt")
        self.assertTrue(result["saved"])

    def test_generate_image_disabled(self):
        """Test image generation when disabled."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        result = gen.generate_image("test prompt")
        
        self.assertEqual(result["status"], "disabled")
        self.assertEqual(result["prompt"], "test prompt")

    def test_generate_image_invalid_prompt(self):
        """Test image generation with invalid prompt."""
        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
            
            # Test empty prompt
            result = gen.generate_image("")
            self.assertIn("error", result)
            
            # Test non-string prompt
            result = gen.generate_image(None)
            self.assertIn("error", result)

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_api_error(self, mock_post):
        """Test image generation with API error."""
        # Mock API error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad request"
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=1)
            result = gen.generate_image("test prompt")

        self.assertIn("error", result)
        self.assertIn("status_code", result)
        self.assertEqual(result["status_code"], 400)

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_retry_on_failure(self, mock_post):
        """Test that image generation retries on failure."""
        # Mock first failure, then success
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Server error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=2)
            with patch('time.sleep'):  # Speed up test
                result = gen.generate_image("test prompt")

        self.assertNotIn("error", result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_timeout(self, mock_post):
        """Test image generation with timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=1)
            result = gen.generate_image("test prompt")

        self.assertIn("error", result)
        # Error message is "Request timed out after 30s" - check for "timed out" or "timeout"
        error_lower = result["error"].lower()
        self.assertTrue("timeout" in error_lower or "timed out" in error_lower,
                       f"Error should mention timeout, got: {result['error']}")

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_max_retries_override(self, mock_post):
        """Test that max_retries_override works."""
        # Mock failures
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Server error"
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=1)
            with patch('time.sleep'):  # Speed up test
                result = gen.generate_image("test prompt", max_retries_override=3)

        # Should have tried 3 times
        self.assertEqual(mock_post.call_count, 3)
        self.assertIn("error", result)

    # -------------------------
    # Aspect Ratio Tests
    # -------------------------

    def test_get_dimensions_1_1(self):
        """Test 1:1 aspect ratio conversion."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("1:1")
        self.assertEqual(width, 1024)
        self.assertEqual(height, 1024)

    def test_get_dimensions_16_9(self):
        """Test 16:9 aspect ratio conversion."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("16:9")
        self.assertEqual(width, 1024)
        self.assertEqual(height, 576)

    def test_get_dimensions_4_5(self):
        """Test 4:5 aspect ratio conversion."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("4:5")
        self.assertEqual(width, 768)
        self.assertEqual(height, 960)

    def test_get_dimensions_3_2(self):
        """Test 3:2 aspect ratio conversion."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("3:2")
        self.assertEqual(width, 1024)
        self.assertEqual(height, 682)

    def test_get_dimensions_4_3(self):
        """Test 4:3 aspect ratio conversion."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("4:3")
        self.assertEqual(width, 1024)
        self.assertEqual(height, 768)

    def test_get_dimensions_unknown(self):
        """Test unknown aspect ratio defaults to 1:1."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        width, height = gen._get_dimensions_from_aspect_ratio("unknown")
        self.assertEqual(width, 1024)
        self.assertEqual(height, 1024)

    # -------------------------
    # Image Response Processing Tests
    # -------------------------

    def test_process_image_response_success(self):
        """Test successful image response processing."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=True,
            width=1024,
            height=1024
        )
        
        self.assertNotIn("error", result)
        self.assertIn("filename", result)
        self.assertIn("filepath", result)
        self.assertEqual(result["seed"], 12345)
        self.assertTrue(result["saved"])

    def test_process_image_response_no_artifacts(self):
        """Test processing response with no artifacts."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {"artifacts": []}
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=True,
            width=1024,
            height=1024
        )
        
        self.assertIn("error", result)

    def test_process_image_response_missing_base64(self):
        """Test processing response with missing base64."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {
            "artifacts": [{
                "seed": 12345
                # Missing base64
            }]
        }
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=True,
            width=1024,
            height=1024
        )
        
        self.assertIn("error", result)

    def test_process_image_response_save_disabled(self):
        """Test processing response with save_image=False."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=False,
            width=1024,
            height=1024
        )
        
        self.assertNotIn("error", result)
        self.assertIsNone(result["filepath"])
        self.assertFalse(result["saved"])

    def test_process_image_response_uses_artifact_dimensions(self):
        """Test that response uses artifact dimensions if available."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 512,  # Different from input
                "height": 512  # Different from input
            }]
        }
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=False,
            width=1024,  # Input dimensions
            height=1024  # Input dimensions
        )
        
        self.assertEqual(result["width"], 512)  # Uses artifact dimensions
        self.assertEqual(result["height"], 512)

    # -------------------------
    # Error Handling Tests
    # -------------------------

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_request_exception(self, mock_post):
        """Test handling of RequestException."""
        import requests
        mock_post.side_effect = requests.exceptions.RequestException("Connection error")

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=1)
            result = gen.generate_image("test prompt")

        self.assertIn("error", result)
        self.assertIn("RequestException", result["error"])

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_unexpected_exception(self, mock_post):
        """Test handling of unexpected exceptions."""
        mock_post.side_effect = ValueError("Unexpected error")

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=1)
            result = gen.generate_image("test prompt")

        self.assertIn("error", result)
        self.assertIn("Unexpected error", result["error"])

    def test_process_image_response_save_error(self):
        """Test handling of save errors."""
        gen = ImageGenerator(enabled=False, output_dir=self.test_output_dir)
        
        response_data = {
            "artifacts": [{
                "base64": "invalid_base64",  # Invalid base64
                "seed": 12345
            }]
        }
        
        result = gen._process_image_response(
            response_data=response_data,
            prompt="test prompt",
            save_image=True,
            width=1024,
            height=1024
        )
        
        self.assertIn("error", result)

    # -------------------------
    # API Request Tests
    # -------------------------

    @patch('agents.content_creator.image_generator.requests.post')
    def test_generate_image_api_request_format(self, mock_post):
        """Test that API request is formatted correctly."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
            gen.generate_image("test prompt", aspect_ratio="16:9", cfg_scale=8.0, steps=40)

        # Verify request was made correctly
        self.assertEqual(mock_post.call_count, 1)
        call_args = mock_post.call_args
        
        # Check headers
        headers = call_args[1]["headers"]
        self.assertIn("Authorization", headers)
        self.assertEqual(headers["Authorization"], "Bearer test_key")
        
        # Check JSON payload
        json_data = call_args[1]["json"]
        self.assertEqual(json_data["text_prompts"][0]["text"], "test prompt")
        self.assertEqual(json_data["cfg_scale"], 8.0)
        self.assertEqual(json_data["steps"], 40)
        self.assertEqual(json_data["width"], 1024)
        self.assertEqual(json_data["height"], 576)  # 16:9 aspect ratio

    # -------------------------
    # Integration Tests
    # -------------------------

    @patch('agents.content_creator.image_generator.requests.post')
    def test_full_workflow_success(self, mock_post):
        """Test full workflow from generation to file save."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        mock_post.return_value = mock_response

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir)
            result = gen.generate_image("test prompt", aspect_ratio="1:1")

        # Verify result structure
        self.assertNotIn("error", result)
        self.assertIn("filename", result)
        self.assertIn("filepath", result)
        self.assertIn("prompt", result)
        self.assertIn("seed", result)
        self.assertIn("timestamp", result)
        self.assertTrue(result["saved"])
        
        # Verify file was created
        self.assertTrue(os.path.exists(result["filepath"]))

    @patch('agents.content_creator.image_generator.requests.post')
    def test_full_workflow_with_retries(self, mock_post):
        """Test full workflow with retries."""
        # First two attempts fail, third succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        mock_response_fail.text = "Server error"
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "artifacts": [{
                "base64": base64.b64encode(b"fake_image_data").decode('utf-8'),
                "seed": 12345,
                "width": 1024,
                "height": 1024
            }]
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]

        with patch.dict(os.environ, {"STABILITY_API_KEY": "test_key"}):
            gen = ImageGenerator(enabled=True, output_dir=self.test_output_dir, max_retries=3)
            with patch('time.sleep'):  # Speed up test
                result = gen.generate_image("test prompt")

        self.assertNotIn("error", result)
        self.assertEqual(mock_post.call_count, 3)


if __name__ == '__main__':
    unittest.main(verbosity=2)
