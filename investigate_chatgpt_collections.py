#!/usr/bin/env python3
"""
Investigate chatgpt videos collected at 3:13am and 3:23am CST (9:13 and 9:23 UTC)
to verify counts and uniqueness
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
    
    # CST is UTC-6, so 3:13am CST = 9:13 UTC, 3:23am CST = 9:23 UTC
    # Looking for collections around those times on Aug 5, 2025
    target_date = "2025-08-05"
    
    print(f"\nLooking for chatgpt collections on {target_date} around 3:13am and 3:23am CST (9:13 and 9:23 UTC)...")
    
    # First, find collection logs for those times
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get all logs from Aug 5
    start_time = datetime(2025, 8, 5, 9, 0, 0, tzinfo=timezone.utc)  # 9:00 UTC
    end_time = datetime(2025, 8, 5, 9, 30, 0, tzinfo=timezone.utc)   # 9:30 UTC
    
    logs = list(logs_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream())
    
    print(f"\nFound {len(logs)} collection logs between 9:00 and 9:30 UTC")
    
    # Find the specific collection runs
    collection_runs = []
    for log in logs:
        data = log.to_dict()
        if 'keywords' in data.get('results', {}):
            keywords_data = data['results']['keywords']
            if 'chatgpt' in keywords_data:
                timestamp = data.get('timestamp')
                # Convert timestamp to CST for display
                if hasattr(timestamp, 'astimezone'):
                    cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
                    print(f"\nCollection run at {cst_time.strftime('%I:%M %p CST')} ({timestamp.strftime('%H:%M UTC')})")
                    print(f"  Document ID: {log.id}")
                    print(f"  ChatGPT data: {keywords_data['chatgpt']}")
                    
                    collection_runs.append({
                        'log_id': log.id,
                        'timestamp': timestamp,
                        'cst_time': cst_time,
                        'chatgpt_data': keywords_data['chatgpt']
                    })
    
    if len(collection_runs) < 2:
        print(f"\nWarning: Found only {len(collection_runs)} collection runs with chatgpt data")
    
    # Now get the actual videos collected for chatgpt around those times
    print("\n\nFetching chatgpt videos collected around those times...")
    
    videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
    
    # Get videos collected between 9:00 and 9:30 UTC on Aug 5
    videos = list(videos_ref.where('collected_at', '>=', start_time).where('collected_at', '<=', end_time).stream())
    
    print(f"\nTotal chatgpt videos collected between 9:00-9:30 UTC: {len(videos)}")
    
    # Group videos by collection time (within 2-minute windows)
    video_groups = {}
    for video in videos:
        video_data = video.to_dict()
        collected_at = video_data.get('collected_at')
        
        # Round to nearest 10 minutes to group collections
        if hasattr(collected_at, 'replace'):
            minute = collected_at.minute
            rounded_minute = (minute // 10) * 10
            group_key = collected_at.replace(minute=rounded_minute, second=0, microsecond=0)
            
            if group_key not in video_groups:
                video_groups[group_key] = []
            
            video_groups[group_key].append({
                'id': video.id,
                'title': video_data.get('title', 'No title'),
                'collected_at': collected_at,
                'url': video_data.get('url', ''),
                'view_count': video_data.get('view_count', 0)
            })
    
    # Analyze each group
    print("\n\nAnalyzing video collections by time group:")
    
    all_video_ids = set()
    for group_time, group_videos in sorted(video_groups.items()):
        cst_time = group_time.astimezone(timezone(timedelta(hours=-6)))
        print(f"\n{'='*60}")
        print(f"Collection around {cst_time.strftime('%I:%M %p CST')} ({group_time.strftime('%H:%M UTC')})")
        print(f"Videos collected: {len(group_videos)}")
        
        # Check for duplicates within this group
        group_ids = [v['id'] for v in group_videos]
        unique_ids = set(group_ids)
        
        if len(group_ids) != len(unique_ids):
            print(f"⚠️  DUPLICATES FOUND within this collection!")
        else:
            print(f"✅ All videos unique within this collection")
        
        # Check for duplicates across collections
        duplicates_from_previous = all_video_ids.intersection(unique_ids)
        if duplicates_from_previous:
            print(f"⚠️  {len(duplicates_from_previous)} videos were already in previous collections!")
            print(f"   Duplicate IDs: {list(duplicates_from_previous)[:5]}...")
        else:
            print(f"✅ No duplicates from previous collections")
        
        all_video_ids.update(unique_ids)
        
        # Show sample videos
        print(f"\nSample videos from this collection:")
        for i, video in enumerate(group_videos[:5]):
            time_str = video['collected_at'].strftime('%H:%M:%S')
            print(f"  {i+1}. [{time_str}] {video['title'][:60]}...")
            print(f"     ID: {video['id']}, Views: {video['view_count']:,}")
    
    # Summary
    print(f"\n\n{'='*60}")
    print("SUMMARY:")
    print(f"Total collection groups found: {len(video_groups)}")
    print(f"Total videos collected: {len(videos)}")
    print(f"Total unique video IDs: {len(all_video_ids)}")
    print(f"Total duplicates: {len(videos) - len(all_video_ids)}")
    
    # Check interval metrics for these times
    print(f"\n\nChecking interval metrics for chatgpt around these times...")
    
    interval_ref = fc.db.collection('youtube_keywords').document('chatgpt').collection('interval_metrics')
    interval_metrics = list(interval_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream())
    
    print(f"\nFound {len(interval_metrics)} interval metrics:")
    for metric in interval_metrics:
        metric_data = metric.to_dict()
        timestamp = metric_data.get('timestamp')
        if hasattr(timestamp, 'astimezone'):
            cst_time = timestamp.astimezone(timezone(timedelta(hours=-6)))
            print(f"\n{cst_time.strftime('%I:%M %p CST')} ({timestamp.strftime('%H:%M UTC')})")
            print(f"  Video count: {metric_data.get('video_count', 0)}")
            print(f"  New videos: {metric_data.get('new_videos', 0)}")
            print(f"  Videos found in search: {metric_data.get('videos_found_in_search', 0)}")

if __name__ == "__main__":
    main()