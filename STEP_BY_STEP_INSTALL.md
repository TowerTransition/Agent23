# Step-by-Step Installation Guide

## Step 1: SSH Into Your Google Cloud Instance

From your local machine (PowerShell), run:

```powershell
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a
```

**Expected output:** You should see a prompt like:
```
username@instance-20260103-165047:~$
```

---

## Step 2: Update System Packages

Once you're SSH'd into the instance, run:

```bash
sudo apt-get update
```

**Expected output:** You'll see package lists being updated.

Then:

```bash
sudo apt-get install -y python3-pip python3-venv git curl wget
```

**Expected output:** Packages will be installed. This may take 1-2 minutes.

---

## Step 3: Check If Code Was Transferred

```bash
ls -la ~/AGENT
```

**If the directory exists:** You should see files like `orchestrator.py`, `requirements.txt`, etc.

**If the directory doesn't exist:** You need to transfer the code first. Go back to your local machine and run:
```powershell
gcloud compute scp --recurse . instance-20260103-165047:~/AGENT --zone=us-central1-a
```

Then come back to this step.

---

## Step 4: Navigate to Code Directory

```bash
cd ~/AGENT
pwd
```

**Expected output:** `/home/YOUR_USERNAME/AGENT`

---

## Step 5: Create Python Virtual Environment

```bash
python3 -m venv venv
```

**Expected output:** Virtual environment created (takes a few seconds)

---

## Step 6: Activate Virtual Environment

```bash
source venv/bin/activate
```

**Expected output:** Your prompt should now show `(venv)` at the beginning:
```
(venv) username@instance-20260103-165047:~/AGENT$
```

---

## Step 7: Upgrade pip

```bash
pip install --upgrade pip
```

**Expected output:** pip will be upgraded to the latest version.

---

## Step 8: Install Python Dependencies

```bash
pip install -r requirements.txt
```

**Expected output:** This will take 2-5 minutes. You'll see packages being downloaded and installed:
- python-dotenv
- requests
- tweepy
- pytz
- APScheduler
- etc.

**If you see errors:** Let me know what the error message says.

---

## Step 9: Create Logs Directory

```bash
mkdir -p logs
ls -la logs
```

**Expected output:** Empty logs directory created.

---

## Step 10: Create .env File Template

```bash
cat > .env << 'EOF'
# Local LLM Configuration
LOCAL_LLM_ENDPOINT=http://localhost:8000/v1/chat/completions
LOCAL_LLM_API_KEY=not-needed-for-local

# Social Media API Keys (REPLACE WITH YOUR ACTUAL KEYS)
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
EOF
```

**Expected output:** File created silently.

Verify it was created:
```bash
ls -la .env
cat .env
```

---

## Step 11: Test Python Setup

```bash
python3 -c "
import sys
print(f'Python version: {sys.version}')
try:
    import dotenv
    import requests
    print('✓ Core dependencies installed')
except ImportError as e:
    print(f'✗ Missing dependency: {e}')
"
```

**Expected output:**
```
Python version: 3.x.x
✓ Core dependencies installed
```

---

## Step 12: Verify Code Structure

```bash
ls -la
python3 -c "import sys; sys.path.insert(0, '.'); from agents.trend_scanner.agent import TrendScannerAgent; print('✓ Agents can be imported')"
```

**Expected output:** `✓ Agents can be imported`

---

## ✅ Installation Complete!

At this point, you should have:
- ✅ Python 3 installed
- ✅ Virtual environment created and activated
- ✅ All dependencies installed
- ✅ `.env` file created
- ✅ Logs directory created
- ✅ Code structure verified

---

## Next Steps:

1. **Set up your LLM** (Ollama or GPU instance)
2. **Edit `.env` file** with your API keys
3. **Test the system**

Tell me when you're ready for the next step, or if you encounter any errors!

