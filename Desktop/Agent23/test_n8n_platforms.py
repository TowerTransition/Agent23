#!/usr/bin/env python3
"""
Test script for Agent23 n8n workflow - Tests Facebook, Instagram, and LinkedIn posting.

Run this on your GCP instance:
    cd ~/Agent23
    python test_n8n_platforms.py

Prerequisites:
    - n8n running at localhost:5678
    - Credentials configured in n8n UI for FB, IG, LI
    - Agent23-Main workflow active
"""

import requests
import json
import uuid
import hashlib
from datetime import datetime, timezone
import time
import os

# n8n webhook URL (on GCP instance, n8n runs on localhost:5678)
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/claude')

def generate_job_id():
    """Generate unique job ID."""
    return str(uuid.uuid4())

def generate_idempotency_key(content, channels):
    """Generate idempotency key from content hash."""
    key_data = json.dumps({
        'text': content,
        'channels': sorted(channels),
        'ts': datetime.now(timezone.utc).strftime('%Y-%m-%d-%H')
    }, sort_keys=True)
    return f"sha256:{hashlib.sha256(key_data.encode()).hexdigest()[:16]}"

def test_health_check():
    """Test n8n webhook health check."""
    print("\n" + "=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json={'message': 'hello n8n'},
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        return response.status_code == 200
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_single_platform(platform, text, hashtags=None):
    """Test posting to a single platform."""
    print(f"\n" + "=" * 60)
    print(f"TEST: {platform.upper()} Post")
    print("=" * 60)

    job_id = generate_job_id()

    payload = {
        'job_id': job_id,
        'idempotency_key': generate_idempotency_key(text, [platform]),
        'channels': [platform],
        'content': {
            'text': {
                'default': text,
                platform: text
            },
            'hashtags': hashtags or ['ElevareByAmaziah', 'Test'],
            'media': []  # No image for this test
        },
        'schedule': {
            'publish_at': datetime.now(timezone.utc).isoformat(),
            'timezone': 'America/New_York'
        },
        'metadata': {
            'test': True,
            'source': 'test_script',
            'platform': platform
        }
    }

    print(f"Job ID: {job_id}")
    print(f"Platform: {platform}")
    print(f"Text: {text[:50]}...")

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        return response.status_code == 200, job_id
    except Exception as e:
        print(f"ERROR: {e}")
        return False, job_id

def test_multi_platform():
    """Test posting to all platforms at once."""
    print("\n" + "=" * 60)
    print("TEST: Multi-Platform Post (FB + IG + LI)")
    print("=" * 60)

    job_id = generate_job_id()
    channels = ['facebook', 'instagram', 'linkedin']

    # Platform-specific text
    base_text = "Testing Agent23 multi-platform posting. This is an automated test from Elevare by Amaziah."

    payload = {
        'job_id': job_id,
        'idempotency_key': generate_idempotency_key(base_text, channels),
        'channels': channels,
        'content': {
            'text': {
                'default': base_text,
                'facebook': f"{base_text}\n\nFollow us for more updates!",
                'instagram': base_text,  # IG needs image, but testing text flow
                'linkedin': f"{base_text}\n\nConnect with us for professional insights."
            },
            'hashtags': ['ElevareByAmaziah', 'Automation', 'Test', 'SocialMedia'],
            'media': []
        },
        'schedule': {
            'publish_at': datetime.now(timezone.utc).isoformat(),
            'timezone': 'America/New_York'
        },
        'metadata': {
            'test': True,
            'source': 'test_script',
            'multi_platform': True
        }
    }

    print(f"Job ID: {job_id}")
    print(f"Channels: {channels}")

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}")
        return response.status_code == 200, job_id
    except Exception as e:
        print(f"ERROR: {e}")
        return False, job_id

def check_n8n_executions(api_key=None):
    """Check recent n8n executions via API."""
    print("\n" + "=" * 60)
    print("Checking n8n Executions")
    print("=" * 60)

    if not api_key:
        api_key = os.getenv('N8N_API_KEY')

    if not api_key:
        print("N8N_API_KEY not set - skipping execution check")
        print("Set it with: export N8N_API_KEY='your-api-key'")
        return

    try:
        response = requests.get(
            'http://localhost:5678/api/v1/executions',
            headers={'X-N8N-API-KEY': api_key},
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            print("\nRecent executions:")
            print("-" * 40)
            for exec in data.get('data', [])[:5]:
                status = "[OK]" if exec['status'] == 'success' else "[!!]"
                print(f"  {status} #{exec['id']}: {exec['status']} - {exec['startedAt'][:19]}")
        else:
            print(f"API returned: {response.status_code}")
    except Exception as e:
        print(f"Could not check executions: {e}")

def main():
    print("=" * 60)
    print("  AGENT23 N8N PLATFORM TEST")
    print("  Testing: Facebook, Instagram, LinkedIn")
    print("=" * 60)
    print(f"\nWebhook URL: {N8N_WEBHOOK_URL}")
    print(f"Timestamp: {datetime.now().isoformat()}")

    results = {}

    # Test 1: Health Check
    results['health'] = test_health_check()

    if not results['health']:
        print("\n[!] Health check failed - n8n may not be running")
        print("    Make sure n8n is running: cd ~/n8n && n8n start")
        return

    time.sleep(1)

    # Test 2: Facebook
    fb_text = "Testing Facebook posting via Agent23. Elevare by Amaziah brings AI-powered content creation to your social media strategy."
    results['facebook'], _ = test_single_platform('facebook', fb_text, ['ElevareByAmaziah', 'Facebook', 'AI', 'ContentCreation'])

    time.sleep(2)

    # Test 3: Instagram (note: IG typically requires an image)
    ig_text = "Testing Instagram posting via Agent23. Transform your content strategy with AI-powered automation."
    results['instagram'], _ = test_single_platform('instagram', ig_text, ['ElevareByAmaziah', 'Instagram', 'AI', 'Automation', 'ContentCreator'])

    time.sleep(2)

    # Test 4: LinkedIn
    li_text = "Testing LinkedIn posting via Agent23. Professional content creation powered by artificial intelligence. Elevare by Amaziah is revolutionizing how businesses approach social media."
    results['linkedin'], _ = test_single_platform('linkedin', li_text, ['ElevareByAmaziah', 'LinkedIn', 'AI', 'Business'])

    time.sleep(2)

    # Test 5: Multi-platform
    results['multi'], _ = test_multi_platform()

    # Check executions
    check_n8n_executions()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for test, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status} {test}")

    passed = sum(1 for r in results.values() if r)
    total = len(results)
    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All tests passed! Check n8n executions and social media accounts for posts.")
    else:
        print("\n[!] Some tests failed. Check n8n logs for errors:")
        print("    cd ~/n8n && cat ~/.n8n/logs/n8n.log | tail -50")

if __name__ == '__main__':
    main()
