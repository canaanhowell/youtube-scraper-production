#!/usr/bin/env python3
"""
Test the simplified logging format for YouTube collection logs
"""

import os
import sys
from datetime import datetime

# Add project path to sys.path
sys.path.insert(0, '/opt/youtube_app')

from src.utils.firebase_client_enhanced import FirebaseClient

def test_simplified_logging():
    """Test the simplified logging format"""
    print("Testing simplified collection logging format...")
    
    # Mock collection stats with all required fields
    test_stats = {
        'session_id': f'test_session_{int(datetime.now().timestamp())}',
        'container': 'youtube-vpn-test',
        'duplicates_filtered': 42,
        'total_videos_collected': 150,
        'videos_per_keyword': {
            'python programming': 25,
            'web development': 35,
            'machine learning': 45,
            'data science': 45
        },
        'duration_seconds': 180.5
    }
    
    try:
        # Initialize Firebase client
        firebase_client = FirebaseClient()
        
        print("Firebase client initialized successfully")
        
        # Test logging with simplified format
        print("Logging test collection run...")
        doc_id = firebase_client.log_collection_run(test_stats)
        
        if doc_id:
            print(f"✅ Successfully logged simplified collection run with ID: {doc_id}")
            print(f"✅ Logged fields:")
            print(f"   - timestamp: SERVER_TIMESTAMP")
            print(f"   - container: {test_stats['container']}")
            print(f"   - duplicates_filtered: {test_stats['duplicates_filtered']}")
            print(f"   - session_id: {test_stats['session_id']}")
            print(f"   - total_videos_collected: {test_stats['total_videos_collected']}")
            print(f"   - duration_seconds: {test_stats['duration_seconds']}")
            print(f"   - videos_per_keyword: {len(test_stats['videos_per_keyword'])} keywords")
            return True
        else:
            print("❌ Failed to log collection run")
            return False
            
    except Exception as e:
        print(f"❌ Error testing simplified logging: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_simplified_logging()
    sys.exit(0 if success else 1)