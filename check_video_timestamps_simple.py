#!/usr/bin/env python3
"""Check video timestamps in Firebase - simple version"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timedelta
from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

# Initialize Firebase
firebase = FirebaseClient()

# Check a keyword's recent videos
keyword = 'claude'
print(f"Checking videos for keyword: '{keyword}'")
print("=" * 80)

# Get videos collection
videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')

# Get most recent 10 videos (no filter)
recent_videos = videos_ref.limit(10).get()

print(f"\nFound {len(recent_videos)} videos (showing first 10)")
print("-" * 80)

for i, doc in enumerate(recent_videos):
    video = doc.to_dict()
    print(f"\n{i+1}. {video.get('title', 'No title')[:60]}...")
    print(f"   Published: {video.get('published_time', 'No timestamp')}")
    print(f"   Views: {video.get('view_count', 'No views')}")
    print(f"   Collected at: {video.get('collected_at', 'Unknown')}")
    print(f"   Video ID: {video.get('id', 'Unknown')}")
    
print("\n" + "=" * 80)
print("Note: 'Published' shows YouTube's relative timestamp (e.g., '2 hours ago')")
print("These should all be within 'Last hour' if the filter is working correctly")