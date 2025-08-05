# YouTube App

## Overview
Enterprise-ready YouTube data collection app with automated deployment, VPN rotation, and comprehensive analytics.

## Recent Updates (2025-08-04)

### 🔄 Production System Active
- Successfully deployed with standardized v2.0 metrics system
- Platform baseline simplified to hardcoded approach (150 videos/day)
- All analytics pipelines operational on production VM
- Auto-deployment fully configured and tested

### 🚀 Production Features
- **Auto-Deployment**: Push to GitHub = automatic VM deployment
- **Hourly Collection**: Cron job runs at :15 past each hour
- **Smart VPN Rotation**: 24 US Surfshark servers with health tracking
- **Firebase Integration**: Real-time data storage and analytics
- **Standardized Metrics v2.0**: Platform-normalized velocity scoring
- **Title Filtering**: Strict keyword matching for improved data quality

### 🔧 Latest Improvements (2025-08-04)
- **NEW**: Simplified platform baseline system (hardcoded approach)
- **Enhanced Metrics**: Platform-normalized velocity scoring operational
- **Streamlined Management**: Manual baseline control via simple script
- **Production Ready**: All systems deployed and verified on VM
- **Documentation Updated**: All docs reflect current system architecture
- Zero-downtime deployment verified
- Enhanced analytics pipeline with v2.0 standardized metrics

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/canaanhowell/youtube-scraper-production.git youtube_app
cd youtube_app
```

### 2. Local Setup (Development)
```bash
# Create .env file (copy from environments/development.env)
ln -s environments/development.env .env

# Update .env with your Firebase credentials path
vim .env
# Set: GOOGLE_SERVICE_KEY_PATH=/path/to/your/firebase.json

# Install dependencies
pip install -r requirements.txt
```

### 3. Deploy to Production
```bash
# Push to GitHub (triggers automatic deployment)
git push origin main

# SSH to VM and add .env (first time only)
ssh -i /path/to/key root@134.199.201.56
cd /opt/youtube_app
vim .env  # Add production credentials

# Deployment is now automatic and simplified:
# ✅ No Git operations on production VM
# ✅ Artifact-based deployment
# ✅ Automatic health checks
# ✅ Zero-downtime updates
```

## Project Structure
```
youtube_app/
├── youtube_collection_manager.py    # Main scraper orchestrator
├── youtube_scraper_production.py    # Core YouTube scraping logic
├── src/
│   ├── utils/                      # Utilities (Firebase, Redis, logging)
│   ├── analytics/                  # Analytics pipeline
│   └── scripts/                    # Executable scripts
├── deployment/
│   ├── scripts/                    # Deployment automation
│   └── systemd/                    # Service configurations
├── environments/                   # Environment configurations
│   ├── development.env
│   └── production.env
└── .github/
    └── workflows/
        └── auto-deploy.yml         # GitHub Actions automation
```

## Key Features

### 🌐 VPN Infrastructure
- 24 verified US Surfshark servers
- Automatic rotation and health tracking
- Docker-based Gluetun container
- Per-keyword isolation

### 📊 Data Pipeline
- Firebase Firestore storage
- Redis caching with 24-hour TTL
- Comprehensive analytics
- Real-time metrics

### 🚀 Deployment
- **Simplified 3-Phase Process**: Infrastructure → GitHub → Monitor
- **Artifact-Based**: No Git operations on production VM
- **Smart Detection**: Only updates changed components
- **Zero-Downtime**: Graceful service restarts
- **Auto-Rollback**: Automatic rollback on deployment failure
- **Health Checks**: Automatic verification post-deployment

### 🔒 Security
- Credentials in environment variables
- `.env` and Firebase keys gitignored
- VPN for anonymity
- Rate limiting and retry logic

## Configuration

### Environment Variables (.env)
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/path/to/firebase.json
FIRESTORE_PROJECT_ID=your-project-id

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN WireGuard Configuration
SURFSHARK_PRIVATE_KEY=your-wireguard-private-key
SURFSHARK_ADDRESS=10.14.0.2/16

# App Settings
ENVIRONMENT=production
LOG_LEVEL=INFO

# YouTube Scraper Settings
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title (default: true)
                                  # Set to false to collect all videos from search results
```

## Deployment

### Automatic (Recommended)
1. Push to `main` branch
2. GitHub Actions deploys automatically via artifact-based deployment
3. SSH to VM and add `.env` file (first time only)

### Manual (Emergency Only)
```bash
# Only use if automatic deployment fails
ssh root@134.199.201.56
cd /opt/youtube_app

# Rollback using backup manager
python3 deployment/scripts/backup_manager.py rollback

# Or manual service restart
sudo systemctl restart youtube-scraper
```

## Monitoring

### Check Status
```bash
# View cron schedule
crontab -l

# Check recent logs
tail -f logs/scraper.log
tail -f logs/cron.log

# View collection metrics
python3 src/scripts/utilities/get_firebase_stats.py
```

### View Metrics
```bash
# Check collection logs in Firebase
python3 src/scripts/validators/check_collection.py

# Monitor VPN IP diversity
python3 src/scripts/utilities/monitor_vpn_ips.py
```

## Troubleshooting

### Common Issues

1. **"Service account file not found"**
   - Ensure `.env` has correct `GOOGLE_SERVICE_KEY_PATH`
   - Verify Firebase JSON file exists at that path

2. **"No such file or directory: /opt/youtube_app"**
   - Project renamed to `youtube_app`
   - Update any scripts using old path

3. **VPN Connection Failed**
   - VPN only works on VM with Docker
   - Cannot test VPN locally

4. **Title Filtering Issues**
   - Check `YOUTUBE_STRICT_TITLE_FILTER` setting in `.env`
   - Set to `true` for strict keyword matching (recommended)
   - Set to `false` to collect all search results

### Logs
- Application: `logs/scraper.log`
- Errors: `logs/error.log`
- Network: `logs/network.log`

## Repository
https://github.com/canaanhowell/youtube-scraper-production