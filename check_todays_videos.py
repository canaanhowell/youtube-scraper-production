#!/usr/bin/env python3
"""
Check for today's video data in Firebase
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def check_todays_videos():
    """Check for videos collected today"""
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Get today's date in UTC
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    print(f"Checking for videos collected on: {today} (UTC)")
    print("=" * 60)
    
    total_videos_today = 0
    keywords_with_videos = 0
    
    try:
        # Get all keywords
        keywords = firebase.get_keywords()
        print(f"Found {len(keywords)} keywords to check")
        print("=" * 60)
        
        # Check each keyword for today's videos
        for keyword in keywords[:10]:  # Check first 10 keywords to avoid timeout
            try:
                # Get videos subcollection for this keyword
                videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
                
                # Query for videos collected today
                # Note: Firestore stores collected_at as string, so we need to check differently
                all_videos = videos_ref.limit(20).get()  # Get recent 20 videos
                
                videos_today = []
                for video in all_videos:
                    video_data = video.to_dict()
                    collected_at_str = video_data.get('collected_at', '')
                    
                    # Parse the ISO format string
                    if collected_at_str:
                        try:
                            collected_at = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
                            if collected_at.date() == today:
                                videos_today.append(video_data)
                        except:
                            pass
                
                if videos_today:
                    keywords_with_videos += 1
                    total_videos_today += len(videos_today)
                    print(f"\n✓ {keyword}: {len(videos_today)} videos today")
                    
                    # Show first video as example
                    if videos_today:
                        first_video = videos_today[0]
                        print(f"  Example: {first_video.get('title', 'No title')[:60]}...")
                        print(f"  Channel: {first_video.get('channel_name', 'Unknown')}")
                        print(f"  Collected: {first_video.get('collected_at', 'Unknown')}")
                
            except Exception as e:
                print(f"\n✗ Error checking {keyword}: {e}")
        
        print("\n" + "=" * 60)
        print(f"Summary for {today}:")
        print(f"- Keywords with videos: {keywords_with_videos}")
        print(f"- Total videos collected: {total_videos_today}")
        
        # Also check collection logs for today
        print("\n" + "=" * 60)
        print("Checking collection logs for today...")
        
        logs_ref = firebase.db.collection('youtube_collection_logs')
        # Get logs from today
        recent_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(20).get()
        
        today_logs = []
        for log in recent_logs:
            log_data = log.to_dict()
            timestamp = log_data.get('timestamp')
            if timestamp and timestamp.date() == today:
                today_logs.append(log_data)
        
        print(f"Found {len(today_logs)} collection runs today")
        
        if today_logs:
            for i, log in enumerate(today_logs[:5], 1):  # Show first 5
                print(f"\nRun {i}:")
                print(f"  Time: {log.get('timestamp')}")
                print(f"  Keywords processed: {log.get('keywords_successful', 0)}")
                print(f"  Videos collected: {log.get('total_videos_collected', 0)}")
                print(f"  Success rate: {log.get('success_rate', 0):.1f}%")
                print(f"  Duration: {log.get('duration_seconds', 0):.1f}s")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_todays_videos()