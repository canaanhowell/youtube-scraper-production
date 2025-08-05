#!/usr/bin/env python3
"""
Analyze the two chatgpt collections to understand overlap
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
    
    print("Analyzing chatgpt collections...")
    
    # Get videos from both collections
    quoted_ref = fc.db.collection('youtube_videos').document('"chatgpt"')
    regular_ref = fc.db.collection('youtube_videos').document('chatgpt')
    
    print("\nLoading videos from '\"chatgpt\"' collection...")
    quoted_videos = list(quoted_ref.collection('videos').stream())
    quoted_ids = set(doc.id for doc in quoted_videos)
    print(f"Found {len(quoted_videos)} videos")
    
    print("\nLoading videos from 'chatgpt' collection...")
    regular_videos = list(regular_ref.collection('videos').stream())
    regular_ids = set(doc.id for doc in regular_videos)
    print(f"Found {len(regular_videos)} videos")
    
    # Analyze overlap
    common_ids = quoted_ids.intersection(regular_ids)
    quoted_only = quoted_ids - regular_ids
    regular_only = regular_ids - quoted_ids
    
    print(f"\n\nAnalysis:")
    print(f"Common videos: {len(common_ids)}")
    print(f"Only in '\"chatgpt\"': {len(quoted_only)}")
    print(f"Only in 'chatgpt': {len(regular_only)}")
    
    # Sample some videos to see dates
    print("\n\nSample videos from '\"chatgpt\"' collection:")
    for i, doc in enumerate(quoted_videos[:5]):
        data = doc.to_dict()
        print(f"  {doc.id}: {data.get('collected_at', 'No date')}")
    
    print("\n\nSample videos from 'chatgpt' collection:")
    for i, doc in enumerate(regular_videos[:5]):
        data = doc.to_dict()
        print(f"  {doc.id}: {data.get('collected_at', 'No date')}")
    
    # Check collection dates
    print("\n\nChecking collection date ranges...")
    
    # For quoted collection
    dates = []
    for doc in quoted_videos:
        data = doc.to_dict()
        if 'collected_at' in data:
            dates.append(data['collected_at'])
    
    if dates:
        dates.sort()
        print(f"\n'\"chatgpt\"' collection:")
        print(f"  Earliest: {dates[0]}")
        print(f"  Latest: {dates[-1]}")
    
    # For regular collection
    dates = []
    for doc in regular_videos:
        data = doc.to_dict()
        if 'collected_at' in data:
            dates.append(data['collected_at'])
    
    if dates:
        dates.sort()
        print(f"\n'chatgpt' collection:")
        print(f"  Earliest: {dates[0]}")
        print(f"  Latest: {dates[-1]}")
    
    # Recommendation
    print("\n\nRecommendation:")
    if len(quoted_only) > 0:
        print(f"Merge {len(quoted_only)} unique videos from '\"chatgpt\"' to 'chatgpt'")
        print("Then delete the '\"chatgpt\"' collection")
    else:
        print("All videos in '\"chatgpt\"' already exist in 'chatgpt'")
        print("Safe to delete '\"chatgpt\"' collection")

if __name__ == "__main__":
    main()