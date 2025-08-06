#!/usr/bin/env python3
"""
Clean up YouTube collection logs older than 7 days
Helps maintain database size and performance
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
    """Remove collection logs older than 7 days"""
    
    print("YouTube Collection Logs Cleanup")
    print("=" * 50)
    
    # Initialize Firebase client
    fc = FirebaseClient()
    
    # Calculate cutoff date (5 days ago)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=5)
    print(f"Cutoff date: {cutoff_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Removing logs created before this date...\n")
    
    # Get all collection logs
    logs_ref = fc.db.collection('youtube_collection_logs')
    all_docs = list(logs_ref.stream())
    
    print(f"Total documents found: {len(all_docs)}")
    
    # Categorize documents
    old_docs = []
    recent_docs = []
    no_timestamp_docs = []
    
    for doc in all_docs:
        doc_data = doc.to_dict()
        
        # Check for timestamp field
        timestamp = doc_data.get('timestamp')
        
        if not timestamp:
            no_timestamp_docs.append(doc)
            continue
        
        # Convert timestamp to datetime if needed
        try:
            if hasattr(timestamp, 'timestamp'):
                # Firestore timestamp object
                doc_datetime = timestamp
            elif isinstance(timestamp, str):
                # String timestamp
                doc_datetime = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                # Unknown format
                no_timestamp_docs.append(doc)
                continue
            
            # Check if older than 7 days
            if doc_datetime < cutoff_date:
                old_docs.append((doc, doc_datetime))
            else:
                recent_docs.append((doc, doc_datetime))
                
        except Exception as e:
            print(f"Error processing timestamp for {doc.id}: {e}")
            no_timestamp_docs.append(doc)
    
    # Display summary
    print(f"\nDocument Analysis:")
    print(f"  Recent (keeping): {len(recent_docs)}")
    print(f"  Old (removing): {len(old_docs)}")
    print(f"  No timestamp: {len(no_timestamp_docs)}")
    
    if old_docs:
        print(f"\nDocuments to delete ({len(old_docs)}):")
        
        # Sort by date for display
        old_docs.sort(key=lambda x: x[1])
        
        # Show sample of documents to delete
        for doc, doc_datetime in old_docs[:10]:
            doc_data = doc.to_dict()
            doc_type = doc_data.get('run_type', doc_data.get('type', 'collection'))
            print(f"  - {doc.id} ({doc_type}) - {doc_datetime.strftime('%Y-%m-%d %H:%M:%S')}")
        
        if len(old_docs) > 10:
            print(f"  ... and {len(old_docs) - 10} more")
        
        # Get confirmation
        print(f"\nThis will permanently delete {len(old_docs)} documents.")
        response = input("Proceed with deletion? (yes/no): ").strip().lower()
        
        if response == 'yes':
            print("\nDeleting old documents...")
            deleted_count = 0
            failed_count = 0
            
            for doc, _ in old_docs:
                try:
                    doc.reference.delete()
                    deleted_count += 1
                    
                    # Progress indicator
                    if deleted_count % 50 == 0:
                        print(f"  Deleted {deleted_count}/{len(old_docs)}...")
                        
                except Exception as e:
                    print(f"  Error deleting {doc.id}: {e}")
                    failed_count += 1
            
            print(f"\n✅ Cleanup complete!")
            print(f"  Successfully deleted: {deleted_count}")
            if failed_count > 0:
                print(f"  Failed to delete: {failed_count}")
        else:
            print("\nDeletion cancelled.")
    else:
        print("\n✅ No old documents to delete!")
    
    # Show recent logs summary
    if recent_docs:
        print(f"\nRecent logs summary (last 5 days):")
        
        # Group by type
        log_types = {}
        for doc, _ in recent_docs:
            doc_data = doc.to_dict()
            log_type = doc_data.get('run_type', doc_data.get('type', 'collection'))
            log_types[log_type] = log_types.get(log_type, 0) + 1
        
        for log_type, count in sorted(log_types.items()):
            print(f"  {log_type}: {count}")
    
    # Handle documents without timestamps
    if no_timestamp_docs:
        print(f"\n⚠️  Found {len(no_timestamp_docs)} documents without valid timestamps")
        print("These documents were skipped. Sample IDs:")
        for doc in no_timestamp_docs[:5]:
            print(f"  - {doc.id}")

if __name__ == "__main__":
    main()