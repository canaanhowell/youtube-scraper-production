# YouTube App - Video Collection Service

## Executive Summary

The YouTube App is a production-ready video collection service that continuously monitors YouTube for AI-related videos. It provides automated keyword-based video discovery with VPN rotation for reliable access.

**Key Value Propositions:**
- Automated discovery of AI-related videos across 70+ active keywords
- VPN-based collection with 24 US server rotation for reliability
- Flexible keyword matching with automatic space handling
- Multi-instance parallel collection with staggered scheduling
- Enterprise-grade architecture with 100x scale design

## System Architecture

### Technical Stack
- **Language**: Python 3.10+
- **Database**: Firebase Firestore (NoSQL) - Video storage only
- **Cache**: Upstash Redis (REST API) - Deduplication only
- **Runtime**: Ubuntu VM (DigitalOcean Droplet)
- **Collection**: wget-based HTTP scraping (20 videos/keyword)
- **VPN**: Surfshark via WireGuard (24 US servers)
- **Container**: Docker with Gluetun for VPN management
- **Deployment**: GitHub Actions auto-deployment

### Infrastructure
- **VM Details**:
  - IP: 134.199.201.56
  - Specs: 4 vCPU, 8GB RAM
  - OS: Ubuntu (latest)
- **Access**: SSH via private key (`/workspace/droplet1`)
- **Python Environment**: Virtual environment at `/opt/youtube_app/venv`
- **Repository**: https://github.com/canaanhowell/youtube-scraper-production

### Project Structure

```
youtube_app/
├── src/
│   ├── scripts/
│   │   ├── youtube_collection_manager.py      # Main orchestrator
│   │   ├── youtube_collection_manager_simple.py # Multi-instance version
│   │   ├── youtube_scraper_production.py      # Core scraping logic
│   │   └── collectors/
│   │       └── run_scraper.py                 # Scraper entry point
│   ├── utils/                                 # Shared utilities
│   │   ├── env_loader.py
│   │   ├── logging_config_enhanced.py
│   │   ├── firebase_client_enhanced.py        # Video storage only
│   │   ├── redis_client_enhanced.py           # Deduplication only
│   │   ├── collection_logger.py
│   │   ├── surfshark_servers.py
│   │   └── wireguard_manager.py
│   └── config/
│       └── category_mapping.json
├── deployment/                                # Deployment scripts
│   ├── scripts/
│   │   ├── smart_deploy.sh
│   │   ├── service_detector.py
│   │   ├── backup_manager.py
│   │   └── health_check.sh
│   ├── youtube_scraper_wrapper.sh
│   ├── youtube_collector_1.sh
│   ├── youtube_collector_2.sh
│   └── youtube_collector_3.sh
├── tests/                                     # Test suite
│   ├── unit/
│   ├── integration/
│   └── performance/
├── docs/
│   └── context/                              # Project documentation
│       ├── youtube_app.md
│       ├── log.md
│       └── firestore_mapping.md
├── logs/                                      # Application logs
├── docker-compose.yml                         # VPN container config
├── docker-compose-multi.yml                   # Multi-VPN config
├── requirements.txt                           # Python dependencies
├── .env                                       # Environment variables (gitignored)
└── ai-tracker-466821-*.json                   # Service account key (gitignored)
```

## Core Functionality

### Video Discovery
- Searches YouTube for 70+ AI-related keywords every 10 minutes
- Collects video metadata: title, views, channel, duration, upload date
- Flexible space-aware title filtering (YOUTUBE_STRICT_TITLE_FILTER=true)
  - Multi-word keywords match all variants: "grok 3" matches "Grok 3", "Grok3", and "grok-3"
  - Eliminates false matches where words appear in wrong order
- Instance-specific Redis deduplication (24-hour cache with namespacing)
- VPN rotation for reliable access across 3 parallel containers

## Development Guidelines

### Core Principles (NO EXCEPTIONS)

1. **No Fake Data - EVER**
   - Errors are always preferred over mock/placeholder data
   - If real data cannot be obtained, throw an error
   - Never fabricate video counts or metadata

2. **100x Scale Test**
   - Every line of code must work at 100x current scale
   - Will this work with 100x more keywords?
   - Will this work with 100x more videos?
   - Will this work with 100x more requests?

3. **Root Cause Only**
   - Fix the cause, not the symptom
   - Use 5-Why analysis for every issue
   - No temporary workarounds

### Code Standards
- Type hints required on all functions
- Comprehensive error handling with logging
- Async for all I/O operations
- No magic numbers - use constants
- Clear logging at INFO level minimum

## Data Flow Pipeline

```
YouTube Search (via VPN)
    ↓ (every 10 minutes)
youtube_collection_manager.py
    ↓ (deduplication check)
youtube_videos/{keyword}/videos collection
    ↓
youtube_collection_logs (audit trail)
```

## Environment Configuration

### Required Environment Variables
```bash
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
YOUTUBE_STRICT_TITLE_FILTER=true  # Only collect videos with keyword in title (default: true)
```

## Primary Scripts

### youtube_collection_manager.py

**Purpose**: Orchestrates YouTube video collection across all keywords

**Schedule**: Every 10 minutes (staggered across 3 instances)

**Firebase Collections Used**:
- **READS** from `youtube_keywords` - Gets active keywords
- **WRITES** to `youtube_videos/{keyword}/videos` - Stores video metadata
- **WRITES** to `youtube_collection_logs` - Logs collection runs

### youtube_scraper_production.py

**Purpose**: Core scraping logic using wget

**Features**:
- wget-based collection (no browser needed)
- Flexible keyword matching for multi-word terms
- VPN IP rotation
- Redis deduplication
- Structured logging

## Schedule Summary

### Multi-Instance Collection (Every 10 minutes)
- **Instance 1**: Runs at :00, :10, :20, :30, :40, :50 (youtube-vpn-1)
- **Instance 2**: Runs at :03, :13, :23, :33, :43, :53 (youtube-vpn-2)  
- **Instance 3**: Runs at :06, :16, :26, :36, :46, :56 (youtube-vpn-3)

Each instance processes ~24 keywords, collecting up to 20 videos per keyword.

## VPN System

### Architecture
- **Provider**: Surfshark via WireGuard
- **Servers**: 24 US city servers
- **Containers**: 3 Docker containers with Gluetun
- **Rotation**: Smart server selection with health tracking

### Server Management
- Working servers (successful connections)
- Failed servers (connection failures)
- Untested servers (not yet tried)
- Automatic retry with different server on failure

## Deployment & Operations

### GitHub Actions Auto-Deployment

1. **Architecture**:
   - GitHub Actions CI/CD pipeline
   - Artifact-based deployment (no Git on VM)
   - Automatic health checks
   - Zero-downtime deployments

2. **Deployment Process**:
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main  # Triggers auto-deployment
   ```

3. **VM Access**:
   ```bash
   ssh -i /workspace/droplet1 root@134.199.201.56
   ```

### Monitoring

1. **Log Files**:
   - `/opt/youtube_app/logs/scraper.log` - Collection logs
   - `/opt/youtube_app/logs/collector_*.log` - Instance-specific logs
   - `/opt/youtube_app/logs/error.log` - Error logs
   - `/opt/youtube_app/logs/network.log` - API requests

2. **Health Checks**:
```bash
# Check collection status
tail -f /opt/youtube_app/logs/scraper.log

# Check cron jobs
crontab -l

# View VPN status
docker ps | grep youtube-vpn
```

## Performance & Scaling

### Current Performance Metrics
- **Active Keywords**: 70+ keywords
- **Videos per Collection**: 10-20 new videos per keyword
- **Collection Time per Instance**: ~75 seconds (processing 24 keywords each)
- **Total Collection Time**: <2 minutes for all keywords across 3 instances
- **VPN Containers**: 3 parallel containers
- **Redis Deduplication**: Instance-specific namespacing prevents false duplicates

### Scaling Limits
- **Keywords**: Designed for 100+ keywords
- **Videos**: Can handle millions of videos
- **VPN Servers**: 24 servers provide redundancy
- **Database**: Firestore scales automatically
- **Cache**: Redis handles deduplication efficiently

## Security & Access

### Credentials Management
- **Service Account**: JSON file, never in code
- **Redis Token**: Environment variable only
- **VPN Keys**: WireGuard private key secured
- **VM Access**: SSH key authentication only

### Security Best Practices
- No credentials in code or logs
- All sensitive data in `.env` file
- `.env` and service account files gitignored
- VPN provides anonymity for collection
- Container isolation for VPN

## Testing & Quality

### Test Coverage
- **Unit Tests**: Core functionality coverage
- **Integration Tests**: Firebase and Redis integration
- **VPN Tests**: IP rotation verification
- **Performance Tests**: Load and stress testing

### Quality Metrics
- **Success Rate**: >95% collection success
- **Data Quality**: Title filtering ensures relevance
- **Uptime**: 99.9%+ with VPN redundancy
- **Data Accuracy**: 100% (no fake data)

## Troubleshooting Guide

### Common Issues

1. **VPN Connection Failed**:
   - Check Docker container status
   - Verify WireGuard credentials
   - Try different server in rotation

2. **No Videos Found**:
   - Check if YouTube changed HTML structure
   - Verify VPN is working (check IP)
   - Check keyword exists on YouTube

3. **Redis Connection Issues**:
   - Verify Redis credentials
   - Check network connectivity
   - Ensure REST URL is correct

### Debug Commands

```bash
# Check VPN status
docker ps | grep youtube-vpn
docker logs youtube-vpn-1

# Test collection for one keyword
cd /opt/youtube_app && source venv/bin/activate
python src/scripts/youtube_collection_manager_simple.py --instance 1 --test

# Check Firebase connection
python -c "from src.utils.firebase_client_enhanced import FirebaseClient; 
f = FirebaseClient(); print('Connected' if f.db else 'Failed')"

# View recent errors
grep ERROR /opt/youtube_app/logs/error.log | tail -20
```

## Key Design Decisions

1. **Title Filtering**: Optional keyword-in-title requirement
   - **Why**: Improves data quality and relevance

2. **VPN Rotation**: 24 US servers with smart selection
   - **Why**: Reliability and anonymity

3. **Multi-Instance Collection**: 3 parallel instances
   - **Why**: Scalability without overloading

4. **Redis Deduplication**: 24-hour cache
   - **Why**: Prevents duplicate videos while allowing re-discovery

5. **Collection Only**: No metrics or analytics
   - **Why**: Single responsibility, focused service

## Integration Points

### With Other Systems
- **Shared Firebase**: Same project as Reddit and PH apps
- **Keywords Source**: Synced with other collection systems

### Firebase Collections
- `youtube_keywords` - Source keywords (read only)
- `youtube_videos/{keyword}/videos` - Video storage
- `youtube_collection_logs` - Audit trail

## Maintenance Notes

### Regular Tasks

1. **Daily**: Check collection success rate
2. **Weekly**: Review VPN server performance
3. **Monthly**: Clean up old logs
4. **Quarterly**: Review keyword performance

### Update Procedures

1. Test locally if possible (limited due to VPN)
2. Deploy via GitHub push to main
3. Monitor logs for 24 hours
4. Rollback if issues arise

## Contact & Support

- **Repository**: https://github.com/canaanhowell/youtube-scraper-production
- **Documentation**: `/workspace/youtube_app/docs/`
- **VM Access**: SSH key at `/workspace/droplet1`
- **Logs**: `/opt/youtube_app/logs/`

---

*Last Updated: 2025-08-08*
*Document Version: 3.0 - Simplified to collection-only service*