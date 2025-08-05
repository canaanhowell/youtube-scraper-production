#!/usr/bin/env python3
"""
Verify final state of all collections
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
    
    print("Verifying final state of keyword sync...\n")
    
    # Get reddit_keywords baseline
    reddit_keywords = ['ash', 'brain max by clickup', 'chatgpt', 'claude', 'clueso', 
                      'dalle', 'higgsfield', 'leonardo_ai', 'midjourney', 'qwen3', 
                      'runway', 'sora', 'stable_diffusion', 'stepfun diligence check', 
                      'testsprite 20', 'trickle - magic canvas']
    
    print("Checking youtube_keywords collection:")
    youtube_keywords = list(fc.db.collection('youtube_keywords').stream())
    yt_ids = set(doc.id for doc in youtube_keywords)
    
    print(f"  Total documents: {len(youtube_keywords)}")
    print(f"  Matching baseline: {len(yt_ids.intersection(set(reddit_keywords)))}/{len(reddit_keywords)}")
    
    missing = set(reddit_keywords) - yt_ids
    if missing:
        print(f"  Missing: {missing}")
    
    extra = yt_ids - set(reddit_keywords)
    if extra:
        print(f"  Extra: {extra}")
    
    print("\n\nChecking youtube_videos collection:")
    all_video_docs = list(fc.db.collection('youtube_videos').stream())
    
    print(f"  Total parent documents: {len(all_video_docs)}")
    
    # Check each keyword
    print("\n  Video counts by keyword:")
    total_videos = 0
    
    for keyword in sorted(reddit_keywords):
        doc_ref = fc.db.collection('youtube_videos').document(keyword)
        if doc_ref.get().exists:
            count = len(list(doc_ref.collection('videos').limit(1000).stream()))
            total_videos += count
            if count > 0:
                print(f"    ✅ {keyword}: {count} videos")
            else:
                print(f"    ⚠️  {keyword}: 0 videos")
        else:
            print(f"    ❌ {keyword}: Missing parent document")
    
    # Check for extra collections
    video_doc_ids = set(doc.id for doc in all_video_docs)
    extra_videos = video_doc_ids - set(reddit_keywords)
    
    if extra_videos:
        print(f"\n  Extra collections not in baseline:")
        for extra in extra_videos:
            doc_ref = fc.db.collection('youtube_videos').document(extra)
            count = len(list(doc_ref.collection('videos').limit(1000).stream()))
            print(f"    ⚠️  '{extra}': {count} videos")
    
    print(f"\n  Total videos across all collections: {total_videos}")
    
    print("\n\n✅ Summary:")
    if not missing and not extra and not extra_videos:
        print("  All collections are properly synced with reddit_keywords baseline!")
    else:
        print("  Some discrepancies remain - manual cleanup may be needed")

if __name__ == "__main__":
    main()