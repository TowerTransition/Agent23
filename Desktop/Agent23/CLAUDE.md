# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent23 is an AI-powered social media content creation and scheduling system. It generates platform-specific posts (Twitter, Instagram, LinkedIn, Facebook) for three trained domains: **Foreclosures**, **Trading Futures**, and **Assisted Living**. The brand identity is **Elevare by Amaziah**.

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

### Environment variables for local development
```bash
# PEFT mode (preferred) - fine-tuned model loaded in-process
PEFT_ADAPTER_PATH="/path/to/Elevaretinyllma"
BASE_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# HTTP fallback mode - OpenAI-compatible endpoint (e.g., Ollama)
LOCAL_LLM_ENDPOINT="http://localhost:11434/v1/chat/completions"
LOCAL_LLM_MODEL="tinyllama"
ALLOW_DEFAULT_LLM_ENDPOINT="true"

# Optional
STABILITY_API_KEY="..."  # Image generation
```

## Architecture

### Two-mode text generation (`text_generator.py`)

TextGenerator operates in two modes with automatic fallback:

1. **PEFT Direct** (preferred): Loads fine-tuned PEFT adapters in-process via `PEFT_ADAPTER_PATH`. Uses minimal prompts because the fine-tuned model is trusted. No HTTP overhead.
2. **HTTP Endpoint** (fallback): Calls an OpenAI-compatible chat completions API via `LOCAL_LLM_ENDPOINT`. Applies more aggressive post-processing since the model output is less predictable.

Footer text ("— Elevare by Amaziah") and hashtags are always appended in Python, never delegated to the model.

### Content creation pipeline (`content_creator_agent.py`)

Orchestrates the full flow: domain classification → expert lens selection → text generation → validation → platform formatting → content moderation → optional image generation.

- **DomainClassifier** (`domain_classifier.py`): Keyword-based classification into the three trained domains (or "General" fallback). Each domain maps to a structured workflow skeleton (decision, constraint, risk owner, human roles).
- **ExpertLensManager** (`expert_lens_manager.py`): Rotates through 8 analytical perspectives (e.g., "What Everyone Gets Wrong", "The Hidden Tradeoff") to produce varied content. Persists rotation state to `lens_state.json`.
- **PlatformFormatter** (`platform_formatter.py`): Enforces platform-specific constraints — Twitter: 280 chars / 3 hashtags, Instagram: 1000 chars / 30 hashtags, LinkedIn: 1000 chars / 5 hashtags, Facebook: 2000 chars / 5 hashtags.
- **ContentModerator** (`content_moderator.py`): Lenient filtering — only blocks extreme claims and inappropriate language. Intentionally avoids over-filtering fine-tuned output.
- **validation_utils.py**: Post-processing utilities — `extract_body()` separates body from footer/hashtags, `ensure_exactly_one_question_at_end()` validates question placement, `split_sentences()` for sentence-level analysis.

### Scheduling system (`agents/scheduler/`)

- **PostScheduler** (`post_scheduler.py`): Fixed daily schedule at **8:15 AM Eastern Time**. Calculates next posting time from current time.
- **SchedulerAgent** (`scheduler_agent.py`): Manages a priority queue of scheduled posts with a background thread. Retry logic uses exponential backoff (5s → 60s max). Post history logged to `post_log.json`. Supports dry-run mode.
- **Platform posters** (`platform_posters/`): Individual API integrations for Twitter, Instagram, LinkedIn, Facebook.

### Brand guidelines (`example_brand_guidelines.json`)

Domain-specific voice definitions (tone, traits, key themes) plus content requirements (stay within trained domains, grounded language, no promises or advice-giving). Loaded and cached by `brand_guidelines_manager.py`.

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
