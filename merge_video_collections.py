#!/usr/bin/env python3
"""
Merge video collections to match reddit_keywords baseline
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def merge_videos(fc, from_doc_id, to_doc_id, keyword):
    """Merge videos from one collection to another"""
    print(f"\nMerging videos: '{from_doc_id}' → '{to_doc_id}'")
    
    from_ref = fc.db.collection('youtube_videos').document(from_doc_id)
    to_ref = fc.db.collection('youtube_videos').document(to_doc_id)
    
    # Ensure target parent exists
    if not to_ref.get().exists:
        to_ref.set({
            'keyword': keyword,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'note': 'Parent document for videos subcollection'
        })
        print(f"  Created parent document: {to_doc_id}")
    
    # Get all videos from source
    from_videos = list(from_ref.collection('videos').stream())
    print(f"  Found {len(from_videos)} videos to merge")
    
    merged = 0
    duplicates = 0
    
    for i, video_doc in enumerate(from_videos):
        video_id = video_doc.id
        video_data = video_doc.to_dict()
        
        # Check if video already exists in target
        target_video = to_ref.collection('videos').document(video_id).get()
        
        if not target_video.exists:
            # Copy video to target
            to_ref.collection('videos').document(video_id).set(video_data)
            merged += 1
        else:
            duplicates += 1
        
        # Progress update every 100 videos
        if (i + 1) % 100 == 0:
            print(f"    Progress: {i + 1}/{len(from_videos)} videos processed...")
    
    print(f"  ✅ Merged {merged} videos ({duplicates} duplicates skipped)")
    
    # Delete source collection if all videos moved
    if merged + duplicates == len(from_videos):
        # Delete all videos first
        for video_doc in from_videos:
            video_doc.reference.delete()
        
        # Delete parent document
        from_ref.delete()
        print(f"  ✅ Deleted source collection: {from_doc_id}")
    
    return merged, duplicates

def main():
    print("Merging video collections to match reddit_keywords baseline...")
    
    fc = FirebaseClient()
    
    # Define the merges needed based on our analysis
    merges_needed = [
        {
            'from': '"chatgpt"',
            'to': 'chatgpt',
            'keyword': 'chatgpt'
        },
        {
            'from': 'Runway',
            'to': 'runway',
            'keyword': 'runway'
        },
        {
            'from': 'leonardo ai',
            'to': 'leonardo_ai',
            'keyword': 'leonardo_ai'
        },
        {
            'from': 'stable diffusion',
            'to': 'stable_diffusion',
            'keyword': 'stable_diffusion'
        }
    ]
    
    print(f"\nPlanning to merge {len(merges_needed)} collections:")
    for merge in merges_needed:
        print(f"  {merge['from']} → {merge['to']}")
    
    print("\n" + "="*60)
    
    total_merged = 0
    total_duplicates = 0
    
    for merge in merges_needed:
        try:
            merged, duplicates = merge_videos(
                fc, 
                merge['from'], 
                merge['to'], 
                merge['keyword']
            )
            total_merged += merged
            total_duplicates += duplicates
        except Exception as e:
            print(f"❌ Error merging {merge['from']}: {e}")
    
    print("\n" + "="*60)
    print(f"\n✅ Merge complete!")
    print(f"  Total videos merged: {total_merged}")
    print(f"  Total duplicates skipped: {total_duplicates}")
    
    # Verify final state
    print("\n\nVerifying final state...")
    
    # Check all keywords from reddit_keywords baseline
    reddit_keywords = ['ash', 'brain max by clickup', 'chatgpt', 'claude', 'clueso', 
                      'dalle', 'higgsfield', 'leonardo_ai', 'midjourney', 'qwen3', 
                      'runway', 'sora', 'stable_diffusion', 'stepfun diligence check', 
                      'testsprite 20', 'trickle - magic canvas']
    
    print("\nVideo collections status:")
    for keyword in sorted(reddit_keywords):
        doc_ref = fc.db.collection('youtube_videos').document(keyword)
        if doc_ref.get().exists:
            video_count = len(list(doc_ref.collection('videos').limit(1000).stream()))
            print(f"  ✅ {keyword}: {video_count} videos")
        else:
            print(f"  ❌ {keyword}: Missing parent document")

if __name__ == "__main__":
    main()