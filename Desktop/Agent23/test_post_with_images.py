#!/usr/bin/env python3
"""
Agent23 Full Test - Post with AI-generated images to FB, IG, LinkedIn

Prerequisites:
    - .env file with STABILITY_API_KEY
    - n8n running with FB/IG/LI credentials configured
    - Agent23-Main workflow active

Usage:
    cd ~/Agent23
    python3 test_post_with_images.py
"""

import os
import sys
import requests
import json
import uuid
import hashlib
import base64
import time
from datetime import datetime, timezone
from pathlib import Path

# Load .env file
def load_env():
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"\'')
        print("[OK] Loaded .env file")
    else:
        print("[!] No .env file found - using environment variables")

load_env()

# Configuration
STABILITY_API_KEY = os.getenv('STABILITY_API_KEY')
N8N_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL', 'http://localhost:5678/webhook/claude')

# Stability AI endpoint
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"


def generate_image(prompt, output_path="test_image.png"):
    """Generate image using Stability AI."""
    print(f"\n[IMAGE] Generating with Stability AI...")
    print(f"  Prompt: {prompt[:60]}...")

    if not STABILITY_API_KEY:
        print("  [ERROR] STABILITY_API_KEY not set!")
        return None

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "text_prompts": [
            {"text": prompt, "weight": 1.0}
        ],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
        "style_preset": "photographic"
    }

    try:
        response = requests.post(STABILITY_API_URL, headers=headers, json=payload, timeout=60)

        if response.status_code == 200:
            data = response.json()
            image_data = data["artifacts"][0]["base64"]

            # Save image locally
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(image_data))

            print(f"  [OK] Image saved to {output_path}")
            return image_data  # Return base64 for n8n
        else:
            print(f"  [ERROR] Stability API: {response.status_code}")
            print(f"  {response.text[:200]}")
            return None
    except Exception as e:
        print(f"  [ERROR] {e}")
        return None


def upload_image_to_hosting(image_base64):
    """
    Upload image to a public hosting service.
    For testing, we'll use imgbb.com (free image hosting).

    You can also use:
    - Your own server
    - AWS S3
    - Google Cloud Storage
    - Cloudinary
    """
    print("\n[UPLOAD] Uploading image to hosting...")

    # Option 1: Use imgbb (free, no API key needed for basic use)
    # For production, use your own hosting

    IMGBB_API_KEY = os.getenv('IMGBB_API_KEY', '')

    if IMGBB_API_KEY:
        try:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                data={
                    "key": IMGBB_API_KEY,
                    "image": image_base64
                },
                timeout=30
            )
            if response.status_code == 200:
                url = response.json()["data"]["url"]
                print(f"  [OK] Uploaded: {url}")
                return url
        except Exception as e:
            print(f"  [ERROR] imgbb upload failed: {e}")

    # Option 2: Use a placeholder image for testing
    print("  [!] No IMGBB_API_KEY - using placeholder image")
    print("  Set IMGBB_API_KEY in .env for real image uploads")

    # Return a placeholder image URL for testing
    # This is a public domain image that works with FB/IG APIs
    return "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1024&h=1024&fit=crop"


def generate_job_id():
    return str(uuid.uuid4())


def generate_idempotency_key(text, channels):
    key_data = json.dumps({
        'text': text[:50],
        'channels': sorted(channels),
        'ts': datetime.now(timezone.utc).strftime('%Y%m%d%H%M')
    }, sort_keys=True)
    return f"sha256:{hashlib.sha256(key_data.encode()).hexdigest()[:16]}"


def test_n8n_health():
    """Check if n8n is responding."""
    print("\n[CHECK] Testing n8n connection...")
    try:
        r = requests.post(N8N_WEBHOOK_URL, json={'message': 'hello n8n'}, timeout=10)
        print(f"  Status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def post_to_platforms(text, image_url, platforms=['facebook', 'instagram', 'linkedin']):
    """Send post job to n8n workflow."""
    print(f"\n[POST] Sending to n8n for {platforms}...")

    job_id = generate_job_id()

    # Platform-specific text formatting
    fb_text = f"{text}\n\n— Elevare by Amaziah"
    ig_text = text  # Instagram caption
    li_text = f"{text}\n\n#AI #Innovation #Business"

    payload = {
        'job_id': job_id,
        'idempotency_key': generate_idempotency_key(text, platforms),
        'channels': platforms,
        'content': {
            'text': {
                'default': text,
                'facebook': fb_text,
                'instagram': ig_text,
                'linkedin': li_text
            },
            'hashtags': [
                'ElevareByAmaziah',
                'AI',
                'Innovation',
                'ContentCreation',
                'SocialMedia'
            ],
            'media': [
                {
                    'type': 'image',
                    'url': image_url,
                    'alt_text': 'AI-generated image by Elevare'
                }
            ]
        },
        'schedule': {
            'publish_at': datetime.now(timezone.utc).isoformat(),
            'timezone': 'America/New_York',
            'priority': 1
        },
        'metadata': {
            'source': 'test_script',
            'test': True,
            'image_generated': True,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
    }

    print(f"  Job ID: {job_id}")
    print(f"  Channels: {platforms}")
    print(f"  Image URL: {image_url[:50]}...")

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        print(f"  Response: {response.status_code}")
        print(f"  Body: {response.text[:200]}")
        return response.status_code == 200, job_id
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False, job_id


def main():
    print("=" * 60)
    print("  AGENT23 FULL PLATFORM TEST")
    print("  Testing: Facebook + Instagram + LinkedIn with Images")
    print("=" * 60)
    print(f"\nTimestamp: {datetime.now().isoformat()}")
    print(f"Webhook: {N8N_WEBHOOK_URL}")
    print(f"Stability API: {'[SET]' if STABILITY_API_KEY else '[NOT SET]'}")

    # Step 1: Check n8n
    if not test_n8n_health():
        print("\n[FATAL] n8n is not responding!")
        print("Make sure n8n is running: cd ~/n8n && n8n start")
        sys.exit(1)

    # Step 2: Generate image with Stability AI
    image_prompt = """
    Professional business concept image: A modern workspace with
    holographic AI interfaces, representing innovation and digital
    transformation. Clean, minimalist style with blue and white tones.
    High quality, photorealistic.
    """

    image_base64 = generate_image(image_prompt.strip())

    if image_base64:
        # Upload to get public URL
        image_url = upload_image_to_hosting(image_base64)
    else:
        print("\n[!] Image generation failed - using placeholder")
        image_url = "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1024&h=1024&fit=crop"

    # Step 3: Create post content
    post_text = """Embracing the future of content creation with AI-powered automation.

At Elevare by Amaziah, we're transforming how businesses connect with their audience through intelligent, personalized content.

The future is here. Are you ready?"""

    # Step 4: Post to all platforms
    print("\n" + "=" * 60)
    print("POSTING TO PLATFORMS")
    print("=" * 60)

    success, job_id = post_to_platforms(
        text=post_text,
        image_url=image_url,
        platforms=['facebook', 'instagram', 'linkedin']
    )

    # Step 5: Results
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

    if success:
        print(f"\n[OK] Job submitted successfully!")
        print(f"  Job ID: {job_id}")
        print(f"\nNext steps:")
        print(f"  1. Check n8n executions: http://localhost:5678/executions")
        print(f"  2. Check your social media accounts for the posts")
        print(f"  3. View n8n logs: tail -f ~/.n8n/logs/n8n.log")
    else:
        print(f"\n[!!] Job submission failed")
        print(f"  Check n8n logs for errors")

    print("\n" + "=" * 60)


if __name__ == '__main__':
    main()
