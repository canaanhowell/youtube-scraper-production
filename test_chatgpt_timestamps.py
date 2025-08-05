#!/usr/bin/env python3
"""Test ChatGPT keyword to verify timestamp sorting"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

# Initialize Firebase
firebase = FirebaseClient()

# Check ChatGPT keyword
keyword = 'chatgpt'
print(f"Checking videos for keyword: '{keyword}'")
print("=" * 80)

# Get videos collection
videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')

# Get most recent 20 videos
recent_videos = videos_ref.limit(20).get()

print(f"\nFound {len(recent_videos)} videos (showing all)")
print("-" * 80)

# Parse and sort by collection time to see most recent first
videos_list = []
for doc in recent_videos:
    video = doc.to_dict()
    videos_list.append(video)

# Sort by collected_at descending (most recent first)
videos_list.sort(key=lambda x: x.get('collected_at', ''), reverse=True)

for i, video in enumerate(videos_list):
    print(f"\n{i+1}. {video.get('title', 'No title')[:60]}...")
    print(f"   Published: {video.get('published_time', 'No timestamp')}")
    print(f"   Views: {video.get('view_count', 'No views')}")
    print(f"   Collected at: {video.get('collected_at', 'Unknown')}")
    print(f"   Video ID: {video.get('id', 'Unknown')}")
    
print("\n" + "=" * 80)
print("Analysis:")
print("- If sorting by 'most recent', we should see only very recent videos (< 10 min)")
print("- The 'published_time' field shows when YouTube says the video was published")
print("- Videos beyond 30-60 minutes old suggest the filter may not be sorting by recency")