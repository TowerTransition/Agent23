# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent23 is an AI-powered social media content creation and scheduling system. It generates platform-specific posts (Twitter, Instagram, LinkedIn, Facebook) for three trained domains: **Foreclosures**, **Trading Futures**, and **Assisted Living**. The brand identity is **Elevare by Amaziah**.

Content is generated locally (PEFT fine-tuned model), then posted to platforms via an n8n workflow engine running on a GCP instance.

## Commands

### Install dependencies
```bash
pip install -r requirements.txt
```

### Run all tests
```bash
python -m unittest discover tests -v
```

### Run a single test file
```bash
python -m unittest tests.test_content_creator_agent -v
```

### Run a single test method
```bash
python -m unittest tests.test_content_creator_agent.TestContentCreatorAgent.test_init_with_peft_adapter -v
```

### End-to-end integration test (runs on GCP instance)
```bash
cd ~/Agent23 && source venv/bin/activate
python official_test_post.py
```

### Environment variables for local development
```bash
# PEFT mode (preferred) - fine-tuned model loaded in-process
PEFT_ADAPTER_PATH="/path/to/Elevaretinyllma"
BASE_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# HTTP fallback mode - OpenAI-compatible endpoint (e.g., Ollama)
LOCAL_LLM_ENDPOINT="http://localhost:11434/v1/chat/completions"
LOCAL_LLM_MODEL="tinyllama"
ALLOW_DEFAULT_LLM_ENDPOINT="true"

# n8n posting (required for live posting)
N8N_WEBHOOK_URL="http://<n8n-host>:5678/webhook/claude"
N8N_API_KEY="..."  # Generated from n8n UI, expires periodically

# Optional
STABILITY_API_KEY="..."  # Image generation
```

## Training data format — what the model was trained to produce

The fine-tuned model (TinyLlama + QLoRA → `Elevaretinyllma`) was trained on 125 examples in `bot_training/train.jsonl`. Every post follows this exact structure:

```
[Opening statement — short, declarative]

[Problem/context paragraph — what happens when clarity is missing]

[AI support paragraph — "AI supports/helps by..." framing, never advice]

[Reinforcement line — short, affirming]

Real-world systems. Real clarity.
— Elevare by Amaziah

#Hashtag1 #Hashtag2 #Hashtag3 #RealWorldAI
```

**Critical rules baked into the training data:**
- Every post uses "AI supports/helps by..." — never "AI will" or "AI can fix"
- Never gives advice (legal, financial, medical) — always "without providing/directing/recommending"
- Always ends with `Real-world systems. Real clarity.\n— Elevare by Amaziah`
- Hashtags always include `#RealWorldAI` plus 3 domain-relevant tags
- Tone is calm, grounded, non-hype — short paragraphs separated by blank lines
- No questions in the body (questions are only added by platform formatting later)

**When testing, generated output must match this format.** If output looks like generic AI text, marketing copy, or includes advice/promises, the generation pipeline is not working correctly. Compare against `bot_training/train.jsonl` examples.

Training config: `bot_training/train_model.py` — QLoRA 4-bit, LoRA r=32, 30 steps, TinyLlama base.

## Architecture

### Two-mode text generation (`agents/content_creator/text_generator.py`)

TextGenerator operates in two modes with automatic fallback:

1. **PEFT Direct** (preferred): Loads fine-tuned PEFT adapters in-process via `PEFT_ADAPTER_PATH`. Uses minimal prompts because the fine-tuned model is trusted. No HTTP overhead.
2. **HTTP Endpoint** (fallback): Calls an OpenAI-compatible chat completions API via `LOCAL_LLM_ENDPOINT`. Applies more aggressive post-processing since the model output is less predictable.

Footer text ("— Elevare by Amaziah") and hashtags are always appended in Python, never delegated to the model. The sanitizer (`agents/content_creator/sanitizer.py`) cleans model output — removes instruction artifacts, template phrases, and normalizes whitespace.

### Content creation pipeline (`agents/content_creator/content_creator_agent.py`)

Orchestrates the full flow: domain classification → expert lens selection → text generation → validation → platform formatting → content moderation → optional image generation.

- **DomainClassifier** (`domain_classifier.py`): Keyword-based classification into the three trained domains (or "General" fallback). Each domain maps to a structured workflow skeleton (decision, constraint, risk owner, human roles).
- **ExpertLensManager** (`expert_lens_manager.py`): Rotates through 8 analytical perspectives (e.g., "What Everyone Gets Wrong", "The Hidden Tradeoff") to produce varied content. Persists rotation state to `lens_state.json`.
- **PlatformFormatter** (`platform_formatter.py`): Enforces platform-specific constraints — Twitter: 280 chars / 3 hashtags, Instagram: 1000 chars / 30 hashtags, LinkedIn: 1000 chars / 5 hashtags, Facebook: 2000 chars / 5 hashtags.
- **ContentModerator** (`content_moderator.py`): Lenient filtering — only blocks extreme claims and inappropriate language. Intentionally avoids over-filtering fine-tuned output.
- **validation_utils.py**: Post-processing utilities — `extract_body()` separates body from footer/hashtags, `ensure_exactly_one_question_at_end()` validates question placement, `split_sentences()` for sentence-level analysis.

### n8n integration (`agents/n8n_client.py`)

N8NClient normalizes generated content into a standardized JSON job and POSTs it to the n8n webhook. The n8n instance runs the **Agent23-Main** workflow which routes to platform-specific adapters (Facebook, Instagram, LinkedIn).

```
ContentCreatorAgent → N8NClient.create_post_job() → POST /webhook/claude → n8n workflows → platforms
```

Key behaviors:
- Idempotency via SHA256-hashed keys prevents duplicate posts
- Platform-specific text variants are sent in the payload (`content.text` as dict with platform keys)
- Image URL is passed to n8n which handles download/upload per platform
- n8n API (`/api/v1/executions`) is polled for results after submission

### n8n workflow architecture

The Agent23-Main workflow (`n-5Nc4toiXAgJMB67Py_L`) receives webhooks and fans out to platform nodes:

- **Facebook**: Graph API node posts with image URL directly
- **Instagram**: Container creation → Publish flow (Meta requires hosted image URL)
- **LinkedIn**: Multi-node approach required due to binary handling:
  1. LI: Init (Code) → calls `/rest/images?action=initializeUpload`
  2. LI: Has Image? (If) → routes image vs text-only
  3. LI: Download Image (HTTP Request node) → native binary download
  4. LI: Upload Image (HTTP Request node) → PUT binary to LinkedIn
  5. LI: Create Post (Code) → creates post with image URN

**Critical — n8n binary data corruption**: n8n Code nodes corrupt binary data (UTF-8 decoding destroys bytes >127, e.g. PNG header 0x89 becomes U+FFFD). This is irreversible. Always use native HTTP Request nodes for binary download/upload operations. The LinkedIn image flow was split into separate nodes specifically to work around this. `this.helpers.httpRequest` with any combination of `encoding: null`, `responseType: 'arraybuffer'`, or `returnFullResponse` all return corrupted strings.

### LinkedIn posting — fallback strategy

LinkedIn has two posting paths:

1. **Via n8n** (current default): All 3 platforms route through the Agent23-Main workflow. LinkedIn uses the multi-node approach above.
2. **Direct from Python** (proven fallback): `post_to_linkedin_direct()` in `official_test_post.py` uses Python requests + subprocess curl for the 4-step image upload. This bypasses n8n entirely and is confirmed working. Use this if n8n LinkedIn breaks again.

### LinkedIn API — important notes

- **Use the new Posts API** (`/rest/posts`) — posts are visible in feed
- **Do NOT use the old UGC API** (`/v2/ugcPosts`) — creates invisible posts
- Required header: `LinkedIn-Version: 202601` (must be an active version)
- Image upload: `/rest/images?action=initializeUpload` → PUT binary → reference `image` URN in post

### Scheduling system (`agents/scheduler/`)

- **PostScheduler** (`post_scheduler.py`): Fixed daily schedule at **8:15 AM Eastern Time**. Calculates next posting time from current time.
- **SchedulerAgent** (`scheduler_agent.py`): Manages a priority queue of scheduled posts with a background thread. Retry logic uses exponential backoff (5s → 60s max). Post history logged to `post_log.json`. Supports dry-run mode.
- **Platform posters** (`platform_posters/`): Individual API integrations for Twitter, Instagram, LinkedIn, Facebook.

### Brand guidelines (`example_brand_guidelines.json`)

Domain-specific voice definitions (tone, traits, key themes) plus content requirements (stay within trained domains, grounded language, no promises or advice-giving). Loaded and cached by `brand_guidelines_manager.py`.

## Deployment

Code runs on a GCP instance. The PEFT model lives at `/home/amaziahy80/LLM_VAULT/Elevaretinyllma` on the instance. Files are synced via rsync/scp. The n8n instance runs on the same GCP VM on port 5678. `official_test_post.py` uses `localhost:5678` as the webhook URL since it runs on the same machine.

Image hosting uses GCS bucket `gs://trade_bucket45ts` (public). IMGBB is unreliable for Meta APIs (FB/IG timeout downloading from it) — prefer GCS.

### Key scripts (run on GCP, not in test suite)

- `official_test_post.py` — Full integration test: generates text, creates images (Stability AI), uploads to GCS, posts to all platforms via n8n, polls for results. Also contains `post_to_linkedin_direct()` as a fallback.
- `generate_sample_posts.py` — Quick test of fine-tuned model output across domains

## State files (gitignored, created at runtime)

- `content_state.json` — Expert lens rotation tracking
- `post_log.json` — Posting history and scheduled posts
- `lens_state.json` — Lens cycle state persistence

## Testing

Tests use `unittest` with extensive mocking. No external services are required to run the test suite. Key test categories:

- **Unit tests**: Per-component with mocking (e.g., `test_domain_classifier.py`, `test_platform_formatter.py`)
- **Integration tests** (`test_integration.py`): Multi-component workflows
- **Functional tests** (`test_functional.py`): End-to-end scenarios with minimal mocking
- **Validation tests** (`test_validation_utils.py`): Body extraction, question detection, sentence splitting
