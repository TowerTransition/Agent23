# GitHub Setup Guide for Agent23

## Step 1: Configure Git Identity

Before committing, you need to set your Git identity. Run these commands:

```powershell
# Set your name and email (replace with your actual info)
git config user.name "Your Name"
git config user.email "your.email@example.com"
```

Or set it globally for all repositories:
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

## Step 2: Create a New GitHub Repository

1. Go to https://github.com/new
2. Repository name: `Agent23` (or your preferred name)
3. Description: "AI Content Creation and Scheduling System"
4. Choose Public or Private
5. **DO NOT** initialize with README, .gitignore, or license (we already have these)
6. Click "Create repository"

## Step 3: Update Remote URL

The current remote points to `agent-22`. You need to either:

**Option A: Update to new repository**
```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/Agent23.git
```

**Option B: Remove old remote and add new one**
```powershell
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/Agent23.git
```

Replace `YOUR_USERNAME` with your GitHub username.

## Step 4: Commit and Push

After setting your Git identity, run:

```powershell
# Stage all files
git add .

# Create initial commit
git commit -m "Initial commit: Agent23 content creation and scheduling system"

# Push to GitHub
git push -u origin main
```

If you get authentication errors, you may need to:
- Use a Personal Access Token instead of password
- Set up SSH keys
- Use GitHub CLI (`gh auth login`)

## Step 5: Verify

Check that everything is pushed:
```powershell
git remote -v
git log --oneline
```

Visit your repository on GitHub to verify all files are there.

## Troubleshooting

### Authentication Issues
If you get authentication errors:
1. Generate a Personal Access Token: https://github.com/settings/tokens
2. Use the token as your password when pushing
3. Or set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### Branch Name Issues
If your branch is called `master` instead of `main`:
```powershell
git branch -M main
git push -u origin main
```

### Large Files
If you have large files (models, etc.), they should be in `.gitignore`. If you need to track them, consider using Git LFS:
```powershell
git lfs install
git lfs track "*.safetensors"
git add .gitattributes
```
