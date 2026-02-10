"""
Tests for n8n Integration Client

Run with: python -m unittest tests.test_n8n_client -v
"""

import unittest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
import json

from agents.n8n_client import (
    N8NClient,
    N8NClientError,
    N8NValidationError,
    N8NConnectionError,
    get_n8n_client,
    reset_client
)


class TestN8NClientInit(unittest.TestCase):
    """Tests for N8NClient initialization."""

    def setUp(self):
        reset_client()

    def test_init_with_defaults(self):
        """Test client initializes with default values."""
        client = N8NClient()

        self.assertEqual(client.webhook_url, N8NClient.DEFAULT_WEBHOOK_URL)
        self.assertEqual(client.timeout, 30)
        self.assertTrue(client.verify_ssl)
        self.assertEqual(client.agent_version, "1.0.0")

    def test_init_with_custom_url(self):
        """Test client initializes with custom webhook URL."""
        custom_url = "http://custom:5678/webhook/test"
        client = N8NClient(webhook_url=custom_url)

        self.assertEqual(client.webhook_url, custom_url)

    @patch.dict('os.environ', {'N8N_WEBHOOK_URL': 'http://env:5678/webhook'})
    def test_init_from_env_var(self):
        """Test client reads webhook URL from environment variable."""
        client = N8NClient()

        self.assertEqual(client.webhook_url, 'http://env:5678/webhook')

    def test_init_custom_overrides_env(self):
        """Test explicit URL overrides environment variable."""
        with patch.dict('os.environ', {'N8N_WEBHOOK_URL': 'http://env:5678'}):
            client = N8NClient(webhook_url='http://explicit:5678')
            self.assertEqual(client.webhook_url, 'http://explicit:5678')


class TestJobIdGeneration(unittest.TestCase):
    """Tests for job ID generation."""

    def setUp(self):
        self.client = N8NClient()

    def test_generate_job_id_format(self):
        """Test job ID is valid UUID v4 format."""
        job_id = self.client.generate_job_id()

        # UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
        self.assertRegex(
            job_id,
            r'^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$'
        )

    def test_generate_job_id_unique(self):
        """Test job IDs are unique."""
        ids = [self.client.generate_job_id() for _ in range(100)]
        self.assertEqual(len(ids), len(set(ids)))


class TestIdempotencyKey(unittest.TestCase):
    """Tests for idempotency key generation."""

    def setUp(self):
        self.client = N8NClient()

    def test_idempotency_key_format(self):
        """Test idempotency key has correct format."""
        key = self.client.generate_idempotency_key(
            content={'text': {'default': 'test'}},
            channels=['facebook'],
            publish_at='2026-02-01T13:15:00Z'
        )

        self.assertTrue(key.startswith('sha256:'))
        self.assertEqual(len(key), 71)  # 'sha256:' + 64 hex chars

    def test_idempotency_key_deterministic(self):
        """Test same inputs produce same key."""
        kwargs = {
            'content': {'text': {'default': 'test content'}},
            'channels': ['facebook', 'instagram'],
            'publish_at': '2026-02-01T13:15:00Z'
        }

        key1 = self.client.generate_idempotency_key(**kwargs)
        key2 = self.client.generate_idempotency_key(**kwargs)

        self.assertEqual(key1, key2)

    def test_idempotency_key_channel_order_independent(self):
        """Test channel order doesn't affect key."""
        content = {'text': {'default': 'test'}}
        publish_at = '2026-02-01T13:15:00Z'

        key1 = self.client.generate_idempotency_key(
            content, ['facebook', 'instagram'], publish_at
        )
        key2 = self.client.generate_idempotency_key(
            content, ['instagram', 'facebook'], publish_at
        )

        self.assertEqual(key1, key2)

    def test_idempotency_key_different_content(self):
        """Test different content produces different keys."""
        channels = ['facebook']
        publish_at = '2026-02-01T13:15:00Z'

        key1 = self.client.generate_idempotency_key(
            {'text': {'default': 'content A'}}, channels, publish_at
        )
        key2 = self.client.generate_idempotency_key(
            {'text': {'default': 'content B'}}, channels, publish_at
        )

        self.assertNotEqual(key1, key2)


class TestCreatePostJob(unittest.TestCase):
    """Tests for post job creation."""

    def setUp(self):
        self.client = N8NClient()
        self.sample_content = {
            'text': 'Test post body\n\n— Elevare by Amaziah',
            'hashtags': ['RealWorldAI', 'Test'],
            'image': {
                'url': 'https://example.com/image.png',
                'alt_text': 'Test image'
            }
        }

    def test_create_job_basic(self):
        """Test basic job creation."""
        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook']
        )

        self.assertIn('job_id', job)
        self.assertIn('idempotency_key', job)
        self.assertEqual(job['channels'], ['facebook'])
        self.assertIn('content', job)
        self.assertIn('schedule', job)
        self.assertIn('metadata', job)

    def test_create_job_multi_channel(self):
        """Test job creation with multiple channels."""
        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook', 'instagram', 'linkedin']
        )

        self.assertEqual(job['channels'], ['facebook', 'instagram', 'linkedin'])

    def test_create_job_invalid_channel(self):
        """Test job creation fails with invalid channel."""
        with self.assertRaises(ValueError) as ctx:
            self.client.create_post_job(
                content=self.sample_content,
                channels=['facebook', 'twitter']  # twitter not supported via n8n
            )

        self.assertIn('twitter', str(ctx.exception))

    def test_create_job_content_normalization(self):
        """Test content is normalized correctly."""
        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook']
        )

        content = job['content']
        self.assertIn('text', content)
        self.assertIn('default', content['text'])
        self.assertEqual(content['hashtags'], ['RealWorldAI', 'Test'])
        self.assertEqual(len(content['media']), 1)
        self.assertEqual(content['media'][0]['type'], 'image')
        self.assertEqual(content['media'][0]['url'], 'https://example.com/image.png')

    def test_create_job_schedule_default(self):
        """Test default schedule is next 8:15 AM ET."""
        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook']
        )

        schedule = job['schedule']
        self.assertIn('publish_at', schedule)
        self.assertEqual(schedule['timezone'], 'America/New_York')
        self.assertEqual(schedule['priority'], 5)

        # Parse and verify time
        publish_at = datetime.fromisoformat(schedule['publish_at'])
        self.assertEqual(publish_at.hour, 8)
        self.assertEqual(publish_at.minute, 15)

    def test_create_job_custom_schedule(self):
        """Test custom schedule time."""
        custom_time = datetime(2026, 3, 15, 14, 30, tzinfo=timezone.utc)

        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook'],
            publish_at=custom_time
        )

        self.assertEqual(job['schedule']['publish_at'], custom_time.isoformat())

    def test_create_job_priority_clamped(self):
        """Test priority is clamped to 1-10."""
        job_low = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook'],
            priority=0
        )
        job_high = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook'],
            priority=100
        )

        self.assertEqual(job_low['schedule']['priority'], 1)
        self.assertEqual(job_high['schedule']['priority'], 10)

    def test_create_job_with_metadata(self):
        """Test metadata is included."""
        metadata = {
            'domain': 'Trading Futures',
            'expert_lens': 'The System View',
            'generation_mode': 'peft_direct'
        }

        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook'],
            metadata=metadata
        )

        self.assertEqual(job['metadata']['domain'], 'Trading Futures')
        self.assertEqual(job['metadata']['expert_lens'], 'The System View')
        self.assertIn('agent_version', job['metadata'])
        self.assertIn('created_at', job['metadata'])

    def test_create_job_with_callbacks(self):
        """Test callbacks are included when provided."""
        callbacks = {
            'on_success': 'http://agent23/callback/success',
            'on_failure': 'http://agent23/callback/failure'
        }

        job = self.client.create_post_job(
            content=self.sample_content,
            channels=['facebook'],
            callbacks=callbacks
        )

        self.assertEqual(job['callbacks'], callbacks)


class TestNormalizeContent(unittest.TestCase):
    """Tests for content normalization."""

    def setUp(self):
        self.client = N8NClient()

    def test_normalize_text_only(self):
        """Test normalization of text-only content."""
        content = {'text': 'Simple post text'}
        normalized = self.client._normalize_content(content, ['facebook'])

        self.assertEqual(normalized['text']['default'], 'Simple post text')
        self.assertNotIn('media', normalized)

    def test_normalize_caption_fallback(self):
        """Test caption is used if text missing (Instagram convention)."""
        content = {'caption': 'Instagram caption'}
        normalized = self.client._normalize_content(content, ['instagram'])

        self.assertEqual(normalized['text']['default'], 'Instagram caption')

    def test_normalize_platform_variants(self):
        """Test platform-specific text variants."""
        content = {
            'text': 'Default text',
            'facebook_text': 'Facebook specific',
            'instagram_text': 'Instagram specific'
        }
        normalized = self.client._normalize_content(
            content,
            ['facebook', 'instagram', 'linkedin']
        )

        self.assertEqual(normalized['text']['default'], 'Default text')
        self.assertEqual(normalized['text']['facebook'], 'Facebook specific')
        self.assertEqual(normalized['text']['instagram'], 'Instagram specific')
        self.assertNotIn('linkedin', normalized['text'])

    def test_normalize_with_image_url(self):
        """Test normalization with image URL."""
        content = {
            'text': 'Post with image',
            'image': {'url': 'https://example.com/img.png'}
        }
        normalized = self.client._normalize_content(content, ['facebook'])

        self.assertEqual(len(normalized['media']), 1)
        self.assertEqual(normalized['media'][0]['type'], 'image')
        self.assertEqual(normalized['media'][0]['url'], 'https://example.com/img.png')

    def test_normalize_with_image_base64(self):
        """Test normalization with base64 image."""
        content = {
            'text': 'Post with base64 image',
            'image': {'base64': 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB...'}
        }
        normalized = self.client._normalize_content(content, ['instagram'])

        self.assertEqual(normalized['media'][0]['base64'], content['image']['base64'])

    def test_normalize_with_alt_text(self):
        """Test alt text is preserved."""
        content = {
            'text': 'Accessible post',
            'image': {
                'url': 'https://example.com/img.png',
                'alt_text': 'Description of image for screen readers'
            }
        }
        normalized = self.client._normalize_content(content, ['facebook'])

        self.assertEqual(
            normalized['media'][0]['alt_text'],
            'Description of image for screen readers'
        )

    def test_normalize_hashtags(self):
        """Test hashtags are preserved."""
        content = {
            'text': 'Post with tags',
            'hashtags': ['Tag1', 'Tag2', 'Tag3']
        }
        normalized = self.client._normalize_content(content, ['facebook'])

        self.assertEqual(normalized['hashtags'], ['Tag1', 'Tag2', 'Tag3'])


class TestSubmitJob(unittest.TestCase):
    """Tests for job submission."""

    def setUp(self):
        self.client = N8NClient(webhook_url='http://test:5678/webhook/claude')
        self.sample_job = {
            'job_id': 'test-job-123',
            'idempotency_key': 'sha256:abc123',
            'channels': ['facebook'],
            'content': {'text': {'default': 'test'}},
            'schedule': {'publish_at': '2026-02-01T13:15:00Z'},
            'metadata': {}
        }

    @patch('requests.post')
    def test_submit_job_success(self, mock_post):
        """Test successful job submission."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            'status': 'accepted',
            'job_id': 'test-job-123'
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        result = self.client.submit_job(self.sample_job)

        self.assertEqual(result['status'], 'accepted')
        mock_post.assert_called_once()

        # Verify request details
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]['json'], self.sample_job)
        self.assertEqual(call_args[1]['timeout'], 30)

    @patch('requests.post')
    def test_submit_job_validation_error(self, mock_post):
        """Test handling of validation errors."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            'errors': ['job_id is required', 'channels is required']
        }
        mock_post.return_value = mock_response

        with self.assertRaises(N8NValidationError) as ctx:
            self.client.submit_job(self.sample_job)

        self.assertEqual(len(ctx.exception.errors), 2)

    @patch('requests.post')
    def test_submit_job_connection_error(self, mock_post):
        """Test handling of connection errors."""
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("Connection refused")

        with self.assertRaises(N8NConnectionError):
            self.client.submit_job(self.sample_job)

    @patch('requests.post')
    def test_submit_job_timeout(self, mock_post):
        """Test handling of timeout."""
        import requests
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with self.assertRaises(N8NConnectionError):
            self.client.submit_job(self.sample_job)


class TestSubmitMultiPlatform(unittest.TestCase):
    """Tests for multi-platform submission."""

    def setUp(self):
        self.client = N8NClient(webhook_url='http://test:5678/webhook/claude')

    @patch('requests.post')
    def test_submit_multi_platform(self, mock_post):
        """Test multi-platform content merging and submission."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {'status': 'accepted'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        content_by_platform = {
            'facebook': {
                'text': 'Facebook version',
                'hashtags': ['FB', 'Test']
            },
            'linkedin': {
                'text': 'LinkedIn version',
                'hashtags': ['LI', 'Professional']
            }
        }

        result = self.client.submit_multi_platform(content_by_platform)

        self.assertEqual(result['status'], 'accepted')

        # Verify merged content
        call_args = mock_post.call_args
        submitted_job = call_args[1]['json']
        self.assertEqual(set(submitted_job['channels']), {'facebook', 'linkedin'})

    def test_submit_multi_platform_empty(self):
        """Test empty content raises error."""
        with self.assertRaises(ValueError):
            self.client.submit_multi_platform({})


class TestHealthCheck(unittest.TestCase):
    """Tests for health check functionality."""

    def setUp(self):
        self.client = N8NClient(webhook_url='http://test:5678/webhook/claude')

    @patch('requests.post')
    def test_health_check_healthy(self, mock_post):
        """Test health check when n8n is healthy."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        result = self.client.health_check()

        self.assertTrue(result['healthy'])
        self.assertIn('latency_ms', result)

    @patch('requests.post')
    def test_health_check_unhealthy(self, mock_post):
        """Test health check when n8n is unreachable."""
        import requests
        mock_post.side_effect = requests.exceptions.ConnectionError("Connection refused")

        result = self.client.health_check()

        self.assertFalse(result['healthy'])
        self.assertIn('Connection', result['message'])


class TestSingletonClient(unittest.TestCase):
    """Tests for singleton client pattern."""

    def setUp(self):
        reset_client()

    def tearDown(self):
        reset_client()

    def test_get_client_singleton(self):
        """Test get_n8n_client returns same instance."""
        client1 = get_n8n_client()
        client2 = get_n8n_client()

        self.assertIs(client1, client2)

    def test_get_client_force_new(self):
        """Test force_new creates new instance."""
        client1 = get_n8n_client()
        client2 = get_n8n_client(force_new=True)

        self.assertIsNot(client1, client2)

    def test_reset_client(self):
        """Test reset_client clears singleton."""
        client1 = get_n8n_client()
        reset_client()
        client2 = get_n8n_client()

        self.assertIsNot(client1, client2)


class TestIntegrationScenarios(unittest.TestCase):
    """Integration-style tests for realistic scenarios."""

    def setUp(self):
        self.client = N8NClient(webhook_url='http://test:5678/webhook/claude')

    @patch('requests.post')
    def test_full_workflow_facebook_only(self, mock_post):
        """Test full workflow: create and submit Facebook post."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {'status': 'accepted', 'job_id': 'fb-123'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Simulate Agent23 content output
        agent23_content = {
            'platform': 'facebook',
            'text': 'Discipline in Futures Trading: The system isn\'t about prediction—it\'s about execution.\n\nReal-world systems. Real clarity.\n— Elevare by Amaziah',
            'hashtags': ['RealWorldAI', 'TradingSystems', 'ExecutionFocus', 'RiskDiscipline'],
            'meta': {'used_direct_model': True}
        }

        # Create and submit job
        job = self.client.create_post_job(
            content=agent23_content,
            channels=['facebook'],
            metadata={
                'domain': 'Trading Futures',
                'expert_lens': 'The System View',
                'generation_mode': 'peft_direct'
            }
        )

        result = self.client.submit_job(job)

        self.assertEqual(result['status'], 'accepted')
        self.assertIn('Discipline in Futures Trading', job['content']['text']['default'])
        self.assertEqual(job['metadata']['domain'], 'Trading Futures')

    @patch('requests.post')
    def test_full_workflow_all_platforms(self, mock_post):
        """Test full workflow: create and submit to all platforms."""
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {'status': 'accepted'}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        # Simulate multi-platform content
        content_by_platform = {
            'facebook': {
                'text': 'Long Facebook post about assisted living decisions...\n\n— Elevare by Amaziah',
                'hashtags': ['AssistedLiving', 'CareDecisions']
            },
            'instagram': {
                'text': 'IG version with image focus\n\n— Elevare by Amaziah',
                'hashtags': ['AssistedLiving', 'SeniorCare', 'CareDecisions'],
                'image': {'url': 'https://storage.example.com/img.png'}
            },
            'linkedin': {
                'text': 'Professional LinkedIn post about care facility evaluation...\n\n— Elevare by Amaziah',
                'hashtags': ['AssistedLiving', 'HealthcareDecisions']
            }
        }

        result = self.client.submit_multi_platform(
            content_by_platform,
            metadata={'domain': 'Assisted Living'}
        )

        self.assertEqual(result['status'], 'accepted')


if __name__ == '__main__':
    unittest.main()
