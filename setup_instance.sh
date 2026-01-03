#!/bin/bash
# Setup script to run on your Google Cloud instance
# Run this after transferring code to the instance

set -e

echo "=========================================="
echo "Setting up Social Media Agent on GCP"
echo "=========================================="

# Update system
echo "Step 1: Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git curl wget

# Navigate to code directory
if [ ! -d ~/AGENT ]; then
    echo "Error: ~/AGENT directory not found!"
    echo "Please transfer your code first using:"
    echo "  gcloud compute scp --recurse . instance-20260103-165047:~/AGENT --zone=us-central1-a"
    exit 1
fi

cd ~/AGENT

# Create virtual environment
echo "Step 2: Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
echo "Step 3: Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Step 4: Installing Python dependencies..."
pip install -r requirements.txt

# Create logs directory
echo "Step 5: Creating logs directory..."
mkdir -p logs

# Create .env template if it doesn't exist
if [ ! -f .env ]; then
    echo "Step 6: Creating .env template..."
    cat > .env << 'EOF'
# Local LLM Configuration
# Will try OpenAI-compatible endpoint first, auto-fallback to native API if needed
LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions
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
    echo "Created .env template. Please edit it with your actual API keys:"
    echo "  nano ~/AGENT/.env"
else
    echo "Step 6: .env file already exists, skipping template creation"
fi

# Test Python setup
echo "Step 7: Testing Python setup..."
python3 -c "
import sys
print(f'Python version: {sys.version}')
try:
    import dotenv
    import requests
    print('✓ Core dependencies installed')
except ImportError as e:
    print(f'✗ Missing dependency: {e}')
    sys.exit(1)
"

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   nano ~/AGENT/.env"
echo ""
echo "2. Choose your LLM setup:"
echo "   - Option A: Set up Ollama with TinyLlama 1.1B (Recommended):"
echo "     curl -fsSL https://ollama.com/install.sh | sh"
echo "     ollama pull tinyllama"
echo "     ollama serve"
echo "     # Then set LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions"
echo "   - See SETUP_TINYLLAMA.md for detailed instructions"
echo ""
echo "   - Option B: Create separate GPU instance for vLLM (see SETUP_GCP_INSTANCE.md)"
echo ""
echo "3. Test the setup:"
echo "   cd ~/AGENT"
echo "   source venv/bin/activate"
echo "   python run_trend_scanner.py"
echo ""
echo "4. Set up automated scheduling (see SETUP_GCP_INSTANCE.md)"
echo ""

