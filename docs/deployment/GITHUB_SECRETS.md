# GitHub Secrets Configuration

## Automated Setup (Recommended)

Run this command to automatically set all secrets:
```bash
python3 deployment/set_github_secrets.py
```

This script will:
- Read your GitHub PAT from .env file
- Extract the deployment token from your VM
- Set all required secrets automatically

## Manual Setup

If you prefer to set secrets manually, add these to your GitHub repository:
https://github.com/canaanhowell/ph-app/settings/secrets/actions

## Required Secrets

### VM_DEPLOY_TOKEN
```
1f7489c19846d550bbe35aedd7642f3ad87466c843e15f0f5bac5412ae912746
```

### VM_DEPLOY_WEBHOOK_URL
```
http://134.199.201.56:8080/deploy
```

### VM_HEALTH_CHECK_URL
```
http://134.199.201.56:8080/health
```

## How to Add Secrets

1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with the exact name and value above

## VM Token Configuration

The deployment service requires two token files on the VM:

### Deployment Token File
Located at `/root/ph_app/.deploy_token`
- Contains the VM deployment token for webhook authentication
- Must match the VM_DEPLOY_TOKEN secret in GitHub

### GitHub Token File
Located at `/root/ph_app/.github_token`
- Contains your GitHub Personal Access Token for artifact downloads
- Required for proper CI/CD deployment (prevents fallback to local copy)
- Create a PAT with `repo` scope at https://github.com/settings/tokens

To create these files on the VM:
```bash
echo "YOUR_DEPLOYMENT_TOKEN" > /root/ph_app/.deploy_token
echo "github_pat_YOUR_TOKEN_HERE" > /root/ph_app/.github_token
chmod 600 /root/ph_app/.deploy_token
chmod 600 /root/ph_app/.github_token
```

Note: Without these token files, the deployment service won't authenticate properly or download artifacts from GitHub.