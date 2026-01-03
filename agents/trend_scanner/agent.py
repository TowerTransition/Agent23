"""
TrendScannerAgent - Monitors social media platforms for trending topics and content formats.

This agent periodically scans Twitter/X, Instagram, LinkedIn, and Facebook to identify trending
hashtags, topics, and content formats relevant to AI solving real-world problems, artificial
intelligence applications, and machine learning innovations. It also identifies the highest
trending topic for Facebook posting priority.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from .twitter_scanner import TwitterScanner
from .instagram_scanner import InstagramScanner
from .linkedin_scanner import LinkedInScanner
from .cache_manager import CacheManager
from .article_searcher import ArticleSearcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("TrendScannerAgent")

class TrendScannerAgent:
    """Agent responsible for scanning social media platforms for trending topics and formats."""
    
    def __init__(
        self, 
        cache_duration: int = 3600,  # Default cache duration: 1 hour
        relevant_topics: List[str] = None
    ):
        """
        Initialize the TrendScannerAgent.
        
        Args:
            cache_duration: Time in seconds before refreshing trends data
            relevant_topics: List of topics of interest (AI solving real-world problems, etc.)
        """
        self.cache_manager = CacheManager()
        self.cache_duration = cache_duration
        
        # Initialize default relevant topics if none provided - focused on AI solving real-world problems
        self.relevant_topics = relevant_topics or [
            "AI solving real world problems", "artificial intelligence", "machine learning",
            "AI applications", "AI healthcare", "AI education", "AI business",
            "AI environment", "AI innovation", "ML real world", "AI tools",
            "AI use cases", "AI success stories", "AI for good"
        ]
        
        # Initialize platform scanners
        self.twitter_scanner = TwitterScanner(self.relevant_topics)
        self.instagram_scanner = InstagramScanner(self.relevant_topics)
        self.linkedin_scanner = LinkedInScanner(self.relevant_topics)
        
        # Initialize article searcher for AI articles
        self.article_searcher = ArticleSearcher(search_query="AI solving real world problems")
        
        logger.info("TrendScannerAgent initialized with %d relevant topics", 
                   len(self.relevant_topics))

    def scan_all_platforms(self, include_articles: bool = False) -> Dict[str, Any]:
        """
        Scan all social media platforms for trends.
        
        Args:
            include_articles: Whether to search for articles about AI solving real-world problems
            
        Returns:
            Dict containing trend data for each platform
        """
        # Check if we have cached data that's still valid
        cached_data = self.cache_manager.get_cached_trends()
        if cached_data and not self._is_cache_expired(cached_data.get('timestamp')):
            logger.info("Using cached trend data from %s", 
                       cached_data.get('timestamp').strftime('%Y-%m-%d %H:%M:%S'))
            return cached_data.get('data')
        
        # If no valid cache, scan all platforms
        logger.info("Scanning all platforms for trends")
        
        # Collect trend data from each platform
        trends_data = {
            "timestamp": datetime.now(),
            "twitter": self._scan_twitter(),
            "instagram": self._scan_instagram(),
            "linkedin": self._scan_linkedin(),
            "facebook": {}  # Facebook trends (can be populated if Facebook API is available)
        }
        
        # Identify highest trending topic across all platforms for Facebook priority
        all_trends = []
        for platform in ["twitter", "instagram", "linkedin"]:
            platform_data = trends_data.get(platform, {})
            if "error" not in platform_data:
                hashtags = platform_data.get("trending_hashtags", [])
                topics = platform_data.get("topics", [])
                trending_topics = platform_data.get("trending_topics", [])
                all_trends.extend(hashtags)
                all_trends.extend(topics)
                all_trends.extend(trending_topics)
        
        # Find highest trending topic (by volume or relevance score)
        if all_trends:
            highest_trend = max(
                all_trends,
                key=lambda x: (
                    x.get('tweet_volume', 0) or x.get('volume', 0) or x.get('engagement', 0),
                    x.get('relevance_score', 0)
                )
            )
            trends_data["highest_trending_topic"] = highest_trend
            trends_data["facebook_priority_topic"] = highest_trend  # For Facebook posting
            logger.info("Identified highest trending topic for Facebook: %s (Volume: %s)",
                       highest_trend.get('name', 'N/A'),
                       highest_trend.get('tweet_volume') or highest_trend.get('volume', 0))
        
        # Search for articles if requested
        if include_articles:
            logger.info("Searching for articles about AI solving real-world problems")
            articles = self.article_searcher.find_articles(count=2)
            trends_data["articles"] = articles
            logger.info("Found %d articles", len(articles))
        
        # Cache the results
        self.cache_manager.cache_trends(trends_data)
        
        return trends_data

    def _scan_twitter(self) -> Dict[str, Any]:
        """Scan Twitter for trending topics and formats."""
        logger.info("Scanning Twitter for trends")
        try:
            return self.twitter_scanner.get_trending_topics()
        except Exception as e:
            logger.error("Error scanning Twitter: %s", str(e))
            return {"error": str(e)}

    def _scan_instagram(self) -> Dict[str, Any]:
        """Scan Instagram for trending hashtags and content formats."""
        logger.info("Scanning Instagram for trends")
        try:
            return self.instagram_scanner.get_trending_hashtags()
        except Exception as e:
            logger.error("Error scanning Instagram: %s", str(e))
            return {"error": str(e)}

    def _scan_linkedin(self) -> Dict[str, Any]:
        """Scan LinkedIn for trending professional topics."""
        logger.info("Scanning LinkedIn for trends")
        try:
            return self.linkedin_scanner.get_trending_topics()
        except Exception as e:
            logger.error("Error scanning LinkedIn: %s", str(e))
            return {"error": str(e)}

    def _is_cache_expired(self, timestamp: Optional[datetime]) -> bool:
        """
        Check if cached data is expired.
        
        Args:
            timestamp: Timestamp of when the data was cached
            
        Returns:
            True if cache is expired, False otherwise
        """
        if not timestamp:
            return True
        
        expiry_time = timestamp + timedelta(seconds=self.cache_duration)
        return datetime.now() > expiry_time

    def generate_trend_report(self) -> str:
        """
        Generate a formatted report of current trends following the TrendScannerAgent MDC rules.
        
        The report focuses on 2-3 key trends per platform, with platform-specific insights
        and content format observations, formatted for easy consumption by the content team.
        
        Returns:
            Formatted string with trend insights for content creation
        """
        trends = self.scan_all_platforms()
        
        report = []
        report.append("# Trend Report - " + datetime.now().strftime("%Y-%m-%d %H:%M"))
        
        # Process Twitter trends
        twitter_data = trends.get("twitter", {})
        twitter_line = "**Twitter:** "
        
        if "error" in twitter_data:
            twitter_line += f"Error retrieving trends: {twitter_data['error']}"
        else:
            # Get top 2-3 hashtags (prioritize by relevance score and tweet volume)
            hashtags = twitter_data.get("trending_hashtags", [])
            formats = twitter_data.get("popular_formats", [])
            
            # Format hashtags and tweet volumes
            if hashtags:
                top_hashtags = hashtags[:2]  # Just get top 2
                hashtag_mentions = []
                
                for tag in top_hashtags:
                    if tag['tweet_volume'] and tag['tweet_volume'] > 1000:
                        volume_str = f"{tag['tweet_volume']/1000:.0f}k+ tweets"
                    else:
                        volume_str = f"{tag['tweet_volume'] or 'unknown'} tweets"
                    
                    hashtag_mentions.append(f"`#{tag['name']}` ({volume_str})")
                
                twitter_line += " and ".join(hashtag_mentions) + " trending. "
            
            # Add format information
            if formats:
                top_format = formats[0]  # Get most popular format
                twitter_line += f"Many users posting {top_format['name'].lower()}s {top_format['description'].lower()}."
        
        report.append(twitter_line)
        
        # Process Instagram trends
        instagram_data = trends.get("instagram", {})
        instagram_line = "**Instagram:** "
        
        if "error" in instagram_data:
            instagram_line += f"Error retrieving trends: {instagram_data['error']}"
        else:
            hashtags = instagram_data.get("trending_hashtags", [])
            formats = instagram_data.get("popular_formats", [])
            
            # Format hashtags with engagement information
            if hashtags:
                top_hashtag = hashtags[0]  # Get top hashtag
                instagram_line += f"`#{top_hashtag['name']}` trending with high engagement; "
            
            # Add format information
            if formats:
                top_format = formats[0]  # Get most popular format
                instagram_line += f"lots of {top_format['name'].lower()}s {top_format['description'].lower()}."
        
        report.append(instagram_line)
        
        # Process LinkedIn trends
        linkedin_data = trends.get("linkedin", {})
        linkedin_line = "**LinkedIn:** "
        
        if "error" in linkedin_data:
            linkedin_line += f"Error retrieving trends: {linkedin_data['error']}"
        else:
            topics = linkedin_data.get("trending_topics", [])
            formats = linkedin_data.get("popular_formats", [])
            
            # Format topics
            if topics:
                top_topic = topics[0]  # Get top topic
                linkedin_line += f"Trending topic on {top_topic['name']}; "
                
                if len(topics) > 1:
                    linkedin_line += f"professionals discussing {topics[1]['name']}. "
            
            # Add format information
            if formats:
                top_format = formats[0]  # Get most popular format
                linkedin_line += f"Popular format: {top_format['name']} {top_format['description'].lower()}."
        
        report.append(linkedin_line)
        
        # Add Facebook highest trending topic identification
        highest_topic = trends.get("facebook_priority_topic") or trends.get("highest_trending_topic")
        if highest_topic:
            volume = highest_topic.get('tweet_volume') or highest_topic.get('volume', 0)
            if volume > 1000:
                volume_str = f"{volume/1000:.0f}k+ engagements"
            else:
                volume_str = f"{volume} engagements"
            
            report.append(f"\n**Facebook:** **Highest trending topic:** {highest_topic.get('name', 'N/A')} "
                         f"({volume_str}). This will be the primary focus for Facebook content.")
        else:
            report.append("\n**Facebook:** No highest trending topic identified at this time.")
        
        # Add a note about data sources and relevance
        report.append("\nThis report focuses on trends relevant to AI solving real-world problems, "
                     "artificial intelligence applications, and machine learning innovations. "
                     "Filtered for SFW content only.")
        
        return "\n".join(report)

if __name__ == "__main__":
    # Example usage
    agent = TrendScannerAgent()
    report = agent.generate_trend_report()
    print(report) 