# PEFT Adapter vs Local Endpoint - Explanation

## The Two Modes

### 1. **PEFT Adapter Mode** (Your Trained Model) ✅ PREFERRED

**What it is:**
- Your **fine-tuned/trained model** (Elevaretinyllma)
- Loads directly: Base model (TinyLlama) + Your adapter weights
- Runs inference **locally** (no HTTP calls)
- Uses **your trained model** that knows your domains

**How it works:**
```python
# Set this environment variable:
PEFT_ADAPTER_PATH="/path/to/Elevaretinyllma"

# TextGenerator automatically:
# 1. Loads base model from HuggingFace
# 2. Loads your adapter from PEFT_ADAPTER_PATH
# 3. Combines them = Your trained model
# 4. Runs inference directly (no HTTP)
```

**Result:** Uses **YOUR trained model** ✅

---

### 2. **Local Endpoint Mode** (Pretrained Model) ⚠️ FALLBACK

**What it is:**
- HTTP endpoint to a running LLM server (like Ollama)
- Connects to a server running a **pretrained model** (not your fine-tuned one)
- Makes HTTP requests to generate text
- Uses whatever model is running on that server

**How it works:**
```python
# Set this environment variable:
LOCAL_LLM_ENDPOINT="http://localhost:11434/v1/chat/completions"

# TextGenerator:
# 1. Makes HTTP POST request to endpoint
# 2. Server (Ollama) runs a pretrained model (e.g., TinyLlama)
# 3. Returns generated text
# 4. Does NOT use your trained model
```

**Result:** Uses **pretrained model** (not your trained one) ⚠️

---

## Priority Order

The system checks in this order:

1. **First:** Check for `PEFT_ADAPTER_PATH`
   - ✅ If found → Use your trained model (direct loading)
   - ✅ No HTTP endpoint needed

2. **Second:** Check for `LOCAL_LLM_ENDPOINT`
   - ⚠️ Only checked if PEFT adapter is NOT available
   - ⚠️ Uses pretrained model on the server
   - ⚠️ Requires a running LLM server (Ollama, etc.)

---

## Why Local Endpoint Uses Pretrained Model

**The local endpoint connects to a server that runs standard pretrained models.**

For example:
- Ollama running `tinyllama` (pretrained)
- OpenAI-compatible API with a pretrained model
- Any LLM server with a standard model

**Your fine-tuned model is ONLY available via PEFT adapter.**

The endpoint server doesn't have your trained model - it has whatever model you installed on that server (typically a pretrained one).

---

## Code Flow

```python
# In content_creator_agent.py (lines 55-76):
peft_adapter_path = os.environ.get("PEFT_ADAPTER_PATH")

if not peft_adapter_path:
    # PEFT not available → require HTTP endpoint
    local_llm_endpoint = os.environ.get("LOCAL_LLM_ENDPOINT")
    # This endpoint uses pretrained model
else:
    # PEFT available → use your trained model
    # No endpoint needed
```

```python
# In text_generator.py (lines 101-127):
if self.peft_adapter_path:
    # Try to load PEFT adapter (your trained model)
    self._load_peft_model()
    self.use_direct_model = True  # ✅ Uses YOUR model
    
if not self.use_direct_model:
    # Fallback to HTTP endpoint (pretrained model)
    # Requires LOCAL_LLM_ENDPOINT
    # ⚠️ Uses PRETRAINED model on server
```

---

## Summary

| Feature | PEFT Adapter | Local Endpoint |
|---------|--------------|----------------|
| **Model** | Your trained model ✅ | Pretrained model ⚠️ |
| **Loading** | Direct (local files) | HTTP requests |
| **Offline** | Yes ✅ | No (needs server) |
| **Speed** | Faster (no network) | Slower (network latency) |
| **Setup** | Set `PEFT_ADAPTER_PATH` | Set `LOCAL_LLM_ENDPOINT` + run server |
| **When to use** | **Always preferred** | Fallback only |

---

## Recommendation

**Always use PEFT adapter mode** if you have your trained model:
- Uses your trained model (not pretrained)
- Faster (no HTTP calls)
- Offline capable
- More reliable

**Only use local endpoint** as a fallback:
- When PEFT adapter is not available
- For testing/development
- When you need to use a different model temporarily
