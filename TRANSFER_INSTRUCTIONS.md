# How to Transfer Code to Google Cloud Instance

## The Issue
You're trying to run `gcloud compute scp` from inside the SSH session, but it needs to run from your **local Windows machine**.

## Solution: Transfer from Local Machine

### Step 1: Exit the SSH Session
If you're currently SSH'd into the instance, type:
```bash
exit
```

You should be back at your local PowerShell prompt:
```
PS C:\Users\Administrator\Desktop\AGENT>
```

### Step 2: Transfer Code from Local Machine
From your local PowerShell (in the AGENT directory), run:

```powershell
gcloud compute scp --recurse . instance-20260103-165047:~/AGENT --zone=us-central1-a
```

**Note:** If you get authentication errors, you may need to:
1. Authenticate with gcloud: `gcloud auth login`
2. Set your project: `gcloud config set project YOUR_PROJECT_ID`

### Step 3: SSH Back Into Instance
After transfer completes, SSH back in:
```powershell
gcloud compute ssh instance-20260103-165047 --zone=us-central1-a
```

### Step 4: Verify Code Was Transferred
Once back in the instance:
```bash
ls -la ~/AGENT
```

You should see your files (orchestrator.py, requirements.txt, etc.)

---

## Alternative: If Code is Already There

If you've already transferred the code (or want to check), you can proceed directly with setup:

```bash
cd ~/AGENT
ls -la
```

If you see your files, skip the transfer and go straight to the setup steps.

