#!/usr/bin/env python3
"""
Test script to validate the logging fixes work correctly
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def test_logging_structure():
    """Test that the logging structure includes all required fields"""
    print("TESTING LOGGING STRUCTURE")
    print("="*50)
    
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Create mock collection stats with all required fields
    test_stats = {
        'session_id': 'test_session_12345_1',
        'start_time': datetime.now(timezone.utc),
        'script_name': 'youtube_collection_manager.py',
        'keywords_processed': ['chatgpt', 'claude', 'copilot'],
        'keywords_successful': 3,
        'keywords_failed': 0,
        'total_videos_collected': 47,
        'videos_per_keyword': {'chatgpt': 20, 'claude': 15, 'copilot': 12},
        'success_rate': 100.0,
        'errors': [],
        'success': True,
        'container': 'youtube-vpn-1',
        'instance_id': 1,
        'vm_hostname': 'test-vm',
        'duration_seconds': 85.3,
        'vpn_servers_used': ['us-nyc.prod.surfshark.com'],
        'redis_enabled': True,
        'duplicates_filtered': 3
    }
    
    print("📊 Test Collection Stats:")
    for key, value in test_stats.items():
        if key != 'start_time':
            print(f"   {key}: {value}")
    
    # Test the log_collection_run method
    print(f"\n📋 Testing Firebase log_collection_run method...")
    
    try:
        # This will create a test log entry
        log_id = firebase.log_collection_run(test_stats)
        
        if log_id:
            print(f"✅ Successfully created test log: {log_id}")
            
            # Verify the log was created with correct fields
            print(f"\n🔍 Verifying logged data...")
            
            log_ref = firebase.db.collection('youtube_collection_logs').document(log_id)
            log_doc = log_ref.get()
            
            if log_doc.exists:
                log_data = log_doc.to_dict()
                print(f"✅ Log document exists")
                
                # Check required fields
                required_fields = [
                    'session_id', 'script_name', 'keywords_successful', 'keywords_failed',
                    'total_videos_collected', 'success_rate', 'container', 'instance_id',
                    'vm_hostname', 'videos_per_keyword'
                ]
                
                missing_fields = []
                for field in required_fields:
                    if field not in log_data:
                        missing_fields.append(field)
                    else:
                        print(f"   ✓ {field}: {log_data[field]}")
                
                if missing_fields:
                    print(f"❌ Missing fields: {missing_fields}")
                else:
                    print(f"✅ All required fields present!")
                
                # Verify the key values are correct
                print(f"\n🎯 Key Value Verification:")
                print(f"   Keywords successful: {log_data.get('keywords_successful')} (expected: 3)")
                print(f"   Keywords failed: {log_data.get('keywords_failed')} (expected: 0)")
                print(f"   Success rate: {log_data.get('success_rate')}% (expected: 100.0%)")
                print(f"   Total videos: {log_data.get('total_videos_collected')} (expected: 47)")
                print(f"   Script name: {log_data.get('script_name')} (expected: youtube_collection_manager.py)")
                
            else:
                print(f"❌ Log document not found")
                
        else:
            print(f"❌ Failed to create log")
            
    except Exception as e:
        print(f"❌ Error testing logging: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "="*50)
    print("LOGGING TEST COMPLETE")

def compare_with_recent_logs():
    """Compare the test structure with recent production logs"""
    print(f"\nCOMPARING WITH RECENT PRODUCTION LOGS")
    print("="*50)
    
    try:
        # Load environment
        load_env()
        firebase = FirebaseClient()
        
        # Get most recent production log
        logs_ref = firebase.db.collection('youtube_collection_logs')
        recent_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(3).get()
        
        print("Recent production logs:")
        for i, log in enumerate(recent_logs, 1):
            log_data = log.to_dict()
            print(f"\n{i}. Log ID: {log.id}")
            print(f"   Keywords successful: {log_data.get('keywords_successful', 'MISSING')}")
            print(f"   Keywords failed: {log_data.get('keywords_failed', 'MISSING')}")
            print(f"   Success rate: {log_data.get('success_rate', 'MISSING')}%")
            print(f"   Script name: {log_data.get('script_name', 'MISSING')}")
            print(f"   Total videos: {log_data.get('total_videos_collected', 'MISSING')}")
            
            # Check if this is a broken log (0 keywords successful)
            keywords_successful = log_data.get('keywords_successful', 0)
            total_videos = log_data.get('total_videos_collected', 0)
            
            if total_videos > 0 and keywords_successful == 0:
                print(f"   🚨 BROKEN LOG: Has {total_videos} videos but 0 successful keywords")
            elif keywords_successful > 0:
                print(f"   ✅ FIXED LOG: {keywords_successful} successful keywords")
    
    except Exception as e:
        print(f"Error comparing logs: {e}")

if __name__ == "__main__":
    test_logging_structure()
    compare_with_recent_logs()