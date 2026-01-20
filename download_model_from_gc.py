"""
Script to help locate and download the trained PEFT model from Google Cloud Storage.

This script helps you:
1. List available buckets
2. Search for model files
3. Download the model to local directory
"""

import subprocess
import os
import sys
from pathlib import Path

def run_gcloud_command(cmd):
    """Run a gcloud command and return output."""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Error output: {e.stderr}")
        return None

def list_buckets():
    """List all Google Cloud Storage buckets."""
    print("Listing Google Cloud Storage buckets...")
    output = run_gcloud_command("gcloud storage buckets list")
    if output:
        print(output)
        return output
    else:
        print("Could not list buckets. Make sure you're authenticated:")
        print("  gcloud auth login")
        return None

def search_for_model_files(bucket_name=None, search_term="Elevaretinyllma"):
    """Search for model files in GCS."""
    if bucket_name:
        print(f"\nSearching for '{search_term}' in bucket: {bucket_name}")
        # List objects in bucket
        cmd = f"gcloud storage ls gs://{bucket_name}/**/*{search_term}*"
        output = run_gcloud_command(cmd)
        if output:
            print(output)
            return output
    else:
        print("\nSearching all buckets for model files...")
        # This is more complex - would need to iterate through buckets
        print("Please specify a bucket name to search")
    return None

def download_model(gcs_path, local_path):
    """Download model from GCS to local path."""
    print(f"\nDownloading from: {gcs_path}")
    print(f"To local path: {local_path}")
    
    # Create local directory if it doesn't exist
    os.makedirs(os.path.dirname(local_path) if os.path.dirname(local_path) else ".", exist_ok=True)
    
    # Download using gcloud storage cp
    cmd = f"gcloud storage cp -r {gcs_path} {local_path}"
    output = run_gcloud_command(cmd)
    
    if output is not None:
        print(f"\n✓ Model downloaded successfully to: {local_path}")
        return True
    else:
        print("\n✗ Download failed")
        return False

def main():
    print("=" * 60)
    print("Google Cloud Model Downloader")
    print("=" * 60)
    
    # Check if gcloud is installed
    gcloud_check = run_gcloud_command("gcloud --version")
    if not gcloud_check:
        print("ERROR: gcloud CLI is not installed or not in PATH")
        print("Install it from: https://cloud.google.com/sdk/docs/install")
        return
    
    print("\n1. Listing available buckets...")
    buckets = list_buckets()
    
    if not buckets:
        print("\nNo buckets found or authentication required.")
        print("Please run: gcloud auth login")
        return
    
    print("\n" + "=" * 60)
    print("Manual Steps:")
    print("=" * 60)
    print("\nIf you know the bucket and path, you can download directly:")
    print("\n  gcloud storage ls gs://YOUR_BUCKET_NAME/**/Elevaretinyllma*")
    print("\n  gcloud storage cp -r gs://YOUR_BUCKET_NAME/path/to/Elevaretinyllma ./models/")
    print("\nOr use the interactive mode below:")
    
    # Interactive mode
    print("\n" + "=" * 60)
    bucket = input("\nEnter bucket name (or press Enter to skip): ").strip()
    
    if bucket:
        search_for_model_files(bucket)
        
        gcs_path = input("\nEnter full GCS path to model (e.g., gs://bucket/path/to/Elevaretinyllma): ").strip()
        if gcs_path:
            local_path = input("Enter local path to save (default: ./models/Elevaretinyllma): ").strip()
            if not local_path:
                local_path = "./models/Elevaretinyllma"
            
            download_model(gcs_path, local_path)
        else:
            print("\nTo download manually, use:")
            print("  gcloud storage cp -r gs://BUCKET/PATH/TO/MODEL ./models/")
    else:
        print("\nTo find your model:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/storage")
        print("2. Browse your buckets")
        print("3. Look for folders containing 'Elevaretinyllma' or adapter files")
        print("4. Copy the gs:// path")
        print("5. Run: gcloud storage cp -r gs://BUCKET/PATH ./models/")

if __name__ == "__main__":
    main()
