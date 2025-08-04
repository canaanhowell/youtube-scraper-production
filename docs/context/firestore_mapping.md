# Firestore Collections Mapping - YouTube App

This document provides a comprehensive mapping of all Firestore collections used by the YouTube application.

## Overview

The YouTube app uses Firebase Firestore as its primary database with the following collections:
- `youtube_keywords` - Keyword configuration and daily metrics
- `youtube_videos` - Raw video data organized by keyword
- `youtube_keywords_interval_metrics` - Hourly metrics calculations
- `youtube_categories` - Category-level aggregated metrics
- `youtube_collection_logs` - Audit trail for collection runs

## Collection Details

### 1. youtube_keywords

**Purpose**: Stores keyword configuration and daily aggregated metrics

**Document ID**: Keyword name (lowercase, hyphenated)

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `keyword` | string | The search keyword | "claude" |
| `category` | string | Keyword category | "ai_chatbots" |
| `active` | boolean | Whether keyword is actively collected | true |
| `created_at` | timestamp | When keyword was added | 2025-07-15T10:00:00Z |
| `updated_at` | timestamp | Last update time | 2025-08-04T14:00:00Z |
| `last_collected` | timestamp | Last successful collection | 2025-08-04T14:15:00Z |
| `source` | string | How keyword was added | "manual" or "product_hunt_sync" |
| `rolling_velocity_24h` | number | 24-hour rolling average velocity | 12.5 |
| `rolling_acceleration_24h` | number | 24-hour rolling acceleration | 0.8 |
| `rolling_velocity_7d` | number | 7-day rolling average velocity | 10.2 |
| `rolling_acceleration_7d` | number | 7-day rolling acceleration | -0.5 |
| `last_interval_update` | timestamp | Last interval metrics update | 2025-08-04T14:00:00Z |
| `daily_metrics` | map | Daily metrics by date | See structure below |

**Daily Metrics Map Structure** (`daily_metrics.{YYYY-MM-DD}`):
```javascript
{
  "date": "2025-08-03",
  "video_count": 752,
  "new_videos_in_day": 45,
  "velocity": 45,  // videos per day
  "acceleration": 5,
  "total_views": 1250000,
  "avg_views_per_video": 1660,
  "timestamp": "2025-08-04T02:00:00Z"
}
```

### 2. youtube_videos

**Purpose**: Stores raw video data collected from YouTube

**Path Structure**: `youtube_videos/{keyword}/videos/{video_id}`

**Document ID**: YouTube video ID

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `video_id` | string | YouTube video ID | "dQw4w9WgXcQ" |
| `title` | string | Video title | "Introduction to Claude AI" |
| `url` | string | Full YouTube URL | "https://youtube.com/watch?v=dQw4w9WgXcQ" |
| `channel_name` | string | Channel name | "AI Explained" |
| `channel_id` | string | YouTube channel ID | "UC_channel123" |
| `view_count` | number | View count at collection time | 125000 |
| `duration` | string | Video duration | "12:34" |
| `published_time_text` | string | Relative publish time | "3 days ago" |
| `thumbnail_url` | string | Thumbnail image URL | "https://i.ytimg.com/vi/..." |
| `collected_at` | timestamp | When we collected this video | 2025-08-04T14:15:00Z |
| `keyword` | string | Search keyword used | "claude" |

### 3. youtube_keywords_interval_metrics

**Purpose**: Stores metrics calculated at regular intervals (every 2 hours)

**Document ID**: `{keyword}_{timestamp}` format

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `keyword` | string | The keyword | "claude" |
| `timestamp` | timestamp | Metric calculation time | 2025-08-04T14:00:00Z |
| `video_count` | number | Total videos for keyword | 671 |
| `new_videos` | number | New videos since last interval | 3 |
| `velocity` | number | Videos per hour | 1.5 |
| `acceleration` | number | Change in velocity | 0.25 |
| `total_views` | number | Sum of all video views | 2500000 |
| `avg_views_per_video` | number | Average views | 3727 |
| `hours_since_last` | number | Hours since last metric | 2.0 |

### 4. youtube_categories

**Purpose**: Stores category-level aggregated metrics and daily snapshots

**Document ID**: Category name (e.g., "ai_chatbots")

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `category` | string | Category name | "ai_media_generation" |
| `keywords` | array | Keywords in this category | ["midjourney", "dalle", "sora"] |
| `last_updated` | timestamp | Last update time | 2025-08-04T02:00:00Z |
| `updated_by` | string | Script that updated | "youtube_daily_metrics_unified_vm.py" |

**Subcollections**:

#### youtube_categories/{category}/7_days_daily/{date}
#### youtube_categories/{category}/30_days_daily/{date}
#### youtube_categories/{category}/90_days_daily/{date}
#### youtube_categories/{category}/all_time_daily/{date}

**Document ID**: Date string (YYYY-MM-DD)

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `date` | string | Date in YYYY-MM-DD format | "2025-08-03" |
| `timestamp` | timestamp | When snapshot was created | 2025-08-04T02:00:00Z |
| `total_videos` | number | Total videos in category | 3521 |
| `total_new_videos` | number | New videos that day | 142 |
| `total_velocity` | number | Sum of keyword velocities | 142 |
| `avg_acceleration` | number | Average acceleration | 2.3 |
| `total_views` | number | Total views across category | 8500000 |
| `keywords` | map | Per-keyword metrics | See structure below |

**Keywords Map Structure** (`keywords.{keyword_name}`):
```javascript
{
  "video_count": 752,
  "new_videos_in_day": 45,
  "velocity": 45,
  "acceleration": 5,
  "total_views": 1250000
}
```

### 5. youtube_collection_logs

**Purpose**: Audit trail for all collection runs and operations

**Document ID**: Auto-generated

**Fields vary by operation type**:

#### Collection Run Logs

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `timestamp` | timestamp | Run timestamp | 2025-08-04T14:15:00Z |
| `session_id` | string | Unique session identifier | "session_1754316901" |
| `script_name` | string | Script that ran | "youtube_collection_manager.py" |
| `keywords_processed` | number | Keywords attempted | 15 |
| `keywords_successful` | number | Successfully collected | 15 |
| `keywords_failed` | number | Failed collections | 0 |
| `total_videos_collected` | number | New videos found | 45 |
| `vpn_servers_used` | array | VPN servers used | ["us-nyc", "us-lax"] |
| `success_rate` | number | Success percentage | 100.0 |
| `errors` | array | Any errors encountered | [] |
| `duration_seconds` | number | Total run time | 180.5 |

#### Interval Metrics Logs

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `timestamp` | timestamp | Run timestamp | 2025-08-04T14:00:00Z |
| `run_type` | string | Type of run | "interval_metrics" |
| `script_name` | string | Script that ran | "youtube_keywords_interval_metrics.py" |
| `keywords_processed` | number | Keywords calculated | 15 |
| `metrics_created` | number | New metric documents | 15 |
| `errors` | number | Error count | 0 |
| `duration_seconds` | number | Run duration | 4.3 |

#### Daily Metrics Logs

| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `timestamp` | timestamp | Run timestamp | 2025-08-04T02:00:00Z |
| `run_type` | string | Type of run | "daily_metrics" |
| `script_name` | string | Script that ran | "youtube_daily_metrics_unified_vm.py" |
| `date_processed` | string | Date being calculated | "2025-08-03" |
| `keywords_processed` | number | Keywords processed | 15 |
| `keyword_metrics_created` | number | Daily metrics created | 15 |
| `category_snapshots_created` | number | Category snapshots | 5 |
| `errors` | number | Error count | 0 |
| `duration_seconds` | number | Run duration | 3.2 |

## Data Flow Relationships

```
youtube_keywords (configuration)
    ↓
youtube_collection_manager.py → youtube_videos/{keyword}/videos
    ↓
youtube_keywords_interval_metrics.py → youtube_keywords_interval_metrics
    ↓                                    ↓
    └→ youtube_keywords (rolling metrics)
                ↓
youtube_daily_metrics_unified_vm.py
    ↓
    ├→ youtube_keywords (daily_metrics field)
    └→ youtube_categories/{category}/*/daily
```

## Key Design Decisions

1. **Nested Video Storage**: 
   - Videos stored under `youtube_videos/{keyword}/videos/{video_id}`
   - Allows efficient querying by keyword
   - Prevents duplicate videos per keyword

2. **Document IDs**:
   - Keywords use hyphenated lowercase names for consistency
   - Videos use YouTube video IDs for deduplication
   - Interval metrics use `{keyword}_{timestamp}` for uniqueness
   - Daily snapshots use date strings (YYYY-MM-DD)

3. **Metrics Storage**:
   - Daily metrics stored as a map field in youtube_keywords document
   - Interval metrics stored as separate documents for time-series queries
   - Category snapshots stored as subcollections for efficient querying

4. **Time Windows**:
   - 7, 30, 90 days, and all-time snapshots maintained
   - Old snapshots automatically cleaned up after 90 days

## Query Patterns

### Common Queries

1. **Get active keywords**:
   ```
   youtube_keywords where active == true
   ```

2. **Get videos for a keyword**:
   ```
   youtube_videos/{keyword}/videos 
   order by collected_at desc
   limit 100
   ```

3. **Get interval metrics for time range**:
   ```
   youtube_keywords_interval_metrics 
   where keyword == "claude"
   and timestamp >= startTime 
   and timestamp <= endTime
   order by timestamp desc
   ```

4. **Get category snapshot for date**:
   ```
   youtube_categories/{category}/30_days_daily/{date}
   ```

5. **Get keywords with high velocity**:
   ```
   youtube_keywords 
   where rolling_velocity_24h > 10
   order by rolling_velocity_24h desc
   ```

## Maintenance Notes

- **Data Retention**: 
  - Videos: Kept indefinitely
  - Interval metrics: Could be pruned after 30 days
  - Daily snapshots: Auto-cleaned after 90 days
  
- **Index Requirements**: 
  - youtube_keywords: Index on (active, category)
  - youtube_keywords_interval_metrics: Composite index on (keyword, timestamp)
  - youtube_videos: Index on collected_at within each keyword
  
- **Size Estimates**:
  - ~15-20 active keywords
  - ~500-1000 videos per keyword
  - ~12 interval metrics per keyword per day
  - ~365 daily metrics per keyword per year

## Integration with Other Systems

- **Redis Cache**: Used for video deduplication (24-hour TTL)
- **Product Hunt Sync**: Keywords can be auto-added from PH top products
- **All Categories Aggregator**: Reads YouTube data for combined metrics

---

*Document Version: 1.0*  
*Last Updated: 2025-08-04*  
*Created for: YouTube App Firestore Schema Documentation*