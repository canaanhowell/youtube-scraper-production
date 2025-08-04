#!/usr/bin/env python3
"""
Firebase Schema Migration Script - v2.0 Standardized Metrics

Migrates YouTube app Firebase structure to match updated firestore_mapping.md:
1. Convert daily_metrics subcollection → daily_metrics map field
2. Remove legacy fields from youtube_keywords
3. Add new standardized fields
4. Update category snapshot field names
5. Add missing fields like avg_acceleration

IMPORTANT: Run with --dry-run first to see what would be changed!
"""

import argparse
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.utils.firebase_client_enhanced import FirebaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class FirebaseSchemaV2Migrator:
    def __init__(self, dry_run: bool = True):
        self.fb_client = FirebaseClient()
        self.dry_run = dry_run
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be modified")
        else:
            logger.warning("⚠️  LIVE MODE - Data will be permanently modified!")
    
    def migrate_keywords_daily_metrics(self):
        """Convert daily_metrics subcollection to map field for all keywords."""
        logger.info("\n" + "="*60)
        logger.info("MIGRATING YOUTUBE_KEYWORDS DAILY_METRICS")
        logger.info("="*60)
        
        keywords_ref = self.fb_client.db.collection('youtube_keywords')
        keywords = list(keywords_ref.stream())
        
        logger.info(f"Found {len(keywords)} keywords to migrate")
        
        for keyword_doc in keywords:
            keyword_id = keyword_doc.id
            keyword_data = keyword_doc.to_dict()
            
            logger.info(f"\nProcessing keyword: {keyword_id}")
            
            # Get daily_metrics subcollection
            daily_metrics_ref = keywords_ref.document(keyword_id).collection('daily_metrics')
            daily_docs = list(daily_metrics_ref.order_by('date').stream())
            
            if not daily_docs:
                logger.info(f"  No daily metrics found for {keyword_id}")
                continue
            
            logger.info(f"  Found {len(daily_docs)} daily metrics documents")
            
            # Convert subcollection to map field
            daily_metrics_map = {}
            
            for daily_doc in daily_docs:
                daily_data = daily_doc.to_dict()
                date_key = daily_data.get('date', daily_doc.id)
                
                # Transform fields according to new schema
                new_daily_data = {
                    'date': date_key,
                    'video_count': daily_data.get('video_count', 0),
                    'new_videos_in_day': daily_data.get('videos_found_in_day', 0),
                    
                    # NEW: Standardized metrics v2.0 (placeholder values for now)
                    'velocity': daily_data.get('velocity', 0),  # Will be platform-normalized
                    'acceleration': daily_data.get('acceleration', 1.0),  # Will be keyword-relative  
                    'trend_score_v2': 50.0,  # Default neutral score
                    
                    # Context data (placeholders)
                    'platform_baseline_daily': 150.0,  # Default YouTube baseline
                    'keyword_baseline_7d': daily_data.get('velocity', 0),  # Use current velocity as baseline
                    
                    'total_views': daily_data.get('views_count', 0),
                    'avg_views_per_video': 0 if daily_data.get('video_count', 0) == 0 
                                         else daily_data.get('views_count', 0) / daily_data.get('video_count', 1),
                    'metrics_version': '2.0',
                    'timestamp': daily_data.get('timestamp', datetime.utcnow())
                }
                
                daily_metrics_map[date_key] = new_daily_data
            
            # Update keyword document
            updated_keyword_data = self._clean_keyword_fields(keyword_data)
            updated_keyword_data['daily_metrics'] = daily_metrics_map
            updated_keyword_data['current_velocity'] = self._calculate_current_velocity(daily_metrics_map)
            
            if self.dry_run:
                logger.info(f"  [DRY RUN] Would update {keyword_id} with {len(daily_metrics_map)} daily metrics")
                logger.info(f"  [DRY RUN] Would add current_velocity: {updated_keyword_data['current_velocity']}")
                logger.info(f"  [DRY RUN] Sample daily metric: {list(daily_metrics_map.values())[0] if daily_metrics_map else 'None'}")
            else:
                # Update the keyword document
                keywords_ref.document(keyword_id).set(updated_keyword_data)
                logger.info(f"  ✅ Updated {keyword_id} with daily_metrics map field")
                
                # Delete the old subcollection
                self._delete_subcollection(keywords_ref.document(keyword_id).collection('daily_metrics'))
                logger.info(f"  ✅ Deleted daily_metrics subcollection for {keyword_id}")
    
    def _clean_keyword_fields(self, keyword_data: Dict) -> Dict:
        """Remove legacy fields and keep only desired fields."""
        desired_fields = {
            'keyword', 'category', 'active', 'created_at', 'updated_at', 
            'last_collected', 'source', 'last_interval_update'
        }
        
        cleaned_data = {}
        for field in desired_fields:
            if field in keyword_data:
                cleaned_data[field] = keyword_data[field]
        
        # Ensure required fields have defaults
        if 'created_at' not in cleaned_data:
            cleaned_data['created_at'] = datetime.utcnow()
        if 'updated_at' not in cleaned_data:
            cleaned_data['updated_at'] = datetime.utcnow()
        if 'active' not in cleaned_data:
            cleaned_data['active'] = True
        if 'source' not in cleaned_data:
            cleaned_data['source'] = 'unknown'
            
        return cleaned_data
    
    def _calculate_current_velocity(self, daily_metrics_map: Dict) -> float:
        """Calculate current velocity from recent daily metrics."""
        if not daily_metrics_map:
            return 0.0
        
        # Get most recent metric
        sorted_dates = sorted(daily_metrics_map.keys(), reverse=True)
        if sorted_dates:
            recent_metric = daily_metrics_map[sorted_dates[0]]
            return recent_metric.get('velocity', 0.0)
        
        return 0.0
    
    def _delete_subcollection(self, subcollection_ref):
        """Helper to delete all documents in a subcollection."""
        docs = list(subcollection_ref.stream())
        
        batch_size = 500
        for i in range(0, len(docs), batch_size):
            batch = self.fb_client.db.batch()
            batch_docs = docs[i:i + batch_size]
            
            for doc in batch_docs:
                batch.delete(doc.reference)
            
            batch.commit()
    
    def migrate_category_snapshots(self):
        """Update category snapshot field names and add missing fields."""
        logger.info("\n" + "="*60)
        logger.info("MIGRATING YOUTUBE_CATEGORIES SNAPSHOTS")
        logger.info("="*60)
        
        categories_ref = self.fb_client.db.collection('youtube_categories')
        categories = list(categories_ref.stream())
        
        snapshot_collections = ['daily_snapshots_7d', 'daily_snapshots_30d', 'daily_snapshots_90d']
        
        for category_doc in categories:
            category_id = category_doc.id
            logger.info(f"\nProcessing category: {category_id}")
            
            for collection_name in snapshot_collections:
                logger.info(f"  Updating {collection_name}")
                
                snapshot_ref = categories_ref.document(category_id).collection(collection_name)
                snapshots = list(snapshot_ref.stream())
                
                updated_count = 0
                for snapshot_doc in snapshots:
                    snapshot_data = snapshot_doc.to_dict()
                    
                    # Transform field names
                    new_snapshot_data = {
                        'date': snapshot_data.get('date'),
                        'timestamp': snapshot_data.get('timestamp'),
                        'total_videos': snapshot_data.get('total_videos', 0),
                        'total_new_videos': snapshot_data.get('videos_added', 0),  # RENAME
                        'avg_velocity': snapshot_data.get('velocity', 0.0),  # RENAME
                        'avg_acceleration': 0.0,  # NEW FIELD - placeholder
                        'total_views': snapshot_data.get('total_views', 0),
                        'keywords': snapshot_data.get('keywords_data', {})  # RENAME
                    }
                    
                    # Transform keywords structure if needed
                    if 'keywords' in new_snapshot_data and isinstance(new_snapshot_data['keywords'], dict):
                        transformed_keywords = {}
                        for keyword, kw_data in new_snapshot_data['keywords'].items():
                            if isinstance(kw_data, dict):
                                transformed_keywords[keyword] = {
                                    'video_count': kw_data.get('videos', kw_data.get('video_count', 0)),
                                    'new_videos_in_day': kw_data.get('added_today', kw_data.get('new_videos_in_day', 0)),
                                    'velocity': kw_data.get('velocity', 0),
                                    'acceleration': kw_data.get('acceleration', 0),
                                    'total_views': kw_data.get('views', kw_data.get('total_views', 0))
                                }
                            else:
                                transformed_keywords[keyword] = kw_data
                        new_snapshot_data['keywords'] = transformed_keywords
                    
                    if self.dry_run:
                        if updated_count < 2:  # Show first 2 examples
                            logger.info(f"    [DRY RUN] Would update {snapshot_doc.id}")
                            logger.info(f"    [DRY RUN] Field changes: videos_added→total_new_videos, velocity→avg_velocity, keywords_data→keywords")
                    else:
                        snapshot_ref.document(snapshot_doc.id).set(new_snapshot_data)
                    
                    updated_count += 1
                
                if self.dry_run:
                    logger.info(f"    [DRY RUN] Would update {updated_count} documents in {collection_name}")
                else:
                    logger.info(f"    ✅ Updated {updated_count} documents in {collection_name}")
    
    def run_migration(self):
        """Run the complete migration process."""
        logger.info("🚀 Starting Firebase Schema v2.0 Migration")
        logger.info("="*60)
        
        # 1. Migrate keywords daily metrics
        self.migrate_keywords_daily_metrics()
        
        # 2. Migrate category snapshots  
        self.migrate_category_snapshots()
        
        logger.info("\n" + "="*60)
        if self.dry_run:
            logger.info("🔍 DRY RUN COMPLETE - No data was modified")
            logger.info("Review the changes above, then run with --live to execute")
        else:
            logger.info("✅ MIGRATION COMPLETE - Firebase schema updated to v2.0")
        logger.info("="*60)

def main():
    parser = argparse.ArgumentParser(description='Migrate Firebase schema to v2.0 standardized metrics')
    parser.add_argument('--live', action='store_true', 
                       help='Actually modify data (default is dry-run)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt (use with --live)')
    
    args = parser.parse_args()
    
    # Confirm if running in live mode
    if args.live and not args.confirm:
        try:
            response = input("⚠️  Are you sure you want to PERMANENTLY MODIFY Firebase data? Type 'MIGRATE' to confirm: ")
            if response != 'MIGRATE':
                print("Migration cancelled.")
                return
        except EOFError:
            print("\nNo input provided. Use --confirm flag to skip confirmation.")
            return
    
    migrator = FirebaseSchemaV2Migrator(dry_run=not args.live)
    migrator.run_migration()

if __name__ == '__main__':
    main()