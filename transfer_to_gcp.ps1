# PowerShell script to transfer code to Google Cloud instance
# Run this from your local Windows machine

$INSTANCE_NAME = "instance-20260103-165047"
$ZONE = "us-central1-a"
$REMOTE_PATH = "~/AGENT"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Transferring code to Google Cloud" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is installed
try {
    $gcloudVersion = gcloud --version 2>&1
    Write-Host "✓ gcloud CLI found" -ForegroundColor Green
} catch {
    Write-Host "✗ gcloud CLI not found. Please install it first:" -ForegroundColor Red
    Write-Host "  https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Check if we're in the right directory
if (-not (Test-Path "orchestrator.py")) {
    Write-Host "✗ Error: orchestrator.py not found in current directory" -ForegroundColor Red
    Write-Host "Please run this script from the AGENT directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "Transferring files to instance..." -ForegroundColor Yellow
Write-Host "Instance: $INSTANCE_NAME" -ForegroundColor Gray
Write-Host "Zone: $ZONE" -ForegroundColor Gray
Write-Host ""

# Transfer code
gcloud compute scp --recurse . "${INSTANCE_NAME}:${REMOTE_PATH}" --zone=$ZONE

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Code transferred successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. SSH into your instance:" -ForegroundColor White
    Write-Host "   gcloud compute ssh $INSTANCE_NAME --zone=$ZONE" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "2. Run the setup script:" -ForegroundColor White
    Write-Host "   cd ~/AGENT" -ForegroundColor Yellow
    Write-Host "   bash setup_instance.sh" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "✗ Transfer failed. Please check:" -ForegroundColor Red
    Write-Host "  - Instance name is correct" -ForegroundColor Yellow
    Write-Host "  - You have permission to access the instance" -ForegroundColor Yellow
    Write-Host "  - Instance is running" -ForegroundColor Yellow
}

