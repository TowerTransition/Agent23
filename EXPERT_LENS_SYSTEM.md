# Expert Lens System - Content Generation Upgrade

## Overview

The content agent has been upgraded to use an **expert lens system** that autonomously selects analytical perspectives, maps real-world workflows, identifies constraints, and highlights human decision points. This creates authoritative, curiosity-driven content rather than generic AI explainers.

## Key Features

### 1. Expert Lens Rotation
The system rotates through 8 expert lenses on a fixed cycle:
- **What Everyone Gets Wrong** - Corrects common misconceptions
- **The Real Constraint** - Identifies actual bottlenecks
- **How This Plays Out in Practice** - Maps real-world workflows
- **Where This Breaks at Scale** - Analyzes scale failure modes
- **The Hidden Tradeoff** - Reveals necessary compromises
- **How We Evaluate It** - Explains decision frameworks
- **What Changes After Adoption** - Explores second-order effects
- **The Open Question We're Exploring** - Shares field notes and investigations

### 2. State Persistence
- Tracks which lenses have been used
- Avoids repeating recently covered domains
- Maintains history of last 20 posts
- Prevents content repetition

### 3. Workflow Analysis
Each lens includes instructions for:
- **Workflow Mapping**: Step-by-step process analysis
- **Constraint Identification**: Naming specific limitations
- **Human Decision Points**: Identifying where judgment is required

### 4. Subtle Brand Anchoring
Uses perspective-based phrases instead of promotion:
- "What we're seeing:"
- "Where this breaks in practice:"
- "The question we're exploring:"
- "What we've learned:"
- "The pattern we're noticing:"

## Architecture

### New Components

1. **`ExpertLensManager`** (`agents/content_creator/expert_lens_manager.py`)
   - Manages lens selection and rotation
   - Handles state persistence
   - Creates content plans with workflow/constraint focus

2. **Updated `ContentCreatorAgent`**
   - Integrated `ExpertLensManager`
   - New `use_expert_lens` parameter
   - Supports `trend_candidates` for multi-trend selection

3. **Updated `TextGenerator`** (`agents/content_creator/text_generator.py`)
   - Enhanced prompt building with lens context
   - Workflow analysis instructions
   - Constraint identification guidance
   - Updated system message for expert perspective
   - **LLM Configuration**: Supports multiple LLM backends:
     - **PEFT Adapter** (preferred): Direct model loading via `PEFT_ADAPTER_PATH` (ElevateTinyLlama fine-tuned model)
     - **HTTP Endpoint**: OpenAI-compatible API via `LOCAL_LLM_ENDPOINT` (e.g., Ollama, vLLM, TGI)
     - **OpenAI API**: Fallback via `OPENAI_API_KEY` (if neither PEFT nor local endpoint available)
   - See `PEFT_ADAPTER_SETUP.md` and `README.md` for LLM setup details

## Usage

### Basic Usage (Single Trend)

```python
from agents.content_creator.content_creator_agent import ContentCreatorAgent

agent = ContentCreatorAgent(
    brand_guidelines_path='agents/content_creator/example_brand_guidelines.json'
)

# Single trend - lens manager will select lens and create plan
trend_data = {
    'title': 'AI-assisted imaging triage',
    'description': 'AI-powered diagnostic tools helping doctors',
    'domain': 'Healthcare',
    'hashtags': ['AIHealthcare', 'HealthTech']
}

content = agent.generate_content_for_platform(
    platform='linkedin',
    trend_data=trend_data,
    use_expert_lens=True  # Default: True
)
```

### Advanced Usage (Multiple Trend Candidates)

```python
# Provide multiple trend candidates - lens manager picks best one
trend_candidates = [
    {
        "trend": "AI-assisted imaging triage for radiology backlogs",
        "domain": "Healthcare",
        "score": 0.92,
        "description": "AI tools reducing wait times in radiology",
        "hashtags": ["AIHealthcare", "Radiology"]
    },
    {
        "trend": "LLM summarization to reduce support handle time",
        "domain": "Customer Support",
        "score": 0.85,
        "description": "AI summarizing customer support tickets",
        "hashtags": ["AISupport", "CustomerService"]
    }
]

content = agent.generate_content_for_platform(
    platform='twitter',
    trend_data=trend_candidates[0],  # Fallback if lens selection fails
    trend_candidates=trend_candidates,
    use_expert_lens=True
)
```

### Multi-Platform Generation

```python
# Define trend data (required)
trend_data = {
    'title': 'AI in Healthcare',
    'description': 'AI-powered diagnostic tools helping doctors detect diseases earlier',
    'domain': 'Healthcare',
    'hashtags': ['AIHealthcare', 'HealthTech']
}

# Optional: define trend candidates for expert lens
trend_candidates = [
    {
        'trend': 'AI in Healthcare',
        'title': 'AI in Healthcare',
        'description': 'AI-powered diagnostic tools helping doctors detect diseases earlier',
        'domain': 'Healthcare',
        'hashtags': ['AIHealthcare', 'HealthTech'],
        'score': 0.9
    }
]

content = agent.generate_multi_platform_content(
    trend_data=trend_data,
    platforms=['twitter', 'linkedin', 'facebook'],
    use_expert_lens=True,
    trend_candidates=trend_candidates  # Optional
)
```

### Disable Expert Lens (Legacy Mode)

```python
# Use traditional content generation
content = agent.generate_content_for_platform(
    platform='instagram',
    trend_data=trend_data,
    use_expert_lens=False  # Falls back to original prompt system
)
```

## Content Plan Structure

When using expert lens system, the generated content plan includes:

```python
{
    "lens": "The Real Constraint",
    "post_type": "Constraint-First",
    "trend": "AI-assisted imaging triage",
    "trend_description": "AI tools reducing wait times...",
    "domain": "Healthcare",
    "hashtags": ["AIHealthcare", "Radiology"],
    "brand_phrase": "What we're seeing:",
    "signature": "— Elevare by Amaziah",
    "workflow_focus": "Map the actual workflow...",
    "constraint_focus": "Name the specific constraint...",
    "platform": "linkedin"
}
```

## State Management

State is persisted in `cache/content_state.json`:

```json
{
  "lens_i": 2,
  "history": [
    {
      "date": "2026-01-08",
      "lens": "What Everyone Gets Wrong",
      "post_type": "Correction",
      "domain": "Healthcare",
      "trend": "AI-assisted imaging triage",
      "platform": "linkedin"
    }
  ]
}
```

## Integration with Existing Code

The expert lens system is **backward compatible**:
- Existing code continues to work
- `use_expert_lens=True` by default (can be disabled)
- Falls back gracefully if lens selection fails
- State file is created automatically

## Example Output

**Before (Generic Explainer):**
> "AI is revolutionizing healthcare! Learn how AI-powered diagnostic tools are helping doctors detect diseases earlier. #AIHealthcare #HealthTech"

**After (Expert Lens - "The Real Constraint"):**
> "What we're seeing: The real constraint in AI-assisted imaging isn't the model accuracy—it's the workflow bottleneck at the human review stage. The system flags 200 cases/hour, but radiologists can only review 50/hour. The decision point isn't 'is this accurate?' but 'which cases need immediate attention vs. routine review?' That's where the system breaks, not in the AI itself.
> 
> — Elevare by Amaziah"

## Benefits

1. **Authority**: Demonstrates deep understanding, not surface-level knowledge
2. **Curiosity**: Readers want to know who Elevare/Amaziah is because of how we think
3. **Differentiation**: No generic AI explainers—every post has a unique analytical angle
4. **Consistency**: Rotating lenses ensure variety while maintaining quality
5. **Persistence**: State tracking prevents repetition and ensures coverage

## Configuration

### Customizing Lenses

Edit `agents/content_creator/expert_lens_manager.py`:
- Modify `LENS_CYCLE` to change lens order or add/remove lenses
- Update `POST_TYPES_BY_LENS` to change post type associations
- Adjust `BRAND_PHRASES` to customize brand anchoring

### State File Location

Change state file location in `ContentCreatorAgent.__init__`:
```python
state_path = os.path.join(cache_dir, "content_state.json")
self.lens_manager = ExpertLensManager(state_path=state_path)
```

## Next Steps

1. Test the system with your trend data
2. Review generated content to ensure lens instructions are followed
3. Adjust lens instructions in `_get_lens_instructions()` if needed
4. Monitor state file to track lens rotation and domain coverage
