#!/usr/bin/env python3
"""
Verify chatgpt collections at specific timestamps
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
    
    # Looking for the specific collection logs you mentioned
    # 3:13:36 AM CST = 8:13:36 UTC
    # 3:23 AM CST = 8:23 UTC (approximately)
    
    print("\nSearching for collection logs at 3:13 and 3:23 AM CST (8:13 and 8:23 UTC)...")
    
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get logs around 8:13 and 8:23 UTC
    start_time = datetime(2025, 8, 5, 8, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2025, 8, 5, 8, 30, 0, tzinfo=timezone.utc)
    
    logs = list(logs_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).order_by('timestamp').stream())
    
    print(f"\nFound {len(logs)} collection logs between 8:10 and 8:30 UTC")
    
    collection_runs = []
    
    for log in logs:
        data = log.to_dict()
        timestamp = data.get('timestamp')
        
        if hasattr(timestamp, 'astimezone'):
            utc_time = timestamp
            cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))  # CST is UTC-6
            
            # Check if this is a scraper log with video counts
            if 'videos_per_keyword' in data:
                videos_per_kw = data['videos_per_keyword']
                if 'chatgpt' in videos_per_kw:
                    chatgpt_count = videos_per_kw['chatgpt']
                    
                    print(f"\n{'='*60}")
                    print(f"Collection at {cst_time.strftime('%I:%M:%S %p CST')} ({utc_time.strftime('%H:%M:%S UTC')})")
                    print(f"Document ID: {log.id}")
                    print(f"ChatGPT videos collected: {chatgpt_count}")
                    print(f"Total videos in run: {data.get('total_videos_collected', 0)}")
                    
                    collection_runs.append({
                        'log_id': log.id,
                        'timestamp': timestamp,
                        'cst_time': cst_time,
                        'chatgpt_count': chatgpt_count,
                        'total_count': data.get('total_videos_collected', 0)
                    })
    
    # Now check interval metrics for the same time period
    print(f"\n\nChecking interval metrics for chatgpt...")
    
    interval_ref = fc.db.collection('youtube_keywords').document('chatgpt').collection('interval_metrics')
    interval_metrics = list(interval_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).order_by('timestamp').stream())
    
    print(f"\nFound {len(interval_metrics)} interval metrics:")
    
    for metric in interval_metrics:
        data = metric.to_dict()
        timestamp = data.get('timestamp')
        
        if hasattr(timestamp, 'astimezone'):
            cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
            
            print(f"\n{cst_time.strftime('%I:%M:%S %p CST')} ({timestamp.strftime('%H:%M:%S UTC')})")
            print(f"  Video count: {data.get('video_count', 0)}")
            print(f"  Videos found in search: {data.get('videos_found_in_search', 0)}")
            print(f"  New videos: {data.get('new_videos', 0)}")
    
    # Now let's check if videos were actually saved
    if collection_runs:
        print(f"\n\nVerifying if videos were actually saved to database...")
        
        videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
        
        # Get videos collected in this time window
        videos = list(videos_ref.where('collected_at', '>=', start_time).where('collected_at', '<=', end_time).stream())
        
        print(f"\nActual videos saved between 8:10-8:30 UTC: {len(videos)}")
        
        if videos:
            # Group by collection minute
            videos_by_minute = {}
            for video in videos:
                video_data = video.to_dict()
                collected_at = video_data.get('collected_at')
                if hasattr(collected_at, 'strftime'):
                    minute_key = collected_at.strftime('%H:%M')
                    if minute_key not in videos_by_minute:
                        videos_by_minute[minute_key] = []
                    videos_by_minute[minute_key].append(video.id)
            
            for minute, video_ids in sorted(videos_by_minute.items()):
                print(f"\n  {minute} UTC: {len(video_ids)} videos")
                # Check for duplicates
                if len(video_ids) != len(set(video_ids)):
                    print(f"    ⚠️  Contains duplicates!")
        else:
            print("\n⚠️  WARNING: Collection logs show videos were collected, but no videos exist in the database!")
            print("This suggests videos are being collected but not saved, or being saved elsewhere.")

if __name__ == "__main__":
    main()