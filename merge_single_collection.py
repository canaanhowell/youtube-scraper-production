#!/usr/bin/env python3
"""
Merge a single video collection
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

def main():
    if len(sys.argv) < 4:
        print("Usage: python3 merge_single_collection.py <from_id> <to_id> <keyword>")
        sys.exit(1)
    
    from_id = sys.argv[1]
    to_id = sys.argv[2]
    keyword = sys.argv[3]
    
    print(f"Merging: '{from_id}' → '{to_id}' (keyword: {keyword})")
    
    fc = FirebaseClient()
    
    from_ref = fc.db.collection('youtube_videos').document(from_id)
    to_ref = fc.db.collection('youtube_videos').document(to_id)
    
    # Check source exists
    if not from_ref.get().exists:
        print(f"❌ Source collection '{from_id}' does not exist")
        return
    
    # Ensure target parent exists
    if not to_ref.get().exists:
        to_ref.set({
            'keyword': keyword,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'note': 'Parent document for videos subcollection'
        })
        print(f"✅ Created parent document: {to_id}")
    
    # Count videos first
    print("Counting videos...")
    from_videos = list(from_ref.collection('videos').stream())
    print(f"Found {len(from_videos)} videos to process")
    
    # Process in batches
    batch_size = 50
    merged = 0
    duplicates = 0
    
    for i in range(0, len(from_videos), batch_size):
        batch = from_videos[i:i+batch_size]
        print(f"\nProcessing batch {i//batch_size + 1} ({i+1}-{min(i+batch_size, len(from_videos))} of {len(from_videos)})")
        
        for video_doc in batch:
            video_id = video_doc.id
            
            # Check if exists in target
            if not to_ref.collection('videos').document(video_id).get().exists:
                # Copy video
                video_data = video_doc.to_dict()
                to_ref.collection('videos').document(video_id).set(video_data)
                merged += 1
            else:
                duplicates += 1
        
        print(f"  Batch complete - Total merged: {merged}, duplicates: {duplicates}")
    
    print(f"\n✅ Merge complete!")
    print(f"  Videos merged: {merged}")
    print(f"  Duplicates skipped: {duplicates}")
    
    # Option to delete source
    if merged + duplicates == len(from_videos):
        print(f"\nAll videos processed. Delete source collection '{from_id}'? (yes/no)")
        # Auto-yes for non-interactive mode
        print("Auto-confirming deletion...")
        
        # Delete videos in batches
        print("Deleting source videos...")
        for i in range(0, len(from_videos), 100):
            batch = from_videos[i:i+100]
            for video_doc in batch:
                video_doc.reference.delete()
            print(f"  Deleted {min(i+100, len(from_videos))}/{len(from_videos)} videos")
        
        # Delete parent
        from_ref.delete()
        print(f"✅ Deleted source collection: {from_id}")

if __name__ == "__main__":
    main()