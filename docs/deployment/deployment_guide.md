# YouTube App - Deployment Guide

## Overview

This deployment system provides a streamlined 3-phase process for deploying the YouTube App on a dedicated VM (134.199.201.56). It implements the same simplified CI/CD practices as the Reddit app.

### Key Features
- ✅ **No Git on VM** - All deployment via GitHub Actions artifacts
- ✅ **Artifact-based deployment** - Clean production files only
- ✅ **Automated deployment** - Push to main = automatic deployment
- ✅ **Health checks** - Automatic verification after deployment
- ✅ **Zero downtime** - Services restart gracefully
- ✅ **Automatic backups** - Before each deployment
- ✅ **Simple 3-phase setup** - Infrastructure → GitHub → Monitor

## Architecture

```
Local Development → GitHub → GitHub Actions → Auto-Deploy → VM
```

### Core Principle: No Git on Production
The VM never has git installed or GitHub credentials. It only receives clean, tested artifacts via the auto-deployment system.

## Simplified 3-Phase Deployment

### Phase 1: Initial VM Setup (One-time)

**Note**: The VM is already set up and running. This phase is documented for reference only.

1. **SSH to VM**:
   ```bash
   ssh -i /workspace/droplet1 root@134.199.201.56
   ```

2. **Directory structure**:
   ```
   /opt/youtube_app/
   ├── src/                    # Application source code
   ├── deployment/             # Deployment scripts
   ├── logs/                   # Application logs
   ├── venv/                   # Python virtual environment
   ├── .env                    # Environment variables (preserved)
   └── ai-tracker-*.json       # Firebase credentials (preserved)
   ```

### Phase 2: Development & Deployment

1. **Make changes locally**:
   ```bash
   cd /workspace/youtube_app
   # Make your changes
   ```

2. **Push to GitHub** (triggers auto-deployment):
   ```bash
   git add .
   git commit -m "feat: your feature description"
   git push origin main
   ```

3. **Auto-deployment process**:
   - GitHub Actions runs tests
   - Creates deployment artifact (no .git)
   - Deploys to VM automatically
   - Runs health checks
   - Restarts services

### Phase 3: Monitor & Verify

1. **Monitor deployment** (optional):
   ```bash
   # Watch GitHub Actions
   # https://github.com/canaanhowell/youtube-scraper-production/actions
   ```

2. **Verify on VM** (if needed):
   ```bash
   ssh -i /workspace/droplet1 root@134.199.201.56
   tail -f /opt/youtube_app/logs/scraper.log
   ```

## How Auto-Deployment Works

1. **You push code** to GitHub main branch
2. **GitHub Actions** automatically:
   - Runs tests
   - Creates deployment artifact
   - Deploys to VM
3. **VM automatically**:
   - Receives new code
   - Backs up current version
   - Deploys new version
   - Restarts services
   - Verifies health

## Current Production Setup

### Services Running
- **Hourly Collection**: Runs at :15 past each hour via cron
- **VPN Container**: Docker container for VPN rotation
- **Auto-deployment**: GitHub Actions webhook system

### Environment Variables
The `.env` file on VM contains:
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/opt/youtube_app/ai-tracker-*.json
FIRESTORE_PROJECT_ID=ai-tracker-*

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN
SURFSHARK_PRIVATE_KEY=your-key
SURFSHARK_ADDRESS=10.14.0.2/16

# YouTube Settings
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title
```

## Common Tasks

### Deploy New Code
```bash
# Simply push to main branch
git push origin main
# Deployment happens automatically!
```

### Check Logs
```bash
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app
tail -f logs/scraper.log      # Application logs
tail -f logs/cron.log         # Cron job logs
```

### Run Manual Collection
```bash
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app && source venv/bin/activate
python youtube_collection_manager.py
```

### Check Cron Jobs
```bash
ssh -i /workspace/droplet1 root@134.199.201.56
crontab -l
# Should show: 15 * * * * /opt/youtube_app/cron_scraper.sh
```

## Emergency Procedures

### Manual Deployment (if auto-deploy fails)
```bash
# From local machine
cd /workspace/youtube_app
tar -czf deploy.tar.gz *.py src/ requirements.txt
scp -i /workspace/droplet1 deploy.tar.gz root@134.199.201.56:/tmp/

# On VM
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app
cp -r /opt/youtube_app /opt/youtube_app_backup_$(date +%Y%m%d_%H%M%S)
tar -xzf /tmp/deploy.tar.gz
source venv/bin/activate
pip install -r requirements.txt
rm /tmp/deploy.tar.gz
```

### Rollback
```bash
# List backups
ls -la /opt/youtube_app_backup_*

# Restore from backup
cp -r /opt/youtube_app_backup_20250803_120000/* /opt/youtube_app/
```

## Best Practices

### When to Deploy
- **Avoid deploying at :15** (hourly collection time)
- **Best times**: :30-:00 or :00-:10
- **Check GitHub Actions** before assuming deployment failed

### Code Quality
- **Test locally first** before pushing
- **Use meaningful commit messages**
- **One feature per commit** when possible

### Monitoring
- **Check logs after deployment** to ensure services resumed
- **Verify collection runs** after major changes
- **Monitor Firebase** for data integrity

## Troubleshooting

### Deployment Not Working
1. Check GitHub Actions: https://github.com/canaanhowell/youtube-scraper-production/actions
2. Verify webhook is configured in GitHub settings
3. Check if code was actually updated on VM:
   ```bash
   ssh -i /workspace/droplet1 root@134.199.201.56
   cd /opt/youtube_app
   ls -la *.py  # Check file timestamps
   ```

### Collection Not Running
1. Check cron logs:
   ```bash
   tail -f /opt/youtube_app/logs/cron.log
   grep ERROR /opt/youtube_app/logs/scraper.log
   ```

2. Test manually:
   ```bash
   cd /opt/youtube_app && source venv/bin/activate
   python youtube_collection_manager.py --test
   ```

### VPN Issues
1. Check Docker container:
   ```bash
   docker ps
   docker logs youtube-vpn
   ```

2. Restart VPN:
   ```bash
   docker restart youtube-vpn
   ```

## Key Differences from Complex Deployment

This simplified deployment:
- ✅ **No manual git operations** on VM
- ✅ **No complex 6-phase process** - just 3 simple phases
- ✅ **No SSH keys on VM** - uses GitHub Actions
- ✅ **Automatic everything** - just push to deploy
- ✅ **Same path for cron** - updates happen transparently

## Summary

The YouTube app uses a simplified deployment process:
1. **Push code** to GitHub main branch
2. **Auto-deployment** handles everything
3. **Monitor** if needed (usually not necessary)

The system maintains all security and reliability features while being simple to use. No git on production, no manual deployment steps, just push and go!