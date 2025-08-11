#!/usr/bin/env python3
"""
Delete ALL YouTube videos collected before a specific date
More comprehensive version that checks all keywords
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

def delete_all_videos_before_date(firebase: FirebaseClient, cutoff_date: datetime) -> Dict[str, int]:
    """Delete all videos collected before the cutoff date"""
    logger.info(f"Deleting all videos collected before {cutoff_date.isoformat()}")
    
    total_deleted = 0
    keyword_counts = {}
    
    # Get all keywords (active and inactive)
    keywords_ref = firebase.db.collection('youtube_keywords').stream()
    all_keywords = [doc.id for doc in keywords_ref]
    logger.info(f"Found {len(all_keywords)} total keywords to check")
    
    for keyword in all_keywords:
        try:
            deleted_count = 0
            videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
            
            # Delete in batches
            while True:
                batch = firebase.db.batch()
                batch_count = 0
                
                # Get videos before cutoff date
                videos_to_delete = videos_ref.where('collected_at', '<', cutoff_date).limit(500).stream()
                
                for doc in videos_to_delete:
                    batch.delete(doc.reference)
                    batch_count += 1
                
                if batch_count == 0:
                    break
                
                # Commit the batch
                batch.commit()
                deleted_count += batch_count
                logger.info(f"  Deleted {batch_count} videos from {keyword} (total: {deleted_count})")
                
                if batch_count < 500:
                    break
            
            if deleted_count > 0:
                keyword_counts[keyword] = deleted_count
                total_deleted += deleted_count
                
        except Exception as e:
            logger.error(f"Error processing {keyword}: {e}")
    
    # Also check for videos without proper collected_at field
    logger.info("\nChecking for videos without proper timestamps...")
    for keyword in all_keywords:
        try:
            videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
            all_videos = videos_ref.stream()
            
            batch = firebase.db.batch()
            batch_count = 0
            old_format_count = 0
            
            for doc in all_videos:
                data = doc.to_dict()
                collected_at = data.get('collected_at')
                
                # Check if it's an old video (by checking document ID format or missing collected_at)
                should_delete = False
                
                if not collected_at:
                    should_delete = True
                elif isinstance(collected_at, str):
                    try:
                        # Parse the timestamp
                        if 'T' in collected_at:
                            dt = datetime.fromisoformat(collected_at.replace('Z', '+00:00'))
                            if dt < cutoff_date:
                                should_delete = True
                    except:
                        # If we can't parse it, it's probably old
                        should_delete = True
                
                # Also check document ID - if it's not ISO format, it's old
                if not should_delete and not (doc.id.startswith('202') and 'T' in doc.id):
                    should_delete = True
                
                if should_delete:
                    batch.delete(doc.reference)
                    batch_count += 1
                    old_format_count += 1
                    
                    if batch_count >= 500:
                        batch.commit()
                        logger.info(f"  Deleted {batch_count} old format videos from {keyword}")
                        batch = firebase.db.batch()
                        batch_count = 0
            
            if batch_count > 0:
                batch.commit()
                logger.info(f"  Deleted {batch_count} old format videos from {keyword}")
                
            if old_format_count > 0:
                keyword_counts[keyword] = keyword_counts.get(keyword, 0) + old_format_count
                total_deleted += old_format_count
                
        except Exception as e:
            logger.error(f"Error checking old format videos in {keyword}: {e}")
    
    return keyword_counts, total_deleted

def main():
    """Main function"""
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Set cutoff date to August 9, 2025 00:00:00 UTC
    cutoff_date = datetime(2025, 8, 9, 0, 0, 0, tzinfo=timezone.utc)
    
    logger.info("=" * 80)
    logger.info(f"YouTube Video Deletion Tool - COMPREHENSIVE")
    logger.info(f"Cutoff date: {cutoff_date.isoformat()}")
    logger.info(f"Will delete ALL videos collected BEFORE this date")
    logger.info(f"This includes videos with old document ID formats")
    logger.info("=" * 80)
    
    # Direct deletion
    logger.info("\nStarting deletion process...")
    keyword_counts, total_deleted = delete_all_videos_before_date(firebase, cutoff_date)
    
    logger.info("\n" + "=" * 80)
    logger.info(f"DELETION COMPLETE")
    logger.info(f"Total videos deleted: {total_deleted}")
    logger.info(f"Keywords affected: {len(keyword_counts)}")
    logger.info("=" * 80)
    
    if keyword_counts:
        logger.info("\nDeletion summary by keyword:")
        for keyword, count in sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True):
            logger.info(f"  {keyword}: {count} videos deleted")

if __name__ == "__main__":
    main()