#!/usr/bin/env python3
"""
Find collection logs with videos_per_keyword data
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
    
    # Search for scraper collection logs (not interval metrics logs)
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get logs around 8:13 UTC
    target_time = datetime(2025, 8, 5, 8, 13, 36, tzinfo=timezone.utc)
    start_time = target_time - timedelta(minutes=5)
    end_time = target_time + timedelta(minutes=20)
    
    # Look for logs with script_name containing 'collection_manager'
    all_logs = list(logs_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream())
    
    print(f"\nFound {len(all_logs)} logs between {start_time.strftime('%H:%M')} and {end_time.strftime('%H:%M')} UTC")
    
    scraper_logs = []
    
    for log in all_logs:
        data = log.to_dict()
        
        # Check if this is a scraper log
        if 'videos_per_keyword' in data or 'total_videos_collected' in data:
            timestamp = data.get('timestamp')
            if hasattr(timestamp, 'astimezone'):
                cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
                
                print(f"\n{'='*60}")
                print(f"SCRAPER LOG at {cst_time.strftime('%I:%M:%S %p CST')} ({timestamp.strftime('%H:%M:%S UTC')})")
                print(f"Document ID: {log.id}")
                print(f"Total videos collected: {data.get('total_videos_collected', 'N/A')}")
                
                if 'videos_per_keyword' in data:
                    print("\nVideos per keyword:")
                    for kw, count in data['videos_per_keyword'].items():
                        print(f"  {kw}: {count}")
                        
                    if 'chatgpt' in data['videos_per_keyword']:
                        scraper_logs.append({
                            'timestamp': timestamp,
                            'chatgpt_count': data['videos_per_keyword']['chatgpt'],
                            'log_id': log.id
                        })
    
    # Check for duplicate video IDs if we found the logs
    if len(scraper_logs) >= 2:
        print(f"\n\nFound {len(scraper_logs)} scraper logs with chatgpt data")
        
        log1 = scraper_logs[0]
        log2 = scraper_logs[1]
        
        print(f"\nRun 1: {log1['chatgpt_count']} chatgpt videos at {log1['timestamp'].strftime('%H:%M:%S UTC')}")
        print(f"Run 2: {log2['chatgpt_count']} chatgpt videos at {log2['timestamp'].strftime('%H:%M:%S UTC')}")
        
        # Both show 14 videos - let's check if they're the same videos
        print("\nChecking if these are unique videos or duplicates...")
        
        # Get the actual video IDs from around these times
        videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
        
        # Get ALL chatgpt videos to analyze
        all_videos = list(videos_ref.stream())
        print(f"\nTotal videos in chatgpt collection: {len(all_videos)}")
        
        # Check collection times
        videos_by_time = {}
        for video in all_videos:
            video_data = video.to_dict()
            collected_at = video_data.get('collected_at')
            
            if hasattr(collected_at, 'strftime'):
                time_key = collected_at.strftime('%Y-%m-%d %H:%M')
                if time_key not in videos_by_time:
                    videos_by_time[time_key] = []
                videos_by_time[time_key].append({
                    'id': video.id,
                    'title': video_data.get('title', ''),
                    'collected_at': collected_at
                })
        
        print("\nVideos grouped by collection time:")
        for time_key, videos in sorted(videos_by_time.items()):
            print(f"  {time_key}: {len(videos)} videos")

if __name__ == "__main__":
    main()