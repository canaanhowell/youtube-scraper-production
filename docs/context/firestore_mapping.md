# Firestore Collections Mapping - YouTube App (Collection Only)

This document provides a mapping of Firestore collections used by the YouTube video collection application.

## Overview

The YouTube app uses Firebase Firestore as its database for storing collected video data with the following collections:
- `youtube_keywords` - Keyword configuration (read only)
- `youtube_videos` - Raw video data organized by keyword (write only)
- `youtube_collection_logs` - Audit trail for collection runs (write only)

## Collection Details

### 1. youtube_keywords

**Purpose**: Stores keyword configuration for collection

**Document ID**: Keyword name (lowercase, hyphenated)

**Fields Used by Collection**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `keyword` | string | The search keyword | "claude" |
| `category` | string | Keyword category | "ai_chatbots" |
| `active` | boolean | Whether keyword is actively collected | true |
| `last_collected` | timestamp | Last successful collection | 2025-08-04T14:15:00Z |

**Note**: This collection is READ ONLY for the collection service. Keywords are managed externally.

### 2. youtube_videos

**Purpose**: Stores raw video data collected from YouTube

**Path Structure**: `youtube_videos/{keyword}/videos/{timestamp}`

**Document ID**: ISO 8601 timestamp (e.g., `2025-08-10T18:53:40.513000Z`)

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `id` | string | YouTube video ID | "dQw4w9WgXcQ" |
| `title` | string | Video title | "Introduction to Claude AI" |
| `url` | string | Full YouTube URL | "https://youtube.com/watch?v=dQw4w9WgXcQ" |
| `channel_name` | string | Channel name | "AI Explained" |
| `channel_id` | string | YouTube channel ID | "UC_channel123" |
| `view_count` | number | View count at collection time | 125000 |
| `duration` | string | Video duration | "12:34" |
| `published_time_text` | string | Relative publish time | "3 days ago" |
| `thumbnail_url` | string | Thumbnail image URL | "https://i.ytimg.com/vi/..." |
| `collected_at` | string | When we collected this video | "2025-08-10T18:53:40.513000Z" |
| `keyword` | string | Search keyword used | "claude" |

### 3. youtube_collection_logs

**Purpose**: Audit trail for all collection runs

**Document ID**: Timestamp-based format (e.g., `collection_2025-08-05_14-30-45_UTC`)

**Fields**:
| Field Name | Type | Description | Example |
|------------|------|-------------|---------|
| `timestamp` | timestamp | Run timestamp | 2025-08-04T14:15:00Z |
| `session_id` | string | Unique session identifier | "session_1754316901_1" |
| `script_name` | string | Script that ran | "youtube_collection_manager_simple.py" |
| `keywords_processed` | array | List of keywords processed | ["claude", "chatgpt", "gemini"] |
| `keywords_successful` | number | Successfully collected | 15 |
| `keywords_failed` | number | Failed collections | 0 |
| `total_videos_collected` | number | New videos found | 45 |
| `videos_per_keyword` | map | Videos collected per keyword | {"claude": 20, "chatgpt": 15, "gemini": 10} |
| `vpn_servers_used` | array | VPN containers used | ["youtube-vpn-1"] |
| `success_rate` | number | Success percentage | 100.0 |
| `errors` | array | Any errors encountered | [] |
| `duration_seconds` | number | Total run time | 180.5 |
| `container` | string | VPN container name | "youtube-vpn-1" |
| `instance_id` | number | Instance number (1-3) | 1 |
| `vm_hostname` | string | VM hostname | "youtube-vm" |

## Data Flow Relationships

```
youtube_keywords (configuration)
    ↓
youtube_collection_manager.py → youtube_videos/{keyword}/videos
    ↓
youtube_collection_logs (audit trail)
```

## Key Design Decisions

1. **Nested Video Storage**:
   - Videos stored under `youtube_videos/{keyword}/videos/{video_id}`
   - Allows efficient querying by keyword
   - Prevents duplicate videos per keyword
   - **IMPORTANT**: Parent document must exist before adding videos to subcollection

2. **Document IDs**:
   - Keywords use underscore-separated names (e.g., `leonardo_ai`, `stable_diffusion`)
   - Videos use ISO 8601 timestamps for efficient time-range queries (e.g., `2025-08-10T18:53:40.513000Z`)
   - Collection logs use readable timestamps (e.g., `collection_2025-08-05_15-30-45_UTC`)

3. **Collection Focus**:
   - No metrics storage
   - No aggregations
   - No analytics
   - Pure video data collection only

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

3. **Get recent collection logs**:
   ```
   youtube_collection_logs
   order by timestamp desc
   limit 10
   ```

## Maintenance Notes

- **Data Retention**:
  - Videos: Kept indefinitely
  - Collection logs: Could be pruned after 30 days

- **Index Requirements**:
  - youtube_keywords: Index on (active)
  - youtube_videos: Index on collected_at within each keyword
  - youtube_collection_logs: Index on timestamp

- **Size Estimates**:
  - 70+ active keywords
  - ~500-1000 videos per keyword
  - ~144 collection runs per day (every 10 minutes)

---

*Document Version: 2.1 - Updated with ISO timestamp document IDs*
*Last Updated: 2025-08-10*