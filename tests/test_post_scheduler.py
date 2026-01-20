"""
Unit tests for PostScheduler.

Tests cover:
- Initialization
- get_optimal_time (single platform)
- get_bulk_schedule (multiple posts)
- get_multi_platform_schedule (multiple platforms)
- Time zone handling
- Edge cases (past times, future times)
"""

import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import pytz
import sys
import os

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.scheduler.post_scheduler import PostScheduler


class TestPostScheduler(unittest.TestCase):
    """Test suite for PostScheduler."""

    def setUp(self):
        """Set up test fixtures."""
        self.scheduler = PostScheduler()
        self.eastern_tz = pytz.timezone("America/New_York")

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init_default_timezone(self):
        """Test initialization with default timezone."""
        scheduler = PostScheduler()
        self.assertEqual(scheduler.posting_hour, 8)
        self.assertEqual(scheduler.posting_minute, 15)
        self.assertEqual(scheduler.time_zone, "America/New_York")

    def test_init_custom_timezone(self):
        """Test initialization with custom timezone."""
        scheduler = PostScheduler(time_zone="UTC")
        self.assertEqual(scheduler.time_zone, "UTC")
        # Should still use Eastern for posting time
        self.assertEqual(scheduler.posting_hour, 8)
        self.assertEqual(scheduler.posting_minute, 15)

    # -------------------------
    # get_optimal_time Tests
    # -------------------------

    def test_get_optimal_time_twitter(self):
        """Test getting optimal time for Twitter."""
        result = self.scheduler.get_optimal_time("twitter")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_instagram(self):
        """Test getting optimal time for Instagram."""
        result = self.scheduler.get_optimal_time("instagram")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_linkedin(self):
        """Test getting optimal time for LinkedIn."""
        result = self.scheduler.get_optimal_time("linkedin")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_facebook(self):
        """Test getting optimal time for Facebook."""
        result = self.scheduler.get_optimal_time("facebook")
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_unsupported_platform(self):
        """Test getting optimal time for unsupported platform."""
        result = self.scheduler.get_optimal_time("unsupported")
        # Should still return 8:15 AM Eastern
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_before_815_today(self):
        """Test getting optimal time when current time is before 8:15 AM today."""
        # Set current time to 7:00 AM Eastern today
        current_time = datetime.now(self.eastern_tz).replace(hour=7, minute=0, second=0, microsecond=0)
        result = self.scheduler.get_optimal_time("twitter", from_time=current_time)
        
        # Should return 8:15 AM today
        self.assertEqual(result.date(), current_time.date())
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_after_815_today(self):
        """Test getting optimal time when current time is after 8:15 AM today."""
        # Set current time to 10:00 AM Eastern today
        current_time = datetime.now(self.eastern_tz).replace(hour=10, minute=0, second=0, microsecond=0)
        result = self.scheduler.get_optimal_time("twitter", from_time=current_time)
        
        # Should return 8:15 AM tomorrow
        expected_date = current_time.date() + timedelta(days=1)
        self.assertEqual(result.date(), expected_date)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_exactly_815_today(self):
        """Test getting optimal time when current time is exactly 8:15 AM today."""
        # Set current time to 8:15 AM Eastern today
        current_time = datetime.now(self.eastern_tz).replace(hour=8, minute=15, second=0, microsecond=0)
        result = self.scheduler.get_optimal_time("twitter", from_time=current_time)
        
        # Should return 8:15 AM tomorrow (since 8:15 today has passed)
        expected_date = current_time.date() + timedelta(days=1)
        self.assertEqual(result.date(), expected_date)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_timezone_aware(self):
        """Test that returned time is timezone-aware."""
        result = self.scheduler.get_optimal_time("twitter")
        self.assertIsNotNone(result.tzinfo)
        self.assertEqual(str(result.tzinfo), str(self.eastern_tz))

    def test_get_optimal_time_with_timezone_naive_input(self):
        """Test get_optimal_time with timezone-naive input."""
        # Create timezone-naive datetime
        naive_time = datetime(2024, 1, 19, 10, 0, 0)
        result = self.scheduler.get_optimal_time("twitter", from_time=naive_time)
        
        # Should convert to Eastern and return 8:15 AM next day
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)
        self.assertIsNotNone(result.tzinfo)

    def test_get_optimal_time_with_timezone_aware_input(self):
        """Test get_optimal_time with timezone-aware input."""
        # Create timezone-aware datetime in UTC
        utc_tz = pytz.UTC
        utc_time = utc_tz.localize(datetime(2024, 1, 19, 13, 0, 0))  # 1 PM UTC = 8 AM EST
        result = self.scheduler.get_optimal_time("twitter", from_time=utc_time)
        
        # Should convert to Eastern and return appropriate time
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)
        self.assertEqual(str(result.tzinfo), str(self.eastern_tz))

    # -------------------------
    # get_bulk_schedule Tests
    # -------------------------

    def test_get_bulk_schedule_single_post(self):
        """Test getting bulk schedule for single post."""
        schedule = self.scheduler.get_bulk_schedule("twitter", count=1)
        self.assertEqual(len(schedule), 1)
        self.assertEqual(schedule[0].hour, 8)
        self.assertEqual(schedule[0].minute, 15)

    def test_get_bulk_schedule_multiple_posts(self):
        """Test getting bulk schedule for multiple posts."""
        schedule = self.scheduler.get_bulk_schedule("twitter", count=3)
        self.assertEqual(len(schedule), 3)
        
        # All should be 8:15 AM
        for time in schedule:
            self.assertEqual(time.hour, 8)
            self.assertEqual(time.minute, 15)
        
        # Should be one day apart (or more if crossing DST boundaries)
        for i in range(len(schedule) - 1):
            time_diff = schedule[i + 1] - schedule[i]
            # Allow 1-2 days due to DST transitions or edge cases
            self.assertGreaterEqual(time_diff.days, 1)
            self.assertLessEqual(time_diff.days, 2)

    def test_get_bulk_schedule_different_platforms(self):
        """Test that bulk schedule works for different platforms."""
        twitter_schedule = self.scheduler.get_bulk_schedule("twitter", count=2)
        instagram_schedule = self.scheduler.get_bulk_schedule("instagram", count=2)
        
        # Both should have same times (8:15 AM Eastern)
        self.assertEqual(twitter_schedule[0].hour, instagram_schedule[0].hour)
        self.assertEqual(twitter_schedule[0].minute, instagram_schedule[0].minute)

    def test_get_bulk_schedule_with_from_time(self):
        """Test bulk schedule with custom from_time."""
        from_time = datetime.now(self.eastern_tz).replace(hour=10, minute=0, second=0, microsecond=0)
        schedule = self.scheduler.get_bulk_schedule("twitter", count=2, from_time=from_time)
        
        # First post should be 8:15 AM tomorrow
        expected_date = from_time.date() + timedelta(days=1)
        self.assertEqual(schedule[0].date(), expected_date)
        self.assertEqual(schedule[0].hour, 8)
        self.assertEqual(schedule[0].minute, 15)
        
        # Second post should be at least 1 day after the first
        time_diff = schedule[1] - schedule[0]
        self.assertGreaterEqual(time_diff.days, 1)
        self.assertLessEqual(time_diff.days, 2)  # Allow for edge cases
        self.assertEqual(schedule[1].hour, 8)
        self.assertEqual(schedule[1].minute, 15)

    # -------------------------
    # get_multi_platform_schedule Tests
    # -------------------------

    def test_get_multi_platform_schedule_single_platform(self):
        """Test multi-platform schedule with single platform."""
        schedule = self.scheduler.get_multi_platform_schedule(["twitter"])
        self.assertEqual(len(schedule), 1)
        self.assertIn("twitter", schedule)
        self.assertEqual(schedule["twitter"].hour, 8)
        self.assertEqual(schedule["twitter"].minute, 15)

    def test_get_multi_platform_schedule_multiple_platforms(self):
        """Test multi-platform schedule with multiple platforms."""
        platforms = ["twitter", "instagram", "linkedin", "facebook"]
        schedule = self.scheduler.get_multi_platform_schedule(platforms)
        
        self.assertEqual(len(schedule), len(platforms))
        
        # All platforms should have the same time (8:15 AM Eastern)
        base_time = schedule[platforms[0]]
        for platform in platforms:
            self.assertIn(platform, schedule)
            self.assertEqual(schedule[platform], base_time)
            self.assertEqual(schedule[platform].hour, 8)
            self.assertEqual(schedule[platform].minute, 15)

    def test_get_multi_platform_schedule_all_same_time(self):
        """Test that all platforms get the same base time."""
        platforms = ["twitter", "instagram", "linkedin"]
        schedule = self.scheduler.get_multi_platform_schedule(platforms)
        
        times = list(schedule.values())
        # All times should be identical
        self.assertEqual(len(set(times)), 1)
        self.assertEqual(times[0].hour, 8)
        self.assertEqual(times[0].minute, 15)

    def test_get_multi_platform_schedule_with_from_time(self):
        """Test multi-platform schedule with custom from_time."""
        from_time = datetime.now(self.eastern_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        platforms = ["twitter", "instagram"]
        schedule = self.scheduler.get_multi_platform_schedule(platforms, from_time=from_time)
        
        # All should be 8:15 AM tomorrow
        expected_date = from_time.date() + timedelta(days=1)
        for platform in platforms:
            self.assertEqual(schedule[platform].date(), expected_date)
            self.assertEqual(schedule[platform].hour, 8)
            self.assertEqual(schedule[platform].minute, 15)

    def test_get_multi_platform_schedule_empty_list(self):
        """Test multi-platform schedule with empty platform list."""
        schedule = self.scheduler.get_multi_platform_schedule([])
        self.assertEqual(len(schedule), 0)

    # -------------------------
    # Edge Cases Tests
    # -------------------------

    def test_get_optimal_time_midnight(self):
        """Test getting optimal time when current time is midnight."""
        midnight = datetime.now(self.eastern_tz).replace(hour=0, minute=0, second=0, microsecond=0)
        result = self.scheduler.get_optimal_time("twitter", from_time=midnight)
        
        # Should return 8:15 AM same day
        self.assertEqual(result.date(), midnight.date())
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_optimal_time_late_night(self):
        """Test getting optimal time when current time is late night."""
        late_night = datetime.now(self.eastern_tz).replace(hour=23, minute=59, second=0, microsecond=0)
        result = self.scheduler.get_optimal_time("twitter", from_time=late_night)
        
        # Should return 8:15 AM next day
        expected_date = late_night.date() + timedelta(days=1)
        self.assertEqual(result.date(), expected_date)
        self.assertEqual(result.hour, 8)
        self.assertEqual(result.minute, 15)

    def test_get_bulk_schedule_zero_count(self):
        """Test bulk schedule with zero count."""
        schedule = self.scheduler.get_bulk_schedule("twitter", count=0)
        self.assertEqual(len(schedule), 0)

    def test_get_bulk_schedule_large_count(self):
        """Test bulk schedule with large count."""
        schedule = self.scheduler.get_bulk_schedule("twitter", count=10)
        self.assertEqual(len(schedule), 10)
        
        # Verify all are 8:15 AM and properly spaced
        for i, time in enumerate(schedule):
            self.assertEqual(time.hour, 8)
            self.assertEqual(time.minute, 15)
            if i > 0:
                # Check that times are at least one day apart (allow 1-2 days for edge cases)
                prev_time = schedule[i - 1]
                time_diff = (time - prev_time).days
                self.assertGreaterEqual(time_diff, 1)
                self.assertLessEqual(time_diff, 2)

    def test_get_optimal_time_case_insensitive_platform(self):
        """Test that platform name is case-insensitive."""
        result1 = self.scheduler.get_optimal_time("TWITTER")
        result2 = self.scheduler.get_optimal_time("Twitter")
        result3 = self.scheduler.get_optimal_time("twitter")
        
        # All should return same time
        self.assertEqual(result1, result2)
        self.assertEqual(result2, result3)

    # -------------------------
    # Integration Tests
    # -------------------------

    def test_full_scheduling_workflow(self):
        """Test full scheduling workflow."""
        # Get optimal time
        optimal_time = self.scheduler.get_optimal_time("twitter")
        
        # Get bulk schedule
        bulk_schedule = self.scheduler.get_bulk_schedule("twitter", count=3)
        
        # Get multi-platform schedule
        multi_schedule = self.scheduler.get_multi_platform_schedule(
            ["twitter", "instagram", "linkedin"]
        )
        
        # Verify all return 8:15 AM Eastern times
        self.assertEqual(optimal_time.hour, 8)
        self.assertEqual(optimal_time.minute, 15)
        
        for time in bulk_schedule:
            self.assertEqual(time.hour, 8)
            self.assertEqual(time.minute, 15)
        
        for platform, time in multi_schedule.items():
            self.assertEqual(time.hour, 8)
            self.assertEqual(time.minute, 15)

    def test_schedule_consistency_across_methods(self):
        """Test that all methods return consistent times."""
        from_time = datetime.now(self.eastern_tz).replace(hour=9, minute=0, second=0, microsecond=0)
        
        optimal = self.scheduler.get_optimal_time("twitter", from_time=from_time)
        bulk = self.scheduler.get_bulk_schedule("twitter", count=1, from_time=from_time)[0]
        multi = self.scheduler.get_multi_platform_schedule(["twitter"], from_time=from_time)["twitter"]
        
        # All should return the same time (8:15 AM next day)
        self.assertEqual(optimal, bulk)
        self.assertEqual(bulk, multi)


if __name__ == '__main__':
    unittest.main(verbosity=2)
