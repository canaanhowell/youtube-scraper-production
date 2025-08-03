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

### 🚀 **Deployed and Running**

The YouTube app is successfully deployed to production with auto-deployment enabled:

✅ **System Status**:
- **VM**: Running at 134.199.201.56 - 4 vCPU, 8GB RAM
- **Project Path**: `/opt/youtube_app/` (successfully migrated from youtube_scraper)
- **VPN System**: 24 verified US Surfshark servers with WireGuard
- **Firebase**: Connected and operational
- **Redis**: Upstash Redis REST API configured
- **Deployment**: GitHub Actions auto-deployment ACTIVE

### 🔧 **Latest Updates**:

**Deployment Complete** (13:00 UTC):
- Successfully deployed to VM via GitHub push
- Fixed all hardcoded paths from `/opt/youtube_app` to `/opt/youtube_app`
- Python virtual environment configured
- All dependencies installed
- Credentials properly configured

**Auto-Deployment Working**:
- GitHub Actions workflow active
- Push to main branch = automatic deployment
- Smart deployment detects changed files
- Automatic backup before updates
- Path fixes deployed and verified

**Current Issues Resolved**:
- ✅ Path migration completed
- ✅ Environment variables corrected (SURFSHARK_PRIVATE_KEY, SURFSHARK_ADDRESS)
- ✅ Firebase credentials deployed
- ✅ Logs directory created

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

### 📝 **Required Environment Variables**
The `.env` file on VM must include:
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/opt/youtube_app/ai-tracker-466821-892ecf5150a3.json
FIRESTORE_PROJECT_ID=ai-tracker-466821

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN WireGuard Configuration
SURFSHARK_PRIVATE_KEY=your-wireguard-private-key
SURFSHARK_ADDRESS=10.14.0.2/16

# Environment
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## System Architecture

### **Production Components**:
- **YouTube Scraper**: Playwright-based scraper with VPN rotation
- **VPN Manager**: WireGuard integration with 24 US Surfshark servers
- **Data Storage**: Firebase Firestore for keywords and results
- **Cache Layer**: Upstash Redis REST API
- **Analytics Pipeline**: Daily metrics and trend analysis
- **Deployment**: GitHub Actions with smart detection

### **Key Commands**:
```bash
# Run collection manually
cd /opt/youtube_app && source venv/bin/activate
python youtube_collection_manager.py

# Check logs
tail -f /opt/youtube_app/logs/scraper.log

# Test with limited keywords
python youtube_collection_manager.py --test
```

## Summary

The YouTube app is now:
- ✅ Fully deployed to production VM
- ✅ Auto-deployment enabled and tested
- ✅ All paths migrated to `/opt/youtube_app`
- ✅ Environment variables properly configured
- ✅ Ready for production data collection

Any push to GitHub main branch automatically deploys to production!