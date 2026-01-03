"""
Brand Guidelines Manager - Module for loading and managing brand guidelines.

Handles loading brand guidelines from JSON files and providing access to specific
guideline elements for content generation.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("BrandGuidelinesManager")

class BrandGuidelinesManager:
    """
    Manages brand guidelines for content generation.
    Loads guidelines from JSON files and provides access to specific elements.
    """
    
    def __init__(self, guidelines_path: Optional[str] = None):
        """
        Initialize the BrandGuidelinesManager.
        
        Args:
            guidelines_path: Path to the JSON file containing brand guidelines
        """
        self.guidelines = None
        
        # Load guidelines if path is provided
        if guidelines_path:
            self.load_guidelines(guidelines_path)
        else:
            # If no guidelines provided, use default AI-focused brand voice
            self.guidelines = self._get_default_guidelines()
            logger.info("Using default brand guidelines for AI-focused content")
    
    def load_guidelines(self, guidelines_path: str) -> bool:
        """
        Load brand guidelines from a JSON file.
        
        Args:
            guidelines_path: Path to the JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(guidelines_path):
                logger.warning("Guidelines file not found: %s", guidelines_path)
                return False
            
            with open(guidelines_path, 'r') as f:
                self.guidelines = json.load(f)
            
            logger.info("Successfully loaded brand guidelines from %s", guidelines_path)
            return True
            
        except json.JSONDecodeError:
            logger.error("Invalid JSON format in guidelines file: %s", guidelines_path)
            return False
            
        except Exception as e:
            logger.error("Error loading guidelines: %s", str(e))
            return False
    
    def get_brand_voice(self) -> str:
        """
        Get the brand voice description from guidelines.
        
        Returns:
            String describing the brand voice
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("voice", "")
        
        return self.guidelines.get("voice", "")
    
    def get_content_requirements(self) -> str:
        """
        Get the content requirements from guidelines.
        
        Returns:
            String describing content requirements
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("content_requirements", "")
        
        return self.guidelines.get("content_requirements", "")
    
    def get_prohibited_content(self) -> str:
        """
        Get the prohibited content guidelines.
        
        Returns:
            String describing prohibited content
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("prohibited", "")
        
        return self.guidelines.get("prohibited", "")
    
    def get_visual_style(self) -> str:
        """
        Get the visual style guidelines.
        
        Returns:
            String describing visual style
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("visual_style", "")
        
        return self.guidelines.get("visual_style", "")
    
    def get_platform_specific_guidelines(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific guidelines.
        
        Args:
            platform: Platform name (twitter, instagram, linkedin, facebook)
            
        Returns:
            Dictionary of platform-specific guidelines
        """
        if not self.guidelines or "platforms" not in self.guidelines:
            return {}
        
        platforms = self.guidelines.get("platforms", {})
        return platforms.get(platform.lower(), {})
    
    def get_product_mention_requirements(self) -> str:
        """
        Get requirements for how to mention products.
        
        Returns:
            String describing product mention requirements
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("product_mentions", "")
        
        return self.guidelines.get("product_mentions", "")
    
    def _get_default_guidelines(self) -> Dict[str, Any]:
        """
        Create default brand guidelines for AI-focused content about solving real-world problems.
        
        Returns:
            Dictionary containing default guidelines
        """
        return {
            "voice": (
                "Educational, enthusiastic, and authoritative but accessible. "
                "Focus on real-world impact and practical applications of AI. "
                "Use friendly language that makes AI concepts approachable. "
                "Be conversational but accurate about AI capabilities. "
                "Balance technical precision with engaging explanations. "
                "Emphasize practical benefits and tangible outcomes. "
                "Inspiring and forward-thinking tone."
            ),
            "content_requirements": (
                "Focus on AI solving real-world problems and practical applications. "
                "Emphasize tangible benefits and outcomes, not just technology. "
                "Use clear, accessible language that explains AI concepts. "
                "Ensure all AI claims are accurate and substantiated. "
                "Relate content to current trends and real-world use cases. "
                "Include examples of AI applications in healthcare, education, business, environment, etc. "
                "Highlight success stories and case studies when relevant."
            ),
            "prohibited": (
                "Avoid political statements. No religious references. "
                "Don't criticize other brands or products. "
                "No exaggerated or unsubstantiated AI claims. "
                "Avoid overly technical jargon without explanation. "
                "No fear-mongering about AI. "
                "No speculative or unproven AI capabilities."
            ),
            "visual_style": (
                "Clean, modern aesthetic with tech-forward theme. "
                "Use modern tech illustrations, real-world application visuals, and data visualizations. "
                "Clear infographics showing AI impact and use cases."
            ),
            "product_mentions": (
                "Focus on AI solutions and outcomes, not specific products. "
                "Emphasize benefits and real-world impact. "
                "Highlight one AI application or use case per post. "
                "Phrase as a benefit, not just a technology feature."
            ),
            "platforms": {
                "twitter": {
                    "tone": "Casual, brief but impactful, trend-aware",
                    "hashtags": ["#AI", "#MachineLearning", "#AISolves", "#TechForGood", "#AIApplications", "#RealWorldAI"],
                    "cta": "Encourage engagement and discussion about AI solutions"
                },
                "instagram": {
                    "tone": "Visual first, focus on impact and transformation",
                    "hashtags": ["#AI", "#MachineLearning", "#AISolves", "#TechForGood", "#AIforGood", "#AIApplications", "#RealWorldAI", "#Innovation"],
                    "cta": "Encourage profile visits and sharing of AI success stories"
                },
                "linkedin": {
                    "tone": "Professional, educational focus, industry insights",
                    "hashtags": ["#AI", "#MachineLearning", "#ArtificialIntelligence", "#TechInnovation", "#DigitalTransformation", "#AIinBusiness"],
                    "cta": "Position as thought leaders, encourage professional discussion about AI applications"
                },
                "facebook": {
                    "tone": "Engaging, community-focused, accessible",
                    "hashtags": ["#AI", "#MachineLearning", "#AISolves", "#TechForGood", "#AIApplications", "#Innovation"],
                    "cta": "Encourage community engagement and sharing of AI impact stories",
                    "focus": "Use the highest trending topic related to AI solving real-world problems"
                }
            }
        } 