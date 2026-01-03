# Quick Start Guide - Google Cloud Setup

## Your Instance
- **Name**: `instance-20260103-165047`
- **Zone**: `us-central1-a`
- **Status**: ✅ Running

## Step 1: Transfer Code (From Your Windows Machine)

Run this PowerShell command from your AGENT directory:

```powershell
.\transfer_to_gcp.ps1
```

Or manually:
```powershell
gcloud compute scp --recurse . instance-20260103-165047:~/AGENT --zone=us-central1-a
```

## Step 2: SSH Into Instance

```powershell
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a
```

## Step 3: Run Setup Script (On the Instance)

```bash
cd ~/AGENT
bash setup_instance.sh
```

This will:
- ✅ Install Python and dependencies
- ✅ Create virtual environment
- ✅ Install all packages
- ✅ Create `.env` template

## Step 4: Choose Your LLM Option

### Option A: Ollama (Easiest - CPU-based)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Download a model (7B models work on 16GB RAM)
ollama pull llama2:7b
# OR
ollama pull mistral:7b

# Start Ollama server
ollama serve

# In another terminal, test it:
curl http://localhost:11434/api/generate -d '{
  "model": "llama2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

Then update `.env`:
```env
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions
```

### Option B: Create GPU Instance for vLLM (Better Performance)

```bash
# From your local machine, create GPU instance:
gcloud compute instances create llm-server \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB

# Get the IP
gcloud compute instances describe llm-server --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# SSH and set up vLLM (see setup_llm_server.sh)
```

### Option C: Use Hugging Face CPU Server (Advanced)

```bash
# Install additional dependencies
pip install flask transformers torch

# Run the CPU LLM server
python setup_cpu_llm.py --model microsoft/DialoGPT-small --port 8000
```

## Step 5: Configure Environment

Edit `.env` file:
```bash
nano ~/AGENT/.env
```

**Required settings:**
```env
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions  # For Ollama
# OR
LOCAL_LLM_ENDPOINT=http://YOUR_GPU_VM_IP:8000/v1/chat/completions  # For vLLM

# Add your social media API keys
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
# ... etc
```

## Step 6: Test Everything

```bash
cd ~/AGENT
source venv/bin/activate

# Test trend scanner
python run_trend_scanner.py

# Test content creator
python run_content_creator.py

# Test full orchestrator
python orchestrator.py --test
```

## Step 7: Set Up Automation

### Using Cron (Simple)

```bash
crontab -e
```

Add this line (8:00 AM Eastern = 13:00 UTC):
```cron
0 13 * * * cd /home/YOUR_USERNAME/AGENT && /home/YOUR_USERNAME/AGENT/venv/bin/python orchestrator.py >> /home/YOUR_USERNAME/AGENT/logs/cron.log 2>&1
```

### Using systemd (Recommended)

See `SETUP_GCP_INSTANCE.md` for detailed systemd setup.

## Troubleshooting

### Can't connect to LLM
```bash
# Test endpoint
curl -X POST http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"test"}]}'
```

### Python import errors
```bash
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Permission denied
```bash
chmod +x ~/AGENT/*.py
chmod 644 ~/AGENT/.env
```

## Quick Commands Reference

```bash
# SSH into instance
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a

# Transfer single file
gcloud compute scp file.txt instance-20260103-165047:~/AGENT/ --zone=us-central1-a

# Get instance IP
gcloud compute instances describe instance-20260103-165047 --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# View logs
tail -f ~/AGENT/logs/*.log
```

## Next Steps After Setup

1. ✅ Code is on the instance
2. ✅ Python environment ready
3. ⏳ LLM server running
4. ⏳ `.env` configured with API keys
5. ⏳ Test runs successful
6. ⏳ Automation scheduled
7. ⏳ Monitor first automated post

---

**Need help?** Check `SETUP_GCP_INSTANCE.md` for detailed instructions.

