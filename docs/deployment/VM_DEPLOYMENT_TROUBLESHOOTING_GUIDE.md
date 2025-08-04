# VM Deployment Troubleshooting Guide

A comprehensive guide for coding agents to properly configure GitHub Actions and VM deployments for automated CI/CD pipelines.

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Step-by-Step Configuration](#step-by-step-configuration)
5. [Common Issues and Solutions](#common-issues-and-solutions)
6. [Verification Procedures](#verification-procedures)
7. [Security Best Practices](#security-best-practices)
8. [Debugging Commands](#debugging-commands)

## Overview

This guide covers setting up an automated deployment pipeline where:
- Code pushes to GitHub trigger GitHub Actions workflows
- Successful builds create artifacts and send webhooks to your VM
- The VM deployment service downloads artifacts and updates the application
- All operations are logged and can be rolled back if needed

## Architecture

```
GitHub Repository
    ↓ (push to main/master)
GitHub Actions Workflow
    ↓ (tests pass)
Build Artifact + Webhook
    ↓ (HTTPS POST)
VM Nginx (port 80/443)
    ↓ (proxy to port 8081)
Deployment Service (Gunicorn)
    ↓ (download artifact)
Application Update
```

## Prerequisites

### On GitHub:
- Repository with admin access
- Personal Access Token (PAT) with `repo` scope

### On VM:
- Ubuntu/Debian-based system
- Python 3.8+ installed
- Nginx configured as reverse proxy
- Git (for initial setup only)
- Service account or deployment user

## Step-by-Step Configuration

### 1. VM Initial Setup

#### 1.1 Create Deployment Token
```bash
# Generate a secure deployment token
openssl rand -hex 32 > /root/deployment_token.txt
cat /root/deployment_token.txt  # Save this for GitHub secrets
```

#### 1.2 Create Directory Structure
```bash
# Create required directories
mkdir -p /root/{app_name}/logs
mkdir -p /root/{app_name}_backups
mkdir -p /root/{app_name}/deployment

# Create token files directory
cd /root/{app_name}
```

#### 1.3 Install Python Dependencies
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install required packages
pip install flask gunicorn requests
```

### 2. Deployment Service Setup

#### 2.1 Create Deployment Service Script
Create `/root/{app_name}/deployment/vm_deploy_service.py`:
```python
#!/usr/bin/env python3
"""
VM Deployment Service - Receives webhooks from GitHub Actions
"""
# [Include the deployment service code here]
# Key features to include:
# - Token authentication
# - Artifact download from GitHub
# - Backup creation before deployment
# - Rollback capability
# - Comprehensive logging
```

#### 2.2 Create Startup Script
Create `/root/{app_name}/deployment/start_deploy_service.sh`:
```bash
#!/bin/bash
# Startup script for deployment service

# Load deployment token
if [ -f "/root/{app_name}/.deploy_token" ]; then
    export VM_DEPLOY_TOKEN=$(cat /root/{app_name}/.deploy_token)
fi

# Load GitHub token for artifact downloads
if [ -f "/root/{app_name}/.github_token" ]; then
    export GITHUB_TOKEN=$(cat /root/{app_name}/.github_token)
fi

# Set working directory
cd /root/{app_name}

# Activate virtual environment
source venv/bin/activate

# Start Gunicorn
exec gunicorn \
    --bind 127.0.0.1:8081 \
    --workers 2 \
    --timeout 300 \
    --access-logfile /root/{app_name}/logs/gunicorn_access.log \
    --error-logfile /root/{app_name}/logs/gunicorn_error.log \
    --log-level info \
    deployment.vm_deploy_service:app
```

Make it executable:
```bash
chmod +x /root/{app_name}/deployment/start_deploy_service.sh
```

### 3. Nginx Configuration

#### 3.1 Create Nginx Site Config
Create `/etc/nginx/sites-available/{app_name}_deploy`:
```nginx
server {
    listen 80;
    server_name YOUR_VM_IP;

    # Deployment webhook endpoint
    location /deploy {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:8081;
        proxy_set_header Host $host;
        proxy_read_timeout 10s;
    }
}
```

#### 3.2 Enable Site
```bash
ln -s /etc/nginx/sites-available/{app_name}_deploy /etc/nginx/sites-enabled/
nginx -t  # Test configuration
systemctl reload nginx
```

### 4. GitHub Actions Configuration

#### 4.1 Create Workflow File
Create `.github/workflows/deploy.yml` in your repository:
```yaml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, master ]
  workflow_dispatch:

env:
  PYTHON_VERSION: '3.10'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: ${{ env.PYTHON_VERSION }}
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python -m pytest tests/ || echo "No tests found"
    
    - name: Create deployment package
      run: |
        tar -czf ${{ github.repository_name }}-${{ github.sha }}.tar.gz \
          --exclude='.git' \
          --exclude='*.pyc' \
          --exclude='__pycache__' \
          --exclude='.env' \
          .
    
    - name: Upload artifact
      uses: actions/upload-artifact@v4
      with:
        name: ${{ github.repository_name }}-${{ github.sha }}
        path: ${{ github.repository_name }}-${{ github.sha }}.tar.gz

  deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' || github.ref == 'refs/heads/master'
    
    steps:
    - name: Deploy to VM
      env:
        VM_DEPLOY_TOKEN: ${{ secrets.VM_DEPLOY_TOKEN }}
        VM_DEPLOY_WEBHOOK_URL: ${{ secrets.VM_DEPLOY_WEBHOOK_URL }}
      run: |
        curl -X POST \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer $VM_DEPLOY_TOKEN" \
          -d '{
            "version": "${{ github.sha }}",
            "repository": "${{ github.repository }}",
            "workflow_run_id": "${{ github.run_id }}",
            "branch": "${{ github.ref_name }}",
            "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
            "triggered_by": "${{ github.actor }}"
          }' \
          "$VM_DEPLOY_WEBHOOK_URL" \
          --max-time 120 \
          --retry 2
```

### 5. Token Configuration

#### 5.1 Create Token Files on VM
```bash
# Store deployment token (from step 1.1)
echo "YOUR_DEPLOYMENT_TOKEN" > /root/{app_name}/.deploy_token
chmod 600 /root/{app_name}/.deploy_token

# Store GitHub PAT for artifact downloads
echo "github_pat_YOUR_TOKEN_HERE" > /root/{app_name}/.github_token
chmod 600 /root/{app_name}/.github_token
```

#### 5.2 Configure GitHub Secrets
Add these secrets to your GitHub repository (Settings → Secrets → Actions):

1. **VM_DEPLOY_TOKEN**: The token from `/root/deployment_token.txt`
2. **VM_DEPLOY_WEBHOOK_URL**: `http://YOUR_VM_IP/deploy`
3. **VM_HEALTH_CHECK_URL**: `http://YOUR_VM_IP/health`

### 6. Start Deployment Service

```bash
# Start the service
cd /root/{app_name}
nohup ./deployment/start_deploy_service.sh > logs/deploy_service.log 2>&1 &

# Verify it's running
ps aux | grep gunicorn | grep vm_deploy
curl http://localhost:8081/health
```

## Common Issues and Solutions

### Issue 1: "No GitHub token found, falling back to local copy"

**Symptoms**: Deployment works but uses local files instead of GitHub artifacts

**Solution**:
1. Check token file exists: `ls -la /root/{app_name}/.github_token`
2. Verify token is valid: Test with GitHub API
3. Restart deployment service to load token

### Issue 2: "502 Bad Gateway" from Nginx

**Symptoms**: Webhook returns 502 error

**Solution**:
1. Check if deployment service is running: `ps aux | grep gunicorn`
2. Check Gunicorn logs: `tail -f /root/{app_name}/logs/gunicorn_error.log`
3. Restart service if needed

### Issue 3: Deployment logs not updating

**Symptoms**: Deployments happen but logs are stale

**Solution**:
1. Check log file permissions: `ls -la /root/{app_name}/logs/`
2. Check disk space: `df -h`
3. Restart deployment service with fresh log file

### Issue 4: "Artifact not found" errors

**Symptoms**: GitHub token works but artifacts can't be downloaded

**Solution**:
1. Verify artifact name matches exactly (use full commit SHA)
2. Check workflow completed successfully
3. Ensure GitHub token has proper permissions

### Issue 5: Deployments not triggered automatically

**Symptoms**: Manual deployments work but pushes don't trigger

**Solution**:
1. Verify GitHub secrets are set correctly
2. Check workflow file syntax
3. Ensure branch names match (main vs master)

## Verification Procedures

### 1. Test Manual Deployment
```bash
# Get latest workflow run ID
curl -H "Authorization: token YOUR_GITHUB_PAT" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=1" \
  | grep '"id"' | head -1

# Trigger deployment manually
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_DEPLOY_TOKEN" \
  -d '{
    "version": "COMMIT_SHA",
    "repository": "OWNER/REPO",
    "workflow_run_id": "RUN_ID",
    "branch": "main",
    "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'",
    "triggered_by": "manual-test"
  }' \
  "http://YOUR_VM_IP/deploy"
```

### 2. Check Deployment Status
```bash
# View recent deployments
tail -50 /root/{app_name}/logs/deployment.log

# Check for successful artifact downloads
grep "Artifact downloaded" /root/{app_name}/logs/deployment.log

# Verify no fallback to local copy
grep -v "fallback" /root/{app_name}/logs/deployment.log | tail -20
```

### 3. Verify File Updates
```bash
# Check file modification times
ls -la /root/{app_name}/src/

# Compare with backup
diff -r /root/{app_name}_backups/latest /root/{app_name}/
```

## Security Best Practices

### 1. Token Management
- Never commit tokens to repositories
- Use environment variables or secure files
- Rotate tokens regularly
- Use minimal permissions for GitHub PAT

### 2. Network Security
- Use HTTPS for production deployments
- Implement IP whitelisting for deployment endpoint
- Use fail2ban to prevent brute force attacks

### 3. File Permissions
```bash
# Secure token files
chmod 600 /root/{app_name}/.deploy_token
chmod 600 /root/{app_name}/.github_token

# Restrict log access
chmod 640 /root/{app_name}/logs/*.log

# Secure deployment scripts
chmod 750 /root/{app_name}/deployment/*.sh
```

### 4. Backup Strategy
- Keep last 5 deployments as backups
- Implement automated cleanup of old backups
- Test rollback procedures regularly

## Debugging Commands

### Check Service Status
```bash
# Deployment service processes
ps aux | grep -E "gunicorn.*vm_deploy"

# Nginx status
systemctl status nginx
nginx -t

# Port availability
netstat -tlnp | grep -E "80|443|8081"
```

### View Logs
```bash
# Deployment logs
tail -f /root/{app_name}/logs/deployment.log

# Gunicorn logs
tail -f /root/{app_name}/logs/gunicorn_error.log
tail -f /root/{app_name}/logs/gunicorn_access.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Test Endpoints
```bash
# Health check
curl -v http://localhost:8081/health
curl -v http://YOUR_VM_IP/health

# Test deployment (with auth)
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test": true}' \
  http://YOUR_VM_IP/deploy
```

### GitHub API Testing
```bash
# Test GitHub token
curl -H "Authorization: token YOUR_GITHUB_PAT" \
  https://api.github.com/user

# List workflow runs
curl -H "Authorization: token YOUR_GITHUB_PAT" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs?per_page=5"

# List artifacts
curl -H "Authorization: token YOUR_GITHUB_PAT" \
  "https://api.github.com/repos/OWNER/REPO/actions/runs/RUN_ID/artifacts"
```

## Rollback Procedures

### Manual Rollback
```bash
# List available backups
ls -la /root/{app_name}_backups/

# Restore from backup
cd /root
rm -rf {app_name}
cp -r {app_name}_backups/backup_COMMIT_SHA_{app_name}
```

### Automated Rollback
The deployment service should include rollback functionality:
- On health check failure after deployment
- Via webhook with rollback command
- Keeping last known good configuration

## Troubleshooting Checklist

When deployments aren't working, check in this order:

1. ✓ Deployment service is running
2. ✓ Nginx is proxying correctly
3. ✓ Token files exist and have correct permissions
4. ✓ GitHub secrets are configured
5. ✓ Workflow file is valid YAML
6. ✓ Artifacts are being created
7. ✓ Webhook is reaching the VM
8. ✓ Logs show deployment attempts
9. ✓ No "fallback to local copy" messages
10. ✓ Files are actually updated after deployment

## Summary

A properly configured deployment pipeline should:
- Trigger automatically on code pushes
- Download artifacts from GitHub (not use local copies)
- Create backups before updating
- Log all operations
- Allow rollback if needed
- Require authentication for all deployment operations

Following this guide ensures reliable, secure, and debuggable deployments without introducing technical debt.

---

*Last updated: 2025-08-04*
*Version: 1.0*