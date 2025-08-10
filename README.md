# YouTube App - Video Collection Service

## Overview
Enterprise-ready YouTube video collection service with automated deployment, VPN rotation, and multi-instance scaling.

## What This App Does
- **Collects** YouTube videos for 70+ AI-related keywords
- **Stores** video metadata in Firebase Firestore
- **Deduplicates** using Redis cache
- **Rotates** VPN servers for reliable access
- **Scales** with 3 parallel collection instances

## What This App Does NOT Do
- ❌ No metrics calculation
- ❌ No trend analysis
- ❌ No data aggregation
- ❌ No analytics pipeline
- ❌ Just pure video collection

## Recent Updates (2025-08-10)

### 🎯 ISO Timestamp Document IDs
- **NEW FORMAT**: Videos now use ISO 8601 timestamps as document IDs
- **EFFICIENT**: Enables fast time-range queries for interval metrics
- **EXAMPLE**: `2025-08-10T18:53:40.513000Z` instead of YouTube video ID
- **PRESERVED**: Original video ID still stored in 'id' field

### 🧹 Major Cleanup - Analytics Removal
- **SIMPLIFIED**: Removed all metrics and analytics code
- **FOCUSED**: App now only collects videos, no processing
- **DELETED**: ~40+ files, ~5,000+ lines of analytics code
- **UPDATED**: All deployment scripts and documentation

### 🔤 Reverse Alphabetical Keyword Processing
- **SORTED**: Keywords now processed Z to A (zapier → youtube → claude)
- **OPTIMIZED**: "claude code" runs before "claude" to prevent duplicates
- **CONSISTENT**: Same processing order every run regardless of Firestore variations

### 🚀 Production Features
- **Auto-Deployment**: Push to GitHub = automatic VM deployment
- **Staggered Collection**: 3 instances run every 10 minutes at :00/:03/:06
- **Smart VPN Rotation**: 24 US Surfshark servers with health tracking
- **Firebase Integration**: Real-time video data storage with timestamp-based IDs
- **Title Filtering**: Flexible keyword matching for multi-word terms

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/canaanhowell/youtube-scraper-production.git youtube_app
cd youtube_app
```

### 2. Local Setup (Development)
```bash
# Create .env file
cp environments/development.env .env
# Edit .env with your credentials

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Note: VPN functionality requires Docker and only works on VM
```

### 3. Deploy to Production
```bash
# Simply push to GitHub
git add .
git commit -m "Deploy to production"
git push origin main

# GitHub Actions will automatically deploy to VM
```

## Project Structure
```
youtube_app/
├── src/
│   ├── scripts/           # Collection scripts
│   ├── utils/             # Utilities (Firebase, Redis, VPN)
│   └── config/            # Configuration files
├── deployment/            # Deployment scripts
├── tests/                 # Test suite
├── docs/                  # Documentation
└── logs/                  # Application logs
```

## Environment Variables
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/path/to/firebase-key.json
FIRESTORE_PROJECT_ID=your-project-id

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN (VM only)
SURFSHARK_PRIVATE_KEY=your-wireguard-key
SURFSHARK_ADDRESS=10.14.0.2/16

# YouTube Settings
YOUTUBE_STRICT_TITLE_FILTER=true
```

## Production VM Access
```bash
# SSH to VM
ssh -i /workspace/droplet1 root@134.199.201.56

# Check logs
cd /opt/youtube_app
tail -f logs/scraper.log

# Check collection status
docker ps | grep youtube-vpn
```

## Collection Schedule
- **Every 10 minutes**, staggered across 3 instances:
  - Instance 1: :00, :10, :20, :30, :40, :50
  - Instance 2: :03, :13, :23, :33, :43, :53
  - Instance 3: :06, :16, :26, :36, :46, :56

## Firebase Collections Used
- `youtube_keywords` - Read keywords to collect
- `youtube_videos/{keyword}/videos` - Store collected videos
- `youtube_collection_logs` - Log collection runs

## Testing
```bash
# Run unit tests
python -m pytest tests/unit/

# Run integration tests (requires credentials)
python -m pytest tests/integration/

# Run all tests
./tests/run_all_tests.sh
```

## Troubleshooting

### VPN Issues
```bash
# Check VPN container
docker logs youtube-vpn-1

# Restart VPN
docker restart youtube-vpn-1
```

### Collection Issues
```bash
# Check recent errors
grep ERROR logs/error.log | tail -20

# Test single keyword
python src/scripts/youtube_collection_manager_simple.py --instance 1 --test
```

## Contributing
1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License
Proprietary - All rights reserved

## Support
- Repository: https://github.com/canaanhowell/youtube-scraper-production
- Documentation: `/docs/context/`
- Logs: `/opt/youtube_app/logs/` (on VM)