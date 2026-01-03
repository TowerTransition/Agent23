"""
Utility functions for syncing data from agents to Django models.
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime
from django.utils import timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent.parent))

from dashboard.models import ScheduledPost, TrendData, PostLog, EngagementStats


def sync_post_log():
    """Sync posts from post_log.json to ScheduledPost model."""
    post_log_path = os.path.join(Path(__file__).parent.parent.parent.parent, "logs", "post_log.json")
    
    if not os.path.exists(post_log_path):
        return
    
    try:
        with open(post_log_path, 'r') as f:
            posts_data = json.load(f)
        
        for post_id, post_data in posts_data.items():
            # Convert scheduled_time string to datetime
            scheduled_time = datetime.fromisoformat(post_data.get('scheduled_time', datetime.now().isoformat()))
            if timezone.is_naive(scheduled_time):
                scheduled_time = timezone.make_aware(scheduled_time)
            
            posted_at = None
            if post_data.get('posted_at'):
                posted_at = datetime.fromisoformat(post_data['posted_at'])
                if timezone.is_naive(posted_at):
                    posted_at = timezone.make_aware(posted_at)
            
            ScheduledPost.objects.update_or_create(
                post_id=post_id,
                defaults={
                    'platform': post_data.get('platform', 'twitter'),
                    'content': post_data.get('content', {}),
                    'scheduled_time': scheduled_time,
                    'status': post_data.get('status', 'scheduled'),
                    'posted_at': posted_at,
                    'result_data': post_data.get('result', {}),
                }
            )
    except Exception as e:
        print(f"Error syncing post log: {e}")


def sync_trend_data(trend_report_path=None):
    """Sync trends from trend report to TrendData model."""
    if not trend_report_path:
        trend_report_path = os.path.join(
            Path(__file__).parent.parent.parent.parent, 
            "data", 
            "trend_report.json"
        )
    
    if not os.path.exists(trend_report_path):
        return
    
    try:
        with open(trend_report_path, 'r') as f:
            trends_data = json.load(f)
        
        # Process each platform's trends
        for platform in ['twitter', 'instagram', 'linkedin', 'facebook']:
            platform_data = trends_data.get(platform, {})
            
            # Process hashtags
            for hashtag in platform_data.get('trending_hashtags', []):
                TrendData.objects.create(
                    platform=platform,
                    trend_name=hashtag.get('name', ''),
                    trend_type='hashtag',
                    volume=hashtag.get('tweet_volume', 0),
                    relevance_score=hashtag.get('relevance_score', 0.0),
                    trend_data=hashtag,
                )
            
            # Process topics
            for topic in platform_data.get('topics', []):
                TrendData.objects.create(
                    platform=platform,
                    trend_name=topic.get('name', ''),
                    trend_type='topic',
                    volume=topic.get('tweet_volume', 0),
                    relevance_score=topic.get('relevance_score', 0.0),
                    trend_data=topic,
                )
        
        # Process articles if available
        for article in trends_data.get('articles', []):
            TrendData.objects.create(
                platform='general',
                trend_name=article.get('title', ''),
                trend_type='article',
                volume=0,
                relevance_score=1.0,
                trend_data=article,
            )
    except Exception as e:
        print(f"Error syncing trend data: {e}")


def create_log_entry(platform, log_type, message, log_data=None):
    """Create a log entry in the database."""
    PostLog.objects.create(
        platform=platform,
        log_type=log_type,
        message=message,
        log_data=log_data or {},
    )


