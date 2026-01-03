"""
Post Scheduler - Module for determining posting times for social media platforms.

This module provides functionality for calculating posting times according to the
daily schedule: all posts go out at 8:15 AM Eastern Time every day.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
import pytz

class PostScheduler:
    """
    Determines posting times for different social media platforms.
    
    All platforms post at 8:15 AM Eastern Time daily, as per the scheduler rules.
    Posts go out simultaneously with small random delays (1-3 seconds) between platforms.
    """
    
    def __init__(self, time_zone: str = "America/New_York"):
        """
        Initialize the PostScheduler.
        
        Args:
            time_zone: Time zone for scheduling calculations (default: Eastern Time)
        """
        self.logger = logging.getLogger(__name__)
        self.time_zone = time_zone
        
        # Fixed posting time: 8:15 AM Eastern Time daily
        # All platforms post at the same time
        self.posting_hour = 8
        self.posting_minute = 15
        
        # Eastern Time zone
        self.eastern_tz = pytz.timezone("America/New_York")
        
        self.logger.info("PostScheduler initialized - All posts scheduled for 8:15 AM Eastern Time daily")
    
    def get_optimal_time(
        self, 
        platform: str,
        from_time: Optional[datetime] = None,
        max_days_ahead: int = 7
    ) -> datetime:
        """
        Get the next posting time for a platform (8:15 AM Eastern Time).
        
        Args:
            platform: Target platform (twitter, instagram, linkedin, facebook)
            from_time: Base time to calculate from (default: now in Eastern Time)
            max_days_ahead: Maximum days to look ahead (not used, kept for compatibility)
            
        Returns:
            Datetime representing the next posting time (8:15 AM Eastern)
        """
        platform = platform.lower()
        supported_platforms = ["twitter", "instagram", "linkedin", "facebook"]
        
        if platform not in supported_platforms:
            self.logger.warning("Unsupported platform: %s, using default schedule", platform)
        
        # Get current time in Eastern Time
        if from_time is None:
            from_time = datetime.now(self.eastern_tz)
        else:
            # Ensure timezone-aware
            if from_time.tzinfo is None:
                from_time = self.eastern_tz.localize(from_time)
            else:
                from_time = from_time.astimezone(self.eastern_tz)
        
        # Calculate next 8:15 AM Eastern
        target_time = from_time.replace(
            hour=self.posting_hour,
            minute=self.posting_minute,
            second=0,
            microsecond=0
        )
        
        # If 8:15 AM today has already passed, use tomorrow
        if target_time <= from_time:
            target_time = target_time + timedelta(days=1)
        
        self.logger.info(
            "Next posting time for %s: %s (8:15 AM Eastern)",
            platform,
            target_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        
        return target_time
    
    def get_bulk_schedule(
        self,
        platform: str,
        count: int,
        from_time: Optional[datetime] = None,
        min_hours_between: int = 8
    ) -> List[datetime]:
        """
        Generate a schedule for multiple posts (one per day at 8:15 AM Eastern).
        
        Args:
            platform: Target platform
            count: Number of posts to schedule (one per day)
            from_time: Base time to calculate from (default: now in Eastern Time)
            min_hours_between: Not used (kept for compatibility)
            
        Returns:
            List of datetimes for the schedule (one per day at 8:15 AM Eastern)
        """
        if from_time is None:
            from_time = datetime.now(self.eastern_tz)
        else:
            if from_time.tzinfo is None:
                from_time = self.eastern_tz.localize(from_time)
            else:
                from_time = from_time.astimezone(self.eastern_tz)
        
        schedule = []
        current_time = from_time
        
        for _ in range(count):
            # Get next 8:15 AM Eastern (one per day)
            next_time = self.get_optimal_time(platform, current_time)
            schedule.append(next_time)
            
            # Move to next day for the next post
            current_time = next_time + timedelta(days=1)
        
        return schedule
    
    def get_multi_platform_schedule(
        self,
        platforms: List[str],
        from_time: Optional[datetime] = None,
        stagger_minutes: int = 15
    ) -> Dict[str, datetime]:
        """
        Get posting times for multiple platforms (all at 8:15 AM Eastern with small delays).
        
        All platforms post at the same time (8:15 AM Eastern), but the actual posting
        will have small random delays (1-3 seconds) between platforms to avoid appearing bot-like.
        
        Args:
            platforms: List of target platforms
            from_time: Base time to calculate from (default: now in Eastern Time)
            stagger_minutes: Not used (kept for compatibility, actual delays are 1-3 seconds)
            
        Returns:
            Dictionary mapping platforms to posting times (all 8:15 AM Eastern)
        """
        if from_time is None:
            from_time = datetime.now(self.eastern_tz)
        else:
            if from_time.tzinfo is None:
                from_time = self.eastern_tz.localize(from_time)
            else:
                from_time = from_time.astimezone(self.eastern_tz)
        
        schedule = {}
        
        # All platforms post at the same time: 8:15 AM Eastern
        base_time = self.get_optimal_time(platforms[0] if platforms else "twitter", from_time)
        
        for platform in platforms:
            # All platforms use the same base time
            # Actual posting will have 1-3 second random delays between platforms
            schedule[platform] = base_time
        
        self.logger.info(
            "Multi-platform schedule: All platforms post at %s (8:15 AM Eastern) with 1-3 second delays between platforms",
            base_time.strftime("%Y-%m-%d %H:%M:%S %Z")
        )
        
        return schedule 