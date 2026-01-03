"""
Text Generator - Module for generating text content using local LLM endpoints.

Handles creating prompts, calling local LLM endpoints, and processing responses
for different content types and platforms. Designed for use with OpenAI-compatible local endpoints.
"""

import logging
import os
import json
import requests
from typing import Dict, List, Any, Optional, Union
import time

from .brand_guidelines_manager import BrandGuidelinesManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TextGenerator")

class TextGenerator:
    """
    Generates text content using local LLM endpoints.
    Incorporates brand guidelines and platform-specific requirements.
    Designed for use with OpenAI-compatible local endpoints (vLLM, TGI, Ollama, etc.).
    """
    
    def __init__(
        self, 
        brand_manager: BrandGuidelinesManager,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        local_llm_endpoint: Optional[str] = None
    ):
        """
        Initialize the TextGenerator.
        
        Args:
            brand_manager: Brand guidelines manager instance
            model: Model identifier for local LLM
            temperature: Creativity parameter (0.0-1.0)
            max_retries: Maximum number of API call retries
            api_key: Optional API key for local LLM (defaults to LOCAL_LLM_API_KEY env var)
            local_llm_endpoint: Optional local LLM endpoint URL (defaults to LOCAL_LLM_ENDPOINT env var)
        """
        self.brand_manager = brand_manager
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        
        # Check for local LLM endpoint first (takes priority)
        self.local_llm_endpoint = local_llm_endpoint or os.environ.get("LOCAL_LLM_ENDPOINT")
        self.use_local_llm = bool(self.local_llm_endpoint)
        
        if self.use_local_llm:
            logger.info("Using local LLM endpoint: %s", self.local_llm_endpoint)
            # For local LLM, API key is optional (some endpoints don't require it)
            self.api_key = api_key or os.environ.get("LOCAL_LLM_API_KEY")
        else:
            logger.warning("No local LLM endpoint configured. Set LOCAL_LLM_ENDPOINT environment variable.")
            self.api_key = None
        
        logger.info("TextGenerator initialized with model: %s (using local LLM)", model)
    
    def generate_text(
        self, 
        context: Dict[str, Any],
        platform: str,
        max_length: int = 1000,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Generate text content using local LLM endpoint.
        
        Args:
            context: Dictionary containing trend data, brand guidelines, platform guidelines, etc.
            platform: Target platform (twitter, instagram, linkedin, facebook)
            max_length: Maximum length of generated text (in tokens)
            temperature: Optional override for creativity parameter
            
        Returns:
            Dictionary containing generated text content with platform-specific formatting
        """
        if not self.use_local_llm or not self.local_llm_endpoint:
            raise ValueError("Local LLM endpoint not configured. Set LOCAL_LLM_ENDPOINT environment variable.")
        
        # Use instance temperature if not overridden
        temp = temperature if temperature is not None else self.temperature
        
        # Build prompt from context
        prompt = self._build_prompt_from_context(context, platform)
        
        # Track retries
        retries = 0
        while retries <= self.max_retries:
            try:
                logger.info("Generating text for %s platform with trend: %s", 
                           platform, context.get("trend", {}).get("title", "unknown"))
                
                # Use local LLM endpoint (OpenAI-compatible API)
                generated_text = self._call_local_llm(prompt, max_length, temp)
                
                logger.info("Successfully generated text (%d characters)", len(generated_text))
                
                # Format response based on platform
                return self._format_response(generated_text, platform, context)
                
            except requests.exceptions.RequestException as e:
                retries += 1
                wait_time = 2 ** retries  # Exponential backoff
                logger.warning("Request error: %s. Retrying in %d seconds...", str(e), wait_time)
                if retries > self.max_retries:
                    raise
                time.sleep(wait_time)
                
            except Exception as e:
                logger.error("Error generating text: %s", str(e))
                if retries >= self.max_retries:
                    raise
                retries += 1
                wait_time = 2 ** retries
                time.sleep(wait_time)
        
        raise Exception(f"Failed to generate text after {self.max_retries} retries")
    
    def _call_local_llm(self, prompt: str, max_tokens: int, temperature: float) -> str:
        """
        Call a local LLM endpoint using OpenAI-compatible API format.
        
        Args:
            prompt: User prompt
            max_tokens: Maximum tokens to generate
            temperature: Temperature parameter
            
        Returns:
            Generated text
        """
        # Prepare the request payload (OpenAI-compatible format)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._get_system_message()},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "n": 1
        }
        
        # Prepare headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add API key if provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        # Make the request
        response = requests.post(
            self.local_llm_endpoint,
            json=payload,
            headers=headers,
            timeout=120  # 2 minute timeout for local LLM
        )
        
        # Check for errors
        response.raise_for_status()
        
        # Parse response (OpenAI-compatible format)
        response_data = response.json()
        
        # Extract generated text
        if "choices" in response_data and len(response_data["choices"]) > 0:
            generated_text = response_data["choices"][0]["message"]["content"].strip()
            return generated_text
        else:
            raise ValueError(f"Unexpected response format from local LLM: {response_data}")
    
    def _build_prompt_from_context(self, context: Dict[str, Any], platform: str) -> str:
        """
        Build a prompt from context data for text generation.
        
        Args:
            context: Dictionary containing trend data, brand guidelines, etc.
            platform: Target platform
            
        Returns:
            Formatted prompt string
        """
        trend = context.get("trend", {})
        platform_guidelines = context.get("platform_guidelines", {})
        product_info = context.get("product_info", {})
        
        # Build the prompt
        prompt_parts = []
        
        # Add trend information
        if trend.get("title"):
            prompt_parts.append(f"Trending Topic: {trend['title']}")
        if trend.get("description"):
            prompt_parts.append(f"Description: {trend['description']}")
        if trend.get("hashtags"):
            prompt_parts.append(f"Related Hashtags: {', '.join(trend['hashtags'])}")
        
        # Add platform-specific instructions
        if platform_guidelines.get("tone"):
            prompt_parts.append(f"Platform Tone: {platform_guidelines['tone']}")
        if platform_guidelines.get("hashtags"):
            prompt_parts.append(f"Recommended Hashtags: {', '.join(platform_guidelines['hashtags'])}")
        
        # Add product information if available
        if product_info:
            if product_info.get("features"):
                prompt_parts.append(f"Product Features: {product_info['features']}")
        
        # Add platform-specific content requirements
        platform_instructions = {
            "twitter": "Create a brief, engaging tweet (max 280 characters). Be concise and impactful.",
            "instagram": "Create an Instagram caption (max 1000 characters). Focus on visual storytelling and include relevant hashtags.",
            "linkedin": "Create a professional LinkedIn post (max 1000 characters). Focus on insights and professional value.",
            "facebook": "Create an engaging Facebook post (max 1000 characters). Focus on community engagement and sharing."
        }
        
        if platform in platform_instructions:
            prompt_parts.append(platform_instructions[platform])
        
        # Combine all parts
        prompt = "\n\n".join(prompt_parts)
        prompt += "\n\nGenerate engaging social media content that follows the brand guidelines and platform requirements."
        
        return prompt
    
    def _format_response(self, text: str, platform: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the generated text response for the platform.
        
        Args:
            text: Generated text content
            platform: Target platform
            context: Original context dictionary
            
        Returns:
            Dictionary with formatted content
        """
        result = {
            "text": text.strip(),
            "platform": platform
        }
        
        # For Instagram, use "caption" instead of "text"
        if platform == "instagram":
            result["caption"] = text.strip()
            if "text" in result:
                del result["text"]
        
        return result
    
    def _get_system_message(self) -> str:
        """
        Create a system message that includes brand guidelines.
        
        Returns:
            System message string for the local LLM
        """
        # Start with a base message focused on AI solving real-world problems
        system_message = (
            "You are a professional social media content creator specializing in "
            "educational and engaging content about AI solving real-world problems. "
            "Your goal is to create factually accurate, informative, and engaging content "
            "that highlights practical AI applications in healthcare, education, business, "
            "environment, and other industries. Focus on real-world impact and tangible benefits "
            "while following brand guidelines."
        )
        
        # Add brand guidelines if available
        if self.brand_manager.guidelines:
            brand_voice = self.brand_manager.get_brand_voice()
            if brand_voice:
                # Handle both dict and string returns
                if isinstance(brand_voice, dict):
                    voice_desc = brand_voice.get("description", "")
                    traits = brand_voice.get("traits", [])
                    if voice_desc:
                        system_message += f"\n\nBrand Voice: {voice_desc}"
                    if traits:
                        system_message += f"\nBrand Voice Traits: {', '.join(traits)}"
                else:
                    system_message += f"\n\nBrand Voice: {brand_voice}"
            
            brand_requirements = self.brand_manager.get_content_requirements()
            if brand_requirements:
                # Handle both list and string returns
                if isinstance(brand_requirements, list):
                    system_message += f"\n\nContent Requirements: {'; '.join(brand_requirements)}"
                else:
                    system_message += f"\n\nContent Requirements: {brand_requirements}"
            
            prohibited_content = self.brand_manager.get_prohibited_content()
            if prohibited_content:
                # Handle both list and string returns
                if isinstance(prohibited_content, list):
                    system_message += f"\n\nProhibited Content: {'; '.join(prohibited_content)}"
                else:
                    system_message += f"\n\nProhibited Content: {prohibited_content}"
        
        return system_message
    
    def generate_image_prompt(
        self,
        trend: Dict[str, Any],
        platform: str,
        brand_guidelines: Dict[str, Any]
    ) -> str:
        """
        Generate an image prompt based on trend data and brand guidelines.
        
        Args:
            trend: Dictionary containing trend information
            platform: Target platform
            brand_guidelines: Brand guidelines dictionary
            
        Returns:
            Image generation prompt string
        """
        visual_style = brand_guidelines.get("visual_style", {})
        trend_title = trend.get("title", "AI technology")
        trend_description = trend.get("description", "")
        
        # Build image prompt
        prompt_parts = []
        
        # Add visual style description if available
        if visual_style.get("description"):
            prompt_parts.append(visual_style["description"])
        
        # Add trend-related imagery
        prompt_parts.append(f"Modern illustration showing {trend_title}")
        if trend_description:
            prompt_parts.append(f"depicting {trend_description}")
        
        # Add preferred imagery style
        if visual_style.get("preferred_imagery"):
            prompt_parts.append(visual_style["preferred_imagery"])
        
        # Add color scheme if available
        if visual_style.get("colors"):
            colors = ", ".join(visual_style["colors"][:3])  # Use first 3 colors
            prompt_parts.append(f"Color scheme: {colors}")
        
        # Combine all parts
        image_prompt = ", ".join(prompt_parts)
        image_prompt += ", high quality, professional, clean design"
        
        return image_prompt 