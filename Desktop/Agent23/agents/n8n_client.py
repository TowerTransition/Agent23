"""
n8n Integration Client for Agent23

This module provides the interface between Agent23's content generation
pipeline and n8n's centralized posting/scheduling system.

Usage:
    from agents.n8n_client import get_n8n_client

    client = get_n8n_client()
    job = client.create_post_job(
        content=generated_content,
        channels=['facebook', 'instagram', 'linkedin'],
        metadata={'domain': 'Trading Futures'}
    )
    result = client.submit_job(job)
"""

import os
import uuid
import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
from zoneinfo import ZoneInfo

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)


class N8NClientError(Exception):
    """Base exception for n8n client errors."""
    pass


class N8NValidationError(N8NClientError):
    """Raised when n8n rejects a job due to validation errors."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Validation errors: {errors}")


class N8NConnectionError(N8NClientError):
    """Raised when unable to connect to n8n."""
    pass


class N8NClient:
    """
    Client for sending post jobs to n8n webhook.

    This client normalizes Agent23's content format into the standardized
    post job schema expected by n8n workflows.

    Attributes:
        webhook_url: The n8n webhook endpoint URL
        timeout: Request timeout in seconds
        verify_ssl: Whether to verify SSL certificates
        agent_version: Version string for tracking
    """

    # Default n8n webhook endpoint
    DEFAULT_WEBHOOK_URL = "http://34.46.199.106:5678/webhook/claude"

    # Valid platforms for posting
    VALID_CHANNELS = {"facebook", "instagram", "linkedin", "twitter"}

    # Platform-specific constraints
    PLATFORM_LIMITS = {
        "twitter": {"max_chars": 280, "max_hashtags": 3},
        "facebook": {"max_chars": 2000, "max_hashtags": 5},
        "instagram": {"max_chars": 1000, "max_hashtags": 30, "requires_media": True},
        "linkedin": {"max_chars": 1000, "max_hashtags": 5},
    }

    def __init__(
        self,
        webhook_url: str = None,
        timeout: int = 30,
        verify_ssl: bool = True,
        agent_version: str = "1.0.0"
    ):
        """
        Initialize n8n client.

        Args:
            webhook_url: n8n webhook endpoint URL. Defaults to N8N_WEBHOOK_URL env var
                        or the default endpoint.
            timeout: Request timeout in seconds (default: 30)
            verify_ssl: Whether to verify SSL certificates (default: True)
            agent_version: Version string for metadata (default: "1.0.0")
        """
        if requests is None:
            raise ImportError("requests library required. Install with: pip install requests")

        self.webhook_url = webhook_url or os.getenv(
            'N8N_WEBHOOK_URL',
            self.DEFAULT_WEBHOOK_URL
        )
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.agent_version = agent_version

        logger.info(f"N8NClient initialized with endpoint: {self.webhook_url}")

    def generate_job_id(self) -> str:
        """
        Generate unique job ID (UUID v4).

        Returns:
            UUID string in format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        """
        return str(uuid.uuid4())

    def generate_idempotency_key(
        self,
        content: Dict,
        channels: List[str],
        publish_at: str
    ) -> str:
        """
        Generate idempotency key from content hash.

        The key is a SHA256 hash of the normalized content, channels, and
        publish time. This ensures duplicate submissions are detected.

        Args:
            content: Post content dict (must have text.default)
            channels: Target platforms
            publish_at: ISO timestamp string

        Returns:
            SHA256 hash prefixed with 'sha256:'
        """
        key_data = json.dumps({
            'text': content.get('text', {}).get('default', ''),
            'channels': sorted(channels),
            'publish_at': publish_at
        }, sort_keys=True)

        hash_value = hashlib.sha256(key_data.encode()).hexdigest()
        return f"sha256:{hash_value}"

    def create_post_job(
        self,
        content: Dict,
        channels: List[str],
        publish_at: Union[datetime, str] = None,
        metadata: Dict = None,
        priority: int = 5,
        callbacks: Dict = None
    ) -> Dict:
        """
        Create a normalized post job payload.

        Converts Agent23's content format into the standardized schema
        expected by n8n workflows.

        Args:
            content: Generated content from ContentCreatorAgent. Expected format:
                {
                    "text": "Post body...",
                    "caption": "Same as text (Instagram)",
                    "hashtags": ["Tag1", "Tag2"],
                    "image": {"url": "...", "base64": "...", "filepath": "..."}
                }
            channels: List of platforms ['facebook', 'instagram', 'linkedin']
            publish_at: Scheduled publish time. If None, defaults to next 8:15 AM ET.
                       Can be datetime object or ISO format string.
            metadata: Agent23 metadata to include (domain, lens, generation_mode, etc.)
            priority: Queue priority 1-10 (1=highest, default: 5)
            callbacks: Optional callback URLs {on_success: "...", on_failure: "..."}

        Returns:
            Normalized post job dict ready for n8n submission

        Raises:
            ValueError: If channels contains invalid platform names
        """
        # Validate channels
        invalid_channels = set(channels) - self.VALID_CHANNELS
        if invalid_channels:
            raise ValueError(f"Invalid channels: {invalid_channels}. Valid: {self.VALID_CHANNELS}")

        # Default publish time to next 8:15 AM ET
        if publish_at is None:
            publish_at = self._get_next_post_time()

        # Ensure publish_at is ISO format string
        if isinstance(publish_at, datetime):
            # Ensure timezone aware
            if publish_at.tzinfo is None:
                publish_at = publish_at.replace(tzinfo=ZoneInfo("America/New_York"))
            publish_at_str = publish_at.isoformat()
        else:
            publish_at_str = publish_at

        job_id = self.generate_job_id()

        # Normalize content structure
        normalized_content = self._normalize_content(content, channels)

        # Generate idempotency key
        idempotency_key = self.generate_idempotency_key(
            normalized_content,
            channels,
            publish_at_str
        )

        # Build job payload
        job = {
            "job_id": job_id,
            "idempotency_key": idempotency_key,
            "channels": channels,
            "content": normalized_content,
            "schedule": {
                "publish_at": publish_at_str,
                "timezone": "America/New_York",
                "priority": max(1, min(10, priority))  # Clamp to 1-10
            },
            "metadata": {
                **(metadata or {}),
                "agent_version": self.agent_version,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
        }

        # Add callbacks if provided
        if callbacks:
            job["callbacks"] = callbacks

        logger.debug(f"Created post job: {job_id} for channels: {channels}")
        return job

    def _normalize_content(
        self,
        content: Dict,
        channels: List[str]
    ) -> Dict:
        """
        Convert Agent23 content format to n8n normalized format.

        Agent23 format (input):
        {
            "platform": "twitter",
            "text": "Full post text with footer and hashtags",
            "caption": "Same as text (Instagram convention)",
            "hashtags": ["Tag1", "Tag2"],
            "image": {"filepath": "...", "url": "...", "base64": "..."},
            "meta": {"used_direct_model": true}
        }

        n8n format (output):
        {
            "text": {"default": "...", "facebook": "...", "instagram": "..."},
            "media": [{"type": "image", "url": "...", "alt_text": "..."}],
            "hashtags": ["Tag1", "Tag2"],
            "link": {"url": "...", "title": "..."}  # optional
        }

        Args:
            content: Agent23 content dict
            channels: Target platforms for text variants

        Returns:
            Normalized content dict for n8n
        """
        # Extract primary text
        primary_text = content.get("text") or content.get("caption") or ""

        # Build text variants
        text_content = {"default": primary_text}

        # Check for platform-specific text variants
        for channel in channels:
            # Look for explicit platform text
            platform_key = f"{channel}_text"
            if platform_key in content:
                text_content[channel] = content[platform_key]
            # Or use caption for Instagram
            elif channel == "instagram" and content.get("caption"):
                text_content[channel] = content["caption"]

        # Normalize media
        media = []
        if content.get("image"):
            img = content["image"]
            media_item = {"type": "image"}

            # Priority: url > base64 > filepath
            if img.get("url"):
                media_item["url"] = img["url"]
            elif img.get("base64"):
                media_item["base64"] = img["base64"]
            elif img.get("filepath"):
                # Note: filepath needs to be converted to URL or base64
                # before submission to n8n
                media_item["filepath"] = img["filepath"]
                logger.warning(f"Media has filepath only - may need conversion: {img['filepath']}")

            # Alt text for accessibility
            if img.get("alt_text"):
                media_item["alt_text"] = img["alt_text"]

            # Aspect ratio hint
            if img.get("aspect_ratio"):
                media_item["aspect_ratio"] = img["aspect_ratio"]

            media.append(media_item)

        # Build normalized content
        normalized = {
            "text": text_content,
            "hashtags": content.get("hashtags", [])
        }

        # Only include media if present
        if media:
            normalized["media"] = media

        # Include link if present
        if content.get("link"):
            normalized["link"] = content["link"]

        return normalized

    def _get_next_post_time(self) -> datetime:
        """
        Calculate next 8:15 AM Eastern time.

        This matches Agent23's fixed daily schedule from PostScheduler.

        Returns:
            datetime object for next 8:15 AM ET
        """
        et = ZoneInfo("America/New_York")
        now = datetime.now(et)

        # Target 8:15 AM
        target = now.replace(hour=8, minute=15, second=0, microsecond=0)

        # If past today's target, schedule for tomorrow
        if now >= target:
            target = target + timedelta(days=1)

        return target

    def submit_job(self, job: Dict) -> Dict:
        """
        Submit post job to n8n webhook.

        Args:
            job: Normalized post job from create_post_job()

        Returns:
            Response from n8n. On success:
            {"status": "accepted", "job_id": "..."}

        Raises:
            N8NValidationError: If n8n rejects the job (400 response)
            N8NConnectionError: If unable to connect to n8n
            N8NClientError: For other errors
        """
        job_id = job.get('job_id', 'unknown')
        logger.info(f"Submitting job {job_id} to n8n at {self.webhook_url}")

        try:
            response = requests.post(
                self.webhook_url,
                json=job,
                timeout=self.timeout,
                verify=self.verify_ssl,
                headers={
                    "Content-Type": "application/json",
                    "X-Agent23-Job-ID": job_id
                }
            )

            # Handle response status
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    errors = error_data.get('errors', [str(error_data)])
                except ValueError:
                    errors = [response.text]
                logger.error(f"Validation error for job {job_id}: {errors}")
                raise N8NValidationError(errors)

            response.raise_for_status()

            # Parse successful response
            try:
                result = response.json()
            except ValueError:
                result = {"status": "accepted", "raw_response": response.text}

            logger.info(f"Job {job_id} accepted by n8n: {result.get('status', 'unknown')}")
            return result

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to n8n: {e}")
            raise N8NConnectionError(f"Unable to connect to n8n at {self.webhook_url}: {e}")

        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout connecting to n8n: {e}")
            raise N8NConnectionError(f"Timeout connecting to n8n: {e}")

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error submitting job {job_id}: {e}")
            raise N8NClientError(f"Failed to submit job: {e}")

    def submit_multi_platform(
        self,
        content_by_platform: Dict[str, Dict],
        publish_at: Union[datetime, str] = None,
        metadata: Dict = None,
        priority: int = 5
    ) -> Dict:
        """
        Submit content for multiple platforms in a single job.

        This is more efficient than submitting separate jobs when all
        platforms should post at the same time.

        Args:
            content_by_platform: Dict mapping platform to content:
                {
                    "facebook": {"text": "FB post...", "hashtags": [...]},
                    "instagram": {"text": "IG post...", "image": {...}},
                    "linkedin": {"text": "LI post...", "hashtags": [...]}
                }
            publish_at: Scheduled time (default: next 8:15 AM ET)
            metadata: Shared metadata for all platforms
            priority: Queue priority 1-10

        Returns:
            n8n response dict
        """
        channels = list(content_by_platform.keys())

        if not channels:
            raise ValueError("content_by_platform cannot be empty")

        # Merge content: use first platform as default, add platform-specific variants
        first_platform = channels[0]
        merged_content = content_by_platform[first_platform].copy()

        # Add platform-specific text variants
        for platform, content in content_by_platform.items():
            platform_text = content.get("text") or content.get("caption")
            if platform_text:
                merged_content[f"{platform}_text"] = platform_text

        # Merge hashtags (union of all)
        all_hashtags = set()
        for content in content_by_platform.values():
            all_hashtags.update(content.get("hashtags", []))
        merged_content["hashtags"] = list(all_hashtags)

        # Use first available image
        for content in content_by_platform.values():
            if content.get("image") and not merged_content.get("image"):
                merged_content["image"] = content["image"]
                break

        job = self.create_post_job(
            content=merged_content,
            channels=channels,
            publish_at=publish_at,
            metadata=metadata,
            priority=priority
        )

        return self.submit_job(job)

    def health_check(self) -> Dict:
        """
        Check if n8n webhook is reachable.

        Sends a minimal test payload to verify connectivity.

        Returns:
            {"healthy": True/False, "message": "...", "latency_ms": ...}
        """
        import time

        start = time.time()
        try:
            response = requests.post(
                self.webhook_url,
                json={"health_check": True, "timestamp": datetime.now(timezone.utc).isoformat()},
                timeout=10,
                verify=self.verify_ssl
            )

            latency_ms = int((time.time() - start) * 1000)

            return {
                "healthy": response.status_code in (200, 202),
                "status_code": response.status_code,
                "message": "n8n webhook reachable",
                "latency_ms": latency_ms
            }

        except requests.exceptions.RequestException as e:
            return {
                "healthy": False,
                "message": str(e),
                "latency_ms": None
            }


# Singleton instance
_client: Optional[N8NClient] = None


def get_n8n_client(
    webhook_url: str = None,
    force_new: bool = False
) -> N8NClient:
    """
    Get or create singleton n8n client.

    Args:
        webhook_url: Override webhook URL (only used if creating new client)
        force_new: If True, always create a new client instance

    Returns:
        N8NClient instance
    """
    global _client

    if _client is None or force_new:
        _client = N8NClient(webhook_url=webhook_url)

    return _client


def reset_client():
    """Reset the singleton client (useful for testing)."""
    global _client
    _client = None
