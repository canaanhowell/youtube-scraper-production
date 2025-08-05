#!/usr/bin/env python3
"""
Check recent scraper logs for video save errors
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    print("Connecting to Firebase...")
    fc = FirebaseClient()
    
    # Check scraper logs
    print("\nChecking recent scraper logs for errors...")
    
    # Check for any error logs
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get recent logs
    start_time = datetime.now(timezone.utc) - timedelta(hours=24)
    recent_logs = list(logs_ref.where('timestamp', '>=', start_time).order_by('timestamp', direction='DESCENDING').limit(20).stream())
    
    print(f"\nFound {len(recent_logs)} recent logs")
    
    # Look for errors in logs
    for log in recent_logs:
        data = log.to_dict()
        
        # Check for errors field
        if 'errors' in data and data['errors']:
            timestamp = data.get('timestamp')
            print(f"\n❌ Errors found in log at {timestamp}:")
            for error in data['errors']:
                print(f"  - {error}")
        
        # Check for failed saves
        if 'results' in data:
            results = data['results']
            if 'errors' in results and results['errors'] > 0:
                print(f"\n⚠️  {results['errors']} errors in run at {data.get('timestamp')}")
    
    # Check collection manager logs to see what's happening
    print("\n\nChecking youtube_collection_manager.py logic...")
    
    # Check if videos are being filtered out
    print("\nLooking for filtered videos in recent logs...")
    
    for log in recent_logs[:5]:
        data = log.to_dict()
        timestamp = data.get('timestamp')
        
        if 'results' in data and 'keywords' in data['results']:
            keywords_data = data['results']['keywords']
            
            # Look for chatgpt specifically
            if 'chatgpt' in keywords_data:
                chatgpt_data = keywords_data['chatgpt']
                
                if hasattr(timestamp, 'strftime'):
                    print(f"\n{timestamp.strftime('%Y-%m-%d %H:%M:%S')} - ChatGPT collection:")
                    print(f"  Videos found: {chatgpt_data.get('videos_found_in_search', 0)}")
                    print(f"  Video count: {chatgpt_data.get('video_count', 0)}")
                    
                    if 'error' in chatgpt_data:
                        print(f"  ❌ Error: {chatgpt_data['error']}")
    
    # Check if there's a different collection path being used
    print("\n\nChecking all collections for video data...")
    
    # List all collections
    collections = fc.db.collections()
    video_collections = []
    
    for collection in collections:
        col_id = collection.id
        if 'video' in col_id.lower():
            video_collections.append(col_id)
            
            # Get a sample document
            docs = list(collection.limit(1).stream())
            if docs:
                print(f"\n📁 Collection: {col_id}")
                print(f"   Sample doc ID: {docs[0].id}")
                
                # Check if it has subcollections
                if col_id == 'youtube_videos':
                    # Check a keyword document
                    keyword_doc = collection.document('chatgpt')
                    if keyword_doc.get().exists:
                        # Check videos subcollection
                        videos_sub = keyword_doc.collection('videos')
                        video_count = len(list(videos_sub.limit(1000).stream()))
                        print(f"   ChatGPT videos subcollection: {video_count} documents")
    
    print(f"\n\nVideo-related collections found: {video_collections}")

if __name__ == "__main__":
    main()