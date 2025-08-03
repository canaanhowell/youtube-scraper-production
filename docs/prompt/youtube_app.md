# YouTube App - Project Overview

## Purpose
A production-grade YouTube video scraper that collects trending videos for AI-related keywords, stores them in Firebase, and provides analytics on trending topics. The system runs on a dedicated VM with VPN rotation for reliable data collection.

## Core Architecture

### Technology Stack
- **Language**: Python 3.10+
- **Database**: Firebase Firestore
- **Cache**: Upstash Redis (REST API)
- **VPN**: Surfshark via WireGuard (24 US servers)
- **Container**: Docker with Gluetun for VPN management
- **Deployment**: GitHub Actions with auto-deployment
- **VM**: Ubuntu server at 134.199.201.56

### Key Components

#### 1. YouTube Collection Manager (`youtube_collection_manager.py`)
- **Purpose**: Orchestrates the entire collection process
- **Responsibilities**:
  - Manages VPN server rotation
  - Processes keywords from Firebase
  - Handles retry logic (3 attempts per keyword)
  - Tracks collection statistics
  - Logs results to Firebase
- **Key Features**:
  - Smart server selection (prioritizes working servers)
  - Exponential backoff for retries
  - Session-based tracking
  - Comprehensive error isolation

#### 2. YouTube Scraper Production (`youtube_scraper_production.py`)
- **Purpose**: Core scraping logic
- **Responsibilities**:
  - Fetches YouTube search results via VPN
  - Extracts video data from ytInitialData
  - Deduplicates using Redis
  - Saves videos to Firebase
- **Data Extracted**:
  - Video ID, title, URL
  - Thumbnail, duration, view count
  - Published time, channel name
  - Collection timestamp

#### 3. Firebase Client (`src/utils/firebase_client_enhanced.py`)
- **Purpose**: Firebase integration
- **Collections**:
  - `keywords`: Managed keywords list
  - `youtube_videos/{keyword}/videos`: Video data
  - `youtube_collection_logs`: Run statistics
  - `analytics/*`: Various analytics collections

#### 4. Redis Client (`src/utils/redis_client_enhanced.py`)
- **Purpose**: Caching and deduplication
- **Features**:
  - REST API fallback for Upstash
  - Native Redis support
  - 24-hour video ID caching
  - Connection pooling

## Project Structure

```
youtube_app/
├── youtube_collection_manager.py      # Main orchestrator
├── youtube_scraper_production.py      # Core scraping logic
├── docker-compose.yml                 # VPN container config
├── .env                              # Environment variables (gitignored)
├── src/
│   ├── analytics/                    # Analytics pipeline
│   │   ├── metrics/                  # Metric calculators
│   │   ├── aggregators/              # Data aggregators
│   │   └── visualizers/              # Visualization tools
│   ├── utils/                        # Utility modules
│   │   ├── firebase_client_enhanced.py
│   │   ├── redis_client_enhanced.py
│   │   ├── env_loader.py
│   │   ├── logging_config_enhanced.py
│   │   └── surfshark_servers.py
│   └── scripts/                      # Executable scripts
│       ├── collectors/               # Data collection scripts
│       ├── utilities/                # Utility scripts
│       └── validators/               # Validation scripts
├── deployment/
│   ├── scripts/                      # Deployment automation
│   │   ├── smart_deploy.sh          # Intelligent deployment
│   │   ├── backup_manager.py        # Backup/restore
│   │   └── service_detector.py      # Service detection
│   ├── systemd/                      # Service definitions
│   │   ├── youtube-scraper.service
│   │   └── youtube-analytics.service
│   └── *.sh                         # Various wrapper scripts
├── tests/                           # Test suites
├── monitoring/                      # Monitoring tools
├── security/                        # Security scanning
└── tools/                          # DevOps utilities
```

## Data Flow

1. **Keyword Management**:
   - Keywords stored in Firebase `keywords` collection
   - Each keyword has metadata (category, last_collected)

2. **Collection Process**:
   ```
   Keywords → VPN Rotation → YouTube Scrape → Deduplication → Firebase Storage
   ```

3. **Video Storage**:
   - Path: `youtube_videos/{keyword}/videos/{video_id}`
   - Includes all metadata + collection timestamp

4. **Analytics Pipeline**:
   - Runs separately via systemd service
   - Calculates trends, velocities, category metrics
   - Stores results in analytics collections

## VPN System

### Server Management
- 24 Surfshark US city servers
- Gluetun handles load balancing within cities
- Smart rotation with health tracking:
  - Working servers (successful connections)
  - Failed servers (connection failures)
  - Untested servers (not yet tried)

### Docker Integration
```yaml
# docker-compose.yml structure
services:
  gluetun:
    container_name: youtube-vpn
    environment:
      - VPN_SERVICE_PROVIDER=surfshark
      - VPN_TYPE=wireguard
      - SERVER_CITIES=us-nyc,us-lax,etc
```

## Environment Configuration

### Required Variables
```env
# Firebase
GOOGLE_SERVICE_KEY_PATH=/opt/youtube_app/ai-tracker-*.json
FIRESTORE_PROJECT_ID=ai-tracker-*

# Redis
UPSTASH_REDIS_REST_URL=https://your-redis.upstash.io
UPSTASH_REDIS_REST_TOKEN=your-token

# VPN (WireGuard)
SURFSHARK_PRIVATE_KEY=your-private-key
SURFSHARK_ADDRESS=10.14.0.2/16

# Settings
ENVIRONMENT=production
LOG_LEVEL=INFO
```

## Deployment System

### GitHub Actions
- **Trigger**: Push to main branch
- **Process**:
  1. SSH to VM
  2. Pull latest code
  3. Run smart deployment script
  4. Verify services

### Smart Deployment Features
- Detects changed components
- Creates automatic backups
- Updates only necessary services
- Rollback capability

### SystemD Services
- `youtube-scraper.service`: Main collection service
- `youtube-analytics.service`: Analytics processing
- Additional monitoring and security services

## Error Handling Philosophy

### No Fake Data Rule
```python
# Never do this:
except Exception:
    return {"name": "Unknown", "data": []}  # FORBIDDEN

# Always do this:
except Exception as e:
    logger.error(f"Operation failed: {e}")
    raise
```

### Isolation Strategy
- Keyword failures don't stop collection
- VPN failures trigger retry with different server
- Each component logs independently

## Logging System

### Structure
- **Main log**: `/opt/youtube_app/logs/scraper.log`
- **Service logs**: SystemD journal
- **Network log**: Separate file for API calls
- **Rotation**: 100MB files, 7-day retention

### Log Levels
- INFO: Normal operations
- WARNING: Recoverable issues
- ERROR: Failures requiring attention

## Analytics Components

### Metrics Calculated
- Keyword velocity (videos/hour)
- Trend acceleration
- Category aggregations
- Channel performance
- Time-based patterns

### Storage Pattern
- Raw data in `youtube_videos`
- Calculated metrics in `analytics/*`
- Historical tracking for trends

## Security Considerations

### Credentials
- All credentials in `.env` (gitignored)
- Firebase service account JSON (gitignored)
- Manual credential deployment to VM

### Network Security
- All requests through VPN
- Container isolation
- Rate limiting built-in

## Development Guidelines

### Code Standards
- Type hints required
- Comprehensive error handling
- Async for I/O operations
- No magic numbers
- Clear logging

### Testing Approach
- Unit tests for components
- Integration tests for VPN
- Manual testing on VM only
- Cannot test VPN locally

## Common Operations

### Manual Run
```bash
cd /opt/youtube_app && source venv/bin/activate
python youtube_collection_manager.py
```

### Check Status
```bash
# View cron schedule
crontab -l

# Check logs
tail -f logs/scraper.log
tail -f logs/cron.log
```

### Deploy Update
```bash
git push origin main  # Triggers auto-deployment
```

### Automation
- **Cron Job**: Runs hourly at :15 past the hour
- **Script**: `/opt/youtube_app/cron_scraper.sh`
- **Logs**: `/opt/youtube_app/logs/cron.log`

## Important Notes

1. **VM-Only Features**: VPN rotation requires VM environment
2. **Path Consistency**: All paths use `/opt/youtube_app`
3. **Credential Management**: Never commit credentials
4. **Scale Considerations**: Designed for 100x current load
5. **Monitoring**: Comprehensive logging and Firebase tracking

## Integration Points

### Firebase Collections
- `keywords`: Source keywords
- `youtube_videos`: Raw video data
- `youtube_collection_logs`: Run history
- `analytics/*`: Processed metrics

### External APIs
- YouTube (via web scraping)
- Upstash Redis (REST API)
- Firebase Admin SDK
- ipinfo.io (VPN verification)

This system is designed for reliable, scalable collection of YouTube data with proper error handling, monitoring, and deployment automation.