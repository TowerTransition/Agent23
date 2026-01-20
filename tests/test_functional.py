"""
Functional tests for the content creation and scheduling system.

Functional tests verify that the system produces correct, usable outputs
and behaves correctly in real-world scenarios. These tests use actual
components with minimal mocking, focusing on functional correctness.
"""

import unittest
import os
import sys
import tempfile
import shutil
import json
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from agents.content_creator.content_creator_agent import ContentCreatorAgent
from agents.content_creator.expert_lens_manager import ExpertLensManager
from agents.content_creator.domain_classifier import DomainClassifier
from agents.content_creator.brand_guidelines_manager import BrandGuidelinesManager
from agents.scheduler.scheduler_agent import SchedulerAgent
from agents.scheduler.post_scheduler import PostScheduler


class TestFunctional(unittest.TestCase):
    """Functional tests for the system."""

    def setUp(self):
        """Set up test fixtures."""
        # Create temporary directories
        self.test_dir = tempfile.mkdtemp()
        self.cache_dir = os.path.join(self.test_dir, "cache")
        self.logs_dir = os.path.join(self.test_dir, "logs")
        self.post_log_path = os.path.join(self.logs_dir, "post_log.json")
        
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Set environment variables for testing
        os.environ.setdefault("ALLOW_DEFAULT_LLM_ENDPOINT", "true")
        os.environ.setdefault("LOCAL_LLM_ENDPOINT", "http://localhost:11434/v1/chat/completions")
        
        # Brand guidelines path
        self.brand_guidelines_path = "agents/content_creator/example_brand_guidelines.json"

    def tearDown(self):
        """Clean up test fixtures."""
        # Clean up temporary directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
        
        # Clean up environment variables
        os.environ.pop("ALLOW_DEFAULT_LLM_ENDPOINT", None)
        os.environ.pop("LOCAL_LLM_ENDPOINT", None)

    # -------------------------
    # Content Creation Functional Tests
    # -------------------------

    def test_content_creation_produces_valid_structure(self):
        """Test that content creation produces valid, structured output."""
        agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "AI in Foreclosure Processes",
            "description": "How AI helps coordinate foreclosure information",
            "domain": "Foreclosures"
        }
        
        result = agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="twitter"
        )
        
        # Verify structure
        self.assertIsNotNone(result)
        self.assertIn("text", result)
        self.assertIn("platform", result)
        self.assertEqual(result["platform"], "twitter")
        
        # Verify text is not empty
        self.assertIsInstance(result["text"], str)
        self.assertGreater(len(result["text"]), 0)
        
        # Verify text contains expected elements (based on training data format)
        text = result["text"]
        # Should contain footer
        self.assertIn("Elevare", text)
        # Should contain hashtags (may be in text or separate field)
        self.assertTrue(
            "#" in text or "hashtags" in result or "HASHTAGS" in text,
            "Content should contain hashtags"
        )

    def test_content_creation_respects_platform_constraints(self):
        """Test that content respects platform-specific constraints."""
        agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "Trading Discipline",
            "description": "Maintaining discipline in trading",
            "domain": "Trading Futures"
        }
        
        # Test Twitter (280 char limit)
        twitter_result = agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="twitter"
        )
        self.assertLessEqual(len(twitter_result["text"]), 280)
        
        # Test LinkedIn (longer format)
        linkedin_result = agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="linkedin"
        )
        # LinkedIn allows longer content
        self.assertIsInstance(linkedin_result["text"], str)
        self.assertGreater(len(linkedin_result["text"]), 0)

    def test_domain_classification_works_correctly(self):
        """Test that domain classification correctly identifies domains."""
        classifier = DomainClassifier()
        
        # Test Foreclosures domain
        foreclosure_content = {
            "title": "Understanding Foreclosure Processes",
            "description": "How homeowners can navigate foreclosure with better information coordination"
        }
        result = classifier.classify(foreclosure_content)
        self.assertIsNotNone(result)
        self.assertIn("domain", result)
        self.assertEqual(result["domain"], "Foreclosures")
        
        # Test Trading Futures domain
        trading_content = {
            "title": "Trading Discipline and Risk Management",
            "description": "Maintaining discipline in futures trading with proper risk management"
        }
        result = classifier.classify(trading_content)
        self.assertIsNotNone(result)
        self.assertEqual(result["domain"], "Trading Futures")
        
        # Test Assisted Living domain
        assisted_living_content = {
            "title": "Care Coordination in Assisted Living",
            "description": "How families can coordinate care decisions for assisted living"
        }
        result = classifier.classify(assisted_living_content)
        self.assertIsNotNone(result)
        self.assertEqual(result["domain"], "Assisted Living")

    def test_expert_lens_selection_rotates(self):
        """Test that expert lens selection rotates through lenses."""
        lens_manager = ExpertLensManager(state_path=os.path.join(self.cache_dir, "lens_state.json"))
        
        # Create mock candidates
        candidates = [
            {
                "title": "Test Content",
                "domain": "Foreclosures",
                "description": "Test description"
            }
        ]
        
        # Get initial lens
        plan1 = lens_manager.pick_plan(candidates=candidates)
        lens1 = plan1["lens"]
        
        # Get next lens (should rotate)
        plan2 = lens_manager.pick_plan(candidates=candidates)
        lens2 = plan2["lens"]
        
        # Lenses should be different (rotation)
        self.assertNotEqual(lens1, lens2)
        
        # Both should be valid lenses
        valid_lenses = lens_manager.get_lens_cycle()
        self.assertIn(lens1, valid_lenses)
        self.assertIn(lens2, valid_lenses)

    def test_brand_guidelines_loading(self):
        """Test that brand guidelines load correctly."""
        manager = BrandGuidelinesManager(
            guidelines_path=self.brand_guidelines_path
        )
        
        # Verify guidelines loaded
        self.assertIsNotNone(manager.guidelines)
        
        # Verify domain voices exist
        foreclosure_voice = manager.get_brand_voice("Foreclosures")
        self.assertIsNotNone(foreclosure_voice)
        self.assertIn("tone", foreclosure_voice)
        
        trading_voice = manager.get_brand_voice("Trading Futures")
        self.assertIsNotNone(trading_voice)
        
        assisted_living_voice = manager.get_brand_voice("Assisted Living")
        self.assertIsNotNone(assisted_living_voice)
        
        # Verify platform guidelines exist
        twitter_guidelines = manager.get_platform_guidelines("twitter")
        self.assertIsNotNone(twitter_guidelines)
        self.assertIn("max_length", twitter_guidelines)

    def test_content_moderation_filters_inappropriate_content(self):
        """Test that content moderation correctly filters inappropriate content."""
        from agents.content_creator.content_moderator import ContentModerator
        
        # Test with inappropriate content
        moderator = ContentModerator()
        
        inappropriate_content = "This is a spam message with extreme claims!"
        result = moderator.check_content(inappropriate_content)
        self.assertIsNotNone(result)
        self.assertIn("is_appropriate", result)
        # Should flag as inappropriate due to "extreme claims"
        self.assertFalse(result["is_appropriate"])
        
        # Test with appropriate content
        appropriate_content = "AI helps organize information to support clarity in complex processes."
        result = moderator.check_content(appropriate_content)
        self.assertTrue(result["is_appropriate"])

    # -------------------------
    # Scheduling Functional Tests
    # -------------------------

    def test_post_scheduler_calculates_correct_times(self):
        """Test that post scheduler calculates correct posting times."""
        scheduler = PostScheduler()
        
        # Test optimal time calculation
        optimal_time = scheduler.get_optimal_time("twitter")
        
        # Should be 8:15 AM Eastern
        self.assertEqual(optimal_time.hour, 8)
        self.assertEqual(optimal_time.minute, 15)
        
        # Should be timezone-aware
        self.assertIsNotNone(optimal_time.tzinfo)
        
        # Test bulk schedule
        bulk_schedule = scheduler.get_bulk_schedule("twitter", count=3)
        self.assertEqual(len(bulk_schedule), 3)
        
        # All should be 8:15 AM
        for time in bulk_schedule:
            self.assertEqual(time.hour, 8)
            self.assertEqual(time.minute, 15)

    def test_scheduler_agent_schedules_posts_correctly(self):
        """Test that scheduler agent schedules posts correctly."""
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        content = {
            "text": "Test post content",
            "platform": "twitter"
        }
        
        result = scheduler.schedule_post(content, "twitter")
        
        # Verify scheduling
        self.assertEqual(result["status"], "scheduled")
        self.assertIn("post_id", result)
        self.assertIn("scheduled_time", result)
        
        # Verify post is in queue
        self.assertFalse(scheduler.post_queue.empty())
        
        # Verify post is logged
        self.assertTrue(os.path.exists(self.post_log_path))
        with open(self.post_log_path, 'r') as f:
            log_data = json.load(f)
            self.assertIn(result["post_id"], log_data)

    def test_scheduler_agent_history_filtering(self):
        """Test that scheduler agent history filtering works correctly."""
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        # Create multiple posts with different times
        base_time = datetime.now() + timedelta(hours=1)
        platforms = ["twitter", "instagram", "linkedin"]
        
        for i, platform in enumerate(platforms):
            content = {"text": f"Test post for {platform}"}
            scheduled_time = base_time + timedelta(minutes=i * 5)
            scheduler.schedule_post(content, platform, scheduled_time=scheduled_time)
        
        # Test filtering by platform
        twitter_history = scheduler.get_posting_history(platform="twitter")
        self.assertEqual(len(twitter_history), 1)
        self.assertEqual(twitter_history[0]["platform"], "twitter")
        
        # Test filtering by status
        scheduled_history = scheduler.get_posting_history(status="scheduled")
        self.assertEqual(len(scheduled_history), 3)
        
        # Test date filtering
        start_date = base_time - timedelta(minutes=10)
        end_date = base_time + timedelta(minutes=20)
        filtered_history = scheduler.get_posting_history(
            start_date=start_date,
            end_date=end_date
        )
        self.assertEqual(len(filtered_history), 3)

    # -------------------------
    # End-to-End Functional Tests
    # -------------------------

    def test_end_to_end_content_to_schedule(self):
        """Test complete end-to-end flow: content creation to scheduling."""
        # 1. Create content
        content_agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "AI in Foreclosure Processes",
            "description": "How AI helps coordinate foreclosure information",
            "domain": "Foreclosures"
        }
        
        content_result = content_agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="twitter"
        )
        
        # Verify content structure
        self.assertIn("text", content_result)
        self.assertIn("platform", content_result)
        self.assertEqual(content_result["platform"], "twitter")
        
        # 2. Schedule content
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        schedule_result = scheduler.schedule_post(
            content=content_result,
            platform="twitter"
        )
        
        # Verify scheduling
        self.assertEqual(schedule_result["status"], "scheduled")
        
        # 3. Verify in history
        history = scheduler.get_posting_history()
        self.assertGreater(len(history), 0)
        
        # Find our post
        our_post = next(
            (p for p in history if p["post_id"] == schedule_result["post_id"]),
            None
        )
        self.assertIsNotNone(our_post)
        self.assertEqual(our_post["platform"], "twitter")
        self.assertEqual(our_post["status"], "scheduled")

    def test_end_to_end_multi_platform_flow(self):
        """Test complete end-to-end flow for multiple platforms."""
        # 1. Create content for multiple platforms
        content_agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "Trading Discipline",
            "description": "Maintaining discipline in trading",
            "domain": "Trading Futures"
        }
        
        content_results = content_agent.generate_multi_platform_content(
            trend_data=trend_data,
            platforms=["twitter", "linkedin"]
        )
        
        # Verify content for all platforms
        self.assertEqual(len(content_results), 2)
        self.assertIn("twitter", content_results)
        self.assertIn("linkedin", content_results)
        
        # 2. Schedule all platforms
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        schedule_results = scheduler.schedule_multi_platform(content_results)
        
        # Verify all scheduled
        self.assertEqual(len(schedule_results), 2)
        for result in schedule_results:
            self.assertEqual(result["status"], "scheduled")
        
        # 3. Verify in history
        history = scheduler.get_posting_history()
        self.assertEqual(len(history), 2)
        
        platforms_in_history = {p["platform"] for p in history}
        self.assertEqual(platforms_in_history, {"twitter", "linkedin"})

    def test_end_to_end_with_expert_lens(self):
        """Test end-to-end flow with expert lens system."""
        # 1. Create content with expert lens
        content_agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "Care Coordination",
            "description": "How information coordination helps families",
            "domain": "Assisted Living"
        }
        
        content_result = content_agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="linkedin",
            use_expert_lens=True
        )
        
        # Verify content was created
        self.assertIsNotNone(content_result)
        self.assertIn("text", content_result)
        
        # 2. Schedule
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        schedule_result = scheduler.schedule_post(
            content=content_result,
            platform="linkedin"
        )
        
        # Verify scheduling
        self.assertEqual(schedule_result["status"], "scheduled")
        
        # 3. Verify lens state was updated
        lens_state_path = os.path.join(self.cache_dir, "content_state.json")
        if os.path.exists(lens_state_path):
            with open(lens_state_path, 'r') as f:
                lens_state = json.load(f)
                self.assertIn("history", lens_state)

    # -------------------------
    # Data Validation Tests
    # -------------------------

    def test_content_contains_required_elements(self):
        """Test that generated content contains required elements."""
        agent = ContentCreatorAgent(
            brand_guidelines_path=self.brand_guidelines_path,
            image_generation_enabled=False,
            cache_dir=self.cache_dir
        )
        
        trend_data = {
            "title": "Test Content",
            "description": "Test description",
            "domain": "Foreclosures"
        }
        
        result = agent.generate_content_for_platform(
            trend_data=trend_data,
            platform="twitter"
        )
        
        text = result["text"]
        
        # Should contain footer/signature
        self.assertTrue(
            "Elevare" in text or "Amaziah" in text,
            "Content should contain brand signature"
        )
        
        # Should contain hashtags (may be in text or separate)
        has_hashtags = (
            "#" in text or 
            "hashtags" in result or 
            "HASHTAGS" in text.upper()
        )
        self.assertTrue(has_hashtags, "Content should contain hashtags")

    def test_scheduled_posts_have_valid_structure(self):
        """Test that scheduled posts have valid structure."""
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        content = {
            "text": "Test post content",
            "platform": "twitter"
        }
        
        result = scheduler.schedule_post(content, "twitter")
        
        # Verify structure
        self.assertIn("status", result)
        self.assertIn("post_id", result)
        self.assertIn("platform", result)
        self.assertIn("scheduled_time", result)
        
        # Verify post_id format
        self.assertTrue(result["post_id"].startswith("twitter_"))
        
        # Verify scheduled_time is valid ISO format
        try:
            datetime.fromisoformat(result["scheduled_time"])
        except ValueError:
            self.fail("scheduled_time should be valid ISO format")

    def test_log_file_structure_is_valid(self):
        """Test that log file structure is valid JSON."""
        scheduler = SchedulerAgent(
            post_log_path=self.post_log_path,
            cache_dir=self.cache_dir,
            dry_run=True
        )
        
        # Create a post
        content = {"text": "Test post"}
        result = scheduler.schedule_post(content, "twitter")
        
        # Verify log file is valid JSON
        self.assertTrue(os.path.exists(self.post_log_path))
        
        with open(self.post_log_path, 'r') as f:
            log_data = json.load(f)
            self.assertIsInstance(log_data, dict)
            
            # Verify post entry structure
            post_id = result["post_id"]
            self.assertIn(post_id, log_data)
            
            post_entry = log_data[post_id]
            self.assertIn("post_id", post_entry)
            self.assertIn("platform", post_entry)
            self.assertIn("status", post_entry)
            self.assertIn("scheduled_time", post_entry)


if __name__ == '__main__':
    unittest.main(verbosity=2)
