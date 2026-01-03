"""
Platform Formatter - Module for formatting content for different social media platforms.

This module provides functionality to format text and image content for various
social media platforms according to their specific requirements and best practices.
"""

import logging
import re
from typing import Dict, List, Any, Optional, Union

class PlatformFormatter:
    """
    Formats content for different social media platforms.
    
    This class handles platform-specific formatting rules, character limits,
    hashtag placement, and other platform requirements to ensure content
    is optimized for each target platform.
    """
    
    def __init__(self, brand_guidelines: Dict[str, Any] = None):
        """
        Initialize the PlatformFormatter.
        
        Args:
            brand_guidelines: Dictionary containing brand guidelines
        """
        self.logger = logging.getLogger(__name__)
        self.brand_guidelines = brand_guidelines or {}
        
        # Platform-specific constraints
        self.platform_constraints = {
            "twitter": {
                "max_length": 280,
                "hashtag_limit": 3,
                "ideal_image_ratio": "16:9"
            },
            "instagram": {
                "max_length": 1000,  # Shorter posts perform better - most people don't like to read long content
                "hashtag_limit": 30,
                "ideal_image_ratio": "1:1"
            },
            "linkedin": {
                "max_length": 1000,  # Shorter posts perform better - most people don't like to read long content
                "hashtag_limit": 5,
                "ideal_image_ratio": "1.91:1"
            },
            "facebook": {
                "max_length": 1000,  # Shorter posts perform better - most people don't like to read long content
                "hashtag_limit": 5,
                "ideal_image_ratio": "1.91:1"  # Landscape format works well for Facebook
            }
        }
        
        # Get attribution settings
        self.attribution = self.brand_guidelines.get("attribution", {})
        self.attribution_enabled = self.attribution.get("enabled", False)
        
        self.logger.info("PlatformFormatter initialized (attribution enabled: %s)", self.attribution_enabled)
    
    def format_for_platform(
        self, 
        content: Dict[str, Any],
        platform: str
    ) -> Dict[str, Any]:
        """
        Format content for a specific platform.
        
        Args:
            content: Dictionary containing generated content
            platform: Target platform (twitter, instagram, linkedin, facebook)
            
        Returns:
            Formatted content dictionary
        """
        if platform not in self.platform_constraints:
            self.logger.error(f"Unsupported platform: {platform}")
            return {"error": f"Unsupported platform: {platform}"}
        
        # Apply platform-specific formatting
        if platform == "twitter":
            return self._format_for_twitter(content)
        elif platform == "instagram":
            return self._format_for_instagram(content)
        elif platform == "linkedin":
            return self._format_for_linkedin(content)
        elif platform == "facebook":
            return self._format_for_facebook(content)
        
        return content
    
    def _format_for_twitter(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format content for Twitter.
        
        Args:
            content: Dictionary containing generated content
            
        Returns:
            Formatted content dictionary
        """
        formatted = content.copy()
        constraints = self.platform_constraints["twitter"]
        
        # Get text content
        text = formatted.get("text", "")
        
        # Extract hashtags
        hashtags = self.extract_hashtags(text)
        if hashtags:
            formatted["hashtags"] = hashtags
        
        # Add attribution if enabled (before checking length)
        if self.attribution_enabled:
            attribution_line = self.attribution.get("default_line", "")
            if attribution_line:
                # Add attribution with a line break
                text = text.rstrip() + "\n\n" + attribution_line
        
        # Check if text exceeds max length
        if len(text) > constraints["max_length"]:
            # Truncate text, but try to preserve attribution
            if self.attribution_enabled:
                attribution_line = self.attribution.get("default_line", "")
                attribution_len = len(attribution_line) + 2  # +2 for \n\n
                # Reserve space for attribution
                trunc_length = constraints["max_length"] - attribution_len - 3
                if trunc_length > 0:
                    formatted["text"] = text[:trunc_length] + "..." + "\n\n" + attribution_line
                else:
                    # Not enough space, just truncate
                    trunc_length = constraints["max_length"] - 3
                    formatted["text"] = text[:trunc_length] + "..."
            else:
                trunc_length = constraints["max_length"] - 3
                formatted["text"] = text[:trunc_length] + "..."
            self.logger.warning(f"Twitter text truncated from {len(text)} to {constraints['max_length']} characters")
        else:
            formatted["text"] = text
        
        # Set image aspect ratio
        formatted["image_ratio"] = constraints["ideal_image_ratio"]
        
        # Set platform
        formatted["platform"] = "twitter"
        
        return formatted
    
    def _format_for_instagram(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format content for Instagram.
        
        Args:
            content: Dictionary containing generated content
            
        Returns:
            Formatted content dictionary
        """
        formatted = content.copy()
        constraints = self.platform_constraints["instagram"]
        
        # Get caption content
        caption = formatted.get("caption", "")
        if not caption and "text" in formatted:
            caption = formatted["text"]
        
        # Extract hashtags
        hashtags = self.extract_hashtags(caption)
        if hashtags:
            formatted["hashtags"] = hashtags
        
        # Add attribution if enabled (before checking length)
        if self.attribution_enabled:
            attribution_line = self.attribution.get("default_line", "")
            if attribution_line:
                caption = caption.rstrip() + "\n\n" + attribution_line
        
        # Check if caption exceeds max length
        if len(caption) > constraints["max_length"]:
            # Truncate caption, but try to preserve attribution
            if self.attribution_enabled:
                attribution_line = self.attribution.get("default_line", "")
                attribution_len = len(attribution_line) + 2  # +2 for \n\n
                trunc_length = constraints["max_length"] - attribution_len - 3
                if trunc_length > 0:
                    formatted["caption"] = caption[:trunc_length] + "..." + "\n\n" + attribution_line
                else:
                    trunc_length = constraints["max_length"] - 3
                    formatted["caption"] = caption[:trunc_length] + "..."
            else:
                trunc_length = constraints["max_length"] - 3
                formatted["caption"] = caption[:trunc_length] + "..."
            self.logger.warning(f"Instagram caption truncated from {len(caption)} to {constraints['max_length']} characters")
        else:
            formatted["caption"] = caption
        
        # Set image aspect ratio
        formatted["image_ratio"] = constraints["ideal_image_ratio"]
        
        # Set platform
        formatted["platform"] = "instagram"
        
        return formatted
    
    def _format_for_linkedin(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format content for LinkedIn.
        
        Args:
            content: Dictionary containing generated content
            
        Returns:
            Formatted content dictionary
        """
        formatted = content.copy()
        constraints = self.platform_constraints["linkedin"]
        
        # Get text content
        text = formatted.get("text", "")
        
        # Extract hashtags
        hashtags = self.extract_hashtags(text)
        if hashtags:
            formatted["hashtags"] = hashtags
        
        # Add attribution if enabled (use long_form for LinkedIn if space allows)
        if self.attribution_enabled:
            long_form = self.attribution.get("long_form", "")
            default_line = self.attribution.get("default_line", "")
            if long_form and len(text) + len(long_form) + 2 <= constraints["max_length"]:
                text = text.rstrip() + "\n\n" + long_form
            elif default_line:
                text = text.rstrip() + "\n\n" + default_line
        
        # Check if text exceeds max length
        if len(text) > constraints["max_length"]:
            # Truncate text, but try to preserve attribution
            if self.attribution_enabled:
                default_line = self.attribution.get("default_line", "")
                attribution_len = len(default_line) + 2
                trunc_length = constraints["max_length"] - attribution_len - 3
                if trunc_length > 0:
                    formatted["text"] = text[:trunc_length] + "..." + "\n\n" + default_line
                else:
                    trunc_length = constraints["max_length"] - 3
                    formatted["text"] = text[:trunc_length] + "..."
            else:
                trunc_length = constraints["max_length"] - 3
                formatted["text"] = text[:trunc_length] + "..."
            self.logger.warning(f"LinkedIn text truncated from {len(text)} to {constraints['max_length']} characters")
        else:
            formatted["text"] = text
        
        # Set image aspect ratio
        formatted["image_ratio"] = constraints["ideal_image_ratio"]
        
        # Set platform
        formatted["platform"] = "linkedin"
        
        return formatted
    
    def _format_for_facebook(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format content for Facebook.
        
        Args:
            content: Dictionary containing generated content
            
        Returns:
            Formatted content dictionary
        """
        formatted = content.copy()
        constraints = self.platform_constraints["facebook"]
        
        # Get text content
        text = formatted.get("text", "")
        
        # Extract hashtags
        hashtags = self.extract_hashtags(text)
        if hashtags:
            formatted["hashtags"] = hashtags
        
        # Add attribution if enabled (use long_form for Facebook if space allows)
        if self.attribution_enabled:
            long_form = self.attribution.get("long_form", "")
            default_line = self.attribution.get("default_line", "")
            if long_form and len(text) + len(long_form) + 2 <= constraints["max_length"]:
                text = text.rstrip() + "\n\n" + long_form
            elif default_line:
                text = text.rstrip() + "\n\n" + default_line
        
        # Check if text exceeds max length (shorter posts perform better - most people don't like to read long content)
        if len(text) > constraints["max_length"]:
            # Truncate text, but try to preserve attribution
            if self.attribution_enabled:
                default_line = self.attribution.get("default_line", "")
                attribution_len = len(default_line) + 2
                trunc_length = constraints["max_length"] - attribution_len - 3
                if trunc_length > 0:
                    formatted["text"] = text[:trunc_length] + "..." + "\n\n" + default_line
                else:
                    trunc_length = constraints["max_length"] - 3
                    formatted["text"] = text[:trunc_length] + "..."
            else:
                trunc_length = constraints["max_length"] - 3
                formatted["text"] = text[:trunc_length] + "..."
            self.logger.warning(f"Facebook text truncated from {len(text)} to {constraints['max_length']} characters")
        else:
            formatted["text"] = text
        
        # Set image aspect ratio
        formatted["image_ratio"] = constraints["ideal_image_ratio"]
        
        # Set platform
        formatted["platform"] = "facebook"
        
        return formatted
    
    def extract_hashtags(self, text: str) -> List[str]:
        """
        Extract hashtags from text.
        
        Args:
            text: Text to extract hashtags from
            
        Returns:
            List of hashtags (without # symbol)
        """
        if not text:
            return []
        
        # Find all hashtags in the text
        hashtag_pattern = r'#(\w+)'
        hashtags = re.findall(hashtag_pattern, text)
        
        # Remove duplicates while preserving order
        unique_hashtags = []
        for tag in hashtags:
            if tag not in unique_hashtags:
                unique_hashtags.append(tag)
        
        return unique_hashtags
    
    def get_image_aspect_ratio(self, platform: str) -> str:
        """
        Get the ideal image aspect ratio for a platform.
        
        Args:
            platform: Target platform
            
        Returns:
            Aspect ratio string (e.g., "1:1", "16:9")
        """
        if platform not in self.platform_constraints:
            return "1:1"  # Default to square
        
        return self.platform_constraints[platform].get("ideal_image_ratio", "1:1")
    
    def get_max_hashtags(self, platform: str) -> int:
        """
        Get the maximum recommended number of hashtags for a platform.
        
        Args:
            platform: Target platform
            
        Returns:
            Maximum number of hashtags
        """
        if platform not in self.platform_constraints:
            return 3  # Conservative default
        
        return self.platform_constraints[platform].get("hashtag_limit", 3)
    
    def get_max_length(self, platform: str) -> int:
        """
        Get the maximum text length for a platform.
        
        Args:
            platform: Target platform
            
        Returns:
            Maximum text length in characters
        """
        if platform not in self.platform_constraints:
            return 280  # Conservative default
        
        return self.platform_constraints[platform].get("max_length", 280) 