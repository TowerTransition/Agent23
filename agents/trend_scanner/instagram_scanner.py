"""
Instagram Scanner - Module for scanning Instagram for trending hashtags and content formats.

Uses Instagram Graph API to search for specific hashtags and analyze trending content.
"""

import logging
import requests
import os
from typing import Dict, List, Any, Optional
from datetime import datetime
import time

logger = logging.getLogger("InstagramScanner")

class InstagramScanner:
    """
    Scanner for Instagram trending hashtags and content formats.
    Uses Instagram Graph API to search for hashtags and analyze popular content.
    """
    
    def __init__(self, relevant_topics: List[str]):
        """
        Initialize the Instagram scanner.
        
        Args:
            relevant_topics: List of topics relevant to our domain
        """
        self.relevant_topics = [topic.lower() for topic in relevant_topics]
        
        # Convert topics to hashtags by removing spaces and adding variations
        self.relevant_hashtags = self._generate_hashtag_variations(relevant_topics)
        
        # Load API credentials from environment variables
        self.access_token = os.environ.get("INSTAGRAM_ACCESS_TOKEN")
        self.app_id = os.environ.get("INSTAGRAM_APP_ID")
        self.app_secret = os.environ.get("INSTAGRAM_APP_SECRET")
        self.instagram_account_id = os.environ.get("INSTAGRAM_ACCOUNT_ID")
        
        # API endpoints
        self.base_url = "https://graph.facebook.com/v18.0"
        
        logger.info("InstagramScanner initialized with %d relevant hashtags", 
                   len(self.relevant_hashtags))
    
    def _generate_hashtag_variations(self, topics: List[str]) -> List[str]:
        """
        Generate hashtag variations from topics focused on AI solving real-world problems.
        
        Args:
            topics: List of topic keywords (AI-focused)
            
        Returns:
            List of hashtag variations
        """
        hashtags = []
        
        for topic in topics:
            # Add the basic topic as a hashtag (remove spaces, lowercase)
            topic_clean = topic.lower().replace(" ", "")
            hashtags.append(topic_clean)
            
            # Add common AI-focused variations
            if "ai" in topic.lower() or "artificial intelligence" in topic.lower():
                hashtags.extend(["ai", "artificialintelligence", "machinelearning", "ml", "aiinnovation", 
                               "aitech", "airevolution", "aifuture", "aiapplications"])
            elif "machine learning" in topic.lower() or "ml" in topic.lower():
                hashtags.extend(["machinelearning", "ml", "deeplearning", "neuralnetworks", 
                               "datascience", "mlmodels"])
            elif "healthcare" in topic.lower() or "health" in topic.lower():
                hashtags.extend(["aihealthcare", "aihealth", "medicalai", "healthtech", 
                               "aiinmedicine", "digitalhealth"])
            elif "education" in topic.lower():
                hashtags.extend(["aieducation", "edtech", "aiineducation", "learningai", 
                               "educationalai", "smartlearning"])
            elif "business" in topic.lower():
                hashtags.extend(["aibusiness", "businessai", "aiforbusiness", "enterpriseai", 
                               "aiautomation", "businessintelligence"])
            elif "environment" in topic.lower() or "climate" in topic.lower():
                hashtags.extend(["aienvironment", "climateai", "greenai", "sustainableai", 
                               "ai4climate", "environmentalai"])
            elif "real world" in topic.lower() or "real-world" in topic.lower():
                hashtags.extend(["airealworld", "realworldai", "aiapplications", "practicalai", 
                               "aiusecases", "airealworldproblems"])
            elif "for good" in topic.lower() or "forgood" in topic.lower():
                hashtags.extend(["aiforgood", "ai4good", "ethicalai", "responsibleai", 
                               "socialgoodai", "positiveai"])
            
            # Add variations with common suffixes
            hashtags.append(f"{topic_clean}tech")
            hashtags.append(f"{topic_clean}innovation")
            hashtags.append(f"{topic_clean}applications")
        
        # Remove duplicates
        return list(set(hashtags))
    
    def get_trending_hashtags(self) -> Dict[str, Any]:
        """
        Get trending hashtags and content formats from Instagram.
        
        Returns:
            Dictionary containing trending hashtags and popular content formats
        """
        try:
            if not self.access_token:
                raise ValueError("Instagram access token is not configured")
            
            # For each relevant hashtag, get its popularity data
            hashtag_data = []
            
            for hashtag in self.relevant_hashtags[:10]:  # Limit to prevent API rate limits
                hashtag_id = self._get_hashtag_id(hashtag)
                if hashtag_id:
                    # Get top media for this hashtag
                    top_media = self._get_top_media(hashtag_id)
                    
                    # Add hashtag information to our results
                    hashtag_data.append({
                        "name": hashtag,
                        "id": hashtag_id,
                        "post_count": len(top_media),
                        "recent_top_posts": len(top_media),
                        "engagement_score": self._calculate_engagement(top_media)
                    })
                
                # Respect API rate limits
                time.sleep(1)
            
            # Sort hashtags by engagement score
            hashtag_data.sort(key=lambda x: x["engagement_score"], reverse=True)
            
            # Detect popular content formats
            formats = self._detect_popular_formats()
            
            return {
                "trending_hashtags": hashtag_data[:10],  # Top 10 hashtags
                "popular_formats": formats,
                "timestamp": datetime.now()
            }
        
        except Exception as e:
            logger.error("Error fetching Instagram trends: %s", str(e))
            raise
    
    def _get_hashtag_id(self, hashtag: str) -> Optional[str]:
        """
        Get the Instagram ID for a hashtag.
        
        Args:
            hashtag: The hashtag to look up (without #)
            
        Returns:
            Hashtag ID or None if not found
        """
        try:
            url = f"{self.base_url}/ig_hashtag_search"
            params = {
                "user_id": self.instagram_account_id,
                "q": hashtag,
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['id']
            
            logger.warning("Hashtag %s not found", hashtag)
            return None
            
        except Exception as e:
            logger.error("Error getting hashtag ID for %s: %s", hashtag, str(e))
            return None
    
    def _get_top_media(self, hashtag_id: str) -> List[Dict[str, Any]]:
        """
        Get top media for a hashtag.
        
        Args:
            hashtag_id: Instagram ID for the hashtag
            
        Returns:
            List of media items
        """
        try:
            url = f"{self.base_url}/{hashtag_id}/top_media"
            params = {
                "user_id": self.instagram_account_id,
                "fields": "id,caption,media_type,permalink,thumbnail_url,media_url,like_count,comments_count",
                "access_token": self.access_token
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'data' in data:
                return data['data']
            
            return []
            
        except Exception as e:
            logger.error("Error getting top media for hashtag %s: %s", hashtag_id, str(e))
            return []
    
    def _calculate_engagement(self, media_items: List[Dict[str, Any]]) -> float:
        """
        Calculate engagement score for a set of media items.
        
        Args:
            media_items: List of media items with engagement data
            
        Returns:
            Engagement score (higher is better)
        """
        if not media_items:
            return 0.0
        
        total_likes = sum(item.get('like_count', 0) for item in media_items)
        total_comments = sum(item.get('comments_count', 0) for item in media_items)
        
        # Simple engagement formula: (likes + comments*2) / post count
        # Comments are weighted more as they require more effort
        return (total_likes + total_comments * 2) / len(media_items)
    
    def _detect_popular_formats(self) -> List[Dict[str, str]]:
        """
        Detect popular content formats currently used on Instagram for AI content.
        
        Returns:
            List of dictionaries describing popular content formats
        """
        # This is a placeholder - in a real implementation, 
        # we would analyze actual Instagram posts to identify formats
        formats = [
            {
                "name": "Carousel",
                "description": "Multi-image posts explaining AI applications and use cases"
            },
            {
                "name": "Reels",
                "description": "Short-form vertical videos showcasing AI demonstrations and real-world applications"
            },
            {
                "name": "Infographic",
                "description": "Educational information about AI solving real-world problems in visually appealing graphics"
            },
            {
                "name": "Case Study",
                "description": "Before/after posts showing AI impact in healthcare, business, or other industries"
            },
            {
                "name": "Data Visualization",
                "description": "Charts and graphs showing AI results and metrics"
            }
        ]
        
        return formats 