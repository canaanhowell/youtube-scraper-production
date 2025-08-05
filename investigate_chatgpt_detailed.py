#!/usr/bin/env python3
"""
Detailed investigation of chatgpt video collections
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
    
    # Get ALL chatgpt videos to understand the pattern
    print("\nFetching ALL chatgpt videos...")
    videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
    
    # Get the most recent videos
    all_videos = list(videos_ref.order_by('collected_at', direction='DESCENDING').limit(100).stream())
    
    print(f"\nTotal recent chatgpt videos: {len(all_videos)}")
    
    # Group by collection hour to see patterns
    videos_by_hour = {}
    
    for video in all_videos:
        video_data = video.to_dict()
        collected_at = video_data.get('collected_at')
        
        if hasattr(collected_at, 'strftime'):
            # Convert to CST
            cst_time = collected_at.astimezone(timezone(timedelta(hours=-6)))
            hour_key = cst_time.strftime('%Y-%m-%d %H:00 CST')
            
            if hour_key not in videos_by_hour:
                videos_by_hour[hour_key] = []
            
            videos_by_hour[hour_key].append({
                'id': video.id,
                'title': video_data.get('title', ''),
                'collected_at': collected_at,
                'cst_time': cst_time,
                'utc_time': collected_at.strftime('%Y-%m-%d %H:%M:%S UTC')
            })
    
    # Show collections by hour
    print("\nVideo collections by hour (CST):")
    for hour, videos in sorted(videos_by_hour.items(), reverse=True)[:10]:
        print(f"\n{hour}: {len(videos)} videos")
        
        # Show time distribution within the hour
        minute_counts = {}
        for v in videos:
            minute = v['cst_time'].strftime('%M')
            minute_counts[minute] = minute_counts.get(minute, 0) + 1
        
        sorted_minutes = sorted(minute_counts.items())
        if sorted_minutes:
            print(f"  Minutes: {', '.join([f':{m}({c})' for m, c in sorted_minutes])}")
    
    # Now specifically look for Aug 5, 3:00-4:00 AM CST
    print("\n\nDetailed look at Aug 5, 3:00-4:00 AM CST:")
    
    aug5_3am = []
    for video in all_videos:
        video_data = video.to_dict()
        collected_at = video_data.get('collected_at')
        
        if hasattr(collected_at, 'strftime'):
            cst_time = collected_at.astimezone(timezone(timedelta(hours=-6)))
            
            # Check if it's Aug 5, 3:00-4:00 AM CST
            if (cst_time.year == 2025 and 
                cst_time.month == 8 and 
                cst_time.day == 5 and 
                cst_time.hour == 3):
                
                aug5_3am.append({
                    'id': video.id,
                    'title': video_data.get('title', ''),
                    'collected_at': collected_at,
                    'cst_time': cst_time,
                    'minute': cst_time.minute,
                    'view_count': video_data.get('view_count', 0)
                })
    
    # Sort by time
    aug5_3am.sort(key=lambda x: x['collected_at'])
    
    print(f"\nFound {len(aug5_3am)} videos collected during 3:00-4:00 AM CST on Aug 5:")
    
    # Group by collection batch (videos within 1 minute of each other)
    if aug5_3am:
        batches = []
        current_batch = [aug5_3am[0]]
        
        for i in range(1, len(aug5_3am)):
            time_diff = (aug5_3am[i]['collected_at'] - current_batch[-1]['collected_at']).total_seconds()
            
            if time_diff < 120:  # Within 2 minutes
                current_batch.append(aug5_3am[i])
            else:
                batches.append(current_batch)
                current_batch = [aug5_3am[i]]
        
        batches.append(current_batch)
        
        print(f"\nFound {len(batches)} collection batches:")
        
        for i, batch in enumerate(batches):
            start_time = batch[0]['cst_time'].strftime('%I:%M:%S %p')
            end_time = batch[-1]['cst_time'].strftime('%I:%M:%S %p')
            
            print(f"\nBatch {i+1}: {start_time} - {end_time} CST ({len(batch)} videos)")
            
            # Check for duplicates within batch
            batch_ids = [v['id'] for v in batch]
            unique_ids = set(batch_ids)
            
            if len(batch_ids) != len(unique_ids):
                print(f"  ⚠️  DUPLICATES within batch!")
            else:
                print(f"  ✅ No duplicates within batch")
            
            # Show first few videos
            print(f"  Sample videos:")
            for j, video in enumerate(batch[:3]):
                print(f"    {j+1}. {video['title'][:50]}...")
                print(f"       Time: {video['cst_time'].strftime('%I:%M:%S %p')}, Views: {video['view_count']:,}")
        
        # Check for duplicates across batches
        all_ids = [v['id'] for v in aug5_3am]
        unique_ids = set(all_ids)
        
        print(f"\n\nOverall statistics for 3:00-4:00 AM CST:")
        print(f"  Total videos: {len(all_ids)}")
        print(f"  Unique videos: {len(unique_ids)}")
        print(f"  Duplicates: {len(all_ids) - len(unique_ids)}")
        
        if len(all_ids) > len(unique_ids):
            # Find duplicate IDs
            from collections import Counter
            id_counts = Counter(all_ids)
            duplicates = {id: count for id, count in id_counts.items() if count > 1}
            
            print(f"\n  Duplicate video IDs:")
            for vid_id, count in list(duplicates.items())[:5]:
                print(f"    {vid_id}: appears {count} times")
                
                # Find when each instance was collected
                instances = [v for v in aug5_3am if v['id'] == vid_id]
                for inst in instances:
                    print(f"      - {inst['cst_time'].strftime('%I:%M:%S %p')} CST")

if __name__ == "__main__":
    main()