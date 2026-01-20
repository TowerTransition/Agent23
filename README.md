# Agent23 - AI Content Creation and Scheduling System

A comprehensive social media content creation and scheduling system powered by fine-tuned language models.

## Features

- **Content Generation**: AI-powered content creation for multiple social media platforms (Twitter, Instagram, LinkedIn, Facebook)
- **Expert Lens System**: Rotating analytical perspectives for authoritative, curiosity-driven content
- **Domain Classification**: Automatic classification into trained domains (Foreclosures, Trading Futures, Assisted Living)
- **Platform Formatting**: Automatic adaptation to platform-specific constraints (character limits, hashtags, etc.)
- **Content Moderation**: Built-in content filtering and validation
- **Scheduling**: Intelligent post scheduling with optimal timing (8:15 AM Eastern daily)
- **Multi-Platform Support**: Generate and schedule content across multiple platforms simultaneously

## Architecture

### Content Creator Agent
- `ContentCreatorAgent`: Main orchestrator for content generation
- `TextGenerator`: Text generation using PEFT adapters or HTTP endpoints
- `ImageGenerator`: Image generation using Stability AI
- `ExpertLensManager`: Expert lens selection and content planning
- `DomainClassifier`: Automatic domain classification
- `PlatformFormatter`: Platform-specific content formatting
- `ContentModerator`: Content validation and filtering

### Scheduler Agent
- `SchedulerAgent`: Post scheduling and execution
- `PostScheduler`: Optimal posting time calculation
- Platform Posters: Twitter, Instagram, LinkedIn, Facebook integration

## Setup

### Prerequisites

```bash
pip install peft transformers torch requests pytz
```

### Environment Variables

**For PEFT Adapter (Direct Model Loading):**
```bash
export PEFT_ADAPTER_PATH="/path/to/your/Elevaretinyllma"
export BASE_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

**For HTTP Endpoint Mode:**
```bash
export LOCAL_LLM_ENDPOINT="http://localhost:11434/v1/chat/completions"
export LOCAL_LLM_MODEL="tinyllama"
export ALLOW_DEFAULT_LLM_ENDPOINT="true"
```

**For Image Generation:**
```bash
export STABILITY_API_KEY="your-stability-ai-api-key"
```

**For Social Media APIs:**
```bash
export TWITTER_BEARER_TOKEN="your-twitter-token"
export INSTAGRAM_ACCESS_TOKEN="your-instagram-token"
export LINKEDIN_ACCESS_TOKEN="your-linkedin-token"
export FACEBOOK_PAGE_ACCESS_TOKEN="your-facebook-token"
```

## Usage

### Basic Content Generation

```python
from agents.content_creator.content_creator_agent import ContentCreatorAgent

agent = ContentCreatorAgent(
    brand_guidelines_path="agents/content_creator/example_brand_guidelines.json"
)

trend_data = {
    "title": "AI in Foreclosure Processes",
    "description": "How AI helps coordinate foreclosure information",
    "domain": "Foreclosures"
}

content = agent.generate_content_for_platform(
    trend_data=trend_data,
    platform="twitter"
)

print(content["text"])
```

### Multi-Platform Content Generation

```python
content_by_platform = agent.generate_multi_platform_content(
    trend_data=trend_data,
    platforms=["twitter", "instagram", "linkedin"]
)
```

### Scheduling Posts

```python
from agents.scheduler.scheduler_agent import SchedulerAgent

scheduler = SchedulerAgent(
    post_log_path="logs/post_log.json",
    dry_run=True  # Set to False for actual posting
)

# Schedule a single post
result = scheduler.schedule_post(
    content=content,
    platform="twitter"
)

# Schedule multiple platforms
scheduler.schedule_multi_platform(content_by_platform)

# Post immediately
scheduler.post_now(content, "twitter")
```

## Testing

### Unit Tests
```bash
python -m unittest tests.test_content_creator_agent -v
python -m unittest tests.test_scheduler_agent -v
```

### Integration Tests
```bash
python -m unittest tests.test_integration -v
```

### Functional Tests
```bash
python -m unittest tests.test_functional -v
```

### Run All Tests
```bash
python -m unittest discover tests -v
```

## Project Structure

```
Agent23/
├── agents/
│   ├── content_creator/
│   │   ├── content_creator_agent.py
│   │   ├── text_generator.py
│   │   ├── expert_lens_manager.py
│   │   ├── domain_classifier.py
│   │   └── ...
│   └── scheduler/
│       ├── scheduler_agent.py
│       ├── post_scheduler.py
│       └── platform_posters/
├── tests/
│   ├── test_content_creator_agent.py
│   ├── test_scheduler_agent.py
│   ├── test_integration.py
│   └── ...
├── cache/          # Cache directory (not committed)
├── logs/           # Log files (not committed)
└── README.md
```

## Training Data

The system is trained on three specific domains:
- **Foreclosures**: Housing stability and foreclosure processes
- **Trading Futures**: Trading discipline and risk management
- **Assisted Living**: Care coordination and family decision-making

## Expert Lens System

The system rotates through 8 expert lenses:
1. What Everyone Gets Wrong
2. The Real Constraint
3. How This Plays Out in Practice
4. Where This Breaks at Scale
5. The Hidden Tradeoff
6. How We Evaluate It
7. What Changes After Adoption
8. The Open Question We're Exploring

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
