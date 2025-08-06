#!/usr/bin/env python3
"""
Check if there are actually any videos being stored in Firebase
to verify our analysis findings.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
load_env()

def check_video_storage(fc):
    """Check actual video storage across all keywords"""
    print("=== CHECKING ACTUAL VIDEO STORAGE ===")
    
    # Get all youtube_videos parent documents
    videos_collection = fc.db.collection('youtube_videos')
    parent_docs = list(videos_collection.stream())
    
    print(f"Found {len(parent_docs)} keyword parent documents")
    
    total_videos = 0
    keywords_with_videos = 0
    
    for parent_doc in parent_docs:
        keyword = parent_doc.id
        videos_subcoll = parent_doc.reference.collection('videos')
        
        # Get total count of videos for this keyword
        videos = list(videos_subcoll.limit(5).stream())  # Just sample to check existence
        
        if videos:
            # Get actual count by sampling and extrapolating if needed
            all_videos = list(videos_subcoll.stream())
            video_count = len(all_videos)
            
            if video_count > 0:
                keywords_with_videos += 1
                total_videos += video_count
                
                # Get newest and oldest videos
                newest_video = None
                oldest_video = None
                
                for video in all_videos[:10]:  # Sample first 10
                    video_data = video.to_dict()
                    collected_at = video_data.get('collected_at')
                    
                    if collected_at:
                        # Handle both datetime objects and strings
                        if isinstance(collected_at, str):
                            try:
                                collected_at = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
                            except:
                                continue
                        
                        if newest_video is None or collected_at > newest_video:
                            newest_video = collected_at
                        if oldest_video is None or collected_at < oldest_video:
                            oldest_video = collected_at
                
                newest_str = newest_video.strftime('%Y-%m-%d %H:%M') if newest_video else 'N/A'
                oldest_str = oldest_video.strftime('%Y-%m-%d %H:%M') if oldest_video else 'N/A'
                
                print(f"  {keyword}: {video_count:,} videos (newest: {newest_str}, oldest: {oldest_str})")
        else:
            print(f"  {keyword}: 0 videos")
    
    print(f"\nSUMMARY:")
    print(f"  Total keywords: {len(parent_docs)}")
    print(f"  Keywords with videos: {keywords_with_videos}")
    print(f"  Total videos stored: {total_videos:,}")
    
    # Check recent activity
    print(f"\n=== RECENT ACTIVITY CHECK ===")
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    
    recent_activity = {}
    
    for parent_doc in parent_docs[:10]:  # Check top 10 keywords
        keyword = parent_doc.id
        videos_subcoll = parent_doc.reference.collection('videos')
        
        try:
            recent_videos = list(videos_subcoll.where('collected_at', '>=', start_time).stream())
            if recent_videos:
                recent_activity[keyword] = len(recent_videos)
                
                # Sample a few recent videos
                for video in recent_videos[:3]:
                    video_data = video.to_dict()
                    title = video_data.get('title', '')[:50]
                    collected_at = video_data.get('collected_at')
                    time_str = collected_at.strftime('%m-%d %H:%M') if collected_at else 'N/A'
                    print(f"    {time_str}: {title}...")
        except:
            pass
    
    if recent_activity:
        print(f"\nKeywords with recent activity (last 24h): {len(recent_activity)}")
        for keyword, count in sorted(recent_activity.items(), key=lambda x: x[1], reverse=True):
            print(f"  {keyword}: {count} new videos")
    else:
        print(f"\nNo recent video activity found in the last 24 hours")

def main():
    print("Checking Actual Video Storage in Firebase")
    print("=" * 50)
    
    try:
        fc = FirebaseClient()
        print("✅ Connected to Firebase")
        
        check_video_storage(fc)
        
        print(f"\n✅ Storage check complete!")
        
    except Exception as e:
        print(f"❌ Storage check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()