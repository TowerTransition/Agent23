# PEFT Adapter Setup for Elevaretinyllma

## Overview

The `TextGenerator` now supports direct loading of PEFT (Parameter-Efficient Fine-Tuning) adapter models for offline text generation. This allows you to use the fine-tuned Elevaretinyllma model (note: directory name is case-sensitive) directly without requiring an HTTP endpoint.

## Setup

### 1. Install Required Dependencies

```bash
pip install peft transformers torch
```

### 2. Set Environment Variables

Set the following environment variables to use the PEFT adapter:

**Find Your Model Path:**
- Your trained model should be in a directory named `Elevaretinyllma` (case-sensitive)
- The directory should contain: `adapter_config.json` and `adapter_model.safetensors`
- Use the **full absolute path** to this directory

**Set the Environment Variable:**

**On Windows (PowerShell):**
```powershell
# Path to the PEFT adapter directory (required)
$env:PEFT_ADAPTER_PATH = "C:\path\to\your\models\Elevaretinyllma"

# Base model name (optional, defaults to TinyLlama)
$env:BASE_MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

**On Windows (Command Prompt):**
```cmd
set PEFT_ADAPTER_PATH=C:\path\to\your\models\Elevaretinyllma
set BASE_MODEL_NAME=TinyLlama/TinyLlama-1.1B-Chat-v1.0
```

**On Linux/Mac:**
```bash
# Path to the PEFT adapter directory (required)
export PEFT_ADAPTER_PATH="/path/to/your/models/Elevaretinyllma"

# Base model name (optional, defaults to TinyLlama)
# IMPORTANT: This must match the base model you used for training
# If you trained on TinyLlama, use TinyLlama. If you trained on a different model, change this.
export BASE_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
```

**Note:** Replace `/path/to/your/models/Elevaretinyllma` or `C:\path\to\your\models\Elevaretinyllma` with the actual path where your trained model is located.

### 3. Usage

The `TextGenerator` will automatically detect the `PEFT_ADAPTER_PATH` environment variable and load the model directly. If the path is not set or loading fails, it will fall back to HTTP endpoint mode.

## How It Works

### Why You Need the Base Model

When you fine-tune a model using PEFT (Parameter-Efficient Fine-Tuning), you're only saving the **adapter weights** (the fine-tuned parameters), not the entire model. The PEFT adapter is a small set of parameters that modify the base model's behavior.

**Think of it like this:**
- **Base Model (TinyLlama)**: The foundation - contains all the original weights (~1.1B parameters)
- **PEFT Adapter**: Your fine-tuned changes - contains only the modified parameters (~few MB)
- **Final Model**: Base Model + Adapter = Your trained model

So even though you trained on TinyLlama, you still need:
1. The original TinyLlama base model (downloaded from HuggingFace)
2. Your PEFT adapter (from your training)

The system combines them at runtime to recreate your fine-tuned model.

### Loading Process

1. **Priority Check**: On initialization, `TextGenerator` checks for `PEFT_ADAPTER_PATH`
2. **Model Loading**: If found and PEFT is available, it loads:
   - Base model from HuggingFace (`TinyLlama/TinyLlama-1.1B-Chat-v1.0`) - this is the model you trained on
   - PEFT adapter from the specified path - this contains your training
3. **Combination**: The adapter is applied to the base model to create your fine-tuned model
4. **Direct Inference**: Text generation uses the combined model directly (no HTTP calls)
5. **Fallback**: If PEFT loading fails, falls back to HTTP endpoint mode

## Model Path Structure

The PEFT adapter directory should contain:
```
Elevaretinyllma/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

## Example Usage

```python
from agents.content_creator.content_creator_agent import ContentCreatorAgent

# Set environment variable before initialization
import os
os.environ["PEFT_ADAPTER_PATH"] = "/path/to/your/models/Elevaretinyllma"

# Initialize agent (will automatically use PEFT adapter)
agent = ContentCreatorAgent(
    brand_guidelines_path='agents/content_creator/example_brand_guidelines.json'
)

# Generate content (uses direct model inference)
content = agent.generate_content_for_platform(
    platform='facebook',
    trend_data={'title': 'AI in Healthcare', 'description': '...'}
)
```

## Benefits

1. **Offline after initial setup**: No HTTP endpoint required for text generation after the base model is downloaded from HuggingFace on first use
2. **Faster**: Direct model inference (no network latency)
3. **Reliable**: No dependency on external services
4. **Flexible**: Falls back to HTTP endpoint if PEFT not available

## Troubleshooting

### Model Not Loading

- Check that `PEFT_ADAPTER_PATH` points to the correct directory
- Verify the directory contains required adapter files
- Ensure `peft`, `transformers`, and `torch` are installed
- Check logs for specific error messages

### CUDA Out of Memory

If using GPU and running out of memory:

**Option A: Use Environment Variable (Recommended)**
- Set `PEFT_DEVICE_MAP=cpu` environment variable before initializing `ContentCreatorAgent`
- The `_load_peft_model()` function in `text_generator.py` reads this setting and uses it when calling `AutoModelForCausalLM.from_pretrained()`
- Defaults to "auto" if CUDA is available, otherwise "cpu"

**Option B: Reduce Memory Usage**
- Reduce `max_tokens` in generation calls
- Use smaller batch sizes
- Consider using quantization if available

### Fallback to HTTP Endpoint

If the system falls back to HTTP endpoint mode:
- Check that `PEFT_ADAPTER_PATH` is set correctly
- Verify PEFT dependencies are installed
- Check logs for loading errors

## Notes

- The PEFT adapter path should be an absolute path
- **The base model must match what you trained on**: If you trained on TinyLlama, use TinyLlama. If you trained on a different base model, update `BASE_MODEL_NAME` accordingly.
- The base model will be downloaded from HuggingFace on first use (cached locally after that)
- Model loading happens once during initialization (cached in memory)
- Direct model inference is faster but uses more memory than HTTP endpoints
- **PEFT adapters are small**: Your adapter only contains the fine-tuned parameters, not the full model. That's why you need the base model too.