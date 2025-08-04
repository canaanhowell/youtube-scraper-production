#!/usr/bin/env python3
"""
Backfill interval metrics for a specific date.
This script creates interval metrics based on video collection data.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def backfill_metrics_for_date(target_date: str):
    """
    Backfill interval metrics for a specific date.
    target_date should be in YYYY-MM-DD format.
    """
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    # Parse the target date
    date_obj = datetime.strptime(target_date, "%Y-%m-%d")
    start_of_day = date_obj.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)
    end_of_day = start_of_day + timedelta(days=1)
    
    print(f"Backfilling interval metrics for {target_date}")
    print(f"Time range: {start_of_day} to {end_of_day}")
    
    # Get all active keywords
    keywords_ref = db.collection('youtube_keywords').where('active', '==', True)
    keywords = list(keywords_ref.stream())
    
    print(f"\nFound {len(keywords)} active keywords")
    
    for keyword_doc in keywords:
        keyword_data = keyword_doc.to_dict()
        keyword = keyword_data['keyword']
        print(f"\nProcessing keyword: {keyword}")
        
        # Get video count at end of day
        videos_ref = db.collection('youtube_videos').document(keyword).collection('videos')
        videos_query = videos_ref.where('collected_at', '<=', end_of_day)
        videos = list(videos_query.stream())
        
        video_count = len(videos)
        total_views = sum(v.to_dict().get('view_count', 0) for v in videos)
        
        # Get video count at start of day for new videos calculation
        videos_at_start = videos_ref.where('collected_at', '<=', start_of_day).stream()
        video_count_at_start = len(list(videos_at_start))
        
        new_videos = video_count - video_count_at_start
        
        print(f"  Total videos: {video_count}")
        print(f"  New videos on {target_date}: {new_videos}")
        print(f"  Total views: {total_views:,}")
        
        # Create a synthetic interval metric at 23:59 of the target date
        metric_timestamp = end_of_day - timedelta(minutes=1)
        
        # Calculate velocity (assume 24 hours for daily backfill)
        velocity = new_videos / 24.0  # videos per hour
        
        # For backfill, we can't calculate accurate acceleration
        acceleration = 0.0
        
        metric_data = {
            'keyword': keyword,
            'timestamp': metric_timestamp,
            'timestamp_str': metric_timestamp.isoformat(),
            'video_count': video_count,
            'views_count': total_views,  # Note: views_count not total_views
            'videos_found_in_search': new_videos,  # This is what daily metrics looks for
            'velocity': velocity,
            'acceleration': acceleration,
            'created_at': metric_timestamp,
            'updated_at': metric_timestamp,
            'is_backfilled': True,
            'backfilled_at': datetime.now(timezone.utc)
        }
        
        # Create the metric document in the subcollection
        metric_ref = (db.collection('youtube_keywords')
                     .document(keyword_doc.id)
                     .collection('interval_metrics')
                     .document())
        metric_ref.set(metric_data)
        
        print(f"  ✓ Created interval metric in subcollection")
        
        # Also update the keyword's rolling metrics
        keyword_ref = db.collection('youtube_keywords').document(keyword_doc.id)
        keyword_ref.update({
            'rolling_velocity_24h': velocity,
            'rolling_velocity_7d': velocity,
            'last_interval_update': metric_timestamp
        })
    
    print(f"\n✅ Backfill complete for {target_date}")
    print("\nYou can now run the daily metrics script to process this data.")


if __name__ == "__main__":
    # Backfill for August 3, 2025
    backfill_metrics_for_date("2025-08-03")