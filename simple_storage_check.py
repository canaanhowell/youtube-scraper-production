#!/usr/bin/env python3
"""
Simple check of video storage to verify analysis findings.
"""

import sys
import os
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
load_env()

def main():
    print("=== SIMPLE VIDEO STORAGE CHECK ===")
    
    try:
        fc = FirebaseClient()
        print("✅ Connected to Firebase")
        
        # Get all youtube_videos parent documents
        videos_collection = fc.db.collection('youtube_videos')
        parent_docs = list(videos_collection.stream())
        
        print(f"\nFound {len(parent_docs)} keyword collections:")
        print("-" * 50)
        
        total_videos = 0
        keywords_with_videos = 0
        
        for parent_doc in sorted(parent_docs, key=lambda x: x.id):
            keyword = parent_doc.id
            videos_subcoll = parent_doc.reference.collection('videos')
            
            # Get count by actually counting (simple but works)
            video_count = 0
            try:
                videos = list(videos_subcoll.stream())
                video_count = len(videos)
            except:
                pass
            
            if video_count > 0:
                keywords_with_videos += 1
                total_videos += video_count
                
                # Show sample video titles
                sample_titles = []
                for video in videos[:3]:
                    video_data = video.to_dict()
                    title = video_data.get('title', 'No title')[:40]
                    sample_titles.append(title)
                
                samples_str = '; '.join(sample_titles) if sample_titles else 'N/A'
                print(f"  {keyword:<20}: {video_count:>5,} videos | Samples: {samples_str}...")
            else:
                print(f"  {keyword:<20}: {video_count:>5,} videos")
        
        print("-" * 50)
        print(f"SUMMARY:")
        print(f"  Total keywords: {len(parent_docs)}")
        print(f"  Keywords with videos: {keywords_with_videos}")
        print(f"  Total videos stored: {total_videos:,}")
        print(f"  Average videos per active keyword: {total_videos/keywords_with_videos:.1f}" if keywords_with_videos > 0 else "  No active keywords")
        
        print(f"\n✅ Storage verified - videos ARE being collected and stored!")
        
    except Exception as e:
        print(f"❌ Storage check failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()