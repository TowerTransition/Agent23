#!/usr/bin/env python3
"""
Official Test Post - Posts to Facebook, Instagram, and LinkedIn via n8n
Uses the Elevare fine-tuned PEFT model for text generation

Usage on GCP:
    cd ~/Agent23
    source venv/bin/activate
    python official_test_post.py
"""

import os
import sys
import json
import uuid
import hashlib
import requests
import base64
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

# Set environment variables BEFORE importing the generator
os.environ["PEFT_ADAPTER_PATH"] = "/home/amaziahy80/LLM_VAULT/Elevaretinyllma"
os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Add Agent23 to path
sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# CONFIGURATION
# ============================================================
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/claude"
N8N_API_URL = "http://localhost:5678/api/v1"
N8N_API_KEY = os.getenv("N8N_API_KEY", "")

# Facebook page ID (for building post URLs)
FB_PAGE_ID = "839011279304615"

# LinkedIn direct posting (bypasses n8n - proven working approach)
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "AQXNCeRn_D9hpEiMe077aZ8Tcv230-UzT0cphvfVT_bOpX-j6LDkvfBZ3W6Dib_gfkm2Hxbcyz4APNw7zLqc1iUT8LBB07ZzXaki1Ll_G_GpgM0fyeLF3Bcvz_dsyEoqP8hsnYQpPuLswN9HAAyjtkv-KzugPdH6-rHVxkpkkKkZVjVFq4ZhNd0VSDTlXForK2nKsAM4DwPxMwmtWB-aRwVB240OpuibzZGjQiRU3N7xExEAnHPAfYx-v3deM29yRW2YtPSq1isBU21Z1P5O07SJKy-iqgH-4K48CUb4mPwutmo6Eb8xMIRXZZOIYHeCvWQA-XBuNSP94CyRlzFMD4OUm2PLgA")
LINKEDIN_AUTHOR_URN = "urn:li:person:FWvPBSKhQa"

# Stability AI for image generation
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

# IMGBB for image hosting (fallback)
IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", "")

# Fallback test image
FALLBACK_IMAGE_URL = "https://images.unsplash.com/photo-1551288049-bebda4e38f71?w=1080&q=80"


def load_env():
    """Load .env file if it exists."""
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip().strip('"\'')
        print("[OK] Loaded .env file")


def generate_text_with_model():
    """Generate text using the fine-tuned PEFT model."""
    print("\n[1/5] GENERATING TEXT WITH FINE-TUNED MODEL")
    print("-" * 50)

    try:
        from agents.content_creator.text_generator import TextGenerator
        generator = TextGenerator()
        print(f"      Model loaded (Direct PEFT: {generator.use_direct_model})")

        # Rotate through trained domains for variety
        domains = [
            {
                "domain": "Foreclosures",
                "title": "AI helps homeowners navigate foreclosure timelines",
                "description": "Coordinating document deadlines and process steps without legal advice"
            },
            {
                "domain": "Trading Futures",
                "title": "AI-powered insights for futures market analysis",
                "description": "Understanding commodity trends and risk management through data"
            },
            {
                "domain": "Assisted Living",
                "title": "Technology supporting care coordination in assisted living",
                "description": "Improving communication and scheduling for caregivers and families"
            },
        ]
        context = random.choice(domains)
        print(f"      Domain: {context['domain']}")

        # Generate for each platform
        texts = {}
        for platform in ["facebook", "instagram", "linkedin"]:
            result = generator.generate_text(context, platform)
            texts[platform] = result["text"]
            print(f"      Generated {platform}: {len(result['text'])} chars")

        # Use facebook as default
        texts["default"] = texts["facebook"]

        return texts, result.get("hashtags", ["ElevareByAmaziah", "AI", "Automation", "ContentCreation"]), context["domain"]

    except Exception as e:
        print(f"      ERROR: {e}")
        print("      Using fallback text...")

        fallback = """Foreclosure involves many moving parts.

When information isn't coordinated, small details fall through the cracks and stress compounds.

AI supports clarity by organizing information\u2014helping people see how pieces relate without stepping into legal guidance.

Coordination reduces avoidable errors.

Real-world systems. Real clarity.
\u2014 Elevare by Amaziah"""

        return {
            "default": fallback,
            "facebook": fallback,
            "instagram": fallback,
            "linkedin": fallback
        }, ["ElevareByAmaziah", "AI", "Automation", "ContentCreation"], "Foreclosures"


def get_image_prompt(domain="General"):
    """Get a domain-specific, varied image prompt."""
    prompts = {
        "Foreclosures": [
            "Professional real estate concept: a modern home with digital overlay showing timeline and documents, warm earth tones, architectural photography style, high quality",
            "Abstract concept: keys and a house silhouette with flowing data streams, warm amber and brown palette, clean minimalist design, photorealistic",
            "Business concept: organized documents on a desk with a model house, natural lighting, professional workspace, warm tones, editorial photography",
            "Modern real estate technology: digital interface overlaid on suburban neighborhood, golden hour lighting, clean composition, professional quality",
        ],
        "Trading Futures": [
            "Professional finance concept: abstract market charts with upward momentum, deep blue and gold color scheme, modern data visualization, cinematic lighting",
            "Trading technology: holographic financial dashboard with commodity data, dark background with vibrant blue and green accents, futuristic corporate style",
            "Business analytics: sleek trading terminal display with grain and energy markets, dark teal and silver palette, modern professional design",
            "Abstract finance: flowing lines representing market trends over a world map, navy and gold colors, premium corporate aesthetic, photorealistic",
        ],
        "Assisted Living": [
            "Healthcare technology: warm modern care facility with subtle digital interface, soft pastel colors, compassionate and professional atmosphere, natural lighting",
            "Senior care concept: hands using a tablet with health monitoring app, warm and inviting tones, gentle natural light, editorial photography style",
            "Modern assisted living: bright communal space with smart home technology, soft greens and warm whites, welcoming atmosphere, architectural photography",
            "Care coordination: abstract visualization of connected care network, gentle purple and teal gradients, clean modern design, professional quality",
        ],
        "General": [
            "Professional business concept: modern workspace with AI-powered analytics dashboard, clean corporate style, blue and white tones, photorealistic lighting",
            "Technology innovation: abstract network of connected nodes representing AI automation, gradient purple and blue, modern minimalist design, cinematic",
            "Digital transformation: hands interacting with holographic business interface, warm corporate tones, professional studio lighting, high quality",
            "Business automation: sleek modern office with floating data visualizations, teal and white color scheme, clean contemporary design, photorealistic",
        ],
    }
    domain_prompts = prompts.get(domain, prompts["General"])
    return random.choice(domain_prompts)


def upload_to_gcs(image_data, filename):
    """Upload image to Google Cloud Storage and return public URL."""
    bucket_name = "trade_bucket45ts"
    blob_path = f"posts/{filename}"

    # Save image locally first
    local_path = Path(__file__).parent / filename
    with open(local_path, "wb") as f:
        f.write(image_data)

    # Upload
    result = subprocess.run(
        ["gsutil", "-h", "Cache-Control:public,max-age=3600",
         "cp", str(local_path), f"gs://{bucket_name}/{blob_path}"],
        capture_output=True, text=True, timeout=30
    )

    # Clean up local file
    local_path.unlink(missing_ok=True)

    if result.returncode == 0:
        public_url = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
        print(f"      Uploaded to GCS: {public_url}")
        return public_url
    else:
        print(f"      GCS upload failed: {result.stderr.strip()[:200]}")
        return None


def generate_image(domain="General"):
    """Generate image using Stability AI and upload to GCS or IMGBB."""
    print("\n[2/5] GENERATING IMAGE")
    print("-" * 50)

    global STABILITY_API_KEY, IMGBB_API_KEY
    STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", STABILITY_API_KEY)
    IMGBB_API_KEY = os.getenv("IMGBB_API_KEY", IMGBB_API_KEY)

    if not STABILITY_API_KEY:
        print("      STABILITY_API_KEY not set - using fallback image")
        return FALLBACK_IMAGE_URL

    prompt = get_image_prompt(domain)
    print(f"      Domain: {domain}")
    print(f"      Prompt: {prompt[:80]}...")

    headers = {
        "Authorization": f"Bearer {STABILITY_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    payload = {
        "text_prompts": [{"text": prompt, "weight": 1.0}],
        "cfg_scale": 7,
        "height": 1024,
        "width": 1024,
        "samples": 1,
        "steps": 30,
        "style_preset": "photographic"
    }

    try:
        response = requests.post(STABILITY_API_URL, headers=headers, json=payload, timeout=120)

        if response.status_code == 200:
            data = response.json()
            image_base64 = data["artifacts"][0]["base64"]
            image_bytes = base64.b64decode(image_base64)
            print("      Image generated successfully!")

            # Try GCS first (most reliable for Meta APIs)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"elevare_{timestamp}.png"
            gcs_url = upload_to_gcs(image_bytes, filename)
            if gcs_url:
                return gcs_url

            # Fallback to IMGBB
            if IMGBB_API_KEY:
                print("      Falling back to IMGBB...")
                upload_resp = requests.post(
                    "https://api.imgbb.com/1/upload",
                    data={"key": IMGBB_API_KEY, "image": image_base64},
                    timeout=30
                )
                if upload_resp.status_code == 200:
                    image_url = upload_resp.json()["data"]["url"]
                    print(f"      Uploaded to IMGBB: {image_url}")
                    # Pre-fetch to warm CDN cache so Meta APIs can download it
                    print("      Warming CDN cache...")
                    for _ in range(3):
                        try:
                            requests.head(image_url, timeout=10)
                            time.sleep(1)
                        except Exception:
                            pass
                    print("      CDN cache warmed")
                    return image_url

            # Last resort
            print("      WARNING: Using fallback image URL")
            return FALLBACK_IMAGE_URL

        else:
            print(f"      Stability API error: {response.status_code}")
            print(f"      {response.text[:200]}")
            return FALLBACK_IMAGE_URL

    except Exception as e:
        print(f"      ERROR: {e}")
        return FALLBACK_IMAGE_URL


def post_to_linkedin_direct(text, hashtags, image_url):
    """Post to LinkedIn directly using the proven 4-step curl approach."""
    print("\n  [LI] Posting to LinkedIn directly (bypassing n8n)...")

    # Build message with hashtags
    message = text
    if hashtags:
        tag_str = ' '.join(['#' + h.lstrip('#') for h in hashtags[:5]])
        message = message + '\n\n' + tag_str

    li_headers = {
        'Authorization': f'Bearer {LINKEDIN_ACCESS_TOKEN}',
        'X-Restli-Protocol-Version': '2.0.0',
        'LinkedIn-Version': '202601',
        'Content-Type': 'application/json'
    }

    image_urn = None

    if image_url:
        try:
            # Step 1: Initialize image upload
            init_resp = requests.post(
                'https://api.linkedin.com/rest/images?action=initializeUpload',
                headers=li_headers,
                json={'initializeUploadRequest': {'owner': LINKEDIN_AUTHOR_URN}},
                timeout=15
            )
            if init_resp.status_code != 200:
                print(f"  [LI] Init upload failed: {init_resp.status_code} {init_resp.text[:200]}")
            else:
                upload_url = init_resp.json()['value']['uploadUrl']
                image_urn = init_resp.json()['value']['image']
                print(f"  [LI] Image URN: {image_urn}")

                # Step 2: Download image to temp file
                tmp_path = Path(__file__).parent / f'li_tmp_{int(time.time())}.jpg'
                dl_resp = requests.get(image_url, timeout=30)
                with open(tmp_path, 'wb') as f:
                    f.write(dl_resp.content)
                print(f"  [LI] Downloaded image: {len(dl_resp.content)} bytes")

                # Step 3: Upload binary to LinkedIn via subprocess curl (proven method)
                upload_result = subprocess.run(
                    [
                        'curl', '-s', '-X', 'PUT', upload_url,
                        '-H', f'Authorization: Bearer {LINKEDIN_ACCESS_TOKEN}',
                        '-H', 'Content-Type: application/octet-stream',
                        '--data-binary', f'@{tmp_path}',
                        '-w', '\nHTTP_STATUS: %{http_code}'
                    ],
                    capture_output=True, text=True, timeout=60
                )
                # Clean up
                tmp_path.unlink(missing_ok=True)

                if 'HTTP_STATUS: 201' in upload_result.stdout:
                    print(f"  [LI] Image uploaded to LinkedIn (201)")
                else:
                    print(f"  [LI] Image upload failed: {upload_result.stdout[-100:]}")
                    image_urn = None  # Fall back to text-only

        except Exception as e:
            print(f"  [LI] Image upload error: {e}")
            image_urn = None

    # Step 4: Create post
    post_body = {
        'author': LINKEDIN_AUTHOR_URN,
        'commentary': message,
        'visibility': 'PUBLIC',
        'distribution': {
            'feedDistribution': 'MAIN_FEED',
            'targetEntities': [],
            'thirdPartyDistributionChannels': []
        },
        'lifecycleState': 'PUBLISHED',
        'isReshareDisabledByAuthor': False
    }

    if image_urn:
        post_body['content'] = {
            'media': {
                'title': 'Elevare by Amaziah',
                'id': image_urn
            }
        }

    try:
        post_resp = requests.post(
            'https://api.linkedin.com/rest/posts',
            headers=li_headers,
            json=post_body,
            timeout=15
        )

        if post_resp.status_code == 201:
            post_id = post_resp.headers.get('x-restli-id', 'posted')
            has_img = 'with image' if image_urn else 'text-only'
            print(f"  [LI] Posted ({has_img}): {post_id}")
            return {
                'status': 'POSTED',
                'post_id': post_id,
                'url': f'https://www.linkedin.com/feed/update/{post_id}/',
                'has_image': bool(image_urn)
            }
        else:
            print(f"  [LI] Post failed: {post_resp.status_code} {post_resp.text[:200]}")
            return {'status': 'FAILED', 'error': f'{post_resp.status_code}: {post_resp.text[:200]}'}

    except Exception as e:
        print(f"  [LI] Post error: {e}")
        return {'status': 'FAILED', 'error': str(e)}


def post_to_n8n(texts, hashtags, image_url):
    """Send post to n8n webhook for Facebook and Instagram only."""
    print("\n[3/5] POSTING TO PLATFORMS")
    print("-" * 50)

    job_id = str(uuid.uuid4())
    idempotency_key = f"sha256:{hashlib.sha256(texts['default'][:50].encode()).hexdigest()[:16]}"

    payload = {
        "job_id": job_id,
        "idempotency_key": idempotency_key,
        "channels": ["facebook", "instagram", "linkedin"],
        "content": {
            "text": texts,
            "hashtags": [],
            "media": [
                {
                    "type": "image",
                    "url": image_url,
                    "alt_text": "AI-powered content creation by Elevare by Amaziah"
                }
            ]
        },
        "schedule": {
            "publish_at": datetime.now(timezone.utc).isoformat(),
            "timezone": "America/New_York",
            "priority": 1
        },
        "metadata": {
            "source": "official_test_post",
            "model": "elevare_peft",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    }

    print(f"      Job ID: {job_id}")
    print(f"      Webhook: {N8N_WEBHOOK_URL}")
    print(f"      Platforms: Facebook, Instagram, LinkedIn")
    print(f"      Image: {image_url[:60]}...")

    try:
        response = requests.post(
            N8N_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        print(f"      Response: {response.status_code}")
        return response.status_code == 200, job_id

    except Exception as e:
        print(f"      ERROR: {e}")
        return False, job_id


def get_post_urls(api_key, job_id=None):
    """Poll n8n for execution results, matching by job_id to avoid stale data."""
    headers = {"X-N8N-API-KEY": api_key}

    # Record the timestamp just before we start polling so we skip older executions
    poll_start = time.time()
    exec_id = None

    # Poll for a completed execution that matches our job
    for attempt in range(24):  # Up to 2 minutes
        time.sleep(5)
        try:
            resp = requests.get(
                f"{N8N_API_URL}/executions?limit=5",
                headers=headers, timeout=10
            )
            if resp.status_code != 200:
                continue
            execs = resp.json().get("data", [])
            if not execs:
                continue

            # Find execution matching our job_id
            for ex in execs:
                if ex["status"] not in ("success", "error"):
                    continue
                # If we have a job_id, fetch execution data to verify it matches
                if job_id:
                    try:
                        detail = requests.get(
                            f"{N8N_API_URL}/executions/{ex['id']}?includeData=true",
                            headers=headers, timeout=15
                        )
                        if detail.status_code != 200:
                            continue
                        detail_data = detail.json()
                        # Check webhook body for our job_id
                        webhook_data = detail_data.get("data", {}).get("resultData", {}).get("runData", {}).get("Webhook", [{}])
                        if webhook_data:
                            webhook_body = webhook_data[0].get("data", {}).get("main", [[]])[0]
                            if webhook_body:
                                body = webhook_body[0].get("json", {}).get("body", {})
                                if body.get("job_id") == job_id:
                                    exec_id = ex["id"]
                                    print(f"      Found matching execution: {exec_id}")
                                    break
                    except Exception:
                        continue
                else:
                    # No job_id filter, just take the latest completed
                    exec_id = ex["id"]
                    break

            if exec_id:
                break

            if attempt > 0 and attempt % 4 == 0:
                print(f"      Still waiting... ({(attempt + 1) * 5}s)")

        except Exception:
            continue
    else:
        print("      Timed out waiting for execution results")
        return {}

    # Get execution details (may already have them if we fetched during matching)
    try:
        resp = requests.get(
            f"{N8N_API_URL}/executions/{exec_id}?includeData=true",
            headers=headers, timeout=15
        )
        if resp.status_code != 200:
            return {}

        data = resp.json()
        run_data = data.get("data", {}).get("resultData", {}).get("runData", {})

        results = {}

        # Facebook
        fb_result = run_data.get("FB: Result", [{}])
        if fb_result:
            fb_json = fb_result[0].get("data", {}).get("main", [[]])[0]
            if fb_json:
                post_id = fb_json[0].get("json", {}).get("post_id", "")
                if post_id and post_id != "queued":
                    results["facebook"] = {
                        "status": "POSTED",
                        "post_id": post_id,
                        "url": f"https://facebook.com/{post_id}"
                    }
                else:
                    fb_photo = run_data.get("FB: Photo", [{}])
                    err_msg = ""
                    if fb_photo and fb_photo[0].get("data", {}).get("main", [[]])[0]:
                        fb_photo_json = fb_photo[0]["data"]["main"][0][0].get("json", {})
                        if "error" in fb_photo_json:
                            err_msg = fb_photo_json["error"].get("message", "Unknown error")
                    results["facebook"] = {"status": "FAILED", "error": err_msg or "No post ID returned"}

        # Instagram
        ig_result = run_data.get("IG: Result", [{}])
        if ig_result:
            ig_json = ig_result[0].get("data", {}).get("main", [[]])[0]
            if ig_json:
                post_id = ig_json[0].get("json", {}).get("post_id", "")
                if post_id and post_id != "queued":
                    results["instagram"] = {
                        "status": "POSTED",
                        "post_id": post_id,
                        "url": f"https://www.instagram.com/elevarebyamaziah/"
                    }
                else:
                    ig_container = run_data.get("IG: Container", [{}])
                    err_msg = ""
                    if ig_container and ig_container[0].get("data", {}).get("main", [[]])[0]:
                        ig_c_json = ig_container[0]["data"]["main"][0][0].get("json", {})
                        if "error" in ig_c_json:
                            err_msg = ig_c_json["error"].get("message", "Unknown error")
                    results["instagram"] = {"status": "FAILED", "error": err_msg or "No post ID returned"}

        # LinkedIn
        li_result = run_data.get("LI: Result", [{}])
        if li_result:
            li_json = li_result[0].get("data", {}).get("main", [[]])[0]
            if li_json:
                post_id = li_json[0].get("json", {}).get("post_id", "")
                if post_id and post_id != "queued":
                    # post_id is already full URN like urn:li:share:123
                    url = f"https://www.linkedin.com/feed/update/{post_id}/"
                    results["linkedin"] = {
                        "status": "POSTED",
                        "post_id": post_id,
                        "url": url
                    }
                else:
                    results["linkedin"] = {"status": "FAILED", "error": "No post ID returned"}

        return results

    except Exception as e:
        return {"error": str(e)}


def print_results(results, texts, hashtags, image_url):
    """Print final results with post URLs."""
    print("\n[5/5] RESULTS")
    print("=" * 60)

    if not results:
        print("\n  [!!] Could not retrieve results from n8n")
        print("  Check n8n executions: http://localhost:5678/executions")
        print("\n" + "=" * 60)
        return

    all_ok = True
    for platform in ["facebook", "instagram", "linkedin"]:
        r = results.get(platform, {})
        status = r.get("status", "UNKNOWN")
        print(f"\n  {platform.upper()}:")
        if status == "POSTED":
            print(f"    Status:  POSTED")
            print(f"    Post ID: {r.get('post_id', 'N/A')}")
            print(f"    URL:     {r.get('url', 'N/A')}")
        else:
            all_ok = False
            print(f"    Status:  FAILED")
            print(f"    Error:   {r.get('error', 'Unknown')}")

    print(f"\n  {'-' * 56}")
    print(f"  Image: {image_url}")

    preview = texts.get("facebook", texts.get("default", ""))[:150]
    print(f"\n  Text Preview: {preview}...")
    print(f"  Hashtags: {' '.join(['#' + h.lstrip('#') for h in hashtags[:5]])}")

    if all_ok:
        print("\n  [OK] ALL PLATFORMS POSTED SUCCESSFULLY!")
    else:
        posted = [p for p in ["facebook", "instagram", "linkedin"] if results.get(p, {}).get("status") == "POSTED"]
        failed = [p for p in ["facebook", "instagram", "linkedin"] if results.get(p, {}).get("status") != "POSTED"]
        if posted:
            print(f"\n  [OK] Posted: {', '.join(posted)}")
        if failed:
            print(f"  [!!] Failed: {', '.join(failed)}")

    print("\n" + "=" * 60)


def main():
    print("=" * 60)
    print("  ELEVARE BY AMAZIAH - OFFICIAL TEST POST")
    print("  Platforms: Facebook, Instagram, LinkedIn")
    print("=" * 60)
    print(f"\n  Timestamp: {datetime.now().isoformat()}")
    print(f"  Webhook: {N8N_WEBHOOK_URL}")

    # Load .env
    load_env()

    # Get n8n API key
    global N8N_API_KEY
    N8N_API_KEY = os.getenv("N8N_API_KEY", N8N_API_KEY)
    if not N8N_API_KEY:
        print("  [!] N8N_API_KEY not set - won't be able to retrieve post URLs")
        print("      Add N8N_API_KEY to .env for full results")

    # Step 1: Generate text
    texts, hashtags, domain = generate_text_with_model()

    # Step 2: Generate/get image (domain-specific)
    image_url = generate_image(domain)

    # Step 3: Post to n8n (all 3 platforms - LinkedIn now uses native Node.js binary)
    success, job_id = post_to_n8n(texts, hashtags, image_url)

    if not success:
        print("\n  [!!] POST SUBMISSION FAILED")
        print("  Check n8n is running: http://localhost:5678")
        return 1

    # Step 4: Wait for results
    print("\n[4/5] WAITING FOR RESULTS")
    print("-" * 50)

    if N8N_API_KEY:
        print("      Polling n8n for execution results...")
        results = get_post_urls(N8N_API_KEY, job_id=job_id)
    else:
        print("      Skipping (no N8N_API_KEY)")
        results = {}

    # Step 5: Print results with URLs
    print_results(results, texts, hashtags, image_url)

    return 0


if __name__ == "__main__":
    sys.exit(main())
