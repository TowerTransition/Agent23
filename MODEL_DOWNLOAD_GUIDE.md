# Downloading Model from Google Cloud

## Step 1: Authenticate with Google Cloud

```powershell
# Login to Google Cloud
gcloud auth login

# Set your project (if needed)
gcloud config set project YOUR_PROJECT_ID
```

## Step 2: Find Your Model in Google Cloud Storage

### Option A: Using Google Cloud Console (Easiest)

1. Go to: https://console.cloud.google.com/storage
2. Browse your buckets
3. Look for:
   - Folders named `Elevaretinyllma`
   - Files named `adapter_model.safetensors` or `adapter_config.json`
   - Training output directories

### Option B: Using gcloud CLI

```powershell
# List all buckets
gcloud storage buckets list

# List contents of a specific bucket
gcloud storage ls gs://YOUR_BUCKET_NAME/

# Search for model files recursively
gcloud storage ls gs://YOUR_BUCKET_NAME/**/*Elevaretinyllma*
gcloud storage ls gs://YOUR_BUCKET_NAME/**/*adapter*
```

## Step 3: Download the Model

Once you find the model path (e.g., `gs://my-bucket/training-output/Elevaretinyllma`):

```powershell
# Create local models directory
mkdir models

# Download the entire model directory
gcloud storage cp -r gs://YOUR_BUCKET_NAME/path/to/Elevaretinyllma ./models/Elevaretinyllma
```

## Step 4: Verify Model Files

The downloaded directory should contain:
```
Elevaretinyllma/
├── adapter_config.json
├── adapter_model.safetensors
├── tokenizer.json (optional)
├── tokenizer_config.json (optional)
└── special_tokens_map.json (optional)
```

## Step 5: Set Environment Variable

After downloading, set the path:

```powershell
# Set the path to your downloaded model
$env:PEFT_ADAPTER_PATH = "C:\Users\Administrator\Desktop\Agent23\models\Elevaretinyllma"
```

Or add to your system environment variables permanently.

## Common Locations in Google Cloud

Models are often stored in:
- `gs://YOUR_BUCKET/training-output/`
- `gs://YOUR_BUCKET/models/`
- `gs://YOUR_BUCKET/checkpoints/`
- `gs://YOUR_BUCKET/artifacts/`

## Using the Helper Script

Run the Python helper script:

```powershell
python download_model_from_gc.py
```

This will guide you through finding and downloading the model.

## Important Notes

⚠️ **Model files are LARGE** (can be 100MB - several GB)
- Do NOT commit model files directly to GitHub
- Use Git LFS if you need version control for models
- Or keep models local and document the GCS path

## Git LFS Setup (Optional)

If you want to track models in Git:

```powershell
# Install Git LFS
git lfs install

# Track model files
git lfs track "*.safetensors"
git lfs track "*.bin"
git add .gitattributes

# Then add and commit models
git add models/
git commit -m "Add trained model files"
```

However, **recommended approach**: Keep models in Google Cloud Storage and document the path in your code/docs.
