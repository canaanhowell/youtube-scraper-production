#!/usr/bin/env python3
"""
Delete the quoted chatgpt collection
"""

import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    fc = FirebaseClient()
    
    print("Deleting '\"chatgpt\"' collection...")
    
    quoted_ref = fc.db.collection('youtube_videos').document('"chatgpt"')
    
    if not quoted_ref.get().exists:
        print("Collection does not exist")
        return
    
    # Get all videos
    videos = list(quoted_ref.collection('videos').stream())
    print(f"Found {len(videos)} videos to delete")
    
    # Delete in batches
    batch_size = 100
    for i in range(0, len(videos), batch_size):
        batch = videos[i:i+batch_size]
        for video in batch:
            video.reference.delete()
        print(f"  Deleted {min(i+batch_size, len(videos))}/{len(videos)} videos")
    
    # Delete parent
    quoted_ref.delete()
    print("✅ Deleted '\"chatgpt\"' collection")

if __name__ == "__main__":
    main()