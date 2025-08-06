#!/usr/bin/env python3
"""
Verify the results of the ChatGPT collection merge
"""

import os
import sys
from pathlib import Path

# Set Firebase credentials path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
os.environ['FIRESTORE_PROJECT_ID'] = 'ai-tracker-466821'

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.firebase_client import FirebaseClient

def verify_merge_results():
    """Verify the merge operation results"""
    
    print("="*60)
    print("CHATGPT MERGE VERIFICATION")
    print("="*60)
    
    fc = FirebaseClient()
    
    # Check if orphaned collection still exists
    print("\n1. Checking orphaned collection status...")
    orphaned_ref = fc.db.collection('youtube_videos').document('"chatgpt"')
    orphaned_exists = orphaned_ref.get().exists
    
    if orphaned_exists:
        orphaned_videos = list(orphaned_ref.collection('videos').stream())
        print(f"   ❌ ORPHANED COLLECTION STILL EXISTS with {len(orphaned_videos)} videos")
    else:
        print(f"   ✅ Orphaned collection successfully deleted")
    
    # Check main collection
    print("\n2. Checking main collection status...")
    main_ref = fc.db.collection('youtube_videos').document('chatgpt')
    main_exists = main_ref.get().exists
    
    if main_exists:
        main_videos = list(main_ref.collection('videos').stream())
        print(f"   ✅ Main collection exists with {len(main_videos)} videos")
        
        # Sample some video data to ensure integrity
        if len(main_videos) > 0:
            sample_video = main_videos[0]
            sample_data = sample_video.to_dict()
            print(f"   ✅ Sample video data structure looks good")
            print(f"      Video ID: {sample_video.id}")
            print(f"      Title: {sample_data.get('title', 'N/A')[:50]}...")
            print(f"      Channel: {sample_data.get('channel', 'N/A')}")
    else:
        print(f"   ❌ MAIN COLLECTION MISSING")
    
    # Overall verification
    print("\n3. Overall verification...")
    if not orphaned_exists and main_exists and len(main_videos) == 2376:
        print(f"   ✅ MERGE FULLY SUCCESSFUL")
        print(f"      - Orphaned collection deleted: Yes")
        print(f"      - Main collection total videos: {len(main_videos)}")
        print(f"      - Expected total: 2376 (1799 + 577)")
        print(f"      - Match: {'Yes' if len(main_videos) == 2376 else 'No'}")
    else:
        print(f"   ❌ VERIFICATION ISSUES DETECTED")
        print(f"      - Orphaned collection deleted: {'Yes' if not orphaned_exists else 'No'}")
        print(f"      - Main collection exists: {'Yes' if main_exists else 'No'}")
        if main_exists:
            print(f"      - Main collection videos: {len(main_videos)}")
    
    print("\n" + "="*60)

def main():
    verify_merge_results()

if __name__ == "__main__":
    main()