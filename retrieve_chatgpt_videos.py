#!/usr/bin/env python3
"""
Script to retrieve ChatGPT videos from Firebase Firestore
Filters for the most recent collection run (around 7:10 timeframe)
"""

import json
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import sys

def main():
    try:
        # Initialize Firebase Admin SDK
        cred = credentials.Certificate('/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json')
        firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        db = firestore.client()
        
        print("Connected to Firebase successfully!")
        print(f"Querying youtube_videos/chatgpt/videos collection...")
        
        # Reference to the chatgpt videos collection
        videos_ref = db.collection('youtube_videos').document('chatgpt').collection('videos')
        
        # Get all videos and sort by collection timestamp
        videos_query = videos_ref.order_by('collected_at', direction=firestore.Query.DESCENDING).limit(50)
        videos = videos_query.stream()
        
        video_list = []
        for video in videos:
            video_data = video.to_dict()
            video_data['document_id'] = video.id
            video_list.append(video_data)
        
        if not video_list:
            print("No videos found in the collection.")
            return
        
        print(f"\nFound {len(video_list)} total videos. Analyzing timestamps...")
        
        # Find videos from the most recent collection batch
        # Look for videos collected within a short time window (e.g., last 2 hours)
        now = datetime.now()
        recent_threshold = now - timedelta(hours=2)
        
        recent_videos = []
        for video in video_list:
            collected_at = video.get('collected_at')
            if collected_at:
                # Convert Firestore timestamp to datetime
                if hasattr(collected_at, 'timestamp'):
                    collected_datetime = datetime.fromtimestamp(collected_at.timestamp())
                else:
                    # Handle different timestamp formats
                    try:
                        collected_datetime = datetime.fromisoformat(str(collected_at).replace('Z', '+00:00'))
                    except:
                        print(f"Could not parse timestamp: {collected_at}")
                        continue
                
                if collected_datetime >= recent_threshold:
                    recent_videos.append((video, collected_datetime))
        
        if not recent_videos:
            print("No videos found from recent collection runs.")
            print("Showing most recent 19 videos regardless of timestamp:")
            recent_videos = [(video, None) for video in video_list[:19]]
        else:
            # Sort by collection time and take the most recent batch
            recent_videos.sort(key=lambda x: x[1] if x[1] else datetime.min, reverse=True)
            
            # If we have more than 19, take the first 19
            if len(recent_videos) > 19:
                recent_videos = recent_videos[:19]
        
        print(f"\nDisplaying {len(recent_videos)} videos from the most recent collection:")
        print("=" * 80)
        
        for i, (video, timestamp) in enumerate(recent_videos, 1):
            print(f"\n--- VIDEO {i} ---")
            print(f"Document ID: {video.get('document_id', 'N/A')}")
            print(f"Video ID: {video.get('video_id', 'N/A')}")
            print(f"Title: {video.get('title', 'N/A')}")
            print(f"URL: https://www.youtube.com/watch?v={video.get('video_id', '')}")
            print(f"Channel: {video.get('channel_name', 'N/A')}")
            view_count = video.get('view_count', 'N/A')
            if isinstance(view_count, int):
                print(f"View Count: {view_count:,}")
            else:
                print(f"View Count: {view_count}")
            print(f"Duration: {video.get('duration', 'N/A')}")
            print(f"Published: {video.get('published_at', 'N/A')}")
            
            # Display collection timestamp
            if timestamp:
                print(f"Collected: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            else:
                collected_at = video.get('collected_at', 'N/A')
                print(f"Collected: {collected_at}")
            
            # Display additional metadata if available
            if video.get('description'):
                desc = video.get('description', '')[:200] + '...' if len(video.get('description', '')) > 200 else video.get('description', '')
                print(f"Description: {desc}")
            
            if video.get('tags'):
                print(f"Tags: {', '.join(video.get('tags', []))}")
            
            if video.get('thumbnail_url'):
                print(f"Thumbnail: {video.get('thumbnail_url')}")
            
            # Any other metadata
            extra_fields = {k: v for k, v in video.items() 
                          if k not in ['document_id', 'video_id', 'title', 'channel_name', 'view_count', 
                                     'duration', 'published_at', 'collected_at', 'description', 'tags', 'thumbnail_url']}
            if extra_fields:
                print("Additional metadata:")
                for key, value in extra_fields.items():
                    print(f"  {key}: {value}")
            
            print("-" * 50)
        
        print(f"\nTotal videos displayed: {len(recent_videos)}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()