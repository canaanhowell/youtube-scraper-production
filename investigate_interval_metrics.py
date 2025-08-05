#!/usr/bin/env python3
"""
Investigate the interval metrics that show videos were found but not collected
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    print("Connecting to Firebase...")
    fc = FirebaseClient()
    
    # Get interval metrics for chatgpt on Aug 5
    print("\nFetching chatgpt interval metrics for Aug 5...")
    
    interval_ref = fc.db.collection('youtube_keywords').document('chatgpt').collection('interval_metrics')
    
    # Get all metrics for Aug 5
    start_of_day = datetime(2025, 8, 5, 0, 0, 0, tzinfo=timezone.utc)
    end_of_day = datetime(2025, 8, 5, 23, 59, 59, tzinfo=timezone.utc)
    
    metrics = list(interval_ref.where('timestamp', '>=', start_of_day).where('timestamp', '<=', end_of_day).order_by('timestamp').stream())
    
    print(f"\nFound {len(metrics)} interval metrics for Aug 5")
    
    # Analyze each metric
    print("\nInterval metrics timeline:")
    print("="*80)
    
    previous_count = None
    
    for metric in metrics:
        data = metric.to_dict()
        timestamp = data.get('timestamp')
        
        if hasattr(timestamp, 'astimezone'):
            cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
            
            video_count = data.get('video_count', 0)
            new_videos = data.get('new_videos', 0)
            videos_found = data.get('videos_found_in_search', 0)
            
            # Calculate actual new videos if we have previous count
            actual_new = 0
            if previous_count is not None:
                actual_new = video_count - previous_count
            
            print(f"\n{cst_time.strftime('%I:%M %p CST')} ({timestamp.strftime('%H:%M UTC')})")
            print(f"  Total videos: {video_count}")
            print(f"  New videos (field): {new_videos}")
            print(f"  Videos found in search: {videos_found}")
            print(f"  Actual change from previous: {actual_new}")
            
            # Check for discrepancies
            if videos_found > 0 and actual_new == 0:
                print(f"  ⚠️  WARNING: Found {videos_found} videos but count didn't increase!")
                print(f"     This suggests Redis deduplication blocked all {videos_found} videos")
            elif videos_found > 0 and actual_new > 0 and actual_new != videos_found:
                print(f"  ⚠️  WARNING: Found {videos_found} but only {actual_new} were new")
                print(f"     This suggests {videos_found - actual_new} were duplicates")
            
            previous_count = video_count
    
    # Now check the actual video collection to verify
    print("\n\nVerifying against actual video collection...")
    
    videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
    
    # Get all videos and check their collection times
    all_videos = list(videos_ref.stream())
    
    print(f"\nTotal videos in chatgpt collection: {len(all_videos)}")
    
    # Group by collection date
    videos_by_date = {}
    for video in all_videos:
        video_data = video.to_dict()
        collected_at = video_data.get('collected_at')
        
        if hasattr(collected_at, 'date'):
            date_key = collected_at.date()
            if date_key not in videos_by_date:
                videos_by_date[date_key] = []
            videos_by_date[date_key].append(video_data)
    
    # Show recent dates
    print("\nVideos by date:")
    for date in sorted(videos_by_date.keys(), reverse=True)[:7]:
        count = len(videos_by_date[date])
        print(f"  {date}: {count} videos")
    
    # Check specifically for Aug 5
    aug5_date = datetime(2025, 8, 5).date()
    if aug5_date in videos_by_date:
        aug5_videos = videos_by_date[aug5_date]
        print(f"\n\nAug 5 videos: {len(aug5_videos)}")
        
        # Group by hour
        by_hour = {}
        for v in aug5_videos:
            collected_at = v.get('collected_at')
            if hasattr(collected_at, 'hour'):
                cst_time = collected_at.astimezone(timezone(timedelta(hours=-6)))
                hour_key = cst_time.strftime('%I %p CST')
                by_hour[hour_key] = by_hour.get(hour_key, 0) + 1
        
        print("\nVideos by hour on Aug 5:")
        for hour in sorted(by_hour.keys()):
            print(f"  {hour}: {by_hour[hour]} videos")
    else:
        print(f"\n\nNo videos found for Aug 5!")
    
    # Check collection logs to see what happened
    print("\n\nChecking collection logs for Aug 5...")
    
    logs_ref = fc.db.collection('youtube_collection_logs')
    logs = list(logs_ref.where('timestamp', '>=', start_of_day).where('timestamp', '<=', end_of_day).order_by('timestamp').stream())
    
    print(f"\nFound {len(logs)} collection logs for Aug 5")
    
    for log in logs:
        log_data = log.to_dict()
        timestamp = log_data.get('timestamp')
        
        if hasattr(timestamp, 'astimezone'):
            cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
            
            # Check if this log has chatgpt data
            if 'results' in log_data and 'keywords' in log_data['results']:
                keywords = log_data['results']['keywords']
                if 'chatgpt' in keywords:
                    chatgpt_data = keywords['chatgpt']
                    print(f"\n{cst_time.strftime('%I:%M %p CST')} - Collection Log")
                    print(f"  Videos found: {chatgpt_data.get('videos_found_in_search', 0)}")
                    print(f"  Video count: {chatgpt_data.get('video_count', 0)}")
                    
                    if 'error' in chatgpt_data:
                        print(f"  ERROR: {chatgpt_data['error']}")

if __name__ == "__main__":
    main()