# Google Cloud Instance Setup Guide

## Your Instance Details
- **Name**: `instance-20260103-165047`
- **Zone**: `us-central1-a`
- **Machine Type**: `e2-standard-4` (4 vCPUs, 16 GB Memory)
- **OS**: Debian 12 Bookworm
- **Status**: Running

## Step 1: Transfer Code to Your Instance

### Option A: Using gcloud (Recommended)
```bash
# From your local machine (Windows PowerShell)
gcloud compute scp --recurse . instance-20260103-165047:~/AGENT --zone=us-central1-a
```

### Option B: Using Git (If code is in a repository)
```bash
# SSH into instance
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a

# On the instance, clone your repo
git clone <your-repo-url> ~/AGENT
cd ~/AGENT
```

## Step 2: Set Up Python Environment on Instance

SSH into your instance:
```bash
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a
```

Then run these commands on the instance:
```bash
# Update system
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git curl

# Navigate to your code
cd ~/AGENT

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Choose Your LLM Setup

### Option A: Use a Separate GPU Instance for LLM (Recommended for Performance)

Create a GPU instance for the LLM:
```bash
# Create GPU instance for LLM server
gcloud compute instances create llm-server \
  --zone=us-central1-a \
  --machine-type=n1-standard-4 \
  --accelerator=type=nvidia-tesla-t4,count=1 \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=100GB \
  --maintenance-policy=TERMINATE
```

Then set up vLLM on the GPU instance (see `setup_llm_server.sh`).

### Option B: Use CPU-Based LLM on Current Instance (Slower but Works)

Your current instance has no GPU, but you can run smaller models on CPU:

**Option B1: Use Ollama (Easiest)**
```bash
# On your instance
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2:7b  # or mistral:7b, llama3:8b
ollama serve  # Runs on port 11434
```

**Option B2: Use Hugging Face Transformers (More Control)**
```bash
# Install transformers
pip install transformers torch

# Run a simple API server (see setup_cpu_llm.py)
```

### Option C: Use Managed LLM Service
- **Google Cloud Vertex AI**: Use Gemini or other models
- **Hugging Face Inference API**: Pay-per-use
- **Replicate API**: Simple API for various models

## Step 4: Configure Environment Variables

On your instance, create `.env` file:
```bash
cd ~/AGENT
nano .env
```

Add these variables:
```env
# Local LLM Configuration
LOCAL_LLM_ENDPOINT=http://YOUR_LLM_IP:8000/v1/chat/completions
# For Ollama: http://localhost:11434/v1/chat/completions
# For vLLM on separate VM: http://LLM_VM_IP:8000/v1/chat/completions
LOCAL_LLM_API_KEY=not-needed-for-local  # or your API key if required

# Social Media API Keys
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token

INSTAGRAM_ACCESS_TOKEN=your_instagram_token
INSTAGRAM_APP_ID=your_instagram_app_id
INSTAGRAM_APP_SECRET=your_instagram_app_secret

LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token

FACEBOOK_ACCESS_TOKEN=your_facebook_token
FACEBOOK_PAGE_ID=your_facebook_page_id

# Image Generation
STABILITY_API_KEY=your_stability_api_key

# Brand Guidelines
BRAND_GUIDELINES_PATH=agents/content_creator/example_brand_guidelines.json
```

## Step 5: Test the Setup

### Test LLM Connection
```bash
cd ~/AGENT
source venv/bin/activate
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
endpoint = os.getenv('LOCAL_LLM_ENDPOINT')
print(f'LLM Endpoint: {endpoint}')
"
```

### Test Trend Scanner
```bash
python run_trend_scanner.py
```

### Test Content Creator
```bash
python run_content_creator.py
```

## Step 6: Set Up Automated Scheduling

### Option A: Using systemd (Recommended)
```bash
# Create systemd service
sudo nano /etc/systemd/system/social-media-agent.service
```

Add this content:
```ini
[Unit]
Description=Social Media Agent - Daily Content Posting
After=network.target

[Service]
Type=oneshot
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME/AGENT
Environment="PATH=/home/YOUR_USERNAME/AGENT/venv/bin"
ExecStart=/home/YOUR_USERNAME/AGENT/venv/bin/python /home/YOUR_USERNAME/AGENT/orchestrator.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Create a timer for 8:00 AM Eastern:
```bash
sudo nano /etc/systemd/system/social-media-agent.timer
```

Add:
```ini
[Unit]
Description=Run Social Media Agent Daily at 8:00 AM Eastern

[Timer]
OnCalendar=*-*-* 13:00:00  # 8:00 AM Eastern = 13:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
```

Enable and start:
```bash
sudo systemctl enable social-media-agent.timer
sudo systemctl start social-media-agent.timer
sudo systemctl status social-media-agent.timer
```

### Option B: Using Cron
```bash
crontab -e
```

Add this line (8:00 AM Eastern = 13:00 UTC):
```cron
0 13 * * * cd /home/YOUR_USERNAME/AGENT && /home/YOUR_USERNAME/AGENT/venv/bin/python orchestrator.py >> /home/YOUR_USERNAME/AGENT/logs/cron.log 2>&1
```

## Step 7: Monitor and Logs

### View Logs
```bash
# Application logs
tail -f ~/AGENT/logs/*.log

# Systemd service logs
sudo journalctl -u social-media-agent.service -f

# Cron logs
tail -f ~/AGENT/logs/cron.log
```

### Check Status
```bash
# Check if service is running
sudo systemctl status social-media-agent.timer

# List scheduled jobs
sudo systemctl list-timers
```

## Troubleshooting

### LLM Connection Issues
```bash
# Test LLM endpoint
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama2","messages":[{"role":"user","content":"Hello"}]}'
```

### Python Import Errors
```bash
# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

### Permission Issues
```bash
# Fix file permissions
chmod +x ~/AGENT/*.py
chmod 644 ~/AGENT/.env
```

## Next Steps

1. ✅ Code transferred to instance
2. ✅ Python environment set up
3. ⏳ Choose and set up LLM (GPU instance or CPU-based)
4. ⏳ Configure `.env` with API keys
5. ⏳ Test all components
6. ⏳ Set up automated scheduling
7. ⏳ Monitor first automated run

## Quick Reference Commands

```bash
# SSH into instance
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a

# Transfer files
gcloud compute scp file.txt instance-20260103-165047:~/AGENT/ --zone=us-central1-a

# Get instance IP
gcloud compute instances describe instance-20260103-165047 --zone=us-central1-a --format='get(networkInterfaces[0].accessConfigs[0].natIP)'

# Stop instance
gcloud compute instances stop instance-20260103-165047 --zone=us-central1-a

# Start instance
gcloud compute instances start instance-20260103-165047 --zone=us-central1-a
```

