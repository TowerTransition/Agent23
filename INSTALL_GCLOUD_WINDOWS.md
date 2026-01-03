# Installing Google Cloud SDK on Windows

## Option 1: Install Google Cloud SDK (Recommended)

### Step 1: Download Google Cloud SDK
1. Go to: https://cloud.google.com/sdk/docs/install-sdk#windows
2. Download the installer for Windows
3. Run the installer and follow the prompts

### Step 2: Restart PowerShell
After installation, close and reopen PowerShell to refresh the PATH.

### Step 3: Initialize gcloud
```powershell
gcloud init
```

This will:
- Log you in
- Set your default project
- Configure your credentials

### Step 4: Verify Installation
```powershell
gcloud --version
```

---

## Option 2: Use Google Cloud Console (No Installation Needed)

You can transfer files directly through the Google Cloud Console:

1. Go to: https://console.cloud.google.com/compute/instances
2. Find your instance: `instance-20260103-165047`
3. Click **SSH** button (opens browser-based SSH)
4. In the SSH window, you can:
   - Use the upload button to transfer files
   - Or use the built-in file browser

---

## Option 3: Use Git (If Your Code is in a Repository)

If your code is in a Git repository (GitHub, GitLab, etc.):

### On the Google Cloud Instance (via SSH):
```bash
# Install git if not already installed
sudo apt-get install -y git

# Clone your repository
cd ~
git clone YOUR_REPO_URL AGENT

# Or if you have SSH access to the repo
git clone git@github.com:YOUR_USERNAME/YOUR_REPO.git AGENT
```

---

## Option 4: Use WinSCP or FileZilla (GUI Method)

1. Download WinSCP: https://winscp.net/eng/download.php
2. Connect to your instance:
   - Host: Your instance's external IP
   - Username: `amaziahy80` (or your username)
   - Use your SSH key for authentication
3. Drag and drop files from local to remote

---

## Option 5: Manual File Transfer via SSH

If you have SSH access, you can manually copy files:

### On your local machine (if you have SCP):
```powershell
# Get your instance's external IP first
# Then use SCP (if available)
scp -r . amaziahy80@INSTANCE_IP:~/AGENT
```

---

## Quick Check: Is gcloud Already Installed?

Try these commands to see if gcloud is installed but not in PATH:

```powershell
# Check common installation locations
Test-Path "C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
Test-Path "$env:USERPROFILE\AppData\Local\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"

# If found, add to PATH temporarily:
$env:PATH += ";C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin"
```

---

## Recommended: Use Google Cloud Console SSH

The easiest method without installing anything:
1. Go to Google Cloud Console
2. Click SSH on your instance
3. Use the file upload feature in the browser SSH window

