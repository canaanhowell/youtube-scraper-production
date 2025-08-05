#!/usr/bin/env python3
"""
Unified YouTube Daily Metrics Calculator V2 - Hardened Version
Enhanced with robust error handling, validation, and recovery mechanisms.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
import pytz
from typing import Dict, Any, Optional, List, Tuple
import time
from contextlib import contextmanager
import traceback

# Add project path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))

# Import Firebase client
from src.utils.firebase_client_enhanced import FirebaseClient
from google.cloud.firestore_v1.batch import WriteBatch
from google.api_core import exceptions as firebase_exceptions

# Set up logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
MAX_BATCH_SIZE = 500  # Firebase limit
MAX_RETRIES = 3
RETRY_DELAY = 1.0  # seconds
MAX_VIDEO_COUNT = 10**12  # Sanity check for extreme values
MAX_VIEWS_COUNT = 10**15  # Sanity check for extreme values


class YouTubeDailyMetricsUnified:
    def __init__(self, dry_run=False):
        self.firebase_client = FirebaseClient()
        self.db = self.firebase_client.db
        self.cst = pytz.timezone('America/Chicago')
        self.category_updates = {}
        self.dry_run = dry_run
        self._errors = []
        self._warnings = []
        
        if self.dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be written to database")
    
    @contextmanager
    def error_context(self, operation: str):
        """Context manager for consistent error handling"""
        try:
            yield
        except Exception as e:
            error_msg = f"Error in {operation}: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            self._errors.append(error_msg)
            raise
    
    def _validate_date(self, date: Any) -> datetime.date:
        """Validate and normalize date input"""
        if date is None:
            return datetime.now(timezone.utc).date() - timedelta(days=1)
        
        if isinstance(date, datetime):
            return date.date()
        
        if hasattr(date, 'year') and hasattr(date, 'month') and hasattr(date, 'day') and not isinstance(date, datetime):
            return date
        
        if isinstance(date, str):
            try:
                # Try multiple date formats
                for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        return datetime.strptime(date, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"Could not parse date string: {date}")
            except Exception as e:
                logger.warning(f"Invalid date string '{date}', using yesterday. Error: {e}")
                return datetime.now(timezone.utc).date() - timedelta(days=1)
        
        logger.warning(f"Invalid date type {type(date)}, using yesterday")
        return datetime.now(timezone.utc).date() - timedelta(days=1)
    
    def _validate_numeric_value(self, value: Any, field_name: str, max_value: int = None) -> int:
        """Validate and sanitize numeric values"""
        if value is None:
            return 0
        
        try:
            num_value = int(value)
            
            # Check for negative values
            if num_value < 0:
                logger.warning(f"Negative value {num_value} for {field_name}, using 0")
                return 0
            
            # Check for extreme values
            if max_value and num_value > max_value:
                logger.warning(f"Extreme value {num_value} for {field_name}, capping at {max_value}")
                return max_value
            
            return num_value
        except (TypeError, ValueError):
            logger.warning(f"Invalid numeric value '{value}' for {field_name}, using 0")
            return 0
    
    def _retry_operation(self, operation, *args, **kwargs):
        """Retry an operation with exponential backoff"""
        last_error = None
        for attempt in range(MAX_RETRIES):
            try:
                return operation(*args, **kwargs)
            except firebase_exceptions.ServiceUnavailable as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY * (2 ** attempt)
                    logger.warning(f"Service unavailable, retrying in {delay}s... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(delay)
                else:
                    raise
            except firebase_exceptions.DeadlineExceeded as e:
                last_error = e
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Deadline exceeded, retrying... (attempt {attempt + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                else:
                    raise
            except Exception as e:
                # Don't retry other exceptions
                raise
        
        raise last_error
    
    def calculate_daily_metrics(self, date: Any = None) -> Dict[str, Any]:
        """Calculate daily metrics with enhanced error handling and validation"""
        
        # Validate date
        date = self._validate_date(date)
        
        # Check if date is in the future
        if date > datetime.now(timezone.utc).date():
            logger.warning(f"Date {date} is in the future. This may result in no metrics.")
        
        logger.info(f"{'='*60}")
        logger.info(f"Calculating YouTube daily metrics for: {date}")
        logger.info(f"{'='*60}")
        
        # Reset error tracking
        self._errors = []
        self._warnings = []
        
        results = {
            'date': str(date),
            'keywords_processed': 0,
            'keyword_metrics_created': 0,
            'category_snapshots_created': 0,
            'errors': 0,
            'warnings': 0,
            'error_details': [],
            'warning_details': []
        }
        
        try:
            with self.error_context("fetching active keywords"):
                # Get all active keywords with retry
                keywords_query = self.db.collection('youtube_keywords').where('active', '==', True)
                keywords = list(self._retry_operation(keywords_query.stream))
                
                if not keywords:
                    logger.warning("No active keywords found")
                    results['warnings'] = 1
                    results['warning_details'].append("No active keywords found")
        except Exception as e:
            results['errors'] = 1
            results['error_details'].append(str(e))
            return results
        
        # Reset category updates for this run
        self.category_updates = {}
        
        # Process each keyword
        for keyword_doc in keywords:
            try:
                keyword_data = keyword_doc.to_dict()
                keyword = keyword_data.get('keyword') or keyword_data.get('name')
                keyword_id = keyword_doc.id
                category = keyword_data.get('category')
                
                if not keyword:
                    logger.warning(f"Skipping keyword doc {keyword_id} - no keyword field")
                    results['warnings'] += 1
                    continue
                
                # Validate keyword is a string
                keyword = str(keyword).strip()
                if not keyword:
                    logger.warning(f"Empty keyword in doc {keyword_id}")
                    continue
                
                logger.info(f"\nProcessing keyword: {keyword} (category: {category})")
                
                try:
                    daily_metric = self._calculate_keyword_daily_metrics(keyword_id, keyword, date)
                    
                    # Store for category aggregation
                    if daily_metric and category:
                        category = str(category).strip()
                        if category:
                            if category not in self.category_updates:
                                self.category_updates[category] = {}
                            self.category_updates[category][keyword] = daily_metric
                    
                    results['keywords_processed'] += 1
                    if daily_metric:
                        results['keyword_metrics_created'] += 1
                        
                except Exception as e:
                    error_msg = f"Error processing keyword {keyword}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'] += 1
                    results['error_details'].append(error_msg)
                    
            except Exception as e:
                error_msg = f"Error reading keyword document {keyword_doc.id}: {str(e)}"
                logger.error(error_msg)
                results['errors'] += 1
                results['error_details'].append(error_msg)
        
        # Update category daily snapshots
        try:
            snapshots_created = self._update_category_daily_snapshots(date)
            results['category_snapshots_created'] = snapshots_created
        except Exception as e:
            error_msg = f"Error updating category snapshots: {str(e)}"
            logger.error(error_msg)
            results['errors'] += 1
            results['error_details'].append(error_msg)
        
        # Clean up old snapshots
        try:
            if not self.dry_run:
                self._cleanup_old_snapshots()
        except Exception as e:
            # Don't fail the whole operation for cleanup errors
            logger.warning(f"Cleanup failed but continuing: {str(e)}")
            results['warnings'] += 1
        
        # Add accumulated warnings
        results['warnings'] = len(self._warnings)
        results['warning_details'] = self._warnings
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Daily metrics calculation complete:")
        logger.info(f"  Date: {date}")
        logger.info(f"  Keywords processed: {results['keywords_processed']}")
        logger.info(f"  Keyword metrics created: {results['keyword_metrics_created']}")
        logger.info(f"  Category snapshots created: {results['category_snapshots_created']}")
        logger.info(f"  Errors: {results['errors']}")
        logger.info(f"  Warnings: {results['warnings']}")
        logger.info(f"{'='*60}")
        
        return results
    
    def _calculate_keyword_daily_metrics(self, keyword_id: str, keyword: str, date: datetime.date) -> Optional[Dict[str, Any]]:
        """Calculate daily metrics with enhanced validation"""
        
        # Get interval metrics for the target date
        start_of_day = datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_of_day = datetime.combine(date, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        try:
            # Get all interval metrics for this day
            interval_metrics_query = (self.db.collection('youtube_keywords')
                                   .document(keyword_id)
                                   .collection('interval_metrics')
                                   .where('timestamp', '>=', start_of_day)
                                   .where('timestamp', '<=', end_of_day)
                                   .order_by('timestamp'))
            
            interval_metrics = list(self._retry_operation(interval_metrics_query.stream))
            
            if not interval_metrics:
                logger.warning(f"  No interval metrics found for {keyword} on {date}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to fetch interval metrics for {keyword}: {e}")
            return None
        
        # Validate and extract metrics
        try:
            # Get the last metric of the day
            last_metric = interval_metrics[-1].to_dict()
            
            # Validate numeric values
            video_count = self._validate_numeric_value(
                last_metric.get('video_count'), 'video_count', MAX_VIDEO_COUNT
            )
            views_count = self._validate_numeric_value(
                last_metric.get('views_count'), 'views_count', MAX_VIEWS_COUNT
            )
            
            # Calculate videos found during the day
            videos_found_in_day = 0
            for m in interval_metrics:
                metric_data = m.to_dict()
                found = self._validate_numeric_value(
                    metric_data.get('videos_found_in_search'), 'videos_found_in_search'
                )
                videos_found_in_day += found
                
        except Exception as e:
            logger.error(f"Error processing interval metrics for {keyword}: {e}")
            return None
        
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
        
        # Calculate velocity and acceleration
        try:
            self._calculate_velocity_acceleration(keyword_id, date, daily_metric, video_count)
        except Exception as e:
            logger.warning(f"Error calculating velocity/acceleration for {keyword}: {e}")
            # Set defaults if calculation fails
            daily_metric['velocity'] = 0
            daily_metric['acceleration'] = 0
            daily_metric['previous_video_count'] = 0
        
        # Save daily metric
        doc_id = str(date)
        
        if not self.dry_run:
            try:
                daily_metrics_collection = (self.db.collection('youtube_keywords')
                                           .document(keyword_id)
                                           .collection('daily_metrics'))
                
                self._retry_operation(
                    daily_metrics_collection.document(doc_id).set,
                    daily_metric
                )
                logger.info(f"  Daily metric created for {keyword} on {date}:")
            except Exception as e:
                logger.error(f"Failed to save daily metric for {keyword}: {e}")
                raise
        else:
            logger.info(f"  [DRY RUN] Would create daily metric for {keyword} on {date}:")
        
        logger.info(f"    Video count: {video_count:,}")
        logger.info(f"    Views count: {views_count:,}")
        logger.info(f"    Videos found: {videos_found_in_day}")
        logger.info(f"    Velocity: {daily_metric.get('velocity', 0)} videos/day")
        logger.info(f"    Acceleration: {daily_metric.get('acceleration', 0)} videos/day²")
        
        return daily_metric
    
    def _calculate_velocity_acceleration(self, keyword_id: str, date: datetime.date, 
                                       daily_metric: Dict[str, Any], video_count: int):
        """Calculate velocity and acceleration with gap detection"""
        
        # Get previous daily metrics
        daily_metrics_query = (self.db.collection('youtube_keywords')
                             .document(keyword_id)
                             .collection('daily_metrics')
                             .where('date', '<', str(date))
                             .order_by('date', direction='DESCENDING')
                             .limit(2))
        
        previous_metrics = list(self._retry_operation(daily_metrics_query.stream))
        
        if not previous_metrics:
            # First daily metric
            daily_metric['velocity'] = 0
            daily_metric['acceleration'] = 0
            daily_metric['previous_video_count'] = 0
            return
        
        # Check for gaps and calculate velocity
        prev_metric = previous_metrics[0].to_dict()
        prev_date_str = prev_metric.get('date')
        
        if not prev_date_str:
            logger.warning("Previous metric missing date field")
            daily_metric['velocity'] = 0
            daily_metric['acceleration'] = 0
            daily_metric['previous_video_count'] = 0
            return
        
        try:
            prev_date = datetime.strptime(prev_date_str, '%Y-%m-%d').date()
        except ValueError:
            logger.warning(f"Invalid date format in previous metric: {prev_date_str}")
            daily_metric['velocity'] = 0
            daily_metric['acceleration'] = 0
            daily_metric['previous_video_count'] = 0
            return
        
        # Check if it's actually the previous day
        days_gap = (date - prev_date).days
        
        if days_gap == 1:
            # No gap - calculate velocity
            prev_video_count = self._validate_numeric_value(
                prev_metric.get('video_count'), 'previous_video_count'
            )
            daily_metric['previous_video_count'] = prev_video_count
            daily_metric['velocity'] = video_count - prev_video_count
            
            # Calculate acceleration if we have 2 previous days
            if len(previous_metrics) >= 2:
                prev_prev_metric = previous_metrics[1].to_dict()
                prev_prev_date_str = prev_prev_metric.get('date')
                
                if prev_prev_date_str:
                    try:
                        prev_prev_date = datetime.strptime(prev_prev_date_str, '%Y-%m-%d').date()
                        
                        if (prev_date - prev_prev_date).days == 1:
                            # Consecutive days - calculate acceleration
                            prev_velocity = prev_metric.get('velocity', 0)
                            current_velocity = daily_metric['velocity']
                            daily_metric['acceleration'] = current_velocity - prev_velocity
                        else:
                            daily_metric['acceleration'] = 0
                            logger.info(f"  Gap in daily metrics, setting acceleration to 0")
                    except ValueError:
                        daily_metric['acceleration'] = 0
                else:
                    daily_metric['acceleration'] = 0
            else:
                daily_metric['acceleration'] = 0
        else:
            # Gap detected
            logger.warning(f"  Gap of {days_gap} days in daily metrics, setting velocity to 0")
            daily_metric['velocity'] = 0
            daily_metric['acceleration'] = 0
            daily_metric['previous_video_count'] = 0
    
    def _update_category_daily_snapshots(self, date: datetime.date) -> int:
        """Update category snapshots with enhanced error handling"""
        logger.info(f"\nUpdating category daily snapshots for {date}")
        
        if not self.category_updates:
            logger.info("  No category updates to process")
            return 0
        
        # Define time windows
        time_windows = {
            'daily_snapshots_90d': 90,
            'daily_snapshots_30d': 30,
            'daily_snapshots_7d': 7
        }
        
        today = datetime.now(timezone.utc).date()
        days_ago = (today - date).days
        
        if days_ago < 0:
            logger.warning(f"  Processing future date: {date}")
        
        # Batch for efficient writes
        batch = self.db.batch()
        batch_count = 0
        snapshots_created = 0
        total_batches_committed = 0
        
        for category, keyword_metrics in self.category_updates.items():
            if not keyword_metrics:
                continue
            
            try:
                logger.info(f"\n  Updating category: {category}")
                
                # Calculate aggregated metrics
                total_videos = sum(
                    self._validate_numeric_value(m.get('video_count'), 'video_count') 
                    for m in keyword_metrics.values()
                )
                total_views = sum(
                    self._validate_numeric_value(m.get('views_count'), 'views_count') 
                    for m in keyword_metrics.values()
                )
                total_videos_found = sum(
                    self._validate_numeric_value(m.get('videos_found_in_day'), 'videos_found_in_day') 
                    for m in keyword_metrics.values()
                )
                total_velocity = sum(
                    m.get('velocity', 0) for m in keyword_metrics.values()
                )
                
                # Prepare keyword-specific data
                keywords_data = {}
                for keyword, metric in keyword_metrics.items():
                    video_count = self._validate_numeric_value(metric.get('video_count'), 'video_count')
                    views_count = self._validate_numeric_value(metric.get('views_count'), 'views_count')
                    
                    keywords_data[keyword] = {
                        'post_count': video_count,
                        'total_upvotes': views_count,
                        'velocity': metric.get('velocity', 0),
                        'avg_upvotes': views_count // max(video_count, 1),
                        'trend_score': abs(metric.get('velocity', 0)) * 100
                    }
                
                # Base document data
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
                    if days_ago < window_days and days_ago >= 0:
                        subcollection_ref = category_ref.collection(subcollection_name)
                        doc_ref = subcollection_ref.document(str(date))
                        
                        if not self.dry_run:
                            batch.set(doc_ref, snapshot_data, merge=True)
                            batch_count += 1
                            snapshots_created += 1
                            
                            # Commit batch if needed
                            if batch_count >= MAX_BATCH_SIZE - 10:  # Leave some margin
                                self._retry_operation(batch.commit)
                                total_batches_committed += 1
                                batch = self.db.batch()
                                batch_count = 0
                        else:
                            logger.info(f"    [DRY RUN] Would update {subcollection_name}/{str(date)}")
                
                logger.info(f"    Keywords: {', '.join(list(keywords_data.keys())[:5])}" + 
                          (f" and {len(keywords_data) - 5} more" if len(keywords_data) > 5 else ""))
                logger.info(f"    Total videos: {total_videos:,}")
                logger.info(f"    Total views: {total_views:,}")
                logger.info(f"    Videos added: {total_videos_found}")
                
            except Exception as e:
                logger.error(f"Error updating category {category}: {e}")
                # Continue with other categories
                continue
        
        # Commit remaining batch
        if batch_count > 0 and not self.dry_run:
            try:
                self._retry_operation(batch.commit)
                total_batches_committed += 1
                logger.info(f"\n  Category daily snapshots updated successfully")
                logger.info(f"  Total batches committed: {total_batches_committed}")
            except Exception as e:
                logger.error(f"Failed to commit final batch: {e}")
                raise
        elif self.dry_run:
            logger.info(f"\n  [DRY RUN] Would create {snapshots_created} snapshots")
        
        return snapshots_created
    
    def _cleanup_old_snapshots(self):
        """Remove snapshots older than their time window with batch processing"""
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
        total_deleted = 0
        
        try:
            # Get all categories
            categories_query = self.db.collection('youtube_categories')
            categories = list(self._retry_operation(categories_query.stream))
            
            for cat_doc in categories:
                category = cat_doc.id
                
                for subcollection_name, window_days in time_windows.items():
                    try:
                        # Calculate cutoff date
                        cutoff_date = today - timedelta(days=window_days)
                        
                        # Get old snapshots in batches
                        while True:
                            old_snapshots_query = (self.db.collection('youtube_categories')
                                                .document(category)
                                                .collection(subcollection_name)
                                                .where('date', '<', str(cutoff_date))
                                                .limit(MAX_BATCH_SIZE))
                            
                            old_snapshots = list(self._retry_operation(old_snapshots_query.stream))
                            
                            if not old_snapshots:
                                break
                            
                            # Delete in batch
                            batch = self.db.batch()
                            for doc in old_snapshots:
                                batch.delete(doc.reference)
                                total_deleted += 1
                            
                            self._retry_operation(batch.commit)
                            
                            # If we got fewer than the limit, we're done
                            if len(old_snapshots) < MAX_BATCH_SIZE:
                                break
                                
                    except Exception as e:
                        logger.warning(f"Error cleaning up {subcollection_name} for {category}: {e}")
                        # Continue with other subcollections
            
            if total_deleted > 0:
                logger.info(f"  Deleted {total_deleted} old snapshots")
            else:
                logger.info("  No old snapshots to delete")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            # Don't raise - cleanup is not critical
    
    def calculate_date_range(self, start_date: datetime.date, end_date: datetime.date) -> List[Dict[str, Any]]:
        """Calculate daily metrics for a range of dates with validation"""
        
        # Validate dates
        start_date = self._validate_date(start_date)
        end_date = self._validate_date(end_date)
        
        if start_date > end_date:
            logger.warning(f"Start date {start_date} is after end date {end_date}")
            return []
        
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            try:
                result = self.calculate_daily_metrics(current_date)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to calculate metrics for {current_date}: {e}")
                results.append({
                    'date': str(current_date),
                    'error': str(e),
                    'keywords_processed': 0,
                    'errors': 1
                })
            
            current_date += timedelta(days=1)
        
        return results
    
    def update_historical_peaks(self):
        """Update historical peak values with validation"""
        logger.info("\nUpdating historical peaks for all keywords")
        
        try:
            keywords_query = self.db.collection('youtube_keywords').where('active', '==', True)
            keywords = list(self._retry_operation(keywords_query.stream))
            
            updated_count = 0
            
            for keyword_doc in keywords:
                try:
                    keyword_data = keyword_doc.to_dict()
                    keyword = keyword_data.get('keyword') or keyword_data.get('name')
                    keyword_id = keyword_doc.id
                    
                    if not keyword:
                        continue
                    
                    # Get all daily metrics
                    daily_metrics_query = (self.db.collection('youtube_keywords')
                                         .document(keyword_id)
                                         .collection('daily_metrics'))
                    
                    max_video_count = 0
                    max_velocity = 0
                    max_videos_in_day = 0
                    max_views_count = 0
                    
                    # Process in batches to avoid memory issues
                    offset = 0
                    batch_size = 100
                    
                    while True:
                        batch_query = daily_metrics_query.limit(batch_size).offset(offset)
                        batch_docs = list(self._retry_operation(batch_query.stream))
                        
                        if not batch_docs:
                            break
                        
                        for metric_doc in batch_docs:
                            metric = metric_doc.to_dict()
                            max_video_count = max(max_video_count, 
                                                self._validate_numeric_value(metric.get('video_count'), 'video_count'))
                            max_views_count = max(max_views_count, 
                                                self._validate_numeric_value(metric.get('views_count'), 'views_count'))
                            max_velocity = max(max_velocity, abs(metric.get('velocity', 0)))
                            max_videos_in_day = max(max_videos_in_day, 
                                                  self._validate_numeric_value(metric.get('videos_found_in_day'), 'videos_found_in_day'))
                        
                        offset += batch_size
                        
                        if len(batch_docs) < batch_size:
                            break
                    
                    # Update keyword document
                    peaks = {
                        'max_video_count': max_video_count,
                        'max_views_count': max_views_count,
                        'max_velocity': max_velocity,
                        'max_videos_in_day': max_videos_in_day,
                        'peaks_updated': datetime.now(timezone.utc)
                    }
                    
                    if not self.dry_run:
                        self._retry_operation(
                            self.db.collection('youtube_keywords').document(keyword_id).update,
                            {'historical_peaks': peaks}
                        )
                        logger.info(f"  Updated peaks for {keyword}: videos={max_video_count:,}, velocity={max_velocity}")
                        updated_count += 1
                    else:
                        logger.info(f"  [DRY RUN] Would update peaks for {keyword}")
                    
                except Exception as e:
                    logger.error(f"Error updating peaks for keyword {keyword_doc.id}: {e}")
            
            logger.info(f"\nHistorical peaks update complete. Updated {updated_count} keywords.")
            
        except Exception as e:
            logger.error(f"Failed to update historical peaks: {e}")
            raise


def main():
    """Main entry point with enhanced error handling"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Calculate YouTube daily metrics and category snapshots (V2 - Hardened)')
    parser.add_argument('--date', type=str, 
                        help='Date to calculate metrics for (YYYY-MM-DD). Default: yesterday')
    parser.add_argument('--range', nargs=2, metavar=('START', 'END'),
                        help='Calculate metrics for date range (YYYY-MM-DD YYYY-MM-DD)')
    parser.add_argument('--peaks', action='store_true',
                        help='Update historical peak values')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without writing to database (preview mode)')
    
    args = parser.parse_args()
    
    try:
        calculator = YouTubeDailyMetricsUnified(dry_run=args.dry_run)
        
        if args.peaks:
            calculator.update_historical_peaks()
        elif args.range:
            start_date = datetime.strptime(args.range[0], '%Y-%m-%d').date()
            end_date = datetime.strptime(args.range[1], '%Y-%m-%d').date()
            results = calculator.calculate_date_range(start_date, end_date)
            
            # Summary
            total_errors = sum(r.get('errors', 0) for r in results)
            total_processed = sum(r.get('keywords_processed', 0) for r in results)
            print(f"\nDate range complete: {len(results)} days, {total_processed} keywords, {total_errors} errors")
        elif args.date:
            target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            result = calculator.calculate_daily_metrics(target_date)
        else:
            # Default to yesterday
            result = calculator.calculate_daily_metrics()
        
        # Save run log
        if not args.dry_run and not args.peaks:
            try:
                log_data = {
                    'type': 'youtube_daily_metrics_v2',
                    'timestamp': datetime.now(timezone.utc),
                    'date_processed': args.date or str(datetime.now(timezone.utc).date() - timedelta(days=1)),
                    'dry_run': args.dry_run,
                    'version': '2.0'
                }
                # Create meaningful document ID for daily metrics log
                doc_id = f"daily_metrics_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
                calculator.db.collection('youtube_collection_logs').document(doc_id).set(log_data)
            except Exception as e:
                logger.warning(f"Failed to save run log: {e}")
    
    except KeyboardInterrupt:
        logger.info("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()