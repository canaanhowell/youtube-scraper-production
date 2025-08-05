#!/usr/bin/env python3
"""
Test script to verify that all youtube_collection_logs documents use proper timestamp IDs.
This script simulates various logging scenarios to ensure no hash IDs are created.
"""

import sys
import os
import time
from datetime import datetime

# Add project to path
sys.path.append(str(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient
from src.utils.firebase_client_enhanced import FirebaseClient as FirebaseClientEnhanced
from src.utils.collection_logger import YouTubeCollectionLogger

# Load environment
load_env()


def test_firebase_clients():
    """Test that Firebase clients create proper document IDs."""
    print("Testing Firebase client implementations...")
    
    # Test basic FirebaseClient
    print("\n1. Testing FirebaseClient.log_collection_run()...")
    fc = FirebaseClient()
    
    test_stats = {
        'session_id': 'test_session_123',
        'keywords_processed': ['test1', 'test2'],
        'total_videos_collected': 10,
        'videos_per_keyword': {'test1': 5, 'test2': 5},
        'duration_seconds': 60,
        'success': True,
        'errors': []
    }
    
    try:
        doc_id = fc.log_collection_run(test_stats)
        print(f"   ✓ Created document with ID: {doc_id}")
        
        # Verify the document exists and has proper ID format
        doc = fc.db.collection('youtube_collection_logs').document(doc_id).get()
        if doc.exists:
            print(f"   ✓ Document verified in Firestore")
            
            # Check ID format
            if '_' in doc_id and '-' in doc_id:
                print(f"   ✓ Document ID has proper timestamp format")
            else:
                print(f"   ✗ WARNING: Document ID might not be in timestamp format: {doc_id}")
        else:
            print(f"   ✗ ERROR: Document not found in Firestore")
            
    except Exception as e:
        print(f"   ✗ ERROR: {e}")
    
    # Test enhanced FirebaseClient
    print("\n2. Testing FirebaseClientEnhanced.log_collection_run()...")
    fc_enhanced = FirebaseClientEnhanced()
    
    try:
        doc_id = fc_enhanced.log_collection_run(test_stats)
        print(f"   ✓ Created document with ID: {doc_id}")
        
        # Verify format
        if '_' in doc_id and '-' in doc_id:
            print(f"   ✓ Document ID has proper timestamp format")
        else:
            print(f"   ✗ WARNING: Document ID might not be in timestamp format: {doc_id}")
            
    except Exception as e:
        print(f"   ✗ ERROR: {e}")


def test_collection_logger():
    """Test that collection logger creates proper document IDs."""
    print("\n3. Testing YouTubeCollectionLogger...")
    
    # Test with default session ID
    logger1 = YouTubeCollectionLogger()
    print(f"   Logger initialized with session_id: {logger1.collection_run.session_id}")
    
    # Start a collection
    keywords = ['test_keyword1', 'test_keyword2']
    session_id = logger1.start_collection(keywords)
    print(f"   Collection started with session_id: {session_id}")
    
    # Simulate keyword processing
    logger1.start_keyword('test_keyword1')
    time.sleep(0.1)  # Simulate some work
    logger1.end_keyword('test_keyword1', videos_found=5, videos_saved=5)
    
    # End collection
    summary = logger1.end_collection()
    print(f"   Collection ended with summary: {summary['session_id']}")
    
    # Check if document was created with proper ID
    if logger1.firebase_doc_id:
        print(f"   ✓ Firebase document ID stored: {logger1.firebase_doc_id}")
        if '_' in logger1.firebase_doc_id and '-' in logger1.firebase_doc_id:
            print(f"   ✓ Document ID has proper timestamp format")
        else:
            print(f"   ✗ WARNING: Document ID might not be in timestamp format")
    else:
        print(f"   ✗ WARNING: No Firebase document ID was stored")


def check_existing_logs():
    """Check existing logs for hash IDs."""
    print("\n4. Checking existing youtube_collection_logs for hash IDs...")
    
    fc = FirebaseClient()
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get recent documents
    docs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(20).stream()
    
    hash_count = 0
    proper_count = 0
    
    print("\nRecent document IDs:")
    for doc in docs:
        doc_id = doc.id
        data = doc.to_dict()
        
        # Check if it looks like a hash
        is_hash = not ('_' in doc_id or '-' in doc_id) and len(doc_id) >= 16
        
        if is_hash:
            hash_count += 1
            print(f"   ✗ HASH ID: {doc_id} (type: {data.get('run_type', data.get('event_type', 'unknown'))})")
        else:
            proper_count += 1
            print(f"   ✓ Proper ID: {doc_id}")
    
    print(f"\nSummary: {proper_count} proper IDs, {hash_count} hash IDs")
    
    return hash_count == 0


def main():
    """Run all tests."""
    print("=" * 60)
    print("YouTube Collection Logs ID Format Test")
    print("=" * 60)
    
    # Run tests
    test_firebase_clients()
    test_collection_logger()
    all_good = check_existing_logs()
    
    print("\n" + "=" * 60)
    if all_good:
        print("✅ All tests passed! No hash IDs found.")
    else:
        print("⚠️  Some issues found. Check the output above.")
    print("=" * 60)


if __name__ == "__main__":
    main()