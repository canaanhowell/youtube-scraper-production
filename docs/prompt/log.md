# YouTube App Production System - Smart Auto-Deployment

## Core Instructions for Coding Agents

You are a coding agent working with a production-ready YouTube scraper system.
You have 2 rules:
**1. No tech debt** - If a problem arises, we provide the long-term solution right away.
**2. No data fabrication** - Errors always preferred over mock data or fallback placeholders.

## Project Overview

- **Project Name**: youtube_app (formerly youtube_scraper)
- **Database**: Firebase Firestore (credentials via file path in .env)
- **Caching**: Upstash Redis with REST API client
- **Runtime**: Python 3.10+ on Ubuntu VM
- **Deployment**: GitHub Actions auto-deployment on push to main
- **VM**: SSH to VM using `/workspace/droplet1` (private key) - IP: 134.199.201.56
- **Repository**: https://github.com/canaanhowell/youtube-scraper-production

## Current Status (2025-08-03)

### 🚀 **Smart Auto-Deployment Ready**

The YouTube scraper has been simplified with GitHub-based deployment and dynamic path handling:

✅ **System Status**:
- **VM**: Clean slate at 134.199.201.56 - 4 vCPU, 8GB RAM
- **Project Path**: `/opt/youtube_app/` (renamed from youtube_scraper)
- **VPN System**: 24 verified US Surfshark servers (VM-only)
- **Firebase**: Credentials via file path in .env
- **Deployment**: Push to GitHub = automatic deployment

### 🔧 **Recent Changes**:

**Project Rename**:
- Changed from `youtube_scraper` to `youtube_app`
- Updated all paths dynamically
- Fixed env_loader.py to use correct paths

**Smart Deployment**:
- GitHub Actions workflow (`.github/workflows/auto-deploy.yml`)
- File change detection (`deployment/scripts/smart_deploy.sh`)
- Service auto-discovery (`deployment/scripts/service_detector.py`)
- Backup/rollback system (`deployment/scripts/backup_manager.py`)

**Path Handling**:
- Local development: Uses current directory (./logs)
- VM production: Uses `/opt/youtube_app/logs`
- Automatic detection based on environment

## Key Features

### 🎯 **Deployment Process**
1. **Push to GitHub** → Triggers auto-deployment
2. **Smart Detection** → Only updates changed components
3. **Auto-Configure** → New services detected and configured
4. **Backup First** → Automatic backup before changes
5. **Auto-Rollback** → If deployment fails

### 📁 **Project Structure**
```
youtube_app/
├── youtube_collection_manager.py      # Main orchestrator
├── youtube_scraper_production.py      # Core scraping logic
├── src/
│   ├── utils/                        # Utilities
│   │   ├── env_loader.py            # Fixed for youtube_app paths
│   │   ├── logging_config_enhanced.py # Dynamic log paths
│   │   └── firebase_client_enhanced.py
│   └── analytics/                    # Analytics pipeline
├── deployment/
│   ├── scripts/
│   │   ├── smart_deploy.sh          # Smart deployment script
│   │   ├── service_detector.py      # Auto-detect services
│   │   └── backup_manager.py        # Backup/rollback
│   └── test_deployment.py           # Deployment verification
├── .github/
│   └── workflows/
│       └── auto-deploy.yml          # GitHub Actions
└── .env                             # Credentials (gitignored)
```

### 🔒 **Security**
- `.env` file gitignored
- Firebase credentials file gitignored  
- Credentials added manually on VM after deployment
- VPN for anonymity (VM-only)

## Usage Instructions

### 🚀 **Deploy to Production**
```bash
# 1. Push to GitHub (triggers deployment)
git push origin main

# 2. Monitor deployment
# Check GitHub Actions: https://github.com/canaanhowell/youtube-scraper-production/actions

# 3. SSH to VM and add credentials
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app
vim .env  # Add production credentials
```

### 📊 **Monitor System**
```bash
# Check service status
sudo systemctl status youtube-scraper

# View logs
tail -f logs/scraper.log

# Check deployment log
tail -f /var/log/youtube_deploy.log

# Manual backup/rollback if needed
python3 deployment/scripts/backup_manager.py backup
python3 deployment/scripts/backup_manager.py rollback
```

## Important Notes

### ⚠️ **Cannot Test Locally**
- VPN/Docker required (only on VM)
- Local testing limited to Firebase connection
- Full testing requires VM environment

### 📝 **Credential Setup**
After deployment, create `.env` on VM:
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/path/to/firebase.json
FIRESTORE_PROJECT_ID=your-project-id

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN
SURFSHARK_USER=your@email.com
SURFSHARK_PASSWORD=your-password

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Next Steps

1. **Commit and push** current changes to GitHub
2. **Auto-deployment** will update VM
3. **SSH to VM** and add production .env
4. **Verify** scraper runs successfully

## Summary

The YouTube scraper is now:
- ✅ Renamed to youtube_app
- ✅ Using smart auto-deployment
- ✅ Working with dynamic paths
- ✅ Ready for production deployment
- ✅ Simplified without complex enterprise features

Push to GitHub and the system handles the rest!