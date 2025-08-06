#!/usr/bin/env python3
"""
Automated cleanup of YouTube collection logs older than 5 days
Designed to run via cron without user interaction
"""

import sys
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

# Set up logging
log_file = '/opt/youtube_app/logs/cleanup_logs.log'
# Create log directory if running locally
if not Path(log_file).parent.exists():
    log_file = 'cleanup_logs.log'

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def cleanup_old_logs(days_to_keep=5, dry_run=False):
    """
    Remove collection logs older than specified days
    
    Args:
        days_to_keep: Number of days to keep logs (default: 7)
        dry_run: If True, only report what would be deleted without actually deleting
    
    Returns:
        Dict with cleanup statistics
    """
    
    logger.info(f"Starting cleanup of logs older than {days_to_keep} days (dry_run={dry_run})")
    
    # Initialize Firebase client
    fc = FirebaseClient()
    
    # Calculate cutoff date
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
    logger.info(f"Cutoff date: {cutoff_date.isoformat()}")
    
    # Get all collection logs
    logs_ref = fc.db.collection('youtube_collection_logs')
    all_docs = list(logs_ref.stream())
    
    logger.info(f"Total documents found: {len(all_docs)}")
    
    # Track statistics
    stats = {
        'total_docs': len(all_docs),
        'old_docs': 0,
        'recent_docs': 0,
        'no_timestamp_docs': 0,
        'deleted': 0,
        'delete_errors': 0,
        'oldest_removed': None,
        'newest_removed': None,
        'space_freed_estimate_mb': 0
    }
    
    # Process documents
    docs_to_delete = []
    
    for doc in all_docs:
        doc_data = doc.to_dict()
        timestamp = doc_data.get('timestamp')
        
        if not timestamp:
            stats['no_timestamp_docs'] += 1
            logger.warning(f"Document {doc.id} has no timestamp")
            continue
        
        try:
            # Convert timestamp to datetime
            if hasattr(timestamp, 'timestamp'):
                doc_datetime = timestamp
            elif isinstance(timestamp, str):
                doc_datetime = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            else:
                stats['no_timestamp_docs'] += 1
                continue
            
            # Check age
            if doc_datetime < cutoff_date:
                stats['old_docs'] += 1
                docs_to_delete.append((doc, doc_datetime))
                
                # Track oldest and newest to be removed
                if not stats['oldest_removed'] or doc_datetime < stats['oldest_removed']:
                    stats['oldest_removed'] = doc_datetime
                if not stats['newest_removed'] or doc_datetime > stats['newest_removed']:
                    stats['newest_removed'] = doc_datetime
                    
                # Estimate document size (rough estimate)
                doc_size_kb = len(str(doc_data)) / 1024
                stats['space_freed_estimate_mb'] += doc_size_kb / 1024
            else:
                stats['recent_docs'] += 1
                
        except Exception as e:
            logger.error(f"Error processing document {doc.id}: {e}")
            stats['no_timestamp_docs'] += 1
    
    # Delete old documents
    if docs_to_delete:
        logger.info(f"Found {len(docs_to_delete)} documents to delete")
        
        if not dry_run:
            logger.info("Starting deletion...")
            
            for doc, doc_datetime in docs_to_delete:
                try:
                    doc.reference.delete()
                    stats['deleted'] += 1
                    
                    if stats['deleted'] % 100 == 0:
                        logger.info(f"Deleted {stats['deleted']}/{len(docs_to_delete)} documents...")
                        
                except Exception as e:
                    logger.error(f"Failed to delete {doc.id}: {e}")
                    stats['delete_errors'] += 1
            
            logger.info(f"Deletion complete. Deleted {stats['deleted']} documents")
        else:
            logger.info("DRY RUN - No documents were deleted")
            stats['deleted'] = len(docs_to_delete)  # What would be deleted
    else:
        logger.info("No old documents found to delete")
    
    # Log summary
    logger.info("Cleanup Summary:")
    logger.info(f"  Total documents: {stats['total_docs']}")
    logger.info(f"  Recent (kept): {stats['recent_docs']}")
    logger.info(f"  Old (deleted): {stats['deleted']}")
    logger.info(f"  Delete errors: {stats['delete_errors']}")
    logger.info(f"  No timestamp: {stats['no_timestamp_docs']}")
    
    if stats['oldest_removed']:
        logger.info(f"  Oldest removed: {stats['oldest_removed'].strftime('%Y-%m-%d')}")
        logger.info(f"  Newest removed: {stats['newest_removed'].strftime('%Y-%m-%d')}")
        logger.info(f"  Est. space freed: {stats['space_freed_estimate_mb']:.2f} MB")
    
    return stats

def main():
    """Main function for automated cleanup"""
    
    # Run cleanup (not a dry run)
    stats = cleanup_old_logs(days_to_keep=5, dry_run=False)
    
    # Log to Firebase for monitoring
    try:
        fc = FirebaseClient()
        cleanup_log = {
            'type': 'maintenance_cleanup',
            'timestamp': datetime.now(timezone.utc),
            'stats': stats,
            'days_kept': 5
        }
        
        # Store in a maintenance collection
        doc_id = f"cleanup_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
        fc.db.collection('youtube_maintenance_logs').document(doc_id).set(cleanup_log)
        
    except Exception as e:
        logger.error(f"Failed to log cleanup stats to Firebase: {e}")

if __name__ == "__main__":
    main()