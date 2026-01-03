"""
Brand Guidelines Manager - Module for loading and managing brand guidelines.

Handles loading brand guidelines from JSON files and providing access to specific
guideline elements for content generation.
"""

import logging
import os
import json
from typing import Dict, List, Any, Optional, Union

class BrandGuidelinesManager:
    """
    Manages brand guidelines for content generation.
    
    This class is responsible for loading brand guidelines from JSON files
    and providing structured access to different guideline components like
    brand voice, content requirements, visual style, and platform-specific
    guidelines.
    """
    
    def __init__(self, guidelines_path: Optional[str] = None):
        """
        Initialize the BrandGuidelinesManager.
        
        Args:
            guidelines_path: Path to the JSON file containing brand guidelines
        """
        self.logger = logging.getLogger(__name__)
        self.guidelines = None
        
        # Load guidelines if path is provided
        if guidelines_path:
            self.load_guidelines(guidelines_path)
        else:
            # If no guidelines provided, use default AI-focused brand voice
            self.guidelines = self._get_default_guidelines()
            self.logger.info("Using default brand guidelines for AI-focused content")
    
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
                self.logger.warning("Guidelines file not found: %s", guidelines_path)
                return False
            
            with open(guidelines_path, 'r') as f:
                self.guidelines = json.load(f)
            
            self.logger.info("Successfully loaded brand guidelines from %s", guidelines_path)
            return True
            
        except json.JSONDecodeError:
            self.logger.error("Invalid JSON format in guidelines file: %s", guidelines_path)
            return False
            
        except Exception as e:
            self.logger.error("Error loading guidelines: %s", str(e))
            return False
    
    def get_guidelines(self) -> Dict[str, Any]:
        """
        Get the full brand guidelines.
        
        Returns:
            Dictionary containing all brand guidelines
        """
        if not self.guidelines:
            return self._get_default_guidelines()
        
        return self.guidelines
    
    def get_brand_voice(self) -> Dict[str, Any]:
        """
        Get the brand voice guidelines.
        
        Returns:
            Dictionary containing brand voice information
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("voice", {})
        
        return self.guidelines.get("voice", {})
    
    def get_content_requirements(self) -> List[str]:
        """
        Get the content requirements guidelines.
        
        Returns:
            List of content requirements
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("content_requirements", [])
        
        return self.guidelines.get("content_requirements", [])
    
    def get_prohibited_content(self) -> List[str]:
        """
        Get the prohibited content guidelines.
        
        Returns:
            List of prohibited content types
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("prohibited_content", [])
        
        return self.guidelines.get("prohibited_content", [])
    
    def get_visual_style(self) -> Dict[str, Any]:
        """
        Get the visual style guidelines.
        
        Returns:
            Dictionary containing visual style guidelines
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("visual_style", {})
        
        return self.guidelines.get("visual_style", {})
    
    def get_platform_guidelines(self, platform: str) -> Dict[str, Any]:
        """
        Get platform-specific guidelines.
        
        Args:
            platform: Platform name (twitter, instagram, linkedin, facebook)
            
        Returns:
            Dictionary containing platform-specific guidelines
        """
        if not self.guidelines or "platforms" not in self.guidelines:
            default = self._get_default_guidelines().get("platforms", {})
            return default.get(platform.lower(), {})
        
        platforms = self.guidelines.get("platforms", {})
        return platforms.get(platform.lower(), {})
    
    def get_product_mentions(self) -> Dict[str, Any]:
        """
        Get requirements for how to mention products.
        
        Returns:
            Dictionary containing product mention guidelines
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("product_mentions", {})
        
        return self.guidelines.get("product_mentions", {})
    
    def get_target_audience(self) -> Dict[str, Any]:
        """
        Get target audience information.
        
        Returns:
            Dictionary containing target audience information
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("target_audience", {})
        
        return self.guidelines.get("target_audience", {})
    
    def get_product_features(self) -> List[Dict[str, Any]]:
        """
        Get product features information.
        
        Returns:
            List of product features
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("product_features", [])
        
        return self.guidelines.get("product_features", [])
    
    def get_attribution(self) -> Dict[str, Any]:
        """
        Get attribution configuration.
        
        Returns:
            Dictionary containing attribution settings
        """
        if not self.guidelines:
            return self._get_default_guidelines().get("attribution", {})
        
        return self.guidelines.get("attribution", {})
    
    def _get_default_guidelines(self) -> Dict[str, Any]:
        """
        Create default brand guidelines for AI-focused content about solving real-world problems.
        
        Returns:
            Dictionary containing default guidelines
        """
        return {
            "brand_name": "Elevare by Amaziah",
            "attribution": {
                "enabled": True,
                "style": "subtle",
                "default_line": "- Elevare by Amaziah",
                "long_form": "Insights from Elevare by Amaziah, building real-world systems with AI."
            },
            "voice": {
                "description": "Educational, enthusiastic, and authoritative but accessible. Focus on real-world impact and practical applications.",
                "traits": [
                    "Friendly language that makes AI concepts approachable",
                    "Conversational but accurate about AI capabilities",
                    "Balances technical precision with engaging explanations",
                    "Passionate about AI solving real-world problems",
                    "Emphasizes practical benefits and tangible outcomes",
                    "Inspiring and forward-thinking tone"
                ]
            },
            "content_requirements": [
                "Focus on AI solving real-world problems and practical applications",
                "Emphasize tangible benefits and outcomes, not just technology",
                "Use clear, accessible language that explains AI concepts",
                "Ensure all AI claims are accurate and substantiated",
                "Relate content to current trends and real-world use cases",
                "Include examples of AI applications in healthcare, education, business, environment, etc.",
                "Highlight success stories and case studies when relevant"
            ],
            "prohibited_content": [
                "Political statements",
                "Religious references",
                "Criticism of other brands or products",
                "Exaggerated or unsubstantiated AI claims",
                "Overly technical jargon without explanation",
                "Fear-mongering about AI",
                "Speculative or unproven AI capabilities"
            ],
            "visual_style": {
                "description": "Clean, modern aesthetic with tech-forward theme",
                "colors": ["#0066FF", "#00D4FF", "#FFFFFF", "#1A1A1A", "#00FF88"],
                "preferred_imagery": "Modern tech illustrations, real-world application visuals, data visualizations",
                "diagrams": "Clear infographics showing AI impact and use cases"
            },
            "product_mentions": {
                "first_mention": "AI solutions",
                "subsequent_mentions": ["AI", "artificial intelligence", "machine learning"],
                "emphasis": "Focus on outcomes and benefits, not just technology features"
            },
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
            },
            "product_features": [
                {
                    "name": "AI in Healthcare",
                    "description": "AI applications improving medical diagnosis, treatment, and patient care",
                    "benefit": "Better health outcomes and more accessible healthcare"
                },
                {
                    "name": "AI in Education",
                    "description": "Personalized learning, intelligent tutoring systems, and educational tools",
                    "benefit": "Enhanced learning experiences and improved educational outcomes"
                },
                {
                    "name": "AI in Business",
                    "description": "Automation, predictive analytics, and intelligent decision-making systems",
                    "benefit": "Increased efficiency, cost savings, and better business decisions"
                },
                {
                    "name": "AI for Environment",
                    "description": "Climate modeling, resource optimization, and environmental monitoring",
                    "benefit": "Sustainable solutions and environmental protection"
                }
            ],
            "target_audience": {
                "primary": [
                    "Tech enthusiasts interested in AI applications",
                    "Business professionals exploring AI solutions",
                    "Educators and students learning about AI",
                    "Healthcare professionals interested in AI tools"
                ],
                "secondary": [
                    "General public curious about AI impact",
                    "Developers and engineers",
                    "Policy makers and thought leaders",
                    "Investors in AI technology"
                ]
            }
        } 