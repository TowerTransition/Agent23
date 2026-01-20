# Downloading Model from Google Cloud via SSH

## Step 1: Connect to Your GCP Instance

```powershell
# Connect via SSH (replace with your instance details)
gcloud compute ssh INSTANCE_NAME --zone=ZONE

# Or if you have the IP and SSH key
ssh -i ~/.ssh/gcp_key user@INSTANCE_IP
```

## Step 2: Find the Model on the Instance

Once connected via SSH, search for the model:

```bash
# Search for the model directory
find ~ -name "Elevaretinyllma" -type d 2>/dev/null
find /home -name "Elevaretinyllma" -type d 2>/dev/null
find / -name "adapter_model.safetensors" 2>/dev/null

# Search in common training output locations
ls -la ~/outputs/
ls -la ~/checkpoints/
ls -la ~/models/
ls -la ~/training/
ls -la ~/wandb/  # If using Weights & Biases

# Check if model is in a specific project directory
ls -la ~/projects/
ls -la ~/workspace/
```

## Step 3: Verify Model Files

Once you find the directory, verify it contains the required files:

```bash
cd /path/to/Elevaretinyllma
ls -lh

# Should see:
# - adapter_config.json
# - adapter_model.safetensors
# - (optional) tokenizer files
```

## Step 4: Download from GCP Instance to Local Machine

### Option A: Using SCP (from your local Windows machine)

```powershell
# Create local models directory
mkdir models

# Download the entire model directory
scp -r user@INSTANCE_IP:/path/to/Elevaretinyllma ./models/

# Or if using gcloud compute scp
gcloud compute scp --recurse INSTANCE_NAME:/path/to/Elevaretinyllma ./models/ --zone=ZONE
```

### Option B: Using gcloud compute scp (Recommended)

```powershell
# Download from GCP instance
gcloud compute scp --recurse INSTANCE_NAME:/path/to/Elevaretinyllma ./models/Elevaretinyllma --zone=ZONE

# Example:
# gcloud compute scp --recurse my-training-vm:/home/user/outputs/Elevaretinyllma ./models/Elevaretinyllma --zone=us-central1-a
```

### Option C: Compress First, Then Download (Faster for large files)

On the GCP instance:
```bash
# Create a compressed archive
cd /path/to/parent/directory
tar -czf Elevaretinyllma.tar.gz Elevaretinyllma/
```

Then from your local machine:
```powershell
# Download the compressed file
gcloud compute scp INSTANCE_NAME:/path/to/Elevaretinyllma.tar.gz ./models/ --zone=ZONE

# Extract locally
cd models
tar -xzf Elevaretinyllma.tar.gz
```

## Step 5: Verify Download

```powershell
# Check the downloaded model
ls models/Elevaretinyllma/

# Should see:
# - adapter_config.json
# - adapter_model.safetensors
```

## Step 6: Set Environment Variable

```powershell
# Get the full absolute path
$fullPath = (Resolve-Path ".\models\Elevaretinyllma").Path

# Set environment variable
$env:PEFT_ADAPTER_PATH = $fullPath

# Verify
echo $env:PEFT_ADAPTER_PATH
```

## Common Locations on GCP Instances

Models are often stored in:
- `~/outputs/Elevaretinyllma/`
- `~/checkpoints/Elevaretinyllma/`
- `~/models/Elevaretinyllma/`
- `~/training/outputs/Elevaretinyllma/`
- `~/wandb/run-*/files/Elevaretinyllma/`
- `/tmp/Elevaretinyllma/` (temporary, might be deleted)

## Quick Commands Reference

```powershell
# 1. List your GCP instances
gcloud compute instances list

# 2. Connect to instance
gcloud compute ssh INSTANCE_NAME --zone=ZONE

# 3. Find model (on instance)
find ~ -name "*adapter*" -o -name "Elevaretinyllma"

# 4. Download model (from local machine)
gcloud compute scp --recurse INSTANCE_NAME:/path/to/model ./models/ --zone=ZONE

# 5. Set path
$env:PEFT_ADAPTER_PATH = "C:\Users\Administrator\Desktop\Agent23\models\Elevaretinyllma"
```

## Troubleshooting

### Permission Denied
```bash
# On GCP instance, check permissions
ls -la /path/to/Elevaretinyllma
chmod -R 755 /path/to/Elevaretinyllma  # If needed
```

### File Not Found
- Check if the model directory exists
- Verify the exact path (case-sensitive)
- Check if model was saved with a different name

### Large File Download
- Use compression (tar.gz) for faster transfer
- Consider using `rsync` for resumable downloads
- Check your network connection
