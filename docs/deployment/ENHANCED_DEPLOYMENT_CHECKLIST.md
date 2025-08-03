# Smart GitHub Auto-Deployment Checklist

## Overview

**Smart Auto-Deployment System**: Push to GitHub main branch = automatic VM deployment with intelligent detection and rollback capabilities.

## One-Time Setup (Required)

### 1. GitHub Secrets Configuration
- [ ] Add `VM_SSH_KEY` secret to GitHub repository
- [ ] Test SSH connection from GitHub Actions to VM (134.199.201.56)
- [ ] Verify repository access permissions

### 2. VM Preparation
- [ ] SSH key authentication configured
- [ ] Project directory exists: `/opt/youtube_scraper`
- [ ] Git repository cloned and configured
- [ ] Basic requirements installed (Python 3.13+, venv)

## How It Works

### Automatic Smart Deployment

**Trigger**: Push to `main` branch

**Process**:
1. **GitHub Actions** automatically detects push
2. **Smart Deploy Script** analyzes what files changed
3. **Intelligent Updates** only restarts affected services
4. **Auto-Detection** finds and configures new services
5. **Automatic Backup** before any changes
6. **Auto-Rollback** if deployment fails
7. **Verification** ensures everything works

**What Gets Auto-Detected**:
- New Python scripts matching service patterns (`*_manager.py`, `*_collector.py`, etc.)
- Systemd service file changes
- Dependency updates (requirements.txt)
- Configuration changes
- Analytics and monitoring components

## Smart Deployment Commands

### For Developers (Push and Forget)
```bash
# 1. Develop locally
vim youtube_collection_manager.py

# 2. Test locally
python3 youtube_collection_manager.py --test

# 3. Push to GitHub (triggers auto-deployment)
git add .
git commit -m "Improve collection logic"
git push origin main

# 4. Deployment happens automatically!
# ✅ GitHub Actions runs
# ✅ Smart script detects changes
# ✅ Only affected services restart
# ✅ New services auto-configure
# ✅ Verification ensures success
```

### Manual Operations (If Needed)

#### Check Deployment Status
```bash
# View GitHub Actions status
# Go to: https://github.com/canaanhowell/youtube-scraper-production/actions

# Or check on VM directly:
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_scraper

# View deployment logs
tail -f /var/log/youtube_deploy.log

# Check service status
sudo systemctl status youtube-scraper
sudo systemctl list-units | grep youtube
```

#### Manual Backup/Rollback
```bash
# Create manual backup
python3 deployment/scripts/backup_manager.py backup --type manual --description "Before major changes"

# List available backups
python3 deployment/scripts/backup_manager.py list

# Rollback to latest backup
python3 deployment/scripts/backup_manager.py rollback

# Rollback to specific backup
python3 deployment/scripts/backup_manager.py rollback --name backup_auto_20250803_143022
```

#### Force Service Detection
```bash
# Manually run service detection
python3 deployment/scripts/service_detector.py

# This will:
# ✅ Scan for new Python scripts
# ✅ Auto-create systemd services
# ✅ Configure and start services
# ✅ Report what was created
```

## Key Features

### 🎯 Smart Detection
- **File Change Analysis**: Only updates what changed
- **Service Pattern Recognition**: Auto-detects `*_manager.py`, `*_collector.py`, etc.
- **Dependency Management**: Auto-updates requirements.txt changes
- **Configuration Updates**: Handles systemd service changes

### 🛡️ Safety Features
- **Automatic Backup**: Before every deployment
- **Auto-Rollback**: If deployment fails
- **Service Isolation**: Single service failures don't break others
- **Verification**: Health checks after deployment

### ⚡ Zero-Configuration
- **Push and Forget**: Just push to GitHub
- **Auto-Service Creation**: New scripts become services automatically
- **Intelligent Restart**: Only affected services restart
- **Status Reporting**: Know immediately if deployment worked

## Verification

### Immediate (Automatic)
- [ ] GitHub Actions workflow completes successfully
- [ ] Core service (youtube-scraper) running
- [ ] No critical errors in deployment logs
- [ ] Basic connectivity test passes

### Optional Manual Checks
- [ ] SSH to VM and verify services: `systemctl status youtube-scraper`
- [ ] Check logs: `tail -f logs/scraper.log`
- [ ] Test functionality: `python3 get_firebase_stats_fixed.py`

## Emergency Procedures

### Automatic Rollback (Preferred)
- Deployment automatically rolls back if verification fails
- Previous backup is restored automatically
- Services are restarted to working state

### Manual Rollback
```bash
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_scraper

# Rollback to latest backup
python3 deployment/scripts/backup_manager.py rollback

# Or rollback to specific backup
python3 deployment/scripts/backup_manager.py list
python3 deployment/scripts/backup_manager.py rollback --name backup_auto_20250803_143022
```

### Nuclear Option (Complete Reset)
```bash
# If everything is broken:
cd /opt/youtube_scraper
git reset --hard origin/main
sudo systemctl restart youtube-scraper
```

## Success Criteria

✅ **Deployment Successful When:**
- [ ] GitHub Actions workflow shows green checkmark
- [ ] Core youtube-scraper service running on VM
- [ ] No errors in `/var/log/youtube_deploy.log`
- [ ] Any new services detected and configured automatically

## Benefits of This System

🚀 **For Developers**:
- **One-command deployment**: Push to GitHub = deployed
- **No manual steps**: Everything automated
- **Safe experiments**: Automatic backup and rollback
- **Immediate feedback**: Know if deployment worked

🛡️ **For Operations**:
- **Reduced complexity**: No complex deployment procedures
- **Better reliability**: Automatic rollback on failure
- **Audit trail**: All deployments tracked in GitHub
- **Easy troubleshooting**: Clear logs and status reporting

📊 **For System**:
- **Intelligent updates**: Only restart what changed
- **Auto-discovery**: New features configure themselves
- **Consistent state**: Always know what's deployed
- **Disaster recovery**: Easy rollback to any previous state

## Repository

- **GitHub**: https://github.com/canaanhowell/youtube-scraper-production
- **VM**: 134.199.201.56
- **Deployment Logs**: `/var/log/youtube_deploy.log`
- **Backup Manager**: `deployment/scripts/backup_manager.py`