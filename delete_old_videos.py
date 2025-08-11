#!/usr/bin/env python3
"""
Delete YouTube videos collected before a specific date
"""
import sys
import os
from datetime import datetime, timezone
from typing import Dict, List

# Add project to path
sys.path.insert(0, '/opt/youtube_app')

from src.utils.firebase_client_enhanced import FirebaseClient
from src.utils.logging_config_enhanced import setup_logging

# Set up logging
logger, _ = setup_logging()

def count_videos_before_date(firebase: FirebaseClient, cutoff_date: datetime) -> Dict[str, int]:
    """Count videos before the cutoff date for each keyword"""
    logger.info(f"Counting videos collected before {cutoff_date.isoformat()}")
    
    counts = {}
    total_count = 0
    
    # Get all keywords
    keywords_ref = firebase.db.collection('youtube_keywords').stream()
    
    for kw_doc in keywords_ref:
        keyword = kw_doc.id
        try:
            # Get videos for this keyword
            videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
            videos = videos_ref.where('collected_at', '<', cutoff_date).stream()
            
            count = 0
            for _ in videos:
                count += 1
            
            if count > 0:
                counts[keyword] = count
                total_count += count
                logger.info(f"  {keyword}: {count} videos")
        except Exception as e:
            logger.error(f"Error counting videos for {keyword}: {e}")
    
    return counts, total_count

def delete_videos_before_date(firebase: FirebaseClient, cutoff_date: datetime, dry_run: bool = True) -> int:
    """Delete videos collected before the cutoff date"""
    if dry_run:
        logger.info("DRY RUN - No videos will be deleted")
    else:
        logger.warning("ACTUAL DELETION - Videos will be permanently deleted")
    
    deleted_count = 0
    batch_size = 500  # Firestore batch limit
    
    # Get all keywords
    keywords_ref = firebase.db.collection('youtube_keywords').stream()
    
    for kw_doc in keywords_ref:
        keyword = kw_doc.id
        try:
            # Get videos for this keyword before cutoff date
            videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
            
            while True:
                # Get a batch of videos
                videos = videos_ref.where('collected_at', '<', cutoff_date).limit(batch_size).stream()
                batch = firebase.db.batch()
                batch_count = 0
                
                for doc in videos:
                    if not dry_run:
                        batch.delete(doc.reference)
                    batch_count += 1
                    deleted_count += 1
                
                if batch_count == 0:
                    break
                
                if not dry_run and batch_count > 0:
                    batch.commit()
                    logger.info(f"Deleted {batch_count} videos from {keyword}")
                elif dry_run:
                    logger.info(f"Would delete {batch_count} videos from {keyword}")
                
                if batch_count < batch_size:
                    break
                    
        except Exception as e:
            logger.error(f"Error deleting videos for {keyword}: {e}")
    
    return deleted_count

def main():
    """Main function"""
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Set cutoff date to August 9, 2025 00:00:00 UTC
    cutoff_date = datetime(2025, 8, 9, 0, 0, 0, tzinfo=timezone.utc)
    
    logger.info("=" * 80)
    logger.info(f"YouTube Video Deletion Tool")
    logger.info(f"Cutoff date: {cutoff_date.isoformat()}")
    logger.info(f"Will delete all videos collected BEFORE this date")
    logger.info("=" * 80)
    
    # First, count videos
    logger.info("\nPhase 1: Counting videos to be deleted...")
    counts, total_count = count_videos_before_date(firebase, cutoff_date)
    
    logger.info("\n" + "=" * 80)
    logger.info(f"SUMMARY: Found {total_count} videos to delete across {len(counts)} keywords")
    logger.info("=" * 80)
    
    if total_count == 0:
        logger.info("No videos found before the cutoff date. Nothing to delete.")
        return
    
    # Ask for confirmation
    logger.info("\nDo you want to proceed with deletion?")
    logger.info("Type 'DELETE' to confirm, or anything else to cancel:")
    
    if len(sys.argv) > 1 and sys.argv[1] == '--confirm':
        confirmation = 'DELETE'
        logger.info("Auto-confirmed via --confirm flag")
    else:
        confirmation = input().strip()
    
    if confirmation == 'DELETE':
        logger.info("\nPhase 2: Deleting videos...")
        deleted = delete_videos_before_date(firebase, cutoff_date, dry_run=False)
        logger.info(f"\n✅ Successfully deleted {deleted} videos")
    else:
        logger.info("\nDeletion cancelled. Running in dry-run mode...")
        deleted = delete_videos_before_date(firebase, cutoff_date, dry_run=True)
        logger.info(f"\n❌ Dry run complete. Would have deleted {deleted} videos")

if __name__ == "__main__":
    main()