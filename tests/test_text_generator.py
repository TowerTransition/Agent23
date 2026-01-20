"""
Unit tests for TextGenerator.

Tests cover:
- Initialization (with/without PEFT, with/without HTTP endpoint)
- Direct model mode (PEFT)
- HTTP endpoint mode
- Ollama fallback (only in HTTP mode)
- Prompt building
- Text generation
- Hashtag generation
- Image prompt generation
- Post-processing
- Error handling
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import os
import sys
import tempfile
import shutil

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.text_generator import TextGenerator


class TestTextGenerator(unittest.TestCase):
    """Test suite for TextGenerator."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear environment variables
        self.env_vars_to_clear = [
            "PEFT_ADAPTER_PATH",
            "BASE_MODEL_NAME",
            "LOCAL_LLM_ENDPOINT",
            "LOCAL_LLM_MODEL",
            "LOCAL_LLM_API_KEY",
            "ALLOW_DEFAULT_LLM_ENDPOINT",
            "PEFT_DEVICE_MAP"
        ]
        self.original_env = {}
        for var in self.env_vars_to_clear:
            self.original_env[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]

    def tearDown(self):
        """Clean up test fixtures."""
        # Restore environment variables
        for var, value in self.original_env.items():
            if value is not None:
                os.environ[var] = value
            elif var in os.environ:
                del os.environ[var]

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init_with_peft_adapter_path(self):
        """Test initialization with PEFT adapter path."""
        # Create a temporary directory to simulate PEFT adapter
        temp_dir = tempfile.mkdtemp()
        try:
            os.environ["PEFT_ADAPTER_PATH"] = temp_dir
            os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            
            with patch('agents.content_creator.text_generator.PEFT_AVAILABLE', True):
                with patch.object(TextGenerator, '_load_peft_model') as mock_load:
                    gen = TextGenerator()
                    self.assertTrue(gen.use_direct_model)
                    mock_load.assert_called_once()
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_init_without_peft_falls_back_to_http(self):
        """Test initialization without PEFT falls back to HTTP mode."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        gen = TextGenerator()
        self.assertFalse(gen.use_direct_model)
        self.assertEqual(gen.local_llm_endpoint, "http://localhost:11434/v1/chat/completions")

    def test_init_without_peft_or_endpoint_raises_error(self):
        """Test initialization without PEFT or endpoint raises error."""
        with self.assertRaises(ValueError) as context:
            TextGenerator()
        self.assertIn("PEFT_ADAPTER_PATH", str(context.exception))
        self.assertIn("LOCAL_LLM_ENDPOINT", str(context.exception))

    def test_init_with_allow_default_endpoint(self):
        """Test initialization with ALLOW_DEFAULT_LLM_ENDPOINT."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        
        gen = TextGenerator()
        self.assertFalse(gen.use_direct_model)
        self.assertEqual(gen.local_llm_endpoint, "http://localhost:11434/v1/chat/completions")

    def test_init_custom_values(self):
        """Test initialization with custom values."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://custom:8080/v1/chat/completions"
        
        gen = TextGenerator(
            model="custom-model",
            temperature=0.9,
            max_retries=5,
            timeout_s=60
        )
        self.assertEqual(gen.model, "custom-model")
        self.assertEqual(gen.temperature, 0.9)
        self.assertEqual(gen.max_retries, 5)
        self.assertEqual(gen.timeout_s, 60)

    # -------------------------
    # Prompt Building Tests
    # -------------------------

    def test_build_minimal_prompt_with_context(self):
        """Test building prompt with context."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False  # Set to avoid loading model
        
        context = {
            "title": "Test Title",
            "description": "Test Description",
            "lens_plan": {
                "decision": "Test Decision",
                "constraint": "Test Constraint",
                "risk_owner": "Test Owner"
            }
        }
        
        prompt = gen._build_minimal_prompt(context, "facebook")
        self.assertIn("CONTEXT: Test Title", prompt)
        self.assertIn("Test Description", prompt)
        self.assertIn("Decision: Test Decision", prompt)
        self.assertIn("Constraint: Test Constraint", prompt)
        self.assertIn("Risk owner: Test Owner", prompt)

    def test_build_minimal_prompt_with_lens_plan_only(self):
        """Test building prompt with lens_plan only."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "lens_plan": {
                "title": "Lens Title",
                "description": "Lens Description"
            }
        }
        
        prompt = gen._build_minimal_prompt(context, "twitter")
        self.assertIn("CONTEXT: Lens Title", prompt)
        self.assertIn("Lens Description", prompt)

    def test_build_minimal_prompt_default_title(self):
        """Test building prompt with default title."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {}
        prompt = gen._build_minimal_prompt(context, "facebook")
        self.assertIn("CONTEXT: AI in real-world workflows", prompt)

    def test_style_line_twitter(self):
        """Test style line for Twitter."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        style = gen._style_line("twitter")
        self.assertIn("270 characters", style)
        self.assertIn("one question", style)

    def test_style_line_linkedin(self):
        """Test style line for LinkedIn."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        style = gen._style_line("linkedin")
        self.assertIn("6-10 sentences", style)

    def test_style_line_instagram(self):
        """Test style line for Instagram."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        style = gen._style_line("instagram")
        self.assertIn("2-5 short paragraphs", style)

    def test_style_line_default(self):
        """Test style line for default platform."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        style = gen._style_line("facebook")
        self.assertIn("4-6 sentences", style)

    # -------------------------
    # Hashtag Generation Tests
    # -------------------------

    def test_ensure_hashtags_from_context(self):
        """Test hashtag generation from context."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {"hashtags": ["#Test1", "#Test2"]}
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertEqual(len(hashtags), 2)
        self.assertIn("#Test1", hashtags)
        self.assertIn("#Test2", hashtags)

    def test_ensure_hashtags_foreclosure_domain(self):
        """Test hashtag generation for foreclosure domain."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "lens_plan": {"domain": "Foreclosures"}
        }
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertIn("#ForeclosureSupport", hashtags)
        self.assertIn("#Homeowners", hashtags)

    def test_ensure_hashtags_assisted_living_domain(self):
        """Test hashtag generation for assisted living domain."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "domain": "Assisted Living"
        }
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertIn("#AssistedLiving", hashtags)
        self.assertIn("#Caregiving", hashtags)

    def test_ensure_hashtags_trading_domain(self):
        """Test hashtag generation for trading domain."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "lens_plan": {"domain": "Trading Futures"}
        }
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertIn("#FuturesTrading", hashtags)
        self.assertIn("#RiskManagement", hashtags)

    def test_ensure_hashtags_default(self):
        """Test hashtag generation with default domain."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {}
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertIn("#RealWorldAI", hashtags)
        self.assertIn("#SystemDesign", hashtags)

    def test_ensure_hashtags_platform_limits(self):
        """Test hashtag platform limits."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {"hashtags": ["#1", "#2", "#3", "#4", "#5"]}
        
        # Twitter: max 2
        hashtags = gen._ensure_hashtags(context, "twitter")
        self.assertEqual(len(hashtags), 2)
        
        # LinkedIn: max 5
        hashtags = gen._ensure_hashtags(context, "linkedin")
        self.assertEqual(len(hashtags), 5)
        
        # Instagram: max 8
        hashtags = gen._ensure_hashtags(context, "instagram")
        self.assertEqual(len(hashtags), 5)  # Only 5 provided
        
        # Facebook: max 3
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertEqual(len(hashtags), 3)

    def test_ensure_hashtags_adds_prefix(self):
        """Test that hashtags get # prefix added."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {"hashtags": ["Test1", "Test2"]}
        hashtags = gen._ensure_hashtags(context, "facebook")
        self.assertTrue(all(tag.startswith("#") for tag in hashtags))

    # -------------------------
    # Image Prompt Generation Tests
    # -------------------------

    def test_generate_image_prompt_with_context(self):
        """Test image prompt generation with context."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "title": "Test Title",
            "description": "Test Description"
        }
        prompt = gen.generate_image_prompt(context, "facebook")
        self.assertIn("Test Title", prompt)
        self.assertIn("Test Description", prompt)
        self.assertIn("high quality", prompt)

    def test_generate_image_prompt_with_lens_plan(self):
        """Test image prompt generation with lens_plan."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {
            "lens_plan": {
                "title": "Lens Title",
                "description": "Lens Description"
            }
        }
        prompt = gen.generate_image_prompt(context, "instagram")
        self.assertIn("Lens Title", prompt)
        self.assertIn("Lens Description", prompt)

    def test_generate_image_prompt_default(self):
        """Test image prompt generation with defaults."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        context = {}
        prompt = gen.generate_image_prompt(context, "facebook")
        self.assertIn("AI technology", prompt)
        self.assertIn("high quality", prompt)

    # -------------------------
    # Post-Processing Tests
    # -------------------------

    def test_clean_model_output_removes_labels(self):
        """Test that clean_model_output removes labels."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        raw = "CONTEXT: Test\nPROBLEM: Issue\nThis is the actual content."
        cleaned = gen._clean_model_output(raw)
        self.assertNotIn("CONTEXT:", cleaned)
        self.assertNotIn("PROBLEM:", cleaned)
        self.assertIn("actual content", cleaned)

    def test_clean_model_output_removes_instructions(self):
        """Test that clean_model_output removes instructions."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        raw = "This is content. 4-6 complete sentences. End with exactly ONE question mark."
        cleaned = gen._clean_model_output(raw)
        self.assertNotIn("4-6 complete sentences", cleaned)

    def test_post_process_content_removes_template_garbage(self):
        """Test post_process_content removes template garbage."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = True  # PEFT mode
        
        text = "1. Start by reproducing\n4-6 sentences. one question.\nThis is content."
        processed = gen._post_process_content(text)
        self.assertNotIn("1. Start by", processed)
        self.assertNotIn("4-6 sentences", processed)
        self.assertIn("This is content", processed)

    def test_sanitize_prompt_echo(self):
        """Test sanitize_prompt_echo removes prompt echoes."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        text = "Start by reproducing: This is content. (not repeat beginning text)"
        sanitized = gen._sanitize_prompt_echo(text)
        self.assertNotIn("Start by reproducing", sanitized)
        self.assertNotIn("not repeat beginning text", sanitized)
        self.assertIn("This is content", sanitized)

    def test_append_footer(self):
        """Test append_footer adds footer."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        body = "This is the body content."
        result = gen._append_footer(body, "facebook")
        self.assertIn("— Elevare by Amaziah", result)
        self.assertIn("Insights from Elevare", result)

    def test_append_footer_removes_existing_footer(self):
        """Test append_footer removes existing footer before adding."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        body = "This is content.\n\n— Elevare by Amaziah\nOld footer"
        result = gen._append_footer(body, "facebook")
        # Should only have one footer
        count = result.count("— Elevare by Amaziah")
        self.assertEqual(count, 1)

    # -------------------------
    # Text Generation Tests
    # -------------------------

    @patch('agents.content_creator.text_generator.requests.post')
    def test_generate_text_http_mode(self, mock_post):
        """Test text generation in HTTP mode."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        # Mock HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five. This is a test post with a question?"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        gen = TextGenerator()
        context = {
            "title": "Test",
            "lens_plan": {}
        }
        
        result = gen.generate_text(context, "facebook")
        self.assertIn("text", result)
        self.assertIn("hashtags", result)
        self.assertIn("platform", result)
        self.assertEqual(result["platform"], "facebook")
        self.assertIn("— Elevare by Amaziah", result["text"])

    @patch('agents.content_creator.text_generator.requests.post')
    def test_generate_text_instagram_returns_caption(self, mock_post):
        """Test text generation for Instagram returns caption."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five. This is an Instagram post with a question?"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        gen = TextGenerator()
        context = {"title": "Test"}
        
        result = gen.generate_text(context, "instagram")
        self.assertIn("caption", result)
        self.assertEqual(result["caption"], result["text"])
        self.assertTrue(result["meta"]["requires_image"])

    @patch('agents.content_creator.text_generator.requests.post')
    def test_generate_text_retries_on_failure(self, mock_post):
        """Test text generation retries on failure."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        # First call fails, second succeeds
        mock_response_fail = Mock()
        mock_response_fail.status_code = 500
        
        mock_response_success = Mock()
        mock_response_success.status_code = 200
        mock_response_success.json.return_value = {
            "choices": [{
                "message": {
                    "content": "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five. This is a test post with a question?"
                }
            }]
        }
        
        mock_post.side_effect = [mock_response_fail, mock_response_success]
        
        gen = TextGenerator(max_retries=2)
        context = {"title": "Test"}
        
        with patch('time.sleep'):  # Speed up test
            result = gen.generate_text(context, "facebook")
        
        self.assertIn("text", result)
        self.assertEqual(mock_post.call_count, 2)

    # -------------------------
    # HTTP Endpoint Tests
    # -------------------------

    @patch('agents.content_creator.text_generator.requests.post')
    def test_call_http_success(self, mock_post):
        """Test successful HTTP call."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{
                "message": {
                    "content": "Test response"
                }
            }]
        }
        mock_post.return_value = mock_response
        
        gen = TextGenerator()
        result = gen._call_http("system", "user", 100, 0.7)
        self.assertEqual(result, "Test response")

    @patch('agents.content_creator.text_generator.requests.post')
    def test_call_http_404_falls_back_to_ollama(self, mock_post):
        """Test HTTP 404 falls back to Ollama."""
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        mock_response_404 = Mock()
        mock_response_404.status_code = 404
        
        mock_response_ollama = Mock()
        mock_response_ollama.status_code = 200
        mock_response_ollama.json.return_value = {
            "response": "Ollama response"
        }
        
        mock_post.side_effect = [mock_response_404, mock_response_ollama]
        
        gen = TextGenerator()
        result = gen._call_http("system", "user", 100, 0.7)
        self.assertEqual(result, "Ollama response")
        self.assertEqual(mock_post.call_count, 2)

    @patch('agents.content_creator.text_generator.requests.post')
    def test_call_http_connection_error_falls_back_to_ollama(self, mock_post):
        """Test HTTP connection error falls back to Ollama."""
        import requests
        os.environ["LOCAL_LLM_ENDPOINT"] = "http://localhost:11434/v1/chat/completions"
        
        mock_post.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            Mock(status_code=200, json=lambda: {"response": "Ollama response"})
        ]
        
        gen = TextGenerator()
        result = gen._call_http("system", "user", 100, 0.7)
        self.assertEqual(result, "Ollama response")

    def test_call_http_raises_error_if_direct_model_enabled(self):
        """Test that _call_http raises error if direct model is enabled."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = True  # Simulate direct model mode
        
        with self.assertRaises(RuntimeError) as context:
            gen._call_http("system", "user", 100, 0.7)
        self.assertIn("Direct model mode", str(context.exception))

    def test_convert_to_ollama_generate_endpoint(self):
        """Test conversion to Ollama generate endpoint."""
        # Test with /v1/chat/completions
        endpoint = TextGenerator._convert_to_ollama_generate_endpoint(
            "http://localhost:11434/v1/chat/completions"
        )
        self.assertEqual(endpoint, "http://localhost:11434/api/generate")
        
        # Test with /api/generate already
        endpoint = TextGenerator._convert_to_ollama_generate_endpoint(
            "http://localhost:11434/api/generate"
        )
        self.assertEqual(endpoint, "http://localhost:11434/api/generate")
        
        # Test with None
        endpoint = TextGenerator._convert_to_ollama_generate_endpoint(None)
        self.assertEqual(endpoint, "http://localhost:11434/api/generate")

    # -------------------------
    # Direct Model Tests (Mocked)
    # -------------------------

    def test_call_direct_model_requires_loaded_model(self):
        """Test that _call_direct_model requires loaded model."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = True
        gen.model_obj = None
        gen.tokenizer = None
        
        with self.assertRaises(RuntimeError) as context:
            gen._call_direct_model("system", "user", 100, 0.7)
        self.assertIn("Direct model not loaded", str(context.exception))

    @patch('agents.content_creator.text_generator.AutoTokenizer')
    @patch('agents.content_creator.text_generator.PeftModel')
    @patch('agents.content_creator.text_generator.AutoModelForCausalLM')
    def test_load_peft_model_success(self, mock_model, mock_peft, mock_tokenizer):
        """Test successful PEFT model loading."""
        temp_dir = tempfile.mkdtemp()
        try:
            os.environ["PEFT_ADAPTER_PATH"] = temp_dir
            os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
            
            # Mock model and tokenizer
            mock_model_instance = Mock()
            mock_model.return_value = mock_model_instance
            mock_peft_instance = Mock()
            mock_peft.from_pretrained.return_value = mock_peft_instance
            mock_tokenizer_instance = Mock()
            mock_tokenizer_instance.pad_token = None
            mock_tokenizer_instance.eos_token = "<eos>"
            mock_tokenizer.return_value = mock_tokenizer_instance
            
            with patch('agents.content_creator.text_generator.PEFT_AVAILABLE', True):
                with patch('agents.content_creator.text_generator.torch') as mock_torch:
                    mock_torch.cuda.is_available.return_value = False
                    gen = TextGenerator()
                    self.assertTrue(gen.use_direct_model)
                    self.assertIsNotNone(gen.model_obj)
                    self.assertIsNotNone(gen.tokenizer)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # -------------------------
    # Validation Tests
    # -------------------------

    def test_enforce_one_question_and_length_twitter(self):
        """Test enforce_one_question_and_length for Twitter."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        # Twitter should limit to 1-2 sentences
        body = "Sentence 1. Sentence 2. Sentence 3. Sentence 4?"
        result = gen._enforce_one_question_and_length(body, "twitter")
        # Should be truncated to 1 sentence with question
        self.assertLessEqual(len(result.split(". ")), 2)

    def test_enforce_one_question_and_length_facebook_too_short(self):
        """Test enforce_one_question_and_length raises error if Facebook too short."""
        os.environ["ALLOW_DEFAULT_LLM_ENDPOINT"] = "true"
        gen = TextGenerator()
        gen.use_direct_model = False
        
        # Facebook needs 4-6 sentences
        body = "Sentence 1. Sentence 2?"
        with self.assertRaises(ValueError) as context:
            gen._enforce_one_question_and_length(body, "facebook")
        self.assertIn("too short", str(context.exception).lower())


if __name__ == '__main__':
    unittest.main(verbosity=2)
