# Updated YouTube Section for Master Documentation

This file contains the updated YouTube section that should replace the existing section in `/workspace/master_docs/all_formulas_and_data_flows.md`

---

## 🎥 YouTube Video Collection Service (Collection Only - Updated August 8, 2025)

**Current System:**
- **youtube_app** (Alpine-based): Multi-instance wget video collection service
- **Location**: `/opt/youtube_app` on VM (IP: 134.199.201.56)
- **Keywords**: 76 active keywords with reverse alphabetical processing (40+ successful daily)
- **Collection**: 3 parallel instances with staggered scheduling every 10 minutes
- **Performance**: ~986+ videos collected daily with ~95% success rate
- **Filtering**: Flexible space matching (e.g., "grok 3" matches "Grok3", "grok-3")
- **Focus**: Video collection ONLY - no metrics, analytics, or processing
- **Logging**: Fixed August 8, 2025 - now accurately reports collection statistics

### YouTube Collection Manager (Every 10 minutes, staggered)
**Script**: `src/scripts/youtube_collection_manager.py`
**Schedule**: Every 10 minutes across 3 instances (staggered at :00/:03/:06, :10/:13/:16, etc.)
**System**: youtube_app with 3 parallel VPN containers (youtube-vpn-1/2/3)

#### Data Flow:
```
YouTube Search (via VPN)
    ↓
[Searches for keywords with flexible matching]
    ↓
youtube_videos/{keyword}/videos/{video_id} ← NEW VIDEOS ONLY
    │
    └─ Fields saved:
        - video_id, title, url
        - channel_name, channel_id  
        - view_count, duration
        - published_time_text
        - thumbnail_url
        - collected_at, keyword
    ↓
youtube_collection_logs/{timestamp_id} ← CREATES LOG ENTRY 
    │
    └─ Format: collection_YYYY-MM-DD_HH-MM-SS_UTC
        - session_id, keywords_processed
        - total_videos_collected, success_rate
        - duration_seconds, container info
```

#### Collection Logic:
```python
# Flexible Space Matching (YOUTUBE_STRICT_TITLE_FILTER=true)
# Multi-word keywords match all variants automatically
def title_contains_keyword(title, keyword):
    title_lower = title.lower()
    keyword_lower = keyword.lower()
    
    # Check exact match
    if keyword_lower in title_lower:
        return True
    
    # Check hyphenated variant (for multi-word keywords)
    if ' ' in keyword_lower:
        hyphenated = keyword_lower.replace(' ', '-')
        if hyphenated in title_lower:
            return True
    
    # Check no-space variant
    if ' ' in keyword_lower:
        no_space = keyword_lower.replace(' ', '')
        if no_space in title_lower:
            return True
    
    return False

# Deduplication with instance-specific Redis keys
redis_key = f"instance_{instance_id}:video:{video_id}"
is_duplicate = redis_client.exists(redis_key)

# Multi-instance keyword distribution
total_keywords = get_active_keywords()
keywords_per_instance = math.ceil(len(total_keywords) / 3)
instance_keywords = total_keywords[(instance_id-1)*keywords_per_instance : instance_id*keywords_per_instance]
```

**⚠️ MAJOR CHANGE: Analytics Removed (August 8, 2025)**
- **All metrics calculation scripts REMOVED**
- **No interval metrics processing**  
- **No daily metrics aggregation**
- **No category snapshots or time windows**
- **No trend analysis or velocity calculations**
- **Video collection data is stored but NOT processed locally**

**Analytics Status**: Video data is collected and stored in Firebase but requires **separate analytics service** for processing. The youtube_app is now a **pure collection service**.

### Performance Metrics (Collection Only)
- **Collection Speed**: ~81 seconds for 24 keywords per instance
- **Success Rate**: ~95% (accurately tracked as of August 8, 2025)
- **Daily Performance**: ~986+ videos collected daily, 40+ successful keywords
- **Videos Collected**: 50-100+ videos per run (varies by keyword activity)
- **Duplication Rate**: 2.22% cross-keyword duplicates (expected behavior)
- **VPN Health**: All 3 containers healthy and rotating
- **Redis Deduplication**: Instance-specific namespacing prevents false duplicates

### Schedule (Cron-based)
```bash
# Instance 1 - Every 10 minutes at :00
0,10,20,30,40,50 * * * * youtube_collector_1.sh

# Instance 2 - Every 10 minutes at :03  
3,13,23,33,43,53 * * * * youtube_collector_2.sh

# Instance 3 - Every 10 minutes at :06
6,16,26,36,46,56 * * * * youtube_collector_3.sh

# Log cleanup - Sundays at 3 AM UTC
0 3 * * 0 find logs/ -name '*.log' -mtime +5 -delete
```

**Note for Analytics Integration**: External analytics services can read from:
- `youtube_videos/{keyword}/videos/*` - Raw video data
- `youtube_collection_logs/*` - Collection run statistics
- `youtube_keywords` - Keyword configuration (read-only)

---

## System Architecture (Updated August 8, 2025)

### YouTube Collection System
- **Method**: wget-based scraping (no browser automation)
- **Architecture**: 3 parallel instances with VPN containers
- **Deployment**: Automated via GitHub Actions
- **Repository**: https://github.com/canaanhowell/youtube-scraper-production
- **Status**: ✅ Production stable, fully operational (collection only)

### Infrastructure
- **VM**: DigitalOcean 4 vCPU, 8GB RAM (IP: 134.199.201.56)
- **VPN**: 3 Surfshark WireGuard containers with 24 US servers
- **Database**: Firebase Firestore (video storage only)
- **Cache**: Upstash Redis (deduplication only)
- **Monitoring**: Log files only (no metrics dashboards)