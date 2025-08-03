#!/usr/bin/env python3
"""
Unified YouTube Daily Metrics Calculator
Updates both youtube_keywords daily_metrics and youtube_categories daily snapshots.
Designed to run once daily to process yesterday's data.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
import pytz
from typing import Dict, Any, Optional

# Add project path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

# Import Firebase client
from src.utils.firebase_client import FirebaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeDailyMetricsUnified:
    def __init__(self, dry_run=False):
        fc = FirebaseClient(); self.db = fc.db
        self.cst = pytz.timezone('America/Chicago')
        # Store category updates to batch at the end
        self.category_updates = {}
        self.dry_run = dry_run
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be written to database")
    
    def calculate_daily_metrics(self, date: datetime = None):
        """Calculate daily metrics for all keywords and update categories for a specific date"""
        
        if date is None:
            # Default to yesterday
            date = datetime.now(timezone.utc).date() - timedelta(days=1)
        elif isinstance(date, datetime):
            date = date.date()
        elif isinstance(date, str):
            try:
                date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                logger.warning(f"Invalid date string '{date}', using yesterday")
                date = datetime.now(timezone.utc).date() - timedelta(days=1)
        
        logger.info(f"{'='*60}")
        logger.info(f"Calculating YouTube daily metrics for: {date}")
        logger.info(f"{'='*60}")
        
        # Get all active keywords
        keywords_ref = self.db.collection('youtube_keywords').where('active', '==', True)
        keywords = list(keywords_ref.stream())
        
        results = {
            'date': str(date),
            'keywords_processed': 0,
            'keyword_metrics_created': 0,
            'category_snapshots_created': 0,
            'errors': 0
        }
        
        # Reset category updates for this run
        self.category_updates = {}
        
        # Process each keyword
        for keyword_doc in keywords:
            keyword_data = keyword_doc.to_dict()
            keyword = keyword_data.get('keyword', keyword_data.get('name'))
            keyword_id = keyword_doc.id
            category = keyword_data.get('category')
            
            if not keyword:
                logger.warning(f"Skipping keyword doc {keyword_id} - no keyword field")
                continue
            
            try:
                logger.info(f"\nProcessing keyword: {keyword} (category: {category})")
                daily_metric = self._calculate_keyword_daily_metrics(keyword_id, keyword, date)
                
                # Store for category aggregation
                if daily_metric and category:
                    if category not in self.category_updates:
                        self.category_updates[category] = {}
                    self.category_updates[category][keyword] = daily_metric
                
                results['keywords_processed'] += 1
                if daily_metric:
                    results['keyword_metrics_created'] += 1
            except Exception as e:
                logger.error(f"Error processing {keyword}: {e}")
                results['errors'] += 1
        
        # Update category daily snapshots
        snapshots_created = self._update_category_daily_snapshots(date)
        results['category_snapshots_created'] = snapshots_created
        
        # Clean up old snapshots
        self._cleanup_old_snapshots()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Daily metrics calculation complete:")
        logger.info(f"  Date: {date}")
        logger.info(f"  Keywords processed: {results['keywords_processed']}")
        logger.info(f"  Keyword metrics created: {results['keyword_metrics_created']}")
        logger.info(f"  Category snapshots created: {results['category_snapshots_created']}")
        logger.info(f"  Errors: {results['errors']}")
        logger.info(f"{'='*60}")
        
        return results
    
    def _calculate_keyword_daily_metrics(self, keyword_id: str, keyword: str, date) -> Optional[Dict[str, Any]]:
        """Calculate daily metrics for a specific keyword and date"""
        
        # Get interval metrics for the target date
        start_of_day = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Get all interval metrics for this day
        interval_metrics_ref = (self.db.collection('youtube_keywords')
                               .document(keyword_id)
                               .collection('interval_metrics')
                               .where('timestamp', '>=', start_of_day)
                               .where('timestamp', '<=', end_of_day)
                               .order_by('timestamp'))
        
        interval_metrics = list(interval_metrics_ref.stream())
        
        if not interval_metrics:
            logger.warning(f"  No interval metrics found for {keyword} on {date}")
            return None
        
        # Get the last metric of the day for end-of-day counts
        last_metric = interval_metrics[-1].to_dict()
        video_count = last_metric.get('video_count', 0)
        views_count = last_metric.get('views_count', 0)
        
        # Calculate videos found during the day
        videos_found_in_day = sum(m.to_dict().get('videos_found_in_search', 0) for m in interval_metrics)
        
        # Prepare daily metric document
        daily_metric = {
            'timestamp': end_of_day,
            'timestamp_cst': end_of_day.astimezone(self.cst).strftime('%Y-%m-%d %H:%M:%S %Z'),
            'date': str(date),
            'video_count': video_count,
            'views_count': views_count,
            'videos_found_in_day': videos_found_in_day,
            'interval_days': 1,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc)
        }
        
        # Get previous daily metrics for velocity and acceleration calculation
        daily_metrics_ref = (self.db.collection('youtube_keywords')
                            .document(keyword_id)
                            .collection('daily_metrics')
                            .where('date', '<', str(date))
                            .order_by('date', direction='DESCENDING')
                            .limit(2))
        
        previous_metrics = list(daily_metrics_ref.stream())
        
        # Calculate velocity (requires 1 previous day)
        if previous_metrics:
            # Get the most recent previous day
            prev_metric = previous_metrics[0].to_dict()
            prev_date = datetime.strptime(prev_metric['date'], '%Y-%m-%d').date()
            
            # Only use if it's actually the previous day
            if prev_date == date - timedelta(days=1):
                prev_video_count = prev_metric.get('video_count', 0)
                daily_metric['previous_video_count'] = prev_video_count
                daily_metric['velocity'] = video_count - prev_video_count  # videos/day
                
                # Calculate acceleration (requires 2 previous days)
                if len(previous_metrics) >= 2:
                    prev_prev_metric = previous_metrics[1].to_dict()
                    prev_prev_date = datetime.strptime(prev_prev_metric['date'], '%Y-%m-%d').date()
                    
                    # Check if we have consecutive days
                    if prev_prev_date == date - timedelta(days=2):
                        prev_velocity = prev_metric.get('velocity', 0)
                        current_velocity = daily_metric['velocity']
                        daily_metric['acceleration'] = current_velocity - prev_velocity  # videos/day²
                    else:
                        daily_metric['acceleration'] = 0
                        logger.info(f"  Gap in daily metrics, setting acceleration to 0")
                else:
                    daily_metric['acceleration'] = 0
            else:
                # Gap in daily metrics
                logger.warning(f"  Gap in daily metrics for {keyword}, cannot calculate velocity")
                daily_metric['velocity'] = 0
                daily_metric['acceleration'] = 0
                daily_metric['previous_video_count'] = 0
        else:
            # No previous keyword daily metrics found - check category snapshots as fallback
            prev_date = date - timedelta(days=1)
            prev_date_str = str(prev_date)
            
            # Get the keyword's category from the keyword document
            keyword_doc = self.db.collection('youtube_keywords').document(keyword_id).get()
            keyword_category = None
            if keyword_doc.exists:
                keyword_category = keyword_doc.to_dict().get('category')
            
            if keyword_category:
                # Try to find previous day data in category snapshots
                category_ref = self.db.collection('youtube_categories').document(keyword_category)
                
                # Check daily_snapshots_7d first (most likely to exist)
                snapshot_ref = category_ref.collection('daily_snapshots_7d').document(prev_date_str)
                snapshot = snapshot_ref.get()
                
                if snapshot.exists:
                    snapshot_data = snapshot.to_dict()
                    keywords_data = snapshot_data.get('keywords_data', {})
                    
                    # Check both the keyword and keyword_id since snapshots might use either
                    keyword_in_snapshot = None
                    if keyword in keywords_data:
                        keyword_in_snapshot = keyword
                    elif keyword_id in keywords_data:
                        keyword_in_snapshot = keyword_id
                    # Also check with underscores replaced by spaces
                    elif keyword_id.replace('_', ' ') in keywords_data:
                        keyword_in_snapshot = keyword_id.replace('_', ' ')
                    
                    if keyword_in_snapshot:
                        # Found previous day data in category snapshot
                        keyword_data = keywords_data[keyword_in_snapshot]
                        # Check different possible field names for video count
                        prev_video_count = keyword_data.get('post_count') or keyword_data.get('videos') or keyword_data.get('video_count', 0)
                        
                        if prev_video_count is not None:
                            logger.info(f"  Using category snapshot fallback for {keyword} velocity calculation")
                            logger.info(f"  Previous day ({prev_date_str}) video count from snapshot: {prev_video_count}")
                            
                            daily_metric['previous_video_count'] = prev_video_count
                            daily_metric['velocity'] = video_count - prev_video_count
                            daily_metric['acceleration'] = 0  # Can't calculate without 2 days of data
                        else:
                            # No video count in snapshot
                            daily_metric['velocity'] = 0
                            daily_metric['acceleration'] = 0
                            daily_metric['previous_video_count'] = 0
                    else:
                        # Keyword not in snapshot
                        logger.info(f"  No previous day data for {keyword} in category snapshot")
                        daily_metric['velocity'] = 0
                        daily_metric['acceleration'] = 0
                        daily_metric['previous_video_count'] = 0
                else:
                    # No category snapshot for previous day
                    daily_metric['velocity'] = 0
                    daily_metric['acceleration'] = 0
                    daily_metric['previous_video_count'] = 0
            else:
                # Couldn't determine category
                daily_metric['velocity'] = 0
                daily_metric['acceleration'] = 0
                daily_metric['previous_video_count'] = 0
        
        # Save daily metric with date as document ID
        doc_id = str(date)  # e.g., "2025-08-01"
        
        if not self.dry_run:
            daily_metrics_collection = (self.db.collection('youtube_keywords')
                                       .document(keyword_id)
                                       .collection('daily_metrics'))
            
            daily_metrics_collection.document(doc_id).set(daily_metric)
            logger.info(f"  Daily metric created for {keyword} on {date}:")
        else:
            logger.info(f"  [DRY RUN] Would create daily metric for {keyword} on {date}:")
        
        logger.info(f"    Video count: {video_count}")
        logger.info(f"    Views count: {views_count:,}")
        logger.info(f"    Videos found: {videos_found_in_day}")
        logger.info(f"    Velocity: {daily_metric.get('velocity', 0)} videos/day")
        logger.info(f"    Acceleration: {daily_metric.get('acceleration', 0)} videos/day²")
        
        return daily_metric
    
    def _update_category_daily_snapshots(self, date) -> int:
        """Update daily snapshots for all categories based on keyword metrics"""
        logger.info(f"\nUpdating category daily snapshots for {date}")
        
        # Define time windows and their day ranges
        time_windows = {
            'daily_snapshots_90d': 90,
            'daily_snapshots_30d': 30,
            'daily_snapshots_7d': 7
        }
        
        today = datetime.now(timezone.utc).date()
        days_ago = (today - date).days
        
        # Batch for efficient writes
        batch = self.db.batch()
        batch_count = 0
        snapshots_created = 0
        
        for category, keyword_metrics in self.category_updates.items():
            if not keyword_metrics:
                continue
                
            logger.info(f"\n  Updating category: {category}")
            
            # Calculate aggregated metrics for the category
            total_videos = sum(m.get('video_count', 0) for m in keyword_metrics.values())
            total_views = sum(m.get('views_count', 0) for m in keyword_metrics.values())
            total_videos_found = sum(m.get('videos_found_in_day', 0) for m in keyword_metrics.values())
            
            # Calculate aggregated velocity (sum of all keyword velocities)
            total_velocity = sum(m.get('velocity', 0) for m in keyword_metrics.values())
            
            # Prepare keyword-specific data matching reddit_categories format
            keywords_data = {}
            for keyword, metric in keyword_metrics.items():
                # Use the same format as reddit categories
                keywords_data[keyword] = {
                    'post_count': metric.get('video_count', 0),  # Total videos
                    'total_upvotes': metric.get('views_count', 0),  # Total views
                    'velocity': metric.get('velocity', 0),
                    'avg_upvotes': metric.get('views_count', 0) // metric.get('video_count', 1) if metric.get('video_count', 0) > 0 else 0,
                    'trend_score': metric.get('velocity', 0) * 100  # Simple trend score based on velocity
                }
            
            # Base document data for snapshots
            snapshot_data = {
                'date': str(date),
                'timestamp': datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'total_videos': total_videos,
                'total_views': total_views,
                'videos_added': total_videos_found,
                'velocity': total_velocity,
                'category': category,
                'keywords_data': keywords_data,
                'updated_at': datetime.now(timezone.utc)
            }
            
            # Update appropriate time window subcollections
            category_ref = self.db.collection('youtube_categories').document(category)
            
            for subcollection_name, window_days in time_windows.items():
                # Check if date falls within this window
                if days_ago < window_days:
                    subcollection_ref = category_ref.collection(subcollection_name)
                    doc_ref = subcollection_ref.document(str(date))
                    
                    if not self.dry_run:
                        batch.set(doc_ref, snapshot_data, merge=True)
                        batch_count += 1
                        snapshots_created += 1
                        
                        # Commit batch if needed
                        if batch_count >= 100:
                            batch.commit()
                            batch = self.db.batch()
                            batch_count = 0
                    else:
                        logger.info(f"    [DRY RUN] Would update {subcollection_name}/{str(date)}")
            
            logger.info(f"    Keywords: {', '.join(keywords_data.keys())}")
            logger.info(f"    Total videos: {total_videos}")
            logger.info(f"    Total views: {total_views:,}")
            logger.info(f"    Videos added: {total_videos_found}")
            logger.info(f"    Total velocity: {total_velocity}")
        
        # Commit remaining batch
        if batch_count > 0 and not self.dry_run:
            batch.commit()
            logger.info(f"\n  Category daily snapshots updated successfully")
        elif self.dry_run:
            logger.info(f"\n  [DRY RUN] Would create {snapshots_created} snapshots")
        
        return snapshots_created
    
    def _cleanup_old_snapshots(self):
        """Remove snapshots older than their time window"""
        if self.dry_run:
            logger.info("\n[DRY RUN] Skipping cleanup of old snapshots")
            return
            
        logger.info("\nCleaning up old snapshots...")
        
        # Define time windows
        time_windows = {
            'daily_snapshots_90d': 90,
            'daily_snapshots_30d': 30,
            'daily_snapshots_7d': 7
        }
        
        today = datetime.now(timezone.utc).date()
        
        # Get all categories
        categories_ref = self.db.collection('youtube_categories')
        categories = list(categories_ref.stream())
        
        total_deleted = 0
        
        for cat_doc in categories:
            category = cat_doc.id
            
            for subcollection_name, window_days in time_windows.items():
                # Calculate cutoff date
                cutoff_date = today - timedelta(days=window_days)
                
                # Get old snapshots
                old_snapshots_ref = (self.db.collection('youtube_categories')
                                    .document(category)
                                    .collection(subcollection_name)
                                    .where('date', '<', str(cutoff_date))
                                    .limit(50))  # Process in batches
                
                old_snapshots = list(old_snapshots_ref.stream())
                
                if old_snapshots:
                    batch = self.db.batch()
                    for doc in old_snapshots:
                        batch.delete(doc.reference)
                        total_deleted += 1
                    batch.commit()
        
        if total_deleted > 0:
            logger.info(f"  Deleted {total_deleted} old snapshots")
    
    def calculate_date_range(self, start_date, end_date):
        """Calculate daily metrics for a range of dates"""
        current_date = start_date
        
        while current_date <= end_date:
            self.calculate_daily_metrics(current_date)
            current_date += timedelta(days=1)
    
    def update_historical_peaks(self):
        """Update historical peak values for all keywords"""
        logger.info("\nUpdating historical peaks for all keywords")
        
        keywords_ref = self.db.collection('youtube_keywords').where('active', '==', True)
        keywords = list(keywords_ref.stream())
        
        for keyword_doc in keywords:
            keyword_data = keyword_doc.to_dict()
            keyword = keyword_data.get('keyword', keyword_data.get('name'))
            keyword_id = keyword_doc.id
            
            if not keyword:
                continue
                
            try:
                # Get all daily metrics
                daily_metrics_ref = (self.db.collection('youtube_keywords')
                                    .document(keyword_id)
                                    .collection('daily_metrics'))
                
                max_video_count = 0
                max_velocity = 0
                max_videos_in_day = 0
                max_views_count = 0
                
                for metric_doc in daily_metrics_ref.stream():
                    metric = metric_doc.to_dict()
                    max_video_count = max(max_video_count, metric.get('video_count', 0))
                    max_views_count = max(max_views_count, metric.get('views_count', 0))
                    max_velocity = max(max_velocity, abs(metric.get('velocity', 0)))
                    max_videos_in_day = max(max_videos_in_day, metric.get('videos_found_in_day', 0))
                
                # Update keyword document
                peaks = {
                    'max_video_count': max_video_count,
                    'max_views_count': max_views_count,
                    'max_velocity': max_velocity,
                    'max_videos_in_day': max_videos_in_day,
                    'peaks_updated': datetime.now(timezone.utc)
                }
                
                if not self.dry_run:
                    self.db.collection('youtube_keywords').document(keyword_id).update({
                        'historical_peaks': peaks
                    })
                    logger.info(f"  Updated peaks for {keyword}: videos={max_video_count}, velocity={max_velocity}")
                else:
                    logger.info(f"  [DRY RUN] Would update peaks for {keyword}")
                
            except Exception as e:
                logger.error(f"Error updating peaks for {keyword}: {e}")


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate YouTube daily metrics and category snapshots')
    parser.add_argument('--date', type=str, 
                        help='Date to calculate metrics for (YYYY-MM-DD). Default: yesterday')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                        help='Calculate metrics for date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--peaks', action='store_true',
                        help='Update historical peak values')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without writing to database (preview mode)')
    
    args = parser.parse_args()
    
    calculator = YouTubeDailyMetricsUnified(dry_run=args.dry_run)
    
    if args.peaks:
        calculator.update_historical_peaks()
    elif args.range:
        start_date = datetime.strptime(args.range[0], '%Y-%m-%d').date()
        end_date = datetime.strptime(args.range[1], '%Y-%m-%d').date()
        calculator.calculate_date_range(start_date, end_date)
    elif args.date:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        calculator.calculate_daily_metrics(target_date)
    else:
        # Default to yesterday
        calculator.calculate_daily_metrics()
    
    # Save run log
    if not args.dry_run:
        log_data = {
            'type': 'youtube_daily_metrics',
            'timestamp': datetime.now(timezone.utc),
            'date_processed': args.date or str(datetime.now(timezone.utc).date() - timedelta(days=1)),
            'dry_run': args.dry_run
        }
        calculator.db.collection('youtube_collection_logs').add(log_data)


if __name__ == "__main__":
    main()