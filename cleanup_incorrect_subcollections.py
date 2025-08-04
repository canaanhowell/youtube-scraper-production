#!/usr/bin/env python3
"""
Cleanup script to remove incorrect subcollections from youtube_categories.

This script removes:
1. daily_metrics subcollection (should be daily_snapshots_90d instead)
2. time_windows subcollection (deprecated aggregation method)

IMPORTANT: Run with --dry-run first to see what would be deleted!
"""

import argparse
import logging
from datetime import datetime
from src.utils.firebase_client_enhanced import FirebaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class YouTubeCategoriesCleanup:
    def __init__(self, dry_run: bool = True):
        self.fb_client = FirebaseClient()
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be deleted")
        else:
            logger.warning("⚠️  LIVE MODE - Data will be permanently deleted!")
    
    def get_categories_with_incorrect_subcollections(self):
        """Find all categories that have incorrect subcollections."""
        categories_ref = self.fb_client.db.collection('youtube_categories')
        
        problematic_categories = []
        
        for category_doc in categories_ref.stream():
            category_id = category_doc.id
            category_ref = categories_ref.document(category_id)
            
            # Get all subcollections
            subcollections = [coll.id for coll in category_ref.collections()]
            
            incorrect_subcollections = []
            if 'daily_metrics' in subcollections:
                incorrect_subcollections.append('daily_metrics')
            if 'time_windows' in subcollections:
                incorrect_subcollections.append('time_windows')
            
            if incorrect_subcollections:
                problematic_categories.append({
                    'category': category_id,
                    'incorrect_subcollections': incorrect_subcollections,
                    'all_subcollections': subcollections
                })
        
        return problematic_categories
    
    def delete_subcollection(self, category: str, subcollection_name: str):
        """Delete all documents in a subcollection."""
        subcollection_ref = (self.fb_client.db
                           .collection('youtube_categories')
                           .document(category)
                           .collection(subcollection_name))
        
        # Get all documents in the subcollection
        docs = list(subcollection_ref.stream())
        
        if not docs:
            logger.info(f"    No documents found in {subcollection_name}")
            return 0
        
        logger.info(f"    Found {len(docs)} documents in {subcollection_name}")
        
        if self.dry_run:
            logger.info(f"    [DRY RUN] Would delete {len(docs)} documents from {subcollection_name}")
            for doc in docs[:5]:  # Show first 5 documents
                logger.info(f"      - {doc.id}: {doc.to_dict().keys()}")
            if len(docs) > 5:
                logger.info(f"      ... and {len(docs) - 5} more documents")
        else:
            # Delete documents in batches
            batch_size = 500
            deleted_count = 0
            
            for i in range(0, len(docs), batch_size):
                batch = self.fb_client.db.batch()
                batch_docs = docs[i:i + batch_size]
                
                for doc in batch_docs:
                    batch.delete(doc.reference)
                
                batch.commit()
                deleted_count += len(batch_docs)
                logger.info(f"    Deleted batch: {deleted_count}/{len(docs)} documents")
            
            logger.info(f"    ✅ Deleted {deleted_count} documents from {subcollection_name}")
        
        return len(docs)
    
    def run_cleanup(self):
        """Run the cleanup process."""
        logger.info("=" * 60)
        logger.info("YouTube Categories Subcollection Cleanup")
        logger.info("=" * 60)
        
        # Find problematic categories
        problematic_categories = self.get_categories_with_incorrect_subcollections()
        
        if not problematic_categories:
            logger.info("✅ No incorrect subcollections found! All categories are clean.")
            return
        
        logger.info(f"Found {len(problematic_categories)} categories with incorrect subcollections:")
        
        total_docs_to_delete = 0
        
        for category_info in problematic_categories:
            category = category_info['category']
            incorrect_subs = category_info['incorrect_subcollections']
            all_subs = category_info['all_subcollections']
            
            logger.info(f"\n📁 Category: {category}")
            logger.info(f"  All subcollections: {all_subs}")
            logger.info(f"  ❌ Incorrect: {incorrect_subs}")
            
            for subcoll in incorrect_subs:
                docs_count = self.delete_subcollection(category, subcoll)
                total_docs_to_delete += docs_count
        
        logger.info("\n" + "=" * 60)
        if self.dry_run:
            logger.info(f"🔍 DRY RUN SUMMARY:")
            logger.info(f"  Categories with issues: {len(problematic_categories)}")  
            logger.info(f"  Total documents that would be deleted: {total_docs_to_delete}")
            logger.info(f"  To actually delete, run with --live flag")
        else:
            logger.info(f"✅ CLEANUP COMPLETE:")
            logger.info(f"  Categories cleaned: {len(problematic_categories)}")
            logger.info(f"  Total documents deleted: {total_docs_to_delete}")
        
        logger.info("=" * 60)

def main():
    parser = argparse.ArgumentParser(description='Clean up incorrect YouTube categories subcollections')
    parser.add_argument('--live', action='store_true', 
                       help='Actually delete data (default is dry-run)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt (use with --live)')
    
    args = parser.parse_args()
    
    # Confirm if running in live mode
    if args.live and not args.confirm:
        try:
            response = input("⚠️  Are you sure you want to PERMANENTLY DELETE data? Type 'DELETE' to confirm: ")
            if response != 'DELETE':
                print("Cleanup cancelled.")
                return
        except EOFError:
            print("\nNo input provided. Use --confirm flag to skip confirmation.")
            return
    
    cleanup = YouTubeCategoriesCleanup(dry_run=not args.live)
    cleanup.run_cleanup()

if __name__ == '__main__':
    main()