# YouTube App - Production System Log

## Core Instructions for Coding Agents

You are a coding agent working with a production-ready YouTube video collection system.
You have 2 rules:
**1. No tech debt** - If a problem arises, we provide the long-term solution right away.
**2. No data fabrication** - Errors always preferred over mock data or fallback placeholders.

## Project Overview

- **Project Name**: youtube_app (Alpine-based wget collection)
- **Purpose**: Collect YouTube videos for AI-related keywords
- **Database**: Firebase Firestore (video storage only)
- **Caching**: Upstash Redis with REST API client (deduplication)
- **Runtime**: Python 3.10+ on Alpine Linux VM
- **Deployment**: GitHub Actions auto-deployment on push to main
- **VM**: SSH to VM using `/workspace/droplet1` (private key) - IP: 134.199.201.56
- **Location**: `/opt/youtube_app` on VM
- **Repository**: https://github.com/canaanhowell/youtube-scraper-production

## Current Status (2025-08-10 - Updated)

### 🚀 **Collection-Only Service Active and Operational**

The YouTube app has been transformed into a lean video collection service:

✅ **System Status**:
- **VM**: Running at 134.199.201.56 - 4 vCPU, 8GB RAM
- **Project Path**: `/opt/youtube_app/`
- **VPN System**: 3 VPN containers (youtube-vpn-1, youtube-vpn-2, youtube-vpn-3) with staggered access
- **Collection**: 3 instances processing keywords in parallel
- **Firebase**: Connected for video storage only
- **Redis**: Upstash Redis REST API for deduplication
- **Deployment**: GitHub Actions auto-deployment ACTIVE
- **Collection Method**: wget-based (20 videos per keyword)
- **Collection Schedule**: Every 10 minutes via cron (staggered multi-instance)
- **Keywords**: 68 active keywords sorted in reverse alphabetical order
- **Daily Performance**: ~1,600+ videos collected daily
- **Success Rate**: ~95% actual performance (now accurately reported in logs)

### 🔧 **Latest Updates (2025-08-10)**:

**🎯 ISO Timestamp Document IDs with Keyword Suffix - IMPLEMENTED**:
- ✅ **Document ID Format Updated**: Now using ISO 8601 timestamps with keyword suffix as document IDs
- ✅ **Format**: `2025-08-10T18:53:40.513000Z_chatgpt` instead of just timestamp
- ✅ **Purpose**: Prevents collisions when multiple keywords have videos at the same timestamp
- ✅ **Implementation**: Updated `_save_to_firebase()` in youtube_scraper_production.py
- ✅ **Benefits**: 
  - Firestore can use `.order_by('__name__').start_at()` for fast filtering
  - No collisions between keywords collecting videos at the same timestamp
- ✅ **Video ID Preserved**: Original YouTube video ID still stored in 'id' field
- ✅ **Duplicate Check**: Still queries by video ID field, not affected by document ID change

### 🔧 **Previous Updates (2025-08-08)**:

**🔧 Collection Logging Statistics Fix - DEPLOYED**:
- ✅ **Fixed Logging Issue**: Collection logs now show accurate success metrics
- ✅ **Problem Resolved**: Previously showed 0% success rate despite collecting 986+ videos daily
- ✅ **Success Tracking Fixed**: Keywords_successful now shows ~40 keywords vs 0
- ✅ **Performance Metrics**: Success rate now displays ~95% vs 0%
- ✅ **Fields Added**: script_name, keywords_failed, instance_id, vm_hostname
- ✅ **Root Cause**: Exception handling was preventing success statistics from being recorded
- ✅ **Impact**: Collection logs now accurately reflect excellent system performance

**📊 Duplicate Analysis - VALIDATED**:
- ✅ **Audit Completed**: Comprehensive duplicate analysis of 1,397 videos
- ✅ **Low Duplication**: Only 2.22% duplication rate (31 duplicates)
- ✅ **Expected Behavior**: All duplicates are cross-keyword (ChatGPT videos under both "chatgpt" and "grok")
- ✅ **Redis Working**: Zero same-keyword duplicates, deduplication system functioning correctly
- ✅ **Content Quality**: Cross-keyword duplicates indicate good semantic matching

**🧹 Major Cleanup - Analytics Removal**:
- ✅ **Removed All Analytics**: Deleted all metrics calculation and aggregation code
- ✅ **Simplified Focus**: App now only collects videos, no processing or analytics
- ✅ **Deleted Components**:
  - Entire `src/analytics/` directory tree
  - All metrics calculation scripts
  - All aggregation and visualization code
  - Analytics deployment scripts
  - Metrics-related cron jobs
- ✅ **Updated Components**:
  - Deployment scripts now only reference youtube-scraper service
  - Health checks simplified to test collection only
  - Documentation updated to reflect collection-only focus

**🎯 Flexible Space Matching Implementation - DEPLOYED**:
- ✅ **Enhanced Keyword Matching**: Added flexible space handling for multi-word keywords
- ✅ **Issue Addressed**: Keywords like "grok 3" were missing videos titled "Grok3" or "grok-3"
- ✅ **Solution**: Updated `_title_contains_keyword()` method to check three variants:
  - Exact match: "grok 3" matches "Grok 3 Release"
  - Hyphenated: "grok 3" matches "grok-3 demo"
  - No-space: "grok 3" matches "Grok3 Features"
- ✅ **Impact**: Captures more relevant videos without changing Firebase keywords

**🎯 Service Key Update & Cleanup - COMPLETED**:
- ✅ **Updated Service Key**: Replaced Firebase service account key
- ✅ **Fixed Hardcoded Paths**: All scripts now use GOOGLE_SERVICE_KEY_PATH from .env
- ✅ **Verified**: Firebase connection working with new key

**🎯 Keyword Ordering Enhancement - DEPLOYED**:
- ✅ **Reverse Alphabetical Sorting**: Keywords now processed Z to A
- ✅ **Purpose**: Ensures "claude code" runs before "claude" to prevent duplicates
- ✅ **Dynamic**: Works for all keywords without hardcoding

## Key Features

### 🎯 **Video Collection Only**
1. **Search YouTube** for AI-related keywords
2. **Filter** videos by title matching
3. **Store** video metadata in Firebase
4. **Deduplicate** using Redis cache
5. **Log** collection runs

### 📁 **Simplified Project Structure**
```
youtube_app/
├── src/
│   ├── scripts/
│   │   ├── youtube_collection_manager.py      # Main orchestrator
│   │   ├── youtube_collection_manager_simple.py # Multi-instance version
│   │   ├── youtube_scraper_production.py      # Core scraping logic
│   │   └── collectors/
│   │       └── run_scraper.py                 # Scraper entry point
│   ├── utils/                                 # Utilities
│   │   ├── env_loader.py                      
│   │   ├── logging_config_enhanced.py         
│   │   ├── firebase_client_enhanced.py        # Video storage only
│   │   ├── redis_client_enhanced.py           # Deduplication only
│   │   └── wireguard_manager.py               # VPN management
│   └── config/
│       └── category_mapping.json
├── deployment/
│   ├── scripts/
│   │   ├── smart_deploy.sh          
│   │   ├── health_check.sh          
│   │   └── backup.sh
│   └── youtube_scraper_wrapper.sh
├── .github/
│   └── workflows/
│       └── auto-deploy.yml          
└── .env                             
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

# 3. SSH to VM for monitoring
ssh -i /workspace/droplet1 root@134.199.201.56
cd /opt/youtube_app
```

### 📊 **Monitor Collection**
```bash
# Check collection logs for all instances
tail -f logs/collector_1.log logs/collector_2.log logs/collector_3.log

# View main scraper log
tail -f logs/scraper.log

# Check VPN containers status
docker ps | grep youtube-vpn

# Check cron jobs
crontab -l
```

## Important Notes

### ⚠️ **Collection Focus**
- This app ONLY collects videos
- No metrics calculation
- No trend analysis
- No aggregations
- Just pure video data collection

### ✅ **Firebase Collections Used**
- `youtube_keywords` - Read only for active keywords
- `youtube_videos/{keyword}/videos` - Write video data
- `youtube_collection_logs` - Write collection run logs

### 📝 **Required Environment Variables**
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/opt/youtube_app/ai-tracker-466821-bc88c21c2489.json
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
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title
```

## Collection Schedule

### Multi-Instance Collection (Every 10 minutes)
- **Instance 1**: Runs at :00, :10, :20, :30, :40, :50 (youtube-vpn-1)
- **Instance 2**: Runs at :03, :13, :23, :33, :43, :53 (youtube-vpn-2)  
- **Instance 3**: Runs at :06, :16, :26, :36, :46, :56 (youtube-vpn-3)

Each instance processes ~24 keywords, collecting up to 20 videos per keyword.

## Summary

The youtube_app is now a lean, focused video collection service that:
- ✅ Collects YouTube videos for AI-related keywords
- ✅ Uses VPN for reliable access
- ✅ Stores video metadata in Firebase
- ✅ Prevents duplicates with Redis
- ✅ Runs continuously via cron
- ❌ Does NOT calculate metrics
- ❌ Does NOT analyze trends
- ❌ Does NOT aggregate data

Any push to GitHub main branch automatically deploys to production!