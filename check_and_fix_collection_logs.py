#!/usr/bin/env python3
"""
Check youtube_collection_logs for hash IDs and optionally clean them up.
Also provides information about which scripts might be creating them.
"""

import re
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()


def is_hash_id(doc_id):
    """
    Check if a document ID looks like a hash (auto-generated ID).
    Hash IDs are typically 20 characters of mixed alphanumeric.
    """
    # If it contains underscore or dash, it's likely a meaningful ID
    if '_' in doc_id or '-' in doc_id:
        return False
    
    # Check if it looks like a hash: 16-28 chars, alphanumeric only
    if re.match(r'^[a-zA-Z0-9]{16,28}$', doc_id):
        return True
    
    return False


def analyze_document(doc):
    """Analyze a document to identify its source."""
    data = doc.to_dict()
    doc_id = doc.id
    
    info = {
        'id': doc_id,
        'timestamp': data.get('timestamp', 'unknown'),
        'source': 'unknown'
    }
    
    # Try to identify the source based on document structure
    if 'event_type' in data and 'keyword_results' in data:
        info['source'] = 'collection_logger.py (YouTubeCollectionLogger)'
        info['event_type'] = data.get('event_type')
        info['session_id'] = data.get('session_id', 'unknown')
    elif 'run_type' in data:
        run_type = data.get('run_type', '')
        if 'interval' in run_type:
            info['source'] = 'interval metrics script'
        elif 'daily' in run_type:
            info['source'] = 'daily metrics script'
        else:
            info['source'] = f'metrics script ({run_type})'
    elif 'script_name' in data:
        info['source'] = data.get('script_name', 'unknown script')
    elif 'keywords_processed' in data and 'total_videos_collected' in data:
        info['source'] = 'youtube_collection_manager.py (via firebase_client)'
        info['session_id'] = data.get('session_id', 'unknown')
    
    return info


def main():
    print("Connecting to Firebase...")
    fc = FirebaseClient()
    
    print("\nFetching all documents from youtube_collection_logs...")
    logs_ref = fc.db.collection('youtube_collection_logs')
    
    # Get all documents
    all_docs = list(logs_ref.stream())
    
    print(f"Total documents found: {len(all_docs)}")
    
    # Categorize documents
    hash_docs = []
    proper_docs = []
    
    for doc in all_docs:
        if is_hash_id(doc.id):
            hash_docs.append(doc)
        else:
            proper_docs.append(doc)
    
    print(f"\nDocuments with hash IDs: {len(hash_docs)}")
    print(f"Documents with proper IDs: {len(proper_docs)}")
    
    # Analyze hash documents by source
    if hash_docs:
        print("\n" + "="*60)
        print("HASH DOCUMENTS ANALYSIS")
        print("="*60)
        
        sources = {}
        for doc in hash_docs:
            info = analyze_document(doc)
            source = info['source']
            if source not in sources:
                sources[source] = []
            sources[source].append(info)
        
        # Print analysis by source
        for source, docs in sources.items():
            print(f"\nSource: {source}")
            print(f"Count: {len(docs)}")
            print("Sample documents:")
            for doc_info in docs[:3]:  # Show first 3
                print(f"  - ID: {doc_info['id']}")
                print(f"    Timestamp: {doc_info['timestamp']}")
                if 'session_id' in doc_info:
                    print(f"    Session ID: {doc_info['session_id']}")
                if 'event_type' in doc_info:
                    print(f"    Event Type: {doc_info['event_type']}")
        
        # Check recent hash documents
        print("\n" + "="*60)
        print("RECENT HASH DOCUMENTS (Last 24 hours)")
        print("="*60)
        
        recent_count = 0
        now = datetime.utcnow()
        for doc in hash_docs:
            data = doc.to_dict()
            timestamp = data.get('timestamp')
            if timestamp:
                # Convert Firestore timestamp to datetime
                try:
                    if hasattr(timestamp, 'seconds'):
                        doc_time = datetime.fromtimestamp(timestamp.seconds)
                    else:
                        doc_time = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                    
                    if now - doc_time < timedelta(hours=24):
                        recent_count += 1
                        print(f"\n  Recent hash doc: {doc.id}")
                        print(f"  Created: {doc_time}")
                        info = analyze_document(doc)
                        print(f"  Source: {info['source']}")
                except:
                    pass
        
        print(f"\nTotal recent hash documents (last 24h): {recent_count}")
        
        # Offer to clean up
        print("\n" + "="*60)
        response = input("\nDo you want to DELETE all hash documents? (yes/no): ")
        
        if response.lower() == 'yes':
            print("\nDeleting hash documents...")
            deleted_count = 0
            
            for doc in hash_docs:
                try:
                    doc.reference.delete()
                    deleted_count += 1
                    if deleted_count % 10 == 0:
                        print(f"  Deleted {deleted_count}/{len(hash_docs)}...")
                except Exception as e:
                    print(f"  Error deleting {doc.id}: {e}")
            
            print(f"\nSuccessfully deleted {deleted_count} hash documents")
        else:
            print("Cleanup cancelled")
    else:
        print("\n✅ Great news! No hash documents found!")
    
    # Show sample of proper documents
    print("\n" + "="*60)
    print("SAMPLE OF PROPER DOCUMENT IDs")
    print("="*60)
    
    if proper_docs:
        for doc in proper_docs[:10]:
            info = analyze_document(doc)
            print(f"\n✓ ID: {doc.id}")
            print(f"  Source: {info['source']}")
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS")
    print("="*60)
    print("\n1. All Firebase client methods have been updated with validation")
    print("2. collection_logger.py has been fixed to use timestamp IDs")
    print("3. Monitor for new hash IDs using: python src/scripts/utilities/monitor_collection_logs.py")
    print("4. The source of hash IDs was likely the collection_logger.py using session_id as doc ID")
    print("\nThe issue should now be resolved!")


if __name__ == "__main__":
    main()