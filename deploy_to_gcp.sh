#!/bin/bash
# Google Cloud Deployment Script
# This script helps deploy the social media agent to Google Cloud

set -e

echo "=========================================="
echo "Google Cloud Deployment Script"
echo "=========================================="

# Configuration
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
ZONE=${GCP_ZONE:-"us-central1-a"}
APP_VM_NAME="social-media-agent"
LLM_VM_NAME="llm-server"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Step 1: Setting up Google Cloud project...${NC}"
gcloud config set project $PROJECT_ID

echo -e "${YELLOW}Step 2: Creating application VM...${NC}"
gcloud compute instances create $APP_VM_NAME \
  --zone=$ZONE \
  --machine-type=e2-medium \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size=20GB \
  --tags=http-server,https-server

echo -e "${YELLOW}Step 3: Transferring code to VM...${NC}"
gcloud compute scp --recurse . $APP_VM_NAME:~/AGENT --zone=$ZONE

echo -e "${YELLOW}Step 4: Setting up application on VM...${NC}"
gcloud compute ssh $APP_VM_NAME --zone=$ZONE --command="
cd ~/AGENT
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
echo 'Setup complete!'
"

echo -e "${GREEN}Deployment complete!${NC}"
echo ""
echo "Next steps:"
echo "1. SSH into the VM: gcloud compute ssh $APP_VM_NAME --zone=$ZONE"
echo "2. Set up your .env file with LOCAL_LLM_ENDPOINT and API keys"
echo "3. Test the connection to your LLM server"
echo "4. Set up cron or Cloud Scheduler for 8:00 AM Eastern daily runs"

