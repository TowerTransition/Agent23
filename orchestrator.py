#!/usr/bin/env python3
"""
AI Agents Orchestrator - Coordinates the TrendScannerAgent, ContentCreatorAgent, and SchedulerAgent

This orchestrator implements a complete pipeline for trend scanning, content creation,
and social media posting, managing the data flow between agents and ensuring each agent
executes its responsibilities at the appropriate time.
"""

import os
import sys
import json
import logging
import argparse
import time
import threading
import schedule
import pytz
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Import agents
from agents.trend_scanner.agent import TrendScannerAgent
from agents.content_creator.content_creator_agent import ContentCreatorAgent
from agents.scheduler.scheduler_agent import SchedulerAgent
from agents.scheduler.post_scheduler import PostScheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orchestrator.log')
    ]
)

logger = logging.getLogger("orchestrator")


class Orchestrator:
    """
    Main orchestrator that coordinates the activities of TrendScannerAgent,
    ContentCreatorAgent, and SchedulerAgent, implementing a full pipeline
    for social media content automation.
    """
    
    def __init__(
        self,
        data_dir: str = "data",
        cache_dir: str = "cache",
        content_dir: str = "content",
        logs_dir: str = "logs",
        brand_file: str = "agents/content_creator/example_brand_guidelines.json",
        platforms: List[str] = ["twitter", "instagram", "linkedin", "facebook"],
        keywords: List[str] = ["astronomy", "physics", "space"],
        time_zone: str = "America/New_York",
        dry_run: bool = False,
        human_review: bool = False,
        trend_scan_interval: int = 4,  # hours
        content_creation_interval: int = 24,  # hours
        max_posts_per_day: Dict[str, int] = None
    ):
        """
        Initialize the Orchestrator.
        
        Args:
            data_dir: Directory for storing data files
            cache_dir: Directory for caching responses
            content_dir: Directory for storing generated content
            logs_dir: Directory for logs
            brand_file: Path to brand guidelines file
            platforms: List of platforms to post to
            keywords: List of keywords to scan for trends
            time_zone: Time zone for scheduling
            dry_run: If True, simulate posting without actually sending to APIs
            human_review: If True, request human approval before posting
            trend_scan_interval: Hours between trend scans
            content_creation_interval: Hours between content creation cycles
            max_posts_per_day: Maximum number of posts per day per platform
        """
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.data_dir = data_dir
        self.cache_dir = cache_dir
        self.content_dir = content_dir
        self.logs_dir = logs_dir
        self.brand_file = brand_file
        self.platforms = platforms
        self.keywords = keywords
        self.time_zone = time_zone
        self.dry_run = dry_run
        self.human_review = human_review
        self.trend_scan_interval = trend_scan_interval
        self.content_creation_interval = content_creation_interval
        
        if max_posts_per_day is None:
            self.max_posts_per_day = {
                "twitter": 5,
                "instagram": 2,
                "linkedin": 1,
                "facebook": 3
            }
        else:
            self.max_posts_per_day = max_posts_per_day
        
        # Create necessary directories
        os.makedirs(data_dir, exist_ok=True)
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(content_dir, exist_ok=True)
        os.makedirs(logs_dir, exist_ok=True)
        
        # Initialize agents
        self._init_agents()
        
        # Paths for storing data
        self.trend_report_path = os.path.join(data_dir, "trend_report.json")
        self.content_pool_path = os.path.join(data_dir, "content_pool.json")
        self.posting_history_path = os.path.join(logs_dir, "posting_history.json")
        
        # Threading control
        self.running = False
        self.scheduler_thread = None
        
        # Initialize content pool if it doesn't exist
        if not os.path.exists(self.content_pool_path):
            self._init_content_pool()
        
        # Status tracking
        self.last_trend_scan = None
        self.last_content_creation = None
        
        self.logger.info("Orchestrator initialized")
    
    def _init_agents(self):
        """Initialize the three main agents."""
        try:
            # Initialize TrendScannerAgent
            self.trend_scanner = TrendScannerAgent(
                api_keys={},  # Use environment variables
                cache_dir=self.cache_dir
            )
            
            # Initialize ContentCreatorAgent
            # Use local LLM endpoint if available, otherwise fall back to OpenAI (for backward compatibility)
            llm_api_key = os.environ.get("LOCAL_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
            self.content_creator = ContentCreatorAgent(
                brand_guidelines_path=self.brand_file,
                llm_api_key=llm_api_key,
                stability_api_key=os.environ.get("STABILITY_API_KEY"),
                cache_dir=self.cache_dir
            )
            
            # Initialize SchedulerAgent
            self.scheduler = SchedulerAgent(
                post_log_path=os.path.join(self.logs_dir, "post_log.json"),
                cache_dir=self.cache_dir,
                time_zone=self.time_zone,
                auto_retry=True,
                max_retries=3,
                dry_run=self.dry_run
            )
            
            # Start the scheduler
            self.scheduler.start_scheduler()
            
            self.logger.info("All agents initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing agents: {e}")
            raise
    
    def _load_brand_guidelines(self) -> Dict[str, Any]:
        """Load brand guidelines from the specified file."""
        try:
            with open(self.brand_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load brand guidelines: {e}")
            return {}
    
    def _init_content_pool(self):
        """Initialize an empty content pool file."""
        content_pool = {platform: [] for platform in self.platforms}
        try:
            with open(self.content_pool_path, 'w') as f:
                json.dump(content_pool, f, indent=2)
            self.logger.info("Initialized empty content pool")
        except Exception as e:
            self.logger.error(f"Error initializing content pool: {e}")
    
    def _load_content_pool(self) -> Dict[str, List[Dict[str, Any]]]:
        """Load the content pool from file."""
        try:
            with open(self.content_pool_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading content pool: {e}")
            return {platform: [] for platform in self.platforms}
    
    def _save_content_pool(self, content_pool: Dict[str, List[Dict[str, Any]]]):
        """Save the content pool to file."""
        try:
            with open(self.content_pool_path, 'w') as f:
                json.dump(content_pool, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving content pool: {e}")
    
    def scan_trends(self, include_articles: bool = False) -> bool:
        """
        Run the TrendScannerAgent to scan for trends.
        
        Args:
            include_articles: Whether to search for articles about AI solving real-world problems
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Starting trend scanning with keywords: {self.keywords}")
            if include_articles:
                self.logger.info("Including article search for AI solving real-world problems")
            
            # Scan for trends (including articles if requested)
            trends = self.trend_scanner.scan_all_platforms(include_articles=include_articles)
            
            # Generate trend report
            trend_report = self.trend_scanner.generate_trend_report()
            
            # If articles were found, add them to the report
            if include_articles and "articles" in trends:
                articles = trends.get("articles", [])
                if articles:
                    article_report = self.trend_scanner.article_searcher.format_articles_for_trend_report(articles)
                    trend_report += "\n\n" + article_report
            
            # Save trend report as JSON
            with open(self.trend_report_path, 'w') as f:
                json.dump(trends, f, indent=2)
            
            # Also save as markdown for readability
            report_path_md = self.trend_report_path.replace('.json', '.md')
            with open(report_path_md, 'w') as f:
                f.write(trend_report)
            
            self.last_trend_scan = datetime.now()
            self.logger.info(f"Trend report saved to {self.trend_report_path}")
            return True
        
        except Exception as e:
            self.logger.error(f"Error scanning trends: {e}")
            return False
    
    def create_content(self) -> bool:
        """
        Run the ContentCreatorAgent to create content based on trends.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Creating content for platforms: {self.platforms}")
            
            # Check if trend report exists
            if not os.path.exists(self.trend_report_path):
                self.logger.error("Trend report not found, scanning trends first")
                if not self.scan_trends():
                    return False
            
            # Load trend data
            with open(self.trend_report_path, 'r') as f:
                trend_data = json.load(f)
            
            # Load current content pool
            content_pool = self._load_content_pool()
            
            # Generate content for each platform
            for platform in self.platforms:
                try:
                    self.logger.info(f"Generating content for {platform}")
                    
                    # Generate content
                    content = self.content_creator.generate_for_platform(
                        platform=platform,
                        trend_data=trend_data
                    )
                    
                    if content:
                        # Add timestamp and unique ID
                        content['created_at'] = datetime.now().isoformat()
                        content['id'] = f"{platform}_{int(time.time())}_{os.urandom(4).hex()}"
                        content['used'] = False
                        
                        # Add to content pool
                        content_pool[platform].append(content)
                        self.logger.info(f"Added new content to pool for {platform}")
                    else:
                        self.logger.warning(f"Failed to generate content for {platform}")
                
                except Exception as e:
                    self.logger.error(f"Error generating content for {platform}: {e}")
            
            # Save updated content pool
            self._save_content_pool(content_pool)
            
            self.last_content_creation = datetime.now()
            self.logger.info("Content creation completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Error creating content: {e}")
            return False
    
    def schedule_posts(self) -> bool:
        """
        Schedule posts using available content from the content pool.
        
        Returns:
            True if scheduling was successful, False otherwise
        """
        try:
            self.logger.info("Scheduling posts from content pool")
            
            # Load content pool
            content_pool = self._load_content_pool()
            
            # Check if we have content to schedule
            has_content = False
            for platform in self.platforms:
                unused_content = [c for c in content_pool[platform] if not c.get('used', False)]
                if unused_content:
                    has_content = True
                    break
            
            if not has_content:
                self.logger.info("No unused content available in pool, creating new content")
                if not self.create_content():
                    return False
                # Reload content pool after creation
                content_pool = self._load_content_pool()
            
            # Get a fresh content piece for each platform and schedule
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            for platform in self.platforms:
                # Get unused content
                unused_content = [c for c in content_pool[platform] if not c.get('used', False)]
                
                if not unused_content:
                    self.logger.warning(f"No unused content available for {platform}")
                    continue
                
                # Schedule based on max_posts_per_day
                max_posts = self.max_posts_per_day.get(platform, 1)
                posts_to_schedule = min(len(unused_content), max_posts)
                
                # Initialize post scheduler for optimal times
                post_scheduler = PostScheduler(time_zone=self.time_zone)
                
                # Get optimal posting times for this platform
                posting_times = post_scheduler.get_bulk_schedule(
                    platform=platform,
                    count=posts_to_schedule,
                    from_time=datetime.now() + timedelta(minutes=15),  # Start 15 minutes from now
                    min_hours_between=3  # At least 3 hours between posts
                )
                
                # Schedule posts for each time slot
                for i in range(posts_to_schedule):
                    content_item = unused_content[i]
                    posting_time = posting_times[i]
                    
                    # Request human review if enabled
                    if self.human_review:
                        approved = self._request_human_approval(platform, content_item, posting_time)
                        if not approved:
                            self.logger.info(f"Content for {platform} was rejected by human review")
                            continue
                    
                    # Schedule the post
                    self.logger.info(f"Scheduling {platform} post for {posting_time}")
                    result = self.scheduler.schedule_post(
                        platform=platform,
                        content=content_item,
                        scheduled_time=posting_time,
                        post_id=content_item['id']
                    )
                    
                    if result.get('status') == 'scheduled':
                        # Mark content as used
                        content_item['used'] = True
                        content_item['scheduled_time'] = posting_time.isoformat()
                        self.logger.info(f"Successfully scheduled post for {platform} at {posting_time}")
                    else:
                        self.logger.error(f"Failed to schedule post for {platform}: {result}")
            
            # Save updated content pool
            self._save_content_pool(content_pool)
            
            self.logger.info("Post scheduling completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Error scheduling posts: {e}")
            return False
    
    def schedule_posts_staggered(self) -> bool:
        """
        Schedule posts following the data.mdc timeline:
        - Twitter: 10:00 AM
        - Instagram: 10:30 AM
        - LinkedIn: 12:00 PM
        - Facebook: 11:00 AM (added for completeness)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Scheduling posts with staggered times")
            
            # Define posting times for each platform (Eastern Time)
            eastern = pytz.timezone('America/New_York')
            now = datetime.now(eastern)
            
            # Set posting times
            posting_times = {
                "twitter": now.replace(hour=10, minute=0, second=0, microsecond=0),
                "instagram": now.replace(hour=10, minute=30, second=0, microsecond=0),
                "linkedin": now.replace(hour=12, minute=0, second=0, microsecond=0),
                "facebook": now.replace(hour=11, minute=0, second=0, microsecond=0)
            }
            
            # If times are in the past, schedule for tomorrow
            for platform, post_time in posting_times.items():
                if post_time < now:
                    post_time += timedelta(days=1)
                    posting_times[platform] = post_time
            
            # Load content pool
            content_pool = self._load_content_pool()
            
            # Schedule posts for each platform
            for platform in self.platforms:
                if platform not in posting_times:
                    self.logger.warning(f"No posting time defined for {platform}, skipping")
                    continue
                
                # Get unused content for this platform
                unused_content = [c for c in content_pool[platform] if not c.get('used', False)]
                
                if not unused_content:
                    self.logger.warning(f"No unused content available for {platform}, creating new content")
                    # Create content for this platform
                    if not os.path.exists(self.trend_report_path):
                        if not self.scan_trends(include_articles=True):
                            continue
                    
                    with open(self.trend_report_path, 'r') as f:
                        trend_data = json.load(f)
                    
                    # Generate content for this platform
                    content = self.content_creator.generate_for_platform(
                        platform=platform,
                        trend_data=trend_data
                    )
                    
                    if not content:
                        self.logger.error(f"Failed to generate content for {platform}")
                        continue
                    
                    content['created_at'] = datetime.now().isoformat()
                    content['id'] = f"{platform}_{int(time.time())}_{os.urandom(4).hex()}"
                    unused_content = [content]
                    content_pool[platform].append(content)
                
                # Use the first unused content item
                content_item = unused_content[0]
                post_time = posting_times[platform]
                
                # Request human review if enabled
                if self.human_review:
                    approved = self._request_human_approval(platform, content_item, post_time)
                    if not approved:
                        self.logger.info(f"Content for {platform} was rejected by human review")
                        continue
                
                # Schedule the post
                self.logger.info(f"Scheduling {platform} post for {post_time.strftime('%I:%M %p')} Eastern")
                result = self.scheduler.schedule_post(
                    platform=platform,
                    content=content_item,
                    scheduled_time=post_time,
                    post_id=content_item['id']
                )
                
                if result.get('status') == 'scheduled':
                    # Mark content as used
                    content_item['used'] = True
                    content_item['scheduled_time'] = post_time.isoformat()
                    self.logger.info(f"Successfully scheduled {platform} post for {post_time.strftime('%I:%M %p')} Eastern")
                else:
                    self.logger.error(f"Failed to schedule {platform} post: {result.get('error', 'Unknown error')}")
            
            # Save updated content pool
            self._save_content_pool(content_pool)
            
            self.logger.info("Staggered post scheduling completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Error scheduling staggered posts: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def schedule_and_post_all_platforms(self) -> bool:
        """
        Schedule and immediately post content to all platforms.
        Used for the daily 8 AM automation cycle.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info("Posting to all platforms: %s", ", ".join(self.platforms))
            
            # Load content pool
            content_pool = self._load_content_pool()
            
            # Post to each platform immediately
            for platform in self.platforms:
                # Get unused content for this platform
                unused_content = [c for c in content_pool[platform] if not c.get('used', False)]
                
                if not unused_content:
                    self.logger.warning(f"No unused content available for {platform}, creating new content")
                    # Create content for this platform
                    if not os.path.exists(self.trend_report_path):
                        if not self.scan_trends(include_articles=True):
                            continue
                    
                    with open(self.trend_report_path, 'r') as f:
                        trend_data = json.load(f)
                    
                    # Generate content for this platform
                    content = self.content_creator.generate_for_platform(
                        platform=platform,
                        trend_data=trend_data
                    )
                    
                    if not content:
                        self.logger.error(f"Failed to generate content for {platform}")
                        continue
                    
                    content['created_at'] = datetime.now().isoformat()
                    content['id'] = f"{platform}_{int(time.time())}_{os.urandom(4).hex()}"
                    unused_content = [content]
                
                # Use the first unused content item
                content_item = unused_content[0]
                
                # Request human review if enabled
                if self.human_review:
                    approved = self._request_human_approval(platform, content_item, datetime.now())
                    if not approved:
                        self.logger.info(f"Content for {platform} was rejected by human review")
                        continue
                
                # Post immediately
                self.logger.info(f"Posting to {platform} immediately")
                result = self.scheduler.post_now(
                    platform=platform,
                    content=content_item,
                    post_id=content_item['id']
                )
                
                if result.get('success'):
                    # Mark content as used
                    content_item['used'] = True
                    content_item['posted_at'] = datetime.now().isoformat()
                    self.logger.info(f"Successfully posted to {platform}")
                else:
                    self.logger.error(f"Failed to post to {platform}: {result.get('error', 'Unknown error')}")
            
            # Save updated content pool
            self._save_content_pool(content_pool)
            
            self.logger.info("Posting to all platforms completed")
            return True
        
        except Exception as e:
            self.logger.error(f"Error posting to platforms: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return False
    
    def _request_human_approval(self, platform: str, content: Dict[str, Any], posting_time: datetime) -> bool:
        """
        Request human approval for content.
        
        Args:
            platform: The platform the content is for
            content: The content to approve
            posting_time: When the content will be posted
            
        Returns:
            True if approved, False otherwise
        """
        try:
            print("\n" + "="*60)
            print(f"CONTENT REVIEW FOR {platform.upper()} - Scheduled for {posting_time}")
            print("="*60)
            
            if platform == "twitter":
                print(f"TEXT: {content.get('text', '')}")
            elif platform == "instagram":
                print(f"CAPTION: {content.get('caption', '')}")
            elif platform == "linkedin":
                print(f"TEXT: {content.get('text', '')}")
            elif platform == "facebook":
                print(f"TEXT: {content.get('text', '')}")
                if 'link' in content:
                    print(f"LINK: {content.get('link', '')}")
            
            if 'image' in content:
                print("IMAGE: [Image data available]")
            
            print("\nApprove this content? (y/n): ", end="")
            response = input().lower().strip()
            
            return response in ('y', 'yes')
        
        except Exception as e:
            self.logger.error(f"Error during human approval: {e}")
            return False
    
    def run_daily_cycle(self, timeout_minutes: int = 15):
        """
        Run a complete daily cycle following the schedule from data.mdc:
        All tasks must be completed between 8:00 AM and 8:15 AM Eastern.
        - 08:00 AM: Fetch latest trends (hashtags, articles)
        - 08:05 AM: Generate draft posts for all platforms
        - 08:06 AM: Generate images (handled during content creation)
        - 08:10 AM: Review content (optional human step)
        - 08:15 AM: Post to all platforms immediately
        
        Args:
            timeout_minutes: Maximum time to run the cycle in minutes (default: 15)
        """
        start_time = datetime.now()
        timeout_seconds = timeout_minutes * 60
        
        try:
            self.logger.info("Starting daily cycle - all tasks must complete by 8:15 AM Eastern (timeout: %d minutes)", timeout_minutes)
            
            # Check timeout before each step
            def check_timeout():
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout_seconds:
                    self.logger.warning("Daily cycle timeout reached (%d minutes), stopping", timeout_minutes)
                    return True
                return False
            
            # 08:00 AM: Step 1 - Fetch latest trends (hashtags, articles)
            if check_timeout():
                return
            
            self.logger.info("[08:00 AM] Fetching latest trends and articles about AI solving real-world problems")
            if not self.scan_trends(include_articles=True):
                self.logger.error("Trend scanning failed, aborting cycle")
                return
            
            # 08:05 AM: Step 2 - Generate draft posts for all platforms
            if check_timeout():
                return
            
            self.logger.info("[08:05 AM] Generating draft posts for all platforms: %s", ", ".join(self.platforms))
            if not self.create_content():
                self.logger.error("Content creation failed, aborting cycle")
                return
            
            # 08:06 AM: Step 3 - Generate images (handled automatically during content creation)
            self.logger.info("[08:06 AM] Images generated during content creation")
            
            # 08:10 AM: Step 4 - Review content (optional human step - handled in posting)
            self.logger.info("[08:10 AM] Content ready for review (human review: %s)", self.human_review)
            
            # 08:15 AM: Step 5 - Post to all platforms immediately
            if check_timeout():
                return
            
            self.logger.info("[08:15 AM] Posting to all platforms immediately")
            if not self.schedule_and_post_all_platforms():
                self.logger.error("Posting to platforms failed")
                return
            
            elapsed = (datetime.now() - start_time).total_seconds()
            self.logger.info("Daily cycle completed successfully in %.1f seconds (all tasks completed by 8:15 AM)", elapsed)
            
        except Exception as e:
            self.logger.error(f"Error in daily cycle: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
    
    def start(self):
        """Start the orchestrator with scheduled tasks running at 8:00 AM Eastern daily."""
        if self.running:
            self.logger.warning("Orchestrator already running")
            return
        
        try:
            self.running = True
            
            # Set up timezone for Eastern Time
            eastern = pytz.timezone('America/New_York')
            
            # Set up scheduled tasks - Run daily cycle at 8:00 AM Eastern
            def run_daily_at_8am():
                """Wrapper to run daily cycle at 8 AM Eastern - all tasks complete by 8:15 AM."""
                # Convert to Eastern time for logging
                now_eastern = datetime.now(eastern)
                self.logger.info("="*60)
                self.logger.info("Running scheduled daily cycle at 8:00 AM Eastern (%s)", 
                               now_eastern.strftime("%Y-%m-%d %H:%M:%S %Z"))
                self.logger.info("All tasks must complete by 8:15 AM Eastern:")
                self.logger.info("  08:00 AM - Fetch trends and articles")
                self.logger.info("  08:05 AM - Generate content")
                self.logger.info("  08:06 AM - Generate images")
                self.logger.info("  08:10 AM - Review content (optional)")
                self.logger.info("  08:15 AM - Post to all platforms immediately")
                self.logger.info("="*60)
                self.run_daily_cycle(timeout_minutes=15)
            
            # Schedule for 8:00 AM Eastern every day
            schedule.every().day.at("08:00").do(run_daily_at_8am)
            
            # Calculate next run time in Eastern
            now_eastern = datetime.now(eastern)
            next_run = now_eastern.replace(hour=8, minute=0, second=0, microsecond=0)
            if now_eastern.hour >= 8:
                next_run += timedelta(days=1)
            
            self.logger.info("Orchestrator scheduled to run daily at 8:00 AM Eastern")
            self.logger.info("Next run: %s Eastern", next_run.strftime("%Y-%m-%d %H:%M:%S %Z"))
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(
                target=self._scheduler_loop,
                daemon=True
            )
            self.scheduler_thread.start()
            
            self.logger.info("Orchestrator started - waiting for scheduled time")
            
        except Exception as e:
            self.logger.error(f"Error starting orchestrator: {e}")
            self.running = False
    
    def _scheduler_loop(self):
        """Background thread for running scheduled tasks."""
        self.logger.info("Scheduler loop started")
        
        while self.running:
            try:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            except Exception as e:
                self.logger.error(f"Error in scheduler loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying after error
    
    def stop(self):
        """Stop the orchestrator."""
        if not self.running:
            self.logger.warning("Orchestrator not running")
            return
        
        self.running = False
        
        if self.scheduler_thread:
            self.scheduler_thread.join(timeout=5.0)
        
        # Stop the scheduler agent
        self.scheduler.stop_scheduler()
        
        self.logger.info("Orchestrator stopped")
    
    def run_once(self):
        """Run the pipeline once without scheduling."""
        self.run_daily_cycle()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI Agents Orchestrator")
    
    parser.add_argument('--keywords', '-k', type=str, nargs='+', 
                        default=['astronomy', 'physics', 'space'],
                        help='Keywords to search for trends')
    
    parser.add_argument('--platforms', '-p', type=str, nargs='+', 
                        default=['twitter', 'instagram', 'linkedin', 'facebook'],
                        choices=['twitter', 'instagram', 'linkedin', 'facebook'],
                        help='Platforms to create content for')
    
    parser.add_argument('--brand-file', '-b', type=str, 
                        default='agents/content_creator/example_brand_guidelines.json',
                        help='Path to the brand guidelines JSON file')
    
    parser.add_argument('--time-zone', '-t', type=str, default='America/New_York',
                        help='Time zone for scheduling')
    
    parser.add_argument('--dry-run', '-d', action='store_true',
                        help='Simulate posting without actually sending to APIs')
    
    parser.add_argument('--human-review', '-r', action='store_true',
                        help='Enable human review of content before posting')
    
    parser.add_argument('--trend-interval', type=int, default=4,
                        help='Hours between trend scans')
    
    parser.add_argument('--content-interval', type=int, default=24,
                        help='Hours between content creation cycles')
    
    parser.add_argument('--daemon', action='store_true',
                        help='Run as a daemon with scheduled tasks')
    
    parser.add_argument('--max-twitter', type=int, default=5,
                        help='Maximum Twitter posts per day')
    
    parser.add_argument('--max-instagram', type=int, default=2,
                        help='Maximum Instagram posts per day')
    
    parser.add_argument('--max-linkedin', type=int, default=1,
                        help='Maximum LinkedIn posts per day')
    
    parser.add_argument('--max-facebook', type=int, default=3,
                        help='Maximum Facebook posts per day')
    
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    
    logger.info("Starting AI Agents Orchestrator")
    logger.info(f"Keywords: {args.keywords}")
    logger.info(f"Platforms: {args.platforms}")
    logger.info(f"Brand file: {args.brand_file}")
    logger.info(f"Time zone: {args.time_zone}")
    logger.info(f"Dry run: {args.dry_run}")
    logger.info(f"Human review: {args.human_review}")
    
    # Configure max posts per day
    max_posts_per_day = {
        "twitter": args.max_twitter,
        "instagram": args.max_instagram,
        "linkedin": args.max_linkedin,
        "facebook": args.max_facebook
    }
    
    # Initialize and start orchestrator
    orchestrator = Orchestrator(
        brand_file=args.brand_file,
        platforms=args.platforms,
        keywords=args.keywords,
        time_zone=args.time_zone,
        dry_run=args.dry_run,
        human_review=args.human_review,
        trend_scan_interval=args.trend_interval,
        content_creation_interval=args.content_interval,
        max_posts_per_day=max_posts_per_day
    )
    
    try:
        if args.daemon:
            # Run as daemon with scheduled tasks
            orchestrator.start()
            
            # Keep main thread alive
            while True:
                try:
                    time.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt detected, stopping orchestrator")
                    orchestrator.stop()
                    break
        else:
            # Run once
            orchestrator.run_once()
    
    except Exception as e:
        logger.error(f"Error in main: {e}")
    
    finally:
        # Ensure proper cleanup
        if orchestrator.running:
            orchestrator.stop()
        
        logger.info("Orchestrator shutdown complete") 