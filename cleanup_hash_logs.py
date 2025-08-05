#!/usr/bin/env python3
"""
Delete all documents in youtube_collection_logs that have hash-like IDs
(auto-generated IDs that look like: fMWWRQq8P6bwIRXgcXv0)
"""

import re
import sys
from pathlib import Path

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
    Our meaningful IDs contain underscores and follow patterns like:
    - interval_metrics_2025-08-05_15-30-45_UTC
    - daily_metrics_2025-08-05_02-00-00_UTC
    - scraper_2025-08-05_15-15-00_UTC
    """
    # If it contains underscore or dash, it's likely a meaningful ID
    if '_' in doc_id or '-' in doc_id:
        return False
    
    # Check if it looks like a hash: 16-28 chars, alphanumeric only
    if re.match(r'^[a-zA-Z0-9]{16,28}$', doc_id):
        return True
    
    return False

def main():
    print("Connecting to Firebase...")
    fc = FirebaseClient()
    
    print("\nFetching all documents from youtube_collection_logs...")
    logs_ref = fc.db.collection('youtube_collection_logs')
    all_docs = list(logs_ref.stream())
    
    print(f"Total documents found: {len(all_docs)}")
    
    # Find hash documents
    hash_docs = []
    meaningful_docs = []
    
    for doc in all_docs:
        doc_id = doc.id
        if is_hash_id(doc_id):
            hash_docs.append(doc)
        else:
            meaningful_docs.append(doc)
    
    print(f"\nDocuments with hash IDs: {len(hash_docs)}")
    print(f"Documents with meaningful IDs: {len(meaningful_docs)}")
    
    if hash_docs:
        print("\nHash documents to delete:")
        for doc in hash_docs[:10]:  # Show first 10
            data = doc.to_dict()
            doc_type = data.get('type', data.get('run_type', 'unknown'))
            timestamp = data.get('timestamp', 'no timestamp')
            print(f"  - {doc.id} (type: {doc_type}, timestamp: {timestamp})")
        
        if len(hash_docs) > 10:
            print(f"  ... and {len(hash_docs) - 10} more")
        
        # Auto-confirm deletion
        print(f"\nProceeding to delete all {len(hash_docs)} hash documents...")
        
        if True:  # Auto-confirm
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
            
            print(f"\nSuccessfully deleted {deleted_count} documents")
        else:
            print("Deletion cancelled")
    else:
        print("\nNo hash documents found!")
    
    # Show sample of meaningful documents
    if meaningful_docs:
        print("\nSample of meaningful document IDs (keeping these):")
        for doc in meaningful_docs[:5]:
            data = doc.to_dict()
            doc_type = data.get('type', data.get('run_type', data.get('script_name', 'unknown')))
            print(f"  - {doc.id} (type: {doc_type})")

if __name__ == "__main__":
    main()