#!/usr/bin/env python3
"""
Debug why videos aren't being stored despite being counted
"""

import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    print("Debugging video storage issue...")
    
    # Check if PLAYWRIGHT is available
    try:
        import playwright
        print("✅ Playwright is installed")
    except ImportError:
        print("❌ Playwright NOT installed - will use wget method")
    
    # Check scraper settings
    print("\nChecking scraper configuration...")
    
    # Check if pagination is enabled
    from src.scripts.youtube_scraper_production import YouTubeScraperProduction
    
    scraper = YouTubeScraperProduction()
    print(f"Enable pagination: {scraper.enable_pagination}")
    print(f"Container name: {scraper.container_name}")
    
    # Test the _save_to_firebase method directly
    print("\n\nTesting Firebase save functionality...")
    
    fc = FirebaseClient()
    
    # Create a test video
    test_video = {
        'id': 'TEST_VIDEO_123',
        'title': 'Test Video for Debugging',
        'url': 'https://youtube.com/watch?v=TEST_VIDEO_123',
        'channel_name': 'Test Channel',
        'view_count': '1,000 views',
        'duration': '10:00',
        'published_time': '1 hour ago',
        'thumbnail_url': 'https://example.com/thumb.jpg',
        'collected_at': datetime.now(timezone.utc).isoformat(),
        'keyword': 'test_keyword'
    }
    
    try:
        # Try to save directly
        print("Attempting to save test video to Firebase...")
        
        result = scraper._save_to_firebase('test_keyword', test_video)
        print(f"Save result: {result}")
        
        # Check if it was saved
        doc_ref = fc.db.collection('youtube_videos').document('test_keyword').collection('videos').document('TEST_VIDEO_123')
        doc = doc_ref.get()
        
        if doc.exists:
            print("✅ Test video saved successfully!")
            # Clean up
            doc_ref.delete()
            print("Test video deleted")
        else:
            print("❌ Test video NOT saved - Firebase write issue")
            
    except Exception as e:
        print(f"❌ Error saving test video: {e}")
        import traceback
        traceback.print_exc()
    
    # Check recent logs for save errors
    print("\n\nChecking scraper logs for save errors...")
    
    try:
        # Read recent scraper log
        result = subprocess.run(
            ['tail', '-n', '100', '/workspace/youtube_app/logs/scraper.log'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log_lines = result.stdout.split('\n')
            error_lines = [line for line in log_lines if 'Error saving' in line or 'Failed to save' in line]
            
            if error_lines:
                print(f"\nFound {len(error_lines)} save errors in logs:")
                for line in error_lines[-5:]:  # Show last 5
                    print(f"  {line}")
            else:
                print("No save errors found in recent logs")
        else:
            print("Could not read scraper.log")
            
    except Exception as e:
        print(f"Error reading logs: {e}")
    
    # Check if the issue is with the keyword document structure
    print("\n\nChecking youtube_videos collection structure...")
    
    # Check if chatgpt keyword document exists
    chatgpt_doc = fc.db.collection('youtube_videos').document('chatgpt').get()
    
    if chatgpt_doc.exists:
        print("✅ chatgpt document exists")
        data = chatgpt_doc.to_dict()
        print(f"   Fields: {list(data.keys()) if data else 'No fields'}")
        
        # Check videos subcollection
        videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
        video_count = len(list(videos_ref.limit(1000).stream()))
        print(f"   Videos subcollection: {video_count} documents")
        
        # Get a sample video
        sample = list(videos_ref.limit(1).stream())
        if sample:
            sample_data = sample[0].to_dict()
            print(f"   Sample video ID: {sample[0].id}")
            print(f"   Collected at: {sample_data.get('collected_at', 'Unknown')}")
    else:
        print("❌ chatgpt document does NOT exist")
        print("   This might be the issue - the parent document needs to exist")
        
        # Try creating the parent document
        print("\n   Attempting to create chatgpt parent document...")
        try:
            fc.db.collection('youtube_videos').document('chatgpt').set({
                'keyword': 'chatgpt',
                'created_at': datetime.now(timezone.utc),
                'note': 'Parent document for videos subcollection'
            })
            print("   ✅ Created chatgpt parent document")
        except Exception as e:
            print(f"   ❌ Failed to create parent document: {e}")

if __name__ == "__main__":
    main()