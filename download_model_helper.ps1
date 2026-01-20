# PowerShell script to help download model from GCP via SSH

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GCP Model Download Helper" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: List GCP instances
Write-Host "Step 1: Listing your GCP instances..." -ForegroundColor Yellow
Write-Host ""
gcloud compute instances list
Write-Host ""

# Get instance details
$instanceName = Read-Host "Enter instance name"
$zone = Read-Host "Enter zone (e.g., us-central1-a)"

# Step 2: Connect and find model
Write-Host ""
Write-Host "Step 2: Searching for model on instance..." -ForegroundColor Yellow
Write-Host "Run this command on the instance to find the model:" -ForegroundColor Yellow
Write-Host ""
Write-Host "  gcloud compute ssh $instanceName --zone=$zone --command='find ~ -name Elevaretinyllma -type d 2>/dev/null'" -ForegroundColor Green
Write-Host ""

$searchNow = Read-Host "Do you want to search now? (y/n)"
if ($searchNow -eq "y" -or $searchNow -eq "Y") {
    Write-Host "Searching for model..." -ForegroundColor Yellow
    gcloud compute ssh $instanceName --zone=$zone --command="find ~ -name Elevaretinyllma -type d 2>/dev/null | head -5"
}

# Step 3: Get model path
Write-Host ""
$modelPath = Read-Host "Enter the full path to Elevaretinyllma on the instance (e.g., /home/user/outputs/Elevaretinyllma)"

# Step 4: Create local directory
Write-Host ""
Write-Host "Step 3: Creating local models directory..." -ForegroundColor Yellow
if (-not (Test-Path "models")) {
    New-Item -ItemType Directory -Path "models" | Out-Null
    Write-Host "Created models directory" -ForegroundColor Green
}

# Step 5: Download
Write-Host ""
Write-Host "Step 4: Downloading model..." -ForegroundColor Yellow
Write-Host "This may take a while depending on model size..." -ForegroundColor Yellow
Write-Host ""

$download = Read-Host "Ready to download? (y/n)"
if ($download -eq "y" -or $download -eq "Y") {
    Write-Host "Downloading from $instanceName:$modelPath to ./models/Elevaretinyllma" -ForegroundColor Yellow
    gcloud compute scp --recurse "$instanceName`:$modelPath" "./models/Elevaretinyllma" --zone=$zone
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ Model downloaded successfully!" -ForegroundColor Green
        Write-Host ""
        
        # Get absolute path
        $absolutePath = (Resolve-Path ".\models\Elevaretinyllma").Path
        Write-Host "Model location: $absolutePath" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Set environment variable:" -ForegroundColor Yellow
        Write-Host "  `$env:PEFT_ADAPTER_PATH = `"$absolutePath`"" -ForegroundColor Green
        Write-Host ""
        Write-Host "Or add to your system environment variables permanently." -ForegroundColor Yellow
    } else {
        Write-Host ""
        Write-Host "✗ Download failed. Check the error above." -ForegroundColor Red
    }
} else {
    Write-Host ""
    Write-Host "To download manually, run:" -ForegroundColor Yellow
    Write-Host "  gcloud compute scp --recurse $instanceName`:$modelPath ./models/Elevaretinyllma --zone=$zone" -ForegroundColor Green
}
