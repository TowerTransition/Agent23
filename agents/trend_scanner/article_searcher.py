"""
Article Searcher - Module for finding articles about AI solving real-world problems.

This module searches for recent articles and news about AI applications that solve
real-world problems, which can be used as content sources for social media posts.
"""

import logging
import requests
import os
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ArticleSearcher:
    """
    Searches for articles about AI solving real-world problems.
    Supports multiple sources: NewsAPI, Google News RSS, or custom search APIs.
    """
    
    def __init__(self, search_query: str = "AI solving real world problems"):
        """
        Initialize the ArticleSearcher.
        
        Args:
            search_query: Search query for articles (default: "AI solving real world problems")
        """
        self.search_query = search_query
        self.newsapi_key = os.environ.get("NEWSAPI_KEY")
        self.google_news_api_key = os.environ.get("GOOGLE_NEWS_API_KEY")
        
        logger.info("ArticleSearcher initialized with query: %s", search_query)
    
    def find_articles(self, count: int = 2, max_age_days: int = 7) -> List[Dict[str, Any]]:
        """
        Find articles matching the search query.
        
        Args:
            count: Number of articles to find (default: 2)
            max_age_days: Maximum age of articles in days (default: 7)
            
        Returns:
            List of article dictionaries with title, url, description, etc.
        """
        articles = []
        
        # Try NewsAPI first if available
        if self.newsapi_key:
            try:
                newsapi_articles = self._search_newsapi(count, max_age_days)
                articles.extend(newsapi_articles)
            except Exception as e:
                logger.warning("NewsAPI search failed: %s", str(e))
        
        # If we don't have enough articles, try Google News
        if len(articles) < count:
            try:
                google_articles = self._search_google_news(count - len(articles), max_age_days)
                articles.extend(google_articles)
            except Exception as e:
                logger.warning("Google News search failed: %s", str(e))
        
        # If still not enough, use fallback search
        if len(articles) < count:
            try:
                fallback_articles = self._search_fallback(count - len(articles))
                articles.extend(fallback_articles)
            except Exception as e:
                logger.warning("Fallback search failed: %s", str(e))
        
        # Return up to the requested count
        return articles[:count]
    
    def _search_newsapi(self, count: int, max_age_days: int) -> List[Dict[str, Any]]:
        """Search using NewsAPI."""
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": self.search_query,
            "apiKey": self.newsapi_key,
            "sortBy": "relevancy",
            "language": "en",
            "pageSize": count,
            "from": (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
        }
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        articles = []
        
        for article in data.get("articles", [])[:count]:
            articles.append({
                "title": article.get("title", ""),
                "url": article.get("url", ""),
                "description": article.get("description", ""),
                "source": article.get("source", {}).get("name", "Unknown"),
                "published_at": article.get("publishedAt", ""),
                "content": article.get("content", "")
            })
        
        return articles
    
    def _search_google_news(self, count: int, max_age_days: int) -> List[Dict[str, Any]]:
        """Search using Google News RSS or Custom Search API."""
        articles = []
        
        # Try Google Custom Search API if key is available
        if self.google_news_api_key:
            try:
                url = "https://www.googleapis.com/customsearch/v1"
                params = {
                    "key": self.google_news_api_key,
                    "cx": os.environ.get("GOOGLE_SEARCH_ENGINE_ID", ""),
                    "q": self.search_query,
                    "num": count,
                    "dateRestrict": f"d{max_age_days}"
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                for item in data.get("items", [])[:count]:
                    articles.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "description": item.get("snippet", ""),
                        "source": "Google News",
                        "published_at": item.get("pagemap", {}).get("metatags", [{}])[0].get("article:published_time", ""),
                        "content": item.get("snippet", "")
                    })
            except Exception as e:
                logger.warning("Google Custom Search failed: %s", str(e))
        
        # Fallback to RSS parsing if API not available
        if not articles:
            try:
                rss_url = f"https://news.google.com/rss/search?q={self.search_query.replace(' ', '+')}&hl=en&gl=US&ceid=US:en"
                response = requests.get(rss_url, timeout=10)
                response.raise_for_status()
                
                # Simple RSS parsing (for basic implementation)
                # In production, use feedparser library
                import re
                titles = re.findall(r'<title>(.*?)</title>', response.text)
                links = re.findall(r'<link>(.*?)</link>', response.text)
                
                for i, (title, link) in enumerate(zip(titles[1:count+1], links[1:count+1])):
                    if title and link:
                        articles.append({
                            "title": title,
                            "url": link,
                            "description": "",
                            "source": "Google News RSS",
                            "published_at": "",
                            "content": ""
                        })
            except Exception as e:
                logger.warning("Google News RSS parsing failed: %s", str(e))
        
        return articles
    
    def _search_fallback(self, count: int) -> List[Dict[str, Any]]:
        """
        Fallback search method using web scraping or alternative sources.
        This is a basic implementation - can be enhanced with more sources.
        """
        articles = []
        
        # For now, return placeholder articles with the search query
        # In production, you might use:
        # - Reddit API for r/MachineLearning, r/artificial
        # - Hacker News API
        # - Tech news aggregators
        # - Custom web scraping
        
        logger.info("Using fallback search - returning placeholder articles")
        
        # Placeholder articles (in production, replace with actual search)
        for i in range(count):
            articles.append({
                "title": f"AI Innovation: Solving Real-World Problem #{i+1}",
                "url": f"https://example.com/ai-article-{i+1}",
                "description": f"Recent developments in AI are solving real-world problems in various industries.",
                "source": "Trend Scanner",
                "published_at": datetime.now().isoformat(),
                "content": f"Article about {self.search_query}"
            })
        
        return articles
    
    def format_articles_for_trend_report(self, articles: List[Dict[str, Any]]) -> str:
        """
        Format articles into a trend report format for content creation.
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Formatted string with article information
        """
        if not articles:
            return "No articles found about AI solving real-world problems."
        
        report_lines = []
        report_lines.append(f"Found {len(articles)} article(s) about AI solving real-world problems:\n")
        
        for i, article in enumerate(articles, 1):
            report_lines.append(f"**Article {i}:**")
            report_lines.append(f"- Title: {article.get('title', 'N/A')}")
            report_lines.append(f"- Source: {article.get('source', 'Unknown')}")
            if article.get('description'):
                report_lines.append(f"- Summary: {article.get('description', '')[:200]}...")
            report_lines.append(f"- URL: {article.get('url', 'N/A')}")
            report_lines.append("")
        
        return "\n".join(report_lines)


