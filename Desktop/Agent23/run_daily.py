#!/usr/bin/env python3
"""
Daily automated post - runs via cron at 8:15 AM ET.
Generates text with PEFT model, creates image, posts to FB/IG/LI via n8n.
Uses round-robin domain selection to avoid repeats.
"""

import os
import sys
import json
import uuid
import hashlib
import requests
import base64
import subprocess
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

# Set defaults BEFORE importing the generator (env vars / .env override these)
if "PEFT_ADAPTER_PATH" not in os.environ:
    os.environ["PEFT_ADAPTER_PATH"] = "/home/amaziahy80/LLM_VAULT/Elevaretinyllma"
if "BASE_MODEL_NAME" not in os.environ:
    os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

sys.path.insert(0, str(Path(__file__).parent))

# ============================================================
# CONFIGURATION
# ============================================================
N8N_WEBHOOK_URL = "http://localhost:5678/webhook/claude"
GCS_BUCKET = "trade_bucket45ts"
STATE_FILE = Path(__file__).parent / "domain_state.json"
LOG_FILE = Path(__file__).parent / "logs" / "daily_post.log"

STABILITY_API_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"

DOMAINS = [
    {
        "domain": "Foreclosures",
        "title": "AI helps homeowners navigate foreclosure timelines",
        "description": "Coordinating document deadlines and process steps without legal advice",
        "image_prompts": [
            "Professional real estate concept: a modern home with digital overlay showing timeline and documents, warm earth tones, architectural photography style, high quality",
            "Abstract concept: keys and a house silhouette with flowing data streams, warm amber and brown palette, clean minimalist design, photorealistic",
            "Business concept: organized documents on a desk with a model house, natural lighting, professional workspace, warm tones, editorial photography",
        ],
    },
    {
        "domain": "Trading Futures",
        "title": "AI-powered insights for futures market analysis",
        "description": "Understanding commodity trends and risk management through data",
        "image_prompts": [
            "Professional finance concept: abstract market charts with upward momentum, deep blue and gold color scheme, modern data visualization, cinematic lighting",
            "Trading technology: holographic financial dashboard with commodity data, dark background with vibrant blue and green accents, futuristic corporate style",
            "Business analytics: sleek trading terminal display with grain and energy markets, dark teal and silver palette, modern professional design",
        ],
    },
    {
        "domain": "Assisted Living",
        "title": "Technology supporting care coordination in assisted living",
        "description": "Improving communication and scheduling for caregivers and families",
        "image_prompts": [
            "Healthcare technology: warm modern care facility with subtle digital interface, soft pastel colors, compassionate and professional atmosphere, natural lighting",
            "Senior care concept: hands using a tablet with health monitoring app, warm and inviting tones, gentle natural light, editorial photography style",
            "Modern assisted living: bright communal space with smart home technology, soft greens and warm whites, welcoming atmosphere, architectural photography",
        ],
    },
]

# ============================================================
# LOGGING
# ============================================================
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger("daily_post")


# ============================================================
# HELPERS
# ============================================================
def load_env():
    """Load .env file if it exists."""
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip() not in os.environ:
                        os.environ[key.strip()] = value.strip().strip("\"'")


def get_next_domain():
    """Round-robin domain selection. Reads/writes state file."""
    last_index = -1
    if STATE_FILE.exists():
        try:
            state = json.loads(STATE_FILE.read_text())
            last_index = state.get("last_domain_index", -1)
        except Exception:
            pass

    next_index = (last_index + 1) % len(DOMAINS)
    STATE_FILE.write_text(json.dumps({
        "last_domain_index": next_index,
        "last_domain": DOMAINS[next_index]["domain"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }))

    return DOMAINS[next_index]


def generate_text(context):
    """Generate platform-specific text using the PEFT model."""
    from agents.content_creator.text_generator import TextGenerator

    generator = TextGenerator()
    log.info("Model loaded (PEFT: %s), domain: %s", generator.use_direct_model, context["domain"])

    texts = {}
    for platform in ["facebook", "instagram", "linkedin"]:
        result = generator.generate_text(context, platform)
        texts[platform] = result["text"]
        log.info("Generated %s: %d chars", platform, len(result["text"]))

    texts["default"] = texts["facebook"]
    hashtags = result.get("hashtags", ["RealWorldAI", "ElevareByAmaziah"])
    return texts, hashtags


def generate_image(context):
    """Generate image via Stability AI and upload to GCS."""
    api_key = os.getenv("STABILITY_API_KEY", "")
    if not api_key:
        log.warning("STABILITY_API_KEY not set, skipping image")
        return ""

    import random
    prompt = random.choice(context["image_prompts"])
    log.info("Image prompt: %s", prompt[:80])

    try:
        resp = requests.post(
            STABILITY_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "text_prompts": [{"text": prompt, "weight": 1.0}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
                "style_preset": "photographic",
            },
            timeout=120,
        )

        if resp.status_code != 200:
            log.error("Stability API error: %d %s", resp.status_code, resp.text[:200])
            return ""

        image_bytes = base64.b64decode(resp.json()["artifacts"][0]["base64"])
        log.info("Image generated: %d bytes", len(image_bytes))

        # Upload to GCS
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"elevare_{timestamp}.png"
        local_path = Path(__file__).parent / filename

        with open(local_path, "wb") as f:
            f.write(image_bytes)

        result = subprocess.run(
            ["gsutil", "-h", "Cache-Control:public,max-age=3600",
             "cp", str(local_path), f"gs://{GCS_BUCKET}/posts/{filename}"],
            capture_output=True, text=True, timeout=30,
        )
        local_path.unlink(missing_ok=True)

        if result.returncode == 0:
            url = f"https://storage.googleapis.com/{GCS_BUCKET}/posts/{filename}"
            log.info("Uploaded to GCS: %s", url)
            return url

        log.error("GCS upload failed: %s", result.stderr[:200])
        return ""

    except Exception as e:
        log.error("Image generation failed: %s", e)
        return ""


def post_to_n8n(texts, hashtags, image_url):
    """Send post to n8n webhook."""
    job_id = str(uuid.uuid4())
    idempotency_key = f"sha256:{hashlib.sha256(texts['default'][:50].encode()).hexdigest()[:16]}"

    media = [{"type": "image", "url": image_url, "alt_text": "Elevare by Amaziah"}] if image_url else []

    payload = {
        "job_id": job_id,
        "idempotency_key": idempotency_key,
        "channels": ["facebook", "instagram", "linkedin"],
        "content": {
            "text": texts,
            "hashtags": [],
            "media": media,
        },
        "schedule": {
            "publish_at": datetime.now(timezone.utc).isoformat(),
            "timezone": "America/New_York",
            "priority": 1,
        },
        "metadata": {
            "source": "run_daily",
            "model": "elevare_peft",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }

    try:
        resp = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=30)
        log.info("n8n response: %d, job_id: %s", resp.status_code, job_id)
        return resp.status_code == 200, job_id
    except Exception as e:
        log.error("n8n webhook failed: %s", e)
        return False, job_id


def poll_results(job_id):
    """Poll n8n API for execution results matching our job_id."""
    api_key = os.getenv("N8N_API_KEY", "")
    if not api_key:
        log.warning("N8N_API_KEY not set, skipping result polling")
        return {}

    api_url = "http://localhost:5678/api/v1"
    headers = {"X-N8N-API-KEY": api_key}

    for attempt in range(24):
        time.sleep(5)
        try:
            resp = requests.get(f"{api_url}/executions?limit=5", headers=headers, timeout=10)
            if resp.status_code != 200:
                continue

            for ex in resp.json().get("data", []):
                if ex["status"] not in ("success", "error"):
                    continue
                detail = requests.get(
                    f"{api_url}/executions/{ex['id']}?includeData=true",
                    headers=headers, timeout=15,
                )
                if detail.status_code != 200:
                    continue
                run_data = detail.json().get("data", {}).get("resultData", {}).get("runData", {})
                webhook = run_data.get("Webhook", [{}])
                if webhook:
                    body = webhook[0].get("data", {}).get("main", [[]])[0]
                    if body and body[0].get("json", {}).get("body", {}).get("job_id") == job_id:
                        # Found our execution — extract results
                        results = {}
                        for node, platform in [("FB: Result", "facebook"), ("IG: Result", "instagram"), ("LI: Result", "linkedin")]:
                            node_data = run_data.get(node, [{}])
                            if node_data:
                                out = node_data[0].get("data", {}).get("main", [[]])[0]
                                if out:
                                    post_id = out[0].get("json", {}).get("post_id", "")
                                    status = out[0].get("json", {}).get("status", "")
                                    if post_id and status == "posted":
                                        results[platform] = {"status": "POSTED", "post_id": post_id}
                                    else:
                                        results[platform] = {"status": "FAILED"}
                        return results
        except Exception:
            continue

    log.warning("Timed out waiting for results")
    return {}


# ============================================================
# MAIN
# ============================================================
def main():
    load_env()

    log.info("=" * 60)
    log.info("DAILY POST - %s", datetime.now(timezone.utc).isoformat())
    log.info("=" * 60)

    # 1. Pick domain (round-robin)
    context = get_next_domain()
    log.info("Domain: %s", context["domain"])

    # 2. Generate text
    try:
        texts, hashtags = generate_text(context)
    except Exception as e:
        log.error("Text generation failed: %s", e)
        return 1

    # 3. Generate image
    image_url = generate_image(context)

    # 4. Post to n8n
    success, job_id = post_to_n8n(texts, hashtags, image_url)
    if not success:
        log.error("n8n webhook failed")
        return 1

    # 5. Poll for results
    results = poll_results(job_id)

    posted = [p for p, r in results.items() if r.get("status") == "POSTED"]
    failed = [p for p, r in results.items() if r.get("status") != "POSTED"]

    if posted:
        log.info("Posted: %s", ", ".join(posted))
    if failed:
        log.warning("Failed: %s", ", ".join(failed))
    if not results:
        log.warning("No results retrieved (posts may still have succeeded)")

    log.info("Done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
