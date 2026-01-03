# Setting Up TinyLlama 1.1B on Google Cloud

## Overview
TinyLlama 1.1B is a lightweight model perfect for your `e2-standard-4` instance (4 vCPUs, 16GB RAM). It can run efficiently on CPU without requiring a GPU.

## Option 1: Using Ollama (Recommended - Easiest)

### Step 1: Install Ollama on Your Instance

SSH into your instance and run:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### Step 2: Pull TinyLlama Model

```bash
ollama pull tinyllama
```

This will download the TinyLlama 1.1B model (approximately 637 MB).

### Step 3: Start Ollama Server

```bash
ollama serve
```

The server will run on `http://localhost:11434`

### Step 4: Test the Model

In another terminal (or background the server), test it:

```bash
# Test the API endpoint
curl http://localhost:11434/api/generate -d '{
  "model": "tinyllama",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

### Step 5: Configure Your .env File

Edit your `.env` file in the AGENT directory:

```bash
cd ~/AGENT
nano .env
```

Set the LLM endpoint:
```env
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions
LOCAL_LLM_API_KEY=not-needed-for-local
```

**Note:** Ollama provides an OpenAI-compatible endpoint at `/v1/chat/completions` when running.

### Step 6: Run Ollama as a Service (Optional - Auto-start on boot)

Create a systemd service so Ollama starts automatically:

```bash
sudo nano /etc/systemd/system/ollama.service
```

Add this content:
```ini
[Unit]
Description=Ollama LLM Server
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama
```

---

## Option 2: Using vLLM (More Control, Better Performance)

If you want more control or better performance, you can use vLLM:

### Step 1: Install vLLM

```bash
cd ~
python3 -m venv vllm-env
source vllm-env/bin/activate
pip install vllm
```

### Step 2: Start vLLM Server with TinyLlama

```bash
python -m vllm.entrypoints.openai.api_server \
    --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 \
    --host 0.0.0.0 \
    --port 8000 \
    --trust-remote-code
```

### Step 3: Configure .env

```env
LOCAL_LLM_ENDPOINT=http://localhost:8000/v1/chat/completions
LOCAL_LLM_API_KEY=not-needed-for-local
```

### Step 4: Run as Service (Optional)

Create systemd service similar to Ollama, but with vLLM command.

---

## Option 3: Using Hugging Face Transformers (CPU-based)

For maximum control and customization:

### Step 1: Install Dependencies

```bash
cd ~/AGENT
source venv/bin/activate
pip install transformers torch accelerate
```

### Step 2: Use the CPU LLM Server Script

The `setup_cpu_llm.py` script can run TinyLlama:

```bash
python setup_cpu_llm.py --model TinyLlama/TinyLlama-1.1B-Chat-v1.0 --port 8000
```

---

## Testing Your Setup

Once your LLM server is running, test the connection:

```bash
cd ~/AGENT
source venv/bin/activate
python3 -c "
import os
import requests
from dotenv import load_dotenv

load_dotenv()
endpoint = os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/v1/chat/completions')

response = requests.post(
    endpoint,
    json={
        'model': 'tinyllama',
        'messages': [{'role': 'user', 'content': 'Hello, test message'}],
        'temperature': 0.7,
        'max_tokens': 50
    },
    timeout=30
)

if response.status_code == 200:
    print('✓ LLM connection successful!')
    print('Response:', response.json()['choices'][0]['message']['content'])
else:
    print('✗ Connection failed:', response.status_code)
    print('Error:', response.text)
"
```

---

## Performance Notes for TinyLlama 1.1B

- **Model Size**: ~637 MB
- **Memory Usage**: ~2-3 GB RAM when loaded
- **Speed**: Fast inference on CPU (your 4 vCPU instance should handle it well)
- **Quality**: Good for basic content generation, but may need prompt engineering for best results
- **Best Use**: Content generation, simple Q&A, basic text tasks

---

## Troubleshooting

### Ollama not starting
```bash
# Check if Ollama is installed
which ollama

# Check logs
journalctl -u ollama -n 50
```

### Model not found
```bash
# List available models
ollama list

# Pull model again
ollama pull tinyllama
```

### Connection refused
```bash
# Check if server is running
curl http://localhost:11434/api/tags

# Check port
netstat -tuln | grep 11434
```

### Out of memory
TinyLlama should work fine on 16GB RAM, but if you have issues:
- Close other applications
- Reduce batch size in vLLM
- Use Ollama (more memory efficient)

---

## Recommended Setup for Your Instance

Given your `e2-standard-4` instance (4 vCPUs, 16GB RAM), I recommend:

1. **Use Ollama** - Easiest setup, good performance
2. **Run as systemd service** - Auto-start on boot
3. **Monitor memory usage** - TinyLlama should use ~2-3GB, leaving plenty for your application

---

## Next Steps

After setting up TinyLlama:

1. ✅ LLM server running
2. ✅ `.env` configured with correct endpoint
3. ⏳ Test content generation: `python run_content_creator.py`
4. ⏳ Set up automated scheduling
5. ⏳ Monitor performance and adjust prompts if needed

