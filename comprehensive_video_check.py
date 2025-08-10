#!/usr/bin/env python3
"""
Comprehensive check for today's video data across ALL keywords
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def comprehensive_check():
    """Check ALL keywords for today's videos"""
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Get today's date in UTC
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
    
    print(f"Comprehensive check for videos collected on: {today} (UTC)")
    print("=" * 80)
    
    total_videos_today = 0
    keywords_with_videos = 0
    hourly_breakdown = defaultdict(int)
    
    try:
        # Get all keywords
        keywords = firebase.get_keywords()
        print(f"Checking ALL {len(keywords)} keywords...")
        print("=" * 80)
        
        # Check each keyword for today's videos
        for i, keyword in enumerate(keywords, 1):
            print(f"Checking {i}/{len(keywords)}: {keyword}...", end=" ")
            
            try:
                # Get videos subcollection for this keyword
                videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
                
                # Get all videos for this keyword (or a large limit)
                all_videos = videos_ref.limit(500).get()  # Increase limit
                
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
                                # Track hourly breakdown
                                hour_key = collected_at.hour
                                hourly_breakdown[hour_key] += 1
                        except:
                            pass
                
                if videos_today:
                    keywords_with_videos += 1
                    total_videos_today += len(videos_today)
                    print(f"✓ {len(videos_today)} videos")
                else:
                    print("✗ 0 videos")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
        
        print("\n" + "=" * 80)
        print(f"COMPREHENSIVE SUMMARY for {today}:")
        print(f"- Keywords with videos: {keywords_with_videos}/{len(keywords)}")
        print(f"- Total videos collected: {total_videos_today}")
        print(f"- Average videos per active keyword: {total_videos_today/keywords_with_videos if keywords_with_videos > 0 else 0:.1f}")
        
        # Show hourly breakdown
        if hourly_breakdown:
            print("\nHourly breakdown (UTC):")
            for hour in sorted(hourly_breakdown.keys()):
                print(f"  {hour:02d}:00-{hour:02d}:59: {hourly_breakdown[hour]} videos")
        
        # Check collection logs in more detail
        print("\n" + "=" * 80)
        print("DETAILED COLLECTION LOG ANALYSIS:")
        
        logs_ref = firebase.db.collection('youtube_collection_logs')
        # Get all logs from today
        all_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(200).get()
        
        today_logs = []
        total_videos_from_logs = 0
        
        for log in all_logs:
            log_data = log.to_dict()
            timestamp = log_data.get('timestamp')
            if timestamp and timestamp.date() == today:
                today_logs.append(log_data)
                total_videos_from_logs += log_data.get('total_videos_collected', 0)
        
        print(f"Collection runs today: {len(today_logs)}")
        print(f"Total videos in logs: {total_videos_from_logs}")
        
        # Calculate expected runs (every 10 minutes = 144 per day)
        minutes_elapsed = (datetime.now(timezone.utc) - today_start).total_seconds() / 60
        expected_runs = int(minutes_elapsed / 10)
        print(f"Expected runs by now: ~{expected_runs} (every 10 min)")
        
        # Show recent collection runs
        if today_logs:
            print(f"\nRecent collection runs (showing first 10):")
            for i, log in enumerate(today_logs[:10], 1):
                time_str = log.get('timestamp', 'Unknown').strftime('%H:%M:%S') if log.get('timestamp') else 'Unknown'
                videos = log.get('total_videos_collected', 0)
                keywords = log.get('keywords_successful', 0)
                success_rate = log.get('success_rate', 0)
                print(f"  {i:2d}. {time_str}: {videos:3d} videos, {keywords:2d} keywords, {success_rate:5.1f}% success")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    comprehensive_check()