#!/bin/bash
# Script to run on GCP instance via SSH to find the model

echo "=========================================="
echo "Searching for Elevaretinyllma model..."
echo "=========================================="

# Search in common locations
echo ""
echo "1. Searching in home directory..."
find ~ -name "Elevaretinyllma" -type d 2>/dev/null | head -10

echo ""
echo "2. Searching for adapter files..."
find ~ -name "adapter_model.safetensors" 2>/dev/null | head -10
find ~ -name "adapter_config.json" 2>/dev/null | head -10

echo ""
echo "3. Checking common output directories..."
for dir in ~/outputs ~/checkpoints ~/models ~/training ~/wandb; do
    if [ -d "$dir" ]; then
        echo "Checking: $dir"
        find "$dir" -name "*Elevaretinyllma*" -o -name "*adapter*" 2>/dev/null | head -5
    fi
done

echo ""
echo "4. Checking current directory and subdirectories..."
find . -maxdepth 3 -name "*Elevaretinyllma*" -o -name "*adapter*" 2>/dev/null | head -10

echo ""
echo "=========================================="
echo "If you found the model, note the full path"
echo "Then download using:"
echo "  gcloud compute scp --recurse INSTANCE:/path/to/Elevaretinyllma ./models/ --zone=ZONE"
echo "=========================================="
