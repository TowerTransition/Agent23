"""
Unit tests for SchedulerAgent.

Tests cover:
- Initialization
- Platform poster initialization
- Scheduling posts (single and multi-platform)
- Posting immediately
- Scheduler thread management
- Post execution
- Logging
- History retrieval
- Error handling
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timedelta
import json
import os
import sys
import tempfile
import shutil
import time
import threading

# Add parent directory to path to import the module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.scheduler.scheduler_agent import SchedulerAgent


class TestSchedulerAgent(unittest.TestCase):
    """Test suite for SchedulerAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directory for logs and cache
        self.test_dir = tempfile.mkdtemp()
        self.post_log_path = os.path.join(self.test_dir, "logs", "post_log.json")
        self.cache_dir = os.path.join(self.test_dir, "cache")
        
        # Mock platform posters
        self.mock_twitter_poster = Mock()
        self.mock_instagram_poster = Mock()
        self.mock_linkedin_poster = Mock()
        self.mock_facebook_poster = Mock()
        
        # Patch platform poster imports
        self.patcher_twitter = patch('agents.scheduler.scheduler_agent.TwitterPoster')
        self.patcher_instagram = patch('agents.scheduler.scheduler_agent.InstagramPoster')
        self.patcher_linkedin = patch('agents.scheduler.scheduler_agent.LinkedInPoster')
        self.patcher_facebook = patch('agents.scheduler.scheduler_agent.FacebookPoster')
        
        MockTwitterPoster = self.patcher_twitter.start()
        MockInstagramPoster = self.patcher_instagram.start()
        MockLinkedInPoster = self.patcher_linkedin.start()
        MockFacebookPoster = self.patcher_facebook.start()
        
        MockTwitterPoster.return_value = self.mock_twitter_poster
        MockInstagramPoster.return_value = self.mock_instagram_poster
        MockLinkedInPoster.return_value = self.mock_linkedin_poster
        MockFacebookPoster.return_value = self.mock_facebook_poster

    def tearDown(self):
        """Clean up test fixtures."""
        # Stop all patchers
        self.patcher_twitter.stop()
        self.patcher_instagram.stop()
        self.patcher_linkedin.stop()
        self.patcher_facebook.stop()
        
        # Clean up temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # -------------------------
    # Initialization Tests
    # -------------------------

    def test_init_default_params(self):
        """Test initialization with default parameters."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.assertEqual(agent.post_log_path, self.post_log_path)
        self.assertEqual(agent.cache_dir, self.cache_dir)
        self.assertEqual(agent.time_zone, "UTC")
        self.assertTrue(agent.auto_retry)
        self.assertEqual(agent.max_retries, 3)
        self.assertFalse(agent.dry_run)
        self.assertFalse(agent.running)
        self.assertIsNotNone(agent.scheduler)
        self.assertIsNotNone(agent.post_queue)

    def test_init_custom_params(self):
        """Test initialization with custom parameters."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            time_zone="America/New_York",
            auto_retry=False,
            max_retries=5,
            dry_run=True
        )
        
        self.assertEqual(agent.time_zone, "America/New_York")
        self.assertFalse(agent.auto_retry)
        self.assertEqual(agent.max_retries, 5)
        self.assertTrue(agent.dry_run)

    def test_init_platform_posters(self):
        """Test that platform posters are initialized."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.assertIsNotNone(agent.twitter_poster)
        self.assertIsNotNone(agent.instagram_poster)
        self.assertIsNotNone(agent.linkedin_poster)
        self.assertIsNotNone(agent.facebook_poster)

    def test_init_creates_log_directory(self):
        """Test that log directory is created on initialization."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        log_dir = os.path.dirname(self.post_log_path)
        self.assertTrue(os.path.exists(log_dir))

    # -------------------------
    # schedule_post Tests
    # -------------------------

    def test_schedule_post_twitter(self):
        """Test scheduling a post for Twitter."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        result = agent.schedule_post(content, "twitter")
        
        self.assertEqual(result["status"], "scheduled")
        self.assertIn("post_id", result)
        self.assertEqual(result["platform"], "twitter")
        self.assertIn("scheduled_time", result)
        self.assertFalse(agent.post_queue.empty())

    def test_schedule_post_with_custom_time(self):
        """Test scheduling a post with custom time."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        scheduled_time = datetime.now() + timedelta(hours=2)
        result = agent.schedule_post(
            content, 
            "instagram", 
            scheduled_time=scheduled_time
        )
        
        self.assertEqual(result["status"], "scheduled")
        self.assertEqual(result["scheduled_time"], scheduled_time.isoformat())

    def test_schedule_post_with_custom_post_id(self):
        """Test scheduling a post with custom post ID."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        post_id = "custom_post_123"
        result = agent.schedule_post(content, "linkedin", post_id=post_id)
        
        self.assertEqual(result["post_id"], post_id)

    def test_schedule_post_unsupported_platform(self):
        """Test scheduling a post for unsupported platform."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        result = agent.schedule_post(content, "unsupported")
        
        self.assertIn("error", result)
        self.assertIn("Unsupported platform", result["error"])

    def test_schedule_post_all_platforms(self):
        """Test scheduling posts for all supported platforms."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        platforms = ["twitter", "instagram", "linkedin", "facebook"]
        
        # Use different scheduled times to avoid priority queue comparison issues
        base_time = datetime.now() + timedelta(hours=1)
        results = []
        for i, platform in enumerate(platforms):
            scheduled_time = base_time + timedelta(minutes=i)
            result = agent.schedule_post(content, platform, scheduled_time=scheduled_time)
            self.assertEqual(result["status"], "scheduled")
            self.assertEqual(result["platform"], platform)
            results.append(result)
        
        # Verify all posts were scheduled
        self.assertEqual(len(results), len(platforms))

    def test_schedule_post_logs_to_file(self):
        """Test that scheduled posts are logged to file."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content = {"text": "Test post"}
        result = agent.schedule_post(content, "twitter")
        post_id = result["post_id"]
        
        # Check that log file exists and contains the post
        self.assertTrue(os.path.exists(self.post_log_path))
        with open(self.post_log_path, 'r') as f:
            log_data = json.load(f)
            self.assertIn(post_id, log_data)
            self.assertEqual(log_data[post_id]["status"], "scheduled")

    # -------------------------
    # schedule_multi_platform Tests
    # -------------------------

    def test_schedule_multi_platform(self):
        """Test scheduling posts across multiple platforms."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content_by_platform = {
            "twitter": {"text": "Twitter post"},
            "instagram": {"text": "Instagram post"},
            "linkedin": {"text": "LinkedIn post"}
        }
        
        results = agent.schedule_multi_platform(content_by_platform)
        
        self.assertEqual(len(results), 3)
        for result in results:
            self.assertEqual(result["status"], "scheduled")

    def test_schedule_multi_platform_with_custom_times(self):
        """Test scheduling multi-platform posts with custom times."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        base_time = datetime.now() + timedelta(hours=1)
        scheduled_times = {
            "twitter": base_time,
            "instagram": base_time + timedelta(minutes=15)
        }
        
        content_by_platform = {
            "twitter": {"text": "Twitter post"},
            "instagram": {"text": "Instagram post"}
        }
        
        results = agent.schedule_multi_platform(
            content_by_platform,
            scheduled_times=scheduled_times
        )
        
        self.assertEqual(len(results), 2)
        # Verify times are set correctly
        for result in results:
            self.assertIn("scheduled_time", result)

    def test_schedule_multi_platform_staggering(self):
        """Test that multi-platform posts are staggered."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        content_by_platform = {
            "twitter": {"text": "Twitter post"},
            "instagram": {"text": "Instagram post"},
            "linkedin": {"text": "LinkedIn post"}
        }
        
        results = agent.schedule_multi_platform(
            content_by_platform,
            stagger_minutes=10
        )
        
        # All should be scheduled
        self.assertEqual(len(results), 3)
        
        # Times should be staggered (check in log file)
        with open(self.post_log_path, 'r') as f:
            log_data = json.load(f)
            times = []
            for result in results:
                post_id = result["post_id"]
                if post_id in log_data:
                    times.append(datetime.fromisoformat(log_data[post_id]["scheduled_time"]))
            
            # Times should be different (staggered)
            if len(times) >= 2:
                time_diffs = [(times[i+1] - times[i]).total_seconds() / 60 
                             for i in range(len(times) - 1)]
                # Should be approximately 10 minutes apart (allow some tolerance)
                self.assertTrue(all(5 <= diff <= 15 for diff in time_diffs))

    # -------------------------
    # post_now Tests
    # -------------------------

    def test_post_now_twitter_success(self):
        """Test posting immediately to Twitter with success."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": True,
            "post_id": "test_123",
            "url": "https://twitter.com/status/123"
        }
        
        content = {"text": "Test post"}
        result = agent.post_now(content, "twitter")
        
        self.assertTrue(result["success"])
        self.mock_twitter_poster.post.assert_called_once()
        # Verify post was logged
        self.assertTrue(os.path.exists(self.post_log_path))

    def test_post_now_instagram_success(self):
        """Test posting immediately to Instagram with success."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_instagram_poster.post.return_value = {
            "success": True,
            "post_id": "test_456"
        }
        
        content = {"text": "Test post", "image": {"filepath": "test.jpg"}}
        result = agent.post_now(content, "instagram")
        
        self.assertTrue(result["success"])
        self.mock_instagram_poster.post.assert_called_once()

    def test_post_now_linkedin_success(self):
        """Test posting immediately to LinkedIn with success."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_linkedin_poster.post.return_value = {
            "success": True,
            "post_id": "test_789"
        }
        
        content = {"text": "Test post"}
        result = agent.post_now(content, "linkedin")
        
        self.assertTrue(result["success"])
        self.mock_linkedin_poster.post.assert_called_once()

    def test_post_now_facebook_success(self):
        """Test posting immediately to Facebook with success."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_facebook_poster.post.return_value = {
            "success": True,
            "post_id": "test_abc"
        }
        
        content = {"text": "Test post"}
        result = agent.post_now(content, "facebook")
        
        self.assertTrue(result["success"])
        self.mock_facebook_poster.post.assert_called_once()

    def test_post_now_failure(self):
        """Test posting immediately with failure."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": False,
            "error": "API error"
        }
        
        content = {"text": "Test post"}
        result = agent.post_now(content, "twitter")
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_post_now_with_custom_post_id(self):
        """Test posting immediately with custom post ID."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": True,
            "post_id": "custom_123"
        }
        
        content = {"text": "Test post"}
        post_id = "custom_123"
        result = agent.post_now(content, "twitter", post_id=post_id)
        
        # Verify post_id was passed to poster
        call_args = self.mock_twitter_poster.post.call_args
        self.assertEqual(call_args[0][1], post_id)

    def test_post_now_logs_result(self):
        """Test that post_now logs the result."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": True,
            "post_id": "test_123"
        }
        
        content = {"text": "Test post"}
        result = agent.post_now(content, "twitter")
        
        # Get the actual post_id from the result (it's generated in post_now)
        # The result should contain success, and we can check the log file
        self.assertTrue(result.get("success"))
        
        # Check log file - should have at least one entry
        with open(self.post_log_path, 'r') as f:
            log_data = json.load(f)
            self.assertGreater(len(log_data), 0)
            # Find the entry that was just posted
            posted_entry = None
            for post_id, entry in log_data.items():
                if entry.get("status") == "posted" and entry.get("platform") == "twitter":
                    posted_entry = entry
                    break
            self.assertIsNotNone(posted_entry)
            self.assertEqual(posted_entry["status"], "posted")

    # -------------------------
    # Scheduler Thread Tests
    # -------------------------

    def test_start_scheduler(self):
        """Test starting the scheduler thread."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.assertFalse(agent.running)
        agent.start_scheduler()
        
        # Give thread a moment to start
        time.sleep(0.1)
        
        self.assertTrue(agent.running)
        self.assertIsNotNone(agent.scheduler_thread)
        self.assertTrue(agent.scheduler_thread.is_alive())
        
        # Clean up
        agent.stop_scheduler()

    def test_stop_scheduler(self):
        """Test stopping the scheduler thread."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        agent.start_scheduler()
        time.sleep(0.1)
        
        agent.stop_scheduler()
        time.sleep(0.2)  # Give thread time to stop
        
        self.assertFalse(agent.running)

    def test_start_scheduler_already_running(self):
        """Test starting scheduler when already running."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        agent.start_scheduler()
        time.sleep(0.1)
        
        # Try to start again (should just log warning)
        agent.start_scheduler()
        
        self.assertTrue(agent.running)
        agent.stop_scheduler()

    def test_stop_scheduler_not_running(self):
        """Test stopping scheduler when not running."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        # Should not raise error
        agent.stop_scheduler()
        self.assertFalse(agent.running)

    # -------------------------
    # Post Execution Tests
    # -------------------------

    def test_execute_post_twitter(self):
        """Test executing a post to Twitter."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": True,
            "post_id": "test_123"
        }
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"}
        }
        
        result = agent._execute_post(post)
        
        self.assertTrue(result["success"])
        self.mock_twitter_poster.post.assert_called_once_with(
            {"text": "Test post"},
            "test_123"
        )

    def test_execute_post_all_platforms(self):
        """Test executing posts to all platforms."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        # Set up mock returns
        self.mock_twitter_poster.post.return_value = {"success": True}
        self.mock_instagram_poster.post.return_value = {"success": True}
        self.mock_linkedin_poster.post.return_value = {"success": True}
        self.mock_facebook_poster.post.return_value = {"success": True}
        
        platforms = ["twitter", "instagram", "linkedin", "facebook"]
        content = {"text": "Test post"}
        
        for platform in platforms:
            post = {
                "post_id": f"test_{platform}",
                "platform": platform,
                "content": content
            }
            result = agent._execute_post(post)
            self.assertTrue(result["success"])

    def test_execute_post_unsupported_platform(self):
        """Test executing post to unsupported platform."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        post = {
            "post_id": "test_123",
            "platform": "unsupported",
            "content": {"text": "Test post"}
        }
        
        result = agent._execute_post(post)
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_execute_post_exception(self):
        """Test executing post when exception occurs."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.side_effect = Exception("API error")
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"}
        }
        
        result = agent._execute_post(post)
        
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    # -------------------------
    # Logging Tests
    # -------------------------

    def test_load_post_log_nonexistent(self):
        """Test loading post log when file doesn't exist."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        log_data = agent._load_post_log()
        self.assertEqual(log_data, {})

    def test_save_and_load_post_log(self):
        """Test saving and loading post log."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        test_log = {
            "post_1": {
                "post_id": "post_1",
                "status": "scheduled",
                "platform": "twitter"
            }
        }
        
        agent._save_post_log(test_log)
        loaded_log = agent._load_post_log()
        
        self.assertEqual(loaded_log, test_log)

    def test_log_scheduled_post(self):
        """Test logging a scheduled post."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "status": "scheduled",
            "content": {"text": "Test"}
        }
        
        agent._log_scheduled_post(post)
        
        loaded_log = agent._load_post_log()
        self.assertIn("test_123", loaded_log)
        self.assertEqual(loaded_log["test_123"]["status"], "scheduled")

    def test_log_post_result(self):
        """Test logging a post result."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "status": "posted",
            "result": {"success": True}
        }
        
        agent._log_post_result(post)
        
        loaded_log = agent._load_post_log()
        self.assertIn("test_123", loaded_log)
        self.assertEqual(loaded_log["test_123"]["status"], "posted")

    # -------------------------
    # History Tests
    # -------------------------

    def test_get_posting_history_empty(self):
        """Test getting posting history when log is empty."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        history = agent.get_posting_history()
        self.assertEqual(history, [])

    def test_get_posting_history_all(self):
        """Test getting all posting history."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        # Create some test posts
        posts = [
            {
                "post_id": "post_1",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": (datetime.now() - timedelta(days=1)).isoformat()
            },
            {
                "post_id": "post_2",
                "platform": "instagram",
                "status": "scheduled",
                "scheduled_time": (datetime.now() + timedelta(days=1)).isoformat()
            }
        ]
        
        log_data = {post["post_id"]: post for post in posts}
        agent._save_post_log(log_data)
        
        history = agent.get_posting_history()
        self.assertEqual(len(history), 2)

    def test_get_posting_history_filter_by_platform(self):
        """Test filtering posting history by platform."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        posts = [
            {
                "post_id": "post_1",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": datetime.now().isoformat()
            },
            {
                "post_id": "post_2",
                "platform": "instagram",
                "status": "posted",
                "scheduled_time": datetime.now().isoformat()
            }
        ]
        
        log_data = {post["post_id"]: post for post in posts}
        agent._save_post_log(log_data)
        
        history = agent.get_posting_history(platform="twitter")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["platform"], "twitter")

    def test_get_posting_history_filter_by_status(self):
        """Test filtering posting history by status."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        posts = [
            {
                "post_id": "post_1",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": datetime.now().isoformat()
            },
            {
                "post_id": "post_2",
                "platform": "twitter",
                "status": "scheduled",
                "scheduled_time": datetime.now().isoformat()
            }
        ]
        
        log_data = {post["post_id"]: post for post in posts}
        agent._save_post_log(log_data)
        
        history = agent.get_posting_history(status="posted")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "posted")

    def test_get_posting_history_filter_by_date(self):
        """Test filtering posting history by date range."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        now = datetime.now()
        posts = [
            {
                "post_id": "post_1",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": (now - timedelta(days=2)).isoformat()
            },
            {
                "post_id": "post_2",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": (now - timedelta(days=1)).isoformat()
            },
            {
                "post_id": "post_3",
                "platform": "twitter",
                "status": "posted",
                "scheduled_time": now.isoformat()
            }
        ]
        
        log_data = {post["post_id"]: post for post in posts}
        agent._save_post_log(log_data)
        
        start_date = now - timedelta(days=1.5)
        end_date = now + timedelta(days=1)
        
        history = agent.get_posting_history(start_date=start_date, end_date=end_date)
        self.assertEqual(len(history), 2)  # post_2 and post_3

    # -------------------------
    # Retry Logic Tests
    # -------------------------

    def test_process_scheduled_post_with_retry(self):
        """Test processing scheduled post with retry on failure."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            auto_retry=True,
            max_retries=3
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": False,
            "error": "API error"
        }
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"},
            "status": "scheduled",
            "retry_count": 0,
            "scheduled_time": datetime.now().isoformat()
        }
        
        agent._process_scheduled_post(post)
        
        # Should be scheduled for retry
        self.assertEqual(post["status"], "scheduled_retry")
        self.assertEqual(post["retry_count"], 1)
        self.assertIn("scheduled_time", post)

    def test_process_scheduled_post_no_retry_when_disabled(self):
        """Test that retry doesn't happen when auto_retry is disabled."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            auto_retry=False
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": False,
            "error": "API error"
        }
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"},
            "status": "scheduled",
            "retry_count": 0,
            "scheduled_time": datetime.now().isoformat()
        }
        
        agent._process_scheduled_post(post)
        
        # Should be marked as failed, not retried
        self.assertEqual(post["status"], "failed")
        self.assertEqual(post["retry_count"], 0)

    def test_process_scheduled_post_max_retries(self):
        """Test that retry stops after max_retries."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            auto_retry=True,
            max_retries=2
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": False,
            "error": "API error"
        }
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"},
            "status": "scheduled",
            "retry_count": 2,  # Already at max
            "scheduled_time": datetime.now().isoformat()
        }
        
        agent._process_scheduled_post(post)
        
        # Should be marked as failed, not retried
        self.assertEqual(post["status"], "failed")
        self.assertEqual(post["retry_count"], 2)  # Unchanged

    def test_process_scheduled_post_success(self):
        """Test processing scheduled post with success."""
        agent = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir
        )
        
        self.mock_twitter_poster.post.return_value = {
            "success": True,
            "post_id": "test_123"
        }
        
        post = {
            "post_id": "test_123",
            "platform": "twitter",
            "content": {"text": "Test post"},
            "status": "scheduled",
            "retry_count": 0,
            "scheduled_time": datetime.now().isoformat()
        }
        
        agent._process_scheduled_post(post)
        
        # Should be marked as posted
        self.assertEqual(post["status"], "posted")
        self.assertIn("result", post)
        self.assertTrue(post["result"]["success"])


if __name__ == '__main__':
    unittest.main(verbosity=2)
