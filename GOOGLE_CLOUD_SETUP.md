# Google Cloud Setup Guide

This guide will help you set up an LLM in Google Cloud and deploy this code to run on Google Cloud.

## Quick Start: LLM Options in Google Cloud

### Option 1: Vertex AI (Easiest - Google's Managed Service)

**Pros**: Fully managed, no infrastructure to maintain  
**Cons**: May require OpenAI-compatible wrapper

1. **Enable Vertex AI API**:
   ```bash
   gcloud services enable aiplatform.googleapis.com
   ```

2. **Use Vertex AI Gemini** (OpenAI-compatible via proxy or wrapper)
   - Endpoint format varies - may need a proxy service

### Option 2: vLLM on Compute Engine (Recommended - Full Control)

**Pros**: Full control, OpenAI-compatible, supports many models  
**Cons**: Requires managing VM and GPU

## Step-by-Step: Deploy vLLM on Google Cloud

### Step 1: Create a VM Instance with GPU

```bash
# Create VM with GPU for LLM
gcloud compute instances create llm-server \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --maintenance-policy=TERMINATE \
  --scopes=https://www.googleapis.com/auth/cloud-platform
```

**Note**: For CPU-only (cheaper but slower):
```bash
gcloud compute instances create llm-server \
  --zone=us-central1-a \
  --machine-type=e2-standard-4 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=50GB
```

### Step 2: SSH into the Instance

```bash
gcloud compute ssh llm-server --zone=us-central1-a
```

### Step 3: Install vLLM

```bash
# Update system
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

# If using GPU, install NVIDIA drivers
sudo apt-get install -y nvidia-driver-535
sudo reboot  # Reboot to activate drivers

# After reboot, SSH back in and create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install vLLM
pip install vllm

# Or for CPU-only (slower):
# pip install vllm --extra-index-url https://download.pytorch.org/whl/cpu
```

### Step 4: Start vLLM Server

```bash
# Activate venv
source venv/bin/activate

# Start vLLM server (example with Llama 2 - adjust model as needed)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8000 \
  --trust-remote-code

# For CPU-only:
# python -m vllm.entrypoints.openai.api_server \
#   --model meta-llama/Llama-2-7b-chat-hf \
#   --host 0.0.0.0 \
#   --port 8000 \
#   --trust-remote-code \
#   --device cpu
```

**Recommended Models**:
- `meta-llama/Llama-2-7b-chat-hf` - Good balance
- `mistralai/Mistral-7B-Instruct-v0.2` - Fast and efficient
- `microsoft/Phi-3-mini-4k-instruct` - Small, fast

### Step 5: Configure Firewall

```bash
# Allow traffic on port 8000
gcloud compute firewall-rules create allow-llm-server \
  --allow tcp:8000 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow LLM server traffic"
```

### Step 6: Get Your Endpoint URL

```bash
# Get external IP
gcloud compute instances describe llm-server \
  --zone=us-central1-a \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)'
```

Your endpoint will be:
```
http://YOUR_EXTERNAL_IP:8000/v1/chat/completions
```

## Deploy Your Application Code

### Step 1: Create Application VM

```bash
# Create VM for your application (smaller instance, no GPU needed)
gcloud compute instances create social-media-agent \
  --zone=us-central1-a \
  --machine-type=e2-medium \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB
```

### Step 2: Transfer Your Code

```bash
# From your local machine, transfer code
gcloud compute scp --recurse . social-media-agent:~/AGENT --zone=us-central1-a

# Or clone from Git
gcloud compute ssh social-media-agent --zone=us-central1-a
git clone YOUR_REPO_URL
cd AGENT
```

### Step 3: Install Dependencies

```bash
# SSH into application VM
gcloud compute ssh social-media-agent --zone=us-central1-a

# Install Python and dependencies
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### Step 4: Configure Environment Variables

Create `.env` file on the VM:

```bash
# Get LLM server IP
LLM_IP=$(gcloud compute instances describe llm-server --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

# Create .env file
cat > .env << EOF
# Local LLM Configuration (Google Cloud)
LOCAL_LLM_ENDPOINT=http://${LLM_IP}:8000/v1/chat/completions
LOCAL_LLM_API_KEY=

# Stability AI (for images)
STABILITY_API_KEY=your_stability_key

# Social Media APIs
TWITTER_API_KEY=your_twitter_key
TWITTER_API_SECRET=your_twitter_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_secret

INSTAGRAM_ACCESS_TOKEN=your_instagram_token
INSTAGRAM_APP_ID=your_instagram_app_id
INSTAGRAM_ACCOUNT_ID=your_instagram_account_id

LINKEDIN_ACCESS_TOKEN=your_linkedin_token

FACEBOOK_APP_ID=your_facebook_app_id
FACEBOOK_APP_SECRET=your_facebook_secret
FACEBOOK_PAGE_ACCESS_TOKEN=your_facebook_page_token
EOF
```

### Step 5: Test the Connection

```bash
# Test LLM connection
python3 -c "
import os
from dotenv import load_dotenv
import requests

load_dotenv()
endpoint = os.environ.get('LOCAL_LLM_ENDPOINT')
print(f'Testing endpoint: {endpoint}')

response = requests.post(
    endpoint,
    json={
        'model': 'meta-llama/Llama-2-7b-chat-hf',
        'messages': [
            {'role': 'user', 'content': 'Hello, test message'}
        ],
        'max_tokens': 50
    },
    timeout=30
)
print('Response:', response.json())
"
```

### Step 6: Set Up Daily Schedule (8:00 AM Eastern)

#### Option A: Using Cron

```bash
# Edit crontab
crontab -e

# Add this line (8:00 AM Eastern = 13:00 UTC in summer, 12:00 UTC in winter)
# Adjust for DST - you may want a script that handles timezone conversion
0 12 * * * cd ~/AGENT && source venv/bin/activate && python3 orchestrator.py >> /var/log/social-media-agent.log 2>&1
```

#### Option B: Using Cloud Scheduler (Recommended)

1. **Create a startup script** that runs the orchestrator:
```bash
# Create startup script
cat > ~/AGENT/run_daily.sh << 'EOF'
#!/bin/bash
cd ~/AGENT
source venv/bin/activate
python3 orchestrator.py
EOF

chmod +x ~/AGENT/run_daily.sh
```

2. **Create Cloud Scheduler job**:
```bash
# First, create a Cloud Function or use HTTP endpoint
# Or use gcloud to create a scheduled task
gcloud scheduler jobs create http daily-content-run \
  --schedule="0 8 * * *" \
  --time-zone="America/New_York" \
  --uri="http://YOUR_VM_IP:8080/run" \
  --http-method=POST
```

## Running the Application

### Test Run

```bash
# SSH into application VM
gcloud compute ssh social-media-agent --zone=us-central1-a

# Activate venv
source venv/bin/activate

# Test trend scanner
cd ~/AGENT
python3 run_trend_scanner.py

# Test content creator
python3 run_content_creator.py

# Run full orchestrator
python3 orchestrator.py
```

### Keep Application Running

Use `screen` or `tmux` to keep it running:

```bash
# Install screen
sudo apt-get install screen

# Start screen session
screen -S social-media-agent

# Run orchestrator
cd ~/AGENT
source venv/bin/activate
python3 orchestrator.py

# Detach: Ctrl+A then D
# Reattach: screen -r social-media-agent
```

## Environment Variables Summary

Required for your `.env` file:

```bash
# LLM Configuration (REQUIRED)
LOCAL_LLM_ENDPOINT=http://YOUR_LLM_VM_IP:8000/v1/chat/completions

# Optional LLM API key (if your endpoint requires it)
LOCAL_LLM_API_KEY=

# Image Generation
STABILITY_API_KEY=your_stability_key

# Social Media APIs
TWITTER_API_KEY=...
TWITTER_API_SECRET=...
TWITTER_ACCESS_TOKEN=...
TWITTER_ACCESS_TOKEN_SECRET=...

INSTAGRAM_ACCESS_TOKEN=...
INSTAGRAM_APP_ID=...
INSTAGRAM_ACCOUNT_ID=...

LINKEDIN_ACCESS_TOKEN=...

FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
FACEBOOK_PAGE_ACCESS_TOKEN=...
```

## Cost Optimization Tips

1. **Use Preemptible VMs** for LLM server (cheaper but can be stopped):
   ```bash
   --preemptible
   ```

2. **Use smaller models** for cost savings:
   - `microsoft/Phi-3-mini-4k-instruct` (3.8B parameters)
   - `mistralai/Mistral-7B-Instruct-v0.2` (7B parameters)

3. **Schedule LLM VM** to only run during posting hours (8:00-8:15 AM Eastern)

## Troubleshooting

### LLM Server Not Responding
```bash
# Check if vLLM is running
ps aux | grep vllm

# Check logs
journalctl -u vllm  # if running as service

# Test endpoint
curl http://localhost:8000/health
```

### Application Can't Connect to LLM
```bash
# Test from application VM
curl http://LLM_VM_IP:8000/v1/models

# Check firewall rules
gcloud compute firewall-rules list
```

## Next Steps

1. ✅ Set up LLM server VM
2. ✅ Deploy vLLM
3. ✅ Set up application VM
4. ✅ Configure environment variables
5. ✅ Test connections
6. ✅ Set up daily schedule
7. ✅ Monitor and optimize
