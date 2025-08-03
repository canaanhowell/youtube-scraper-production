# YouTube Scraper Production System

## Overview
Enterprise-ready YouTube scraper with automated deployment, VPN rotation, and comprehensive analytics.

## Recent Updates (2025-08-03)

### 🔄 Project Renamed
- Changed from `youtube_scraper` to `youtube_app`
- Updated all paths to use new name
- Dynamic path detection for local vs VM environments

### 🚀 Smart Auto-Deployment
- Push to GitHub = automatic deployment to VM
- Intelligent file change detection
- Service auto-discovery and configuration
- Automatic backup and rollback on failure

### 🔧 Key Improvements
- Firebase credentials via file path in `.env`
- Dynamic logging paths (local: `./logs`, VM: `/opt/youtube_app/logs`)
- Simplified deployment process
- Better error handling

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
# Push to GitHub (triggers auto-deployment)
git push origin main

# SSH to VM and add .env
ssh -i /path/to/key root@134.199.201.56
cd /opt/youtube_app
vim .env  # Add production credentials
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
- GitHub Actions CI/CD
- Smart file change detection
- Automatic service management
- Backup and rollback capabilities

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
```

## Deployment

### Automatic (Recommended)
1. Push to `main` branch
2. GitHub Actions deploys automatically
3. SSH to VM and add `.env` file

### Manual
```bash
ssh root@134.199.201.56
cd /opt/youtube_app
git pull
pip install -r requirements.txt
sudo systemctl restart youtube-scraper
```

## Monitoring

### Check Status
```bash
sudo systemctl status youtube-scraper
tail -f logs/scraper.log
```

### View Metrics
```bash
# Check collection logs in Firebase
python3 src/scripts/utilities/check_collection.py

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

### Logs
- Application: `logs/scraper.log`
- Errors: `logs/error.log`
- Network: `logs/network.log`

## Repository
https://github.com/canaanhowell/youtube-scraper-production