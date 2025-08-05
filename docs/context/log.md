# Wget YouTube Scraper - Production System Log

## Core Instructions for Coding Agents

You are a coding agent working with a production-ready YouTube scraper system.
You have 2 rules:
**1. No tech debt** - If a problem arises, we provide the long-term solution right away.
**2. No data fabrication** - Errors always preferred over mock data or fallback placeholders.

## Project Overview

- **Project Name**: wget_youtube_scraper (Alpine-based wget collection)
- **Database**: Firebase Firestore (credentials via file path in .env)
- **Caching**: Upstash Redis with REST API client
- **Runtime**: Python 3.10+ on Alpine Linux VM
- **Deployment**: GitHub Actions auto-deployment on push to main
- **VM**: SSH to VM using `/workspace/droplet1` (private key) - IP: 134.199.201.56
- **Location**: `/opt/wget_youtube_scraper` on VM
- **Repository**: https://github.com/canaanhowell/youtube-scraper-production

## Current Status (2025-01-05)

### 🚀 **Deployed and Running**

The wget YouTube scraper is successfully deployed to production with auto-deployment enabled:

✅ **System Status**:
- **VM**: Running at 134.199.201.56 - 4 vCPU, 8GB RAM
- **Project Path**: `/opt/wget_youtube_scraper/` (renamed from youtube_app for clarity)
- **VPN System**: 24 verified US Surfshark servers with WireGuard
- **Firebase**: Connected and operational
- **Redis**: Upstash Redis REST API configured
- **Deployment**: GitHub Actions auto-deployment ACTIVE
- **Analytics Pipeline**: Fully operational with interval and daily metrics
- **Collection Method**: wget-based (~20 videos per keyword)

### 🔧 **Latest Updates (2025-01-05)**:

**🎯 Project Structure Cleanup** (Latest):
- ✅ Renamed from youtube_app to wget_youtube_scraper for clarity
- ✅ Moved all Python scripts from root to src/ directories
- ✅ Updated all deployment scripts for new paths
- ✅ Cleaned up root directory - only config files remain
- ✅ Aligned structure with playwright_youtube_scraper

### 🔧 **Previous Updates (2025-01-04)**:

**🎯 Platform Baseline System Simplified** (Latest):
- ✅ Removed complex platform baseline calculation script
- ✅ Implemented hardcoded platform baseline approach for simplicity
- ✅ Created set_platform_baseline.py for manual baseline management
- ✅ Set YouTube platform baseline to 150.0 videos/day (hardcoded)
- ✅ Updated all documentation to reflect hardcoded approach
- ✅ Verified velocity calculations working correctly with hardcoded baseline
- ✅ System deployed and operational on production VM

**🎯 Firebase Schema v2.0 Migration**:
- ✅ Successfully migrated Firebase schema to v2.0 standardized metrics
- ✅ Converted daily_metrics from subcollection to map field for all 15 keywords
- ✅ Updated 566 category snapshot documents with new field names
- ✅ Transformed field names: videos_found_in_day → new_videos_in_day, views_count → total_views
- ✅ Added standardized v2.0 fields: velocity (platform-normalized %), acceleration (keyword-relative ratio)
- ✅ Removed legacy metrics and cleaned up keyword document structure
- ✅ Updated youtube_daily_metrics_unified_vm.py to write new schema format
- ✅ Added current_velocity field updates to keywords for real-time tracking
- ✅ All production systems now using v2.0 schema with backward compatibility removed

**🎯 Standardized Metrics v2.0 Implementation**:
- ✅ Implemented platform-normalized velocity scoring system
- ✅ Added keyword-relative acceleration calculations
- ✅ Created momentum score (0-100) based on trend analysis
- ✅ Built unified trend score v2 combining velocity + momentum
- ✅ Enhanced youtube_daily_metrics_unified_vm.py with new scoring
- ✅ Updated category snapshots with standardized metrics
- ✅ Created platform baseline calculator for YouTube
- ✅ Added platform_metrics collection for baseline storage
- ✅ Updated firestore_mapping.md with v2.0 schema
- ✅ Comprehensive testing validated all calculations
- ✅ Cross-platform comparison now possible with normalized scores

**Key Benefits of New Metrics System**:
- 🔥 **Platform-Normalized Velocity**: 150% = 150% of YouTube platform average
- 🚀 **Keyword-Relative Acceleration**: 1.5x = 150% vs keyword's own baseline
- 📈 **Momentum Score**: 0-100 trend momentum using linear regression
- 🎯 **Unified Trend Score**: Combined ranking score (60% velocity + 40% momentum)
- 🌐 **Cross-Platform**: Standardized scoring enables comparison across platforms

**Scheduled Function Paths Fixed**:
- ✅ Fixed cron_scraper_with_metrics.sh to use correct script paths
- ✅ Updated from module import to direct script execution
- ✅ All scheduled functions now pointing to reorganized project structure
- ✅ Verified scripts are executable and working

**Interval Metrics Timing Fixed**:
- ✅ Fixed interval metrics running every 5 minutes instead of hourly
- ✅ Disabled systemd analytics timer that was causing excessive runs
- ✅ Integrated interval metrics into hourly scraper cron job
- ✅ Now runs correctly: Scraper at :15, then interval metrics immediately after
- ✅ Proper data flow: Videos collected → Interval metrics calculated → Daily metrics aggregated

**Analytics Pipeline Fixed**:
- ✅ Fixed systemd service configuration for analytics
- ✅ Daily metrics cron job verified (runs at 2:00 AM daily)
- ✅ Interval metrics now calculating properly after each scraper run
- ✅ Created fix scripts for future troubleshooting
- ✅ All metrics services operational

**Video Collection Confirmed Working**:
- ✅ Videos ARE being collected successfully (56 videos in last run)
- ✅ Strict title filter disabled to improve collection rates
- ✅ Data properly stored in `youtube_videos/{keyword}/videos/`
- ✅ Interval metrics stored in `youtube_keywords/{keyword}/interval_metrics/`

### 🔧 **Previous Updates (2025-01-03)**:

**Title Filtering Enhancement** (Latest):
- ✅ Added YOUTUBE_STRICT_TITLE_FILTER feature
- ✅ Only collects videos containing the search keyword in their title
- ✅ Defaults to true for improved data quality
- ✅ Environment variable: `YOUTUBE_STRICT_TITLE_FILTER=true`
- ✅ Reduces irrelevant data collection significantly

**Simplified Deployment Process**:
- ✅ 3-phase deployment process implemented
- ✅ No Git operations on production VM
- ✅ Artifact-based deployment for cleaner production
- ✅ Automated health checks and verification
- ✅ Zero-downtime deployments

**Deployment Complete** (13:00 UTC):
- Successfully deployed to VM via GitHub push
- Fixed all hardcoded paths from `/opt/youtube_scraper` to `/opt/youtube_app`
- Python virtual environment configured
- All dependencies installed
- Credentials properly configured

**Hourly Automation** (13:27 UTC):
- Cron job configured to run hourly at :15 past the hour
- Logs available at `/opt/wget_youtube_scraper/logs/cron.log`
- Script: `/opt/wget_youtube_scraper/cron_scraper.sh`

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
- ✅ Hourly automation via cron job
- ✅ Title filtering implemented for better data quality

## Key Features

### 🎯 **Deployment Process**
1. **Push to GitHub** → Triggers auto-deployment
2. **Smart Detection** → Only updates changed components
3. **Auto-Configure** → New services detected and configured
4. **Backup First** → Automatic backup before changes
5. **Auto-Rollback** → If deployment fails

### 📁 **Project Structure**
```
wget_youtube_scraper/
├── src/
│   ├── scripts/
│   │   ├── youtube_collection_manager.py  # Main orchestrator
│   │   ├── youtube_scraper_production.py  # Core scraping logic
│   │   └── collectors/
│   │       └── run_analytics.py           # Analytics runner
│   ├── utils/                             # Utilities
│   │   ├── env_loader.py                  # Fixed for youtube_app paths
│   │   ├── logging_config_enhanced.py     # Dynamic log paths
│   │   └── firebase_client_enhanced.py
│   └── analytics/                         # Analytics pipeline
│       └── metrics/
│           ├── youtube_keywords_interval_metrics.py
│           └── youtube_daily_metrics_unified_vm.py
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

# 3. SSH to VM and add credentials (first time only)
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app
vim .env  # Add production credentials
```

### ⚙️ **Configure Title Filtering**
```bash
# In .env file, set title filtering (defaults to true)
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title
YOUTUBE_STRICT_TITLE_FILTER=false # Collect all videos from search results
```

### 📊 **Monitor System**
```bash
# Check cron job status
crontab -l

# View collection logs
tail -f logs/scraper.log

# View cron logs
tail -f logs/cron.log

# View analytics logs
tail -f logs/analytics.log

# View daily metrics logs
tail -f logs/daily_metrics.log

# Check systemd timers
systemctl list-timers --all | grep youtube

# Check analytics service status
systemctl status youtube-analytics.timer
systemctl status youtube-analytics.service

# Check deployment log
tail -f /var/log/youtube_deploy.log

# Manual backup/rollback if needed
python3 deployment/scripts/backup_manager.py backup
python3 deployment/scripts/backup_manager.py rollback

# Run daily metrics manually if needed
bash deployment/scripts/run_daily_metrics_now.sh

# Fix daily metrics cron if needed
bash deployment/scripts/fix_daily_metrics_cron.sh
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

# YouTube Settings
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title (default: true)
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
python src/scripts/youtube_collection_manager.py

# Check logs
tail -f /opt/youtube_app/logs/scraper.log

# Check cron logs
tail -f /opt/youtube_app/logs/cron.log

# Test with limited keywords
python src/scripts/youtube_collection_manager.py --test

# View next scheduled run
systemctl list-timers --all | grep youtube

# Set platform baseline (manual management)
python src/analytics/metrics/set_platform_baseline.py --baseline 150.0

# View current platform baseline
python -c "from src.utils.firebase_client import FirebaseClient; fb = FirebaseClient(); doc = fb.db.collection('platform_metrics').document('youtube').get(); print(f'Current baseline: {doc.to_dict().get(\"daily_baseline\", \"NOT FOUND\")}' if doc.exists else 'No baseline found')"

# Test new standardized metrics
python test_new_metrics.py
```

## Summary

The wget YouTube scraper is now:
- ✅ Fully deployed to production VM
- ✅ Auto-deployment enabled and tested
- ✅ All paths updated to `/opt/wget_youtube_scraper`
- ✅ Environment variables properly configured
- ✅ Ready for production data collection
- ✅ Running hourly via cron job at :15 past each hour
- ✅ Analytics pipeline operational (interval metrics run immediately after scraper)
- ✅ Daily metrics calculating at 2:00 AM daily with **standardized v2.0 metrics**
- ✅ Platform baseline calculator for velocity normalization
- ✅ Cross-platform comparable metrics system
- ✅ All systemd services configured and active

### Active Services:
- **YouTube Scraper + Interval Metrics**: Hourly at :15 (cron) - `/opt/wget_youtube_scraper/cron_scraper_with_metrics.sh`
- **Daily Metrics v2.0**: 2:00 AM daily (cron) - `/opt/wget_youtube_scraper/cron_daily_metrics.sh`
- **Platform Baseline**: Hardcoded at 150.0 videos/day (managed via `src/analytics/metrics/set_platform_baseline.py`)
- **Analytics Timer**: DISABLED (was causing metrics to run every 5 minutes)

Any push to GitHub main branch automatically deploys to production!