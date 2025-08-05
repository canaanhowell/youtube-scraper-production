#!/usr/bin/env python3
"""
Unified YouTube Daily Metrics Calculator
Updates both youtube_keywords daily_metrics and youtube_categories daily snapshots.
Designed to run once daily to process yesterday's data.
"""

import os
import sys
import logging
import numpy as np
import math
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
        # Cache platform baseline
        self._platform_baseline = None
        
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
        
        # Update all_youtube aggregate snapshot
        all_youtube_created = self._update_all_youtube_snapshot(date)
        if all_youtube_created:
            results['category_snapshots_created'] += all_youtube_created
        
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
        
        # Get platform baseline for normalization
        platform_baseline = self._get_platform_baseline()
        
        # Prepare daily metric document with new standardized v2.0 fields
        daily_metric = {
            'date': str(date),
            'video_count': video_count,
            'new_videos_in_day': videos_found_in_day,  # RENAMED from videos_found_in_day
            'total_views': views_count,  # RENAMED from views_count
            'avg_views_per_video': 0 if video_count == 0 else views_count / video_count,  # NEW
            'platform_baseline_daily': platform_baseline,  # Context data
            'metrics_version': '2.0',
            'timestamp': end_of_day
        }
        
        # Get previous daily metrics from the daily_metrics subcollection
        daily_metrics_ref = (self.db.collection('youtube_keywords')
                            .document(keyword_id)
                            .collection('daily_metrics')
                            .where('date', '<', str(date))
                            .order_by('date', direction='DESCENDING')
                            .limit(2))
        
        previous_metrics = [doc.to_dict() for doc in daily_metrics_ref.stream()]
        
        # Calculate velocity (requires 1 previous day)
        if previous_metrics:
            # Get the most recent previous day
            prev_metric = previous_metrics[0]
            prev_date = datetime.strptime(prev_metric['date'], '%Y-%m-%d').date()
            
            # Only use if it's actually the previous day
            if prev_date == date - timedelta(days=1):
                prev_video_count = prev_metric.get('video_count', 0)
                raw_velocity = videos_found_in_day  # Raw velocity (new videos per day)
                
                # Calculate platform-normalized velocity (NEW: this becomes the main 'velocity' field)
                velocity_normalized = self._calculate_platform_normalized_velocity(
                    videos_found_in_day, platform_baseline
                )
                daily_metric['velocity'] = velocity_normalized  # Platform-normalized percentage
                
                # Calculate acceleration and momentum (requires velocity history)
                velocity_history = self._get_keyword_velocity_history(keyword_id, date, days=7)
                daily_metric['acceleration'] = self._calculate_keyword_relative_acceleration(
                    velocity_history, raw_velocity
                )
                daily_metric['momentum_score'] = self._calculate_momentum_score(velocity_history)
                
                # Calculate unified trend score v2
                daily_metric['trend_score_v2'] = self._calculate_trend_score(
                    velocity_normalized,
                    daily_metric['momentum_score']
                )
                
                # Store keyword baseline for context
                daily_metric['keyword_baseline_7d'] = np.mean(velocity_history) if velocity_history else 0
                
                # Legacy acceleration (for backwards compatibility if needed)
                if len(previous_metrics) >= 2:
                    prev_prev_metric = previous_metrics[1]  # Already a dict
                    prev_prev_date = datetime.strptime(prev_prev_metric['date'], '%Y-%m-%d').date()
                    
                    if prev_prev_date == date - timedelta(days=2):
                        prev_velocity = prev_metric.get('velocity', 0)
                        daily_metric['acceleration'] = raw_velocity - prev_velocity  # videos/day²
                    else:
                        daily_metric['acceleration'] = 0
                else:
                    daily_metric['acceleration'] = 0
            else:
                # Gap in daily metrics
                logger.warning(f"  Gap in daily metrics for {keyword}, cannot calculate velocity")
                self._set_default_metrics(daily_metric, videos_found_in_day, platform_baseline, keyword_id, date)
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
                            raw_velocity = video_count - prev_video_count
                            
                            # Calculate platform-normalized velocity as the main velocity field
                            velocity_normalized = self._calculate_platform_normalized_velocity(
                                videos_found_in_day, platform_baseline
                            )
                            daily_metric['velocity'] = velocity_normalized  # Platform-normalized percentage
                            
                            velocity_history = self._get_keyword_velocity_history(keyword_id, date, days=7)
                            daily_metric['acceleration_keyword_relative'] = self._calculate_keyword_relative_acceleration(
                                velocity_history, raw_velocity
                            )
                            daily_metric['momentum_score'] = self._calculate_momentum_score(velocity_history)
                            daily_metric['trend_score_v2'] = self._calculate_trend_score(
                                velocity_normalized,
                                daily_metric['momentum_score']
                            )
                            daily_metric['keyword_baseline_7d'] = np.mean(velocity_history) if velocity_history else 0
                            daily_metric['acceleration'] = 0  # Legacy field
                        else:
                            # No video count in snapshot
                            self._set_default_metrics(daily_metric, videos_found_in_day, platform_baseline, keyword_id, date)
                    else:
                        # Keyword not in snapshot
                        logger.info(f"  No previous day data for {keyword} in category snapshot")
                        self._set_default_metrics(daily_metric, videos_found_in_day, platform_baseline, keyword_id, date)
                else:
                    # No category snapshot for previous day
                    self._set_default_metrics(daily_metric, videos_found_in_day, platform_baseline, keyword_id, date)
            else:
                # Couldn't determine category
                self._set_default_metrics(daily_metric, videos_found_in_day, platform_baseline, keyword_id, date)
        
        # Store the daily metric in the keyword's daily_metrics subcollection
        date_key = str(date)  # e.g., "2025-08-01"
        
        if not self.dry_run:
            # Create/update document in daily_metrics subcollection
            daily_metrics_ref = (self.db.collection('youtube_keywords')
                                .document(keyword_id)
                                .collection('daily_metrics'))
            
            # Save daily metric as a document with date as ID
            daily_metrics_ref.document(date_key).set(daily_metric)
            
            # Also update current_velocity in the main keyword document
            keyword_ref = self.db.collection('youtube_keywords').document(keyword_id)
            keyword_ref.update({
                'current_velocity': daily_metric.get('velocity', 0),
                'updated_at': datetime.now(timezone.utc)
            })
            
            logger.info(f"  Daily metric created for {keyword} on {date}:")
        else:
            logger.info(f"  [DRY RUN] Would create daily metric for {keyword} on {date}:")
        
        logger.info(f"    Video count: {video_count}")
        logger.info(f"    Views count: {views_count:,}")
        logger.info(f"    Videos found: {videos_found_in_day}")
        logger.info(f"    Velocity (raw): {videos_found_in_day} videos/day")
        logger.info(f"    Velocity (normalized): {daily_metric.get('velocity', 0):.1f}")
        logger.info(f"    Acceleration (relative): {daily_metric.get('acceleration', 0):.2f}")
        logger.info(f"    Momentum score: {daily_metric.get('momentum_score', 0):.1f}")
        logger.info(f"    Trend score v2: {daily_metric.get('trend_score_v2', 0):.1f}")
        
        return daily_metric
    
    def _get_platform_baseline(self) -> float:
        """Get YouTube platform baseline for velocity normalization"""
        if self._platform_baseline is not None:
            return self._platform_baseline
        
        try:
            platform_doc = self.db.collection('platform_metrics').document('youtube').get()
            if platform_doc.exists:
                baseline = platform_doc.to_dict().get('daily_baseline', 150.0)
                self._platform_baseline = baseline
                logger.info(f"Using platform baseline: {baseline} videos/day")
                return baseline
            else:
                # Fallback baseline for YouTube
                self._platform_baseline = 150.0
                logger.warning("No platform baseline found, using fallback: 150 videos/day")
                return self._platform_baseline
        except Exception as e:
            logger.error(f"Error fetching platform baseline: {e}, using fallback")
            self._platform_baseline = 150.0
            return self._platform_baseline
    
    def _calculate_platform_normalized_velocity(self, videos_found_today: int, platform_baseline: float) -> float:
        """Calculate velocity as percentage of platform's typical daily volume"""
        if platform_baseline <= 0:
            return 0.0
        return round((videos_found_today / platform_baseline) * 100, 1)
    
    def _get_keyword_velocity_history(self, keyword_id: str, current_date, days: int = 7) -> list:
        """Get keyword's velocity history for the last N days"""
        try:
            end_date = current_date - timedelta(days=1)  # Yesterday
            start_date = end_date - timedelta(days=days-1)  # N days ago
            
            daily_metrics_ref = (self.db.collection('youtube_keywords')
                                .document(keyword_id)
                                .collection('daily_metrics')
                                .where('date', '>=', str(start_date))
                                .where('date', '<=', str(end_date))
                                .order_by('date'))
            
            velocities = []
            for doc in daily_metrics_ref.stream():
                metric = doc.to_dict()
                velocity = metric.get('velocity', 0)
                if velocity is not None:
                    velocities.append(velocity)
            
            return velocities
        except Exception as e:
            logger.error(f"Error fetching velocity history for {keyword_id}: {e}")
            return []
    
    def _calculate_keyword_relative_acceleration(self, velocity_history: list, current_velocity: float) -> float:
        """Calculate acceleration as ratio change from keyword's own baseline"""
        if not velocity_history or len(velocity_history) < 2:
            return 1.0  # No acceleration data
        
        baseline_velocity = np.mean(velocity_history)
        
        if baseline_velocity == 0:
            return 2.0 if current_velocity > 0 else 0.5
        
        return round(current_velocity / baseline_velocity, 3)
    
    def _calculate_momentum_score(self, velocity_history: list) -> float:
        """Calculate momentum score (0-100) based on velocity trend"""
        if not velocity_history or len(velocity_history) < 3:
            return 50.0  # Neutral momentum
        
        try:
            # Calculate trend using linear regression
            days = np.arange(len(velocity_history))
            slope, intercept = np.polyfit(days, velocity_history, 1)
            
            # Normalize slope to keyword's average velocity
            avg_velocity = np.mean(velocity_history)
            normalized_slope = slope / avg_velocity if avg_velocity > 0 else 0
            
            # Convert to 0-100 score with sigmoid
            momentum_score = 50 + (50 * math.tanh(normalized_slope * 2))
            
            return round(momentum_score, 1)
        except Exception as e:
            logger.error(f"Error calculating momentum score: {e}")
            return 50.0
    
    def _calculate_trend_score(self, velocity_platform_normalized: float, momentum_score: float) -> float:
        """Calculate unified trend score combining velocity and momentum"""
        # Velocity component (cap at 200 for scoring)
        velocity_capped = min(200, velocity_platform_normalized)
        velocity_score = velocity_capped / 2  # Convert to 0-100 scale
        
        # Weighted combination: 60% velocity, 40% momentum
        trend_score = (0.6 * velocity_score) + (0.4 * momentum_score)
        
        return round(trend_score, 1)
    
    def _set_default_metrics(self, daily_metric: dict, videos_found_in_day: int, platform_baseline: float, keyword_id: str, date):
        """Set default values for new standardized metrics when no historical data available"""
        # Calculate platform-normalized velocity as the main velocity field
        velocity_normalized = self._calculate_platform_normalized_velocity(
            videos_found_in_day, platform_baseline
        )
        daily_metric['velocity'] = velocity_normalized  # Platform-normalized percentage
        daily_metric['acceleration'] = 0
        daily_metric['previous_video_count'] = 0
        daily_metric['acceleration_keyword_relative'] = 1.0  # Neutral
        daily_metric['momentum_score'] = 50.0  # Neutral
        daily_metric['trend_score_v2'] = self._calculate_trend_score(
            velocity_normalized, 50.0
        )
        daily_metric['keyword_baseline_7d'] = 0
    
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
            total_views = sum(m.get('total_views', 0) for m in keyword_metrics.values())  # UPDATED field name
            total_new_videos = sum(m.get('new_videos_in_day', 0) for m in keyword_metrics.values())  # UPDATED field name
            
            # Calculate aggregated velocity (sum of all keyword velocities - platform normalized)
            total_velocity_normalized = sum(m.get('velocity', 0) for m in keyword_metrics.values())
            
            # Prepare keyword-specific data with new standardized metrics
            keywords_data = {}
            total_acceleration = 0
            total_momentum_score = 0
            keyword_count = 0
            
            for keyword, metric in keyword_metrics.items():
                # New standardized format matching firestore_mapping.md
                keywords_data[keyword] = {
                    'video_count': metric.get('video_count', 0),
                    'new_videos_in_day': metric.get('new_videos_in_day', 0),
                    'velocity': metric.get('velocity', 0),  # Platform-normalized percentage
                    'acceleration': metric.get('acceleration', 1.0),  # Keyword-relative ratio
                    'total_views': metric.get('total_views', 0)
                }
                
                # Aggregate for category-level metrics
                total_acceleration += metric.get('acceleration', 1.0)
                total_momentum_score += metric.get('momentum_score', 50.0)
                keyword_count += 1
            
            # Calculate category-level standardized metrics
            avg_velocity_normalized = total_velocity_normalized / keyword_count if keyword_count > 0 else 0
            avg_acceleration = total_acceleration / keyword_count if keyword_count > 0 else 1.0
            avg_momentum_score = total_momentum_score / keyword_count if keyword_count > 0 else 50.0
            
            # Base document data for snapshots with NEW v2.0 schema (matching firestore_mapping.md)
            snapshot_data = {
                'date': str(date),
                'timestamp': datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
                'total_videos': total_videos,
                'total_new_videos': total_new_videos,  # RENAMED from videos_added
                'velocity': round(total_velocity_normalized, 1),  # Sum of keyword velocities (platform-normalized)
                'acceleration': round(avg_acceleration, 2),  # Average of keyword accelerations
                'total_views': total_views,
                'keywords': keywords_data  # RENAMED from keywords_data
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
            logger.info(f"    Videos added: {total_new_videos}")
            logger.info(f"    Total velocity (raw): {total_new_videos}")  # Raw sum of new videos
            logger.info(f"    Avg velocity (normalized): {avg_velocity_normalized:.1f}")
            logger.info(f"    Avg acceleration (relative): {avg_acceleration:.2f}")
            logger.info(f"    Avg momentum score: {avg_momentum_score:.1f}")
        
        # Commit remaining batch
        if batch_count > 0 and not self.dry_run:
            batch.commit()
            logger.info(f"\n  Category daily snapshots updated successfully")
        elif self.dry_run:
            logger.info(f"\n  [DRY RUN] Would create {snapshots_created} snapshots")
        
        return snapshots_created
    
    def _update_all_youtube_snapshot(self, date) -> int:
        """Update all_youtube aggregate snapshot combining all keywords"""
        logger.info(f"\nUpdating all_youtube aggregate snapshot for {date}")
        
        # Define time windows
        time_windows = {
            'daily_snapshots_90d': 90,
            'daily_snapshots_30d': 30,
            'daily_snapshots_7d': 7
        }
        
        today = datetime.now(timezone.utc).date()
        days_ago = (today - date).days
        
        # Aggregate all keywords across all categories
        all_keywords_metrics = {}
        for category, keyword_metrics in self.category_updates.items():
            all_keywords_metrics.update(keyword_metrics)
        
        if not all_keywords_metrics:
            logger.info("  No keyword metrics to aggregate for all_youtube")
            return 0
        
        # Calculate totals across all keywords
        total_videos = sum(m.get('video_count', 0) for m in all_keywords_metrics.values())
        total_views = sum(m.get('total_views', 0) for m in all_keywords_metrics.values())
        total_new_videos = sum(m.get('new_videos_in_day', 0) for m in all_keywords_metrics.values())
        total_velocity_normalized = sum(m.get('velocity', 0) for m in all_keywords_metrics.values())
        
        # Calculate averages
        keyword_count = len(all_keywords_metrics)
        avg_velocity_normalized = total_velocity_normalized / keyword_count if keyword_count > 0 else 0
        
        total_acceleration = sum(m.get('acceleration', 1.0) for m in all_keywords_metrics.values())
        avg_acceleration = total_acceleration / keyword_count if keyword_count > 0 else 1.0
        
        # Prepare keyword data
        keywords_data = {}
        for keyword, metric in all_keywords_metrics.items():
            keywords_data[keyword] = {
                'video_count': metric.get('video_count', 0),
                'new_videos_in_day': metric.get('new_videos_in_day', 0),
                'velocity': metric.get('velocity', 0),
                'acceleration': metric.get('acceleration', 1.0),
                'total_views': metric.get('total_views', 0)
            }
        
        # Create snapshot data
        snapshot_data = {
            'date': str(date),
            'timestamp': datetime.combine(date, datetime.min.time()).replace(tzinfo=timezone.utc),
            'total_videos': total_videos,
            'total_new_videos': total_new_videos,
            'velocity': round(total_velocity_normalized, 1),  # Sum of all keyword velocities
            'acceleration': round(avg_acceleration, 2),  # Average acceleration
            'total_views': total_views,
            'keywords': keywords_data
        }
        
        # Update time window subcollections
        category_ref = self.db.collection('youtube_categories').document('all_youtube')
        snapshots_created = 0
        
        for subcollection_name, window_days in time_windows.items():
            # Check if date falls within this window
            if days_ago < window_days:
                subcollection_ref = category_ref.collection(subcollection_name)
                doc_ref = subcollection_ref.document(str(date))
                
                if not self.dry_run:
                    doc_ref.set(snapshot_data, merge=True)
                    snapshots_created += 1
                else:
                    logger.info(f"    [DRY RUN] Would update {subcollection_name}/{str(date)}")
        
        # Update the main all_youtube document
        if not self.dry_run:
            category_ref.set({
                'category': 'all_youtube',
                'keywords': list(all_keywords_metrics.keys()),
                'last_updated': datetime.now(timezone.utc),
                'updated_by': 'youtube_daily_metrics_unified_vm.py'
            }, merge=True)
        
        logger.info(f"  all_youtube aggregate snapshot created:")
        logger.info(f"    Total keywords: {keyword_count}")
        logger.info(f"    Total videos: {total_videos}")
        logger.info(f"    Total views: {total_views:,}")
        logger.info(f"    Total new videos: {total_new_videos}")
        logger.info(f"    Avg velocity (normalized): {avg_velocity_normalized:.1f}")
        logger.info(f"    Avg acceleration: {avg_acceleration:.2f}")
        
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
        # Create meaningful document ID for daily metrics log
        doc_id = f"daily_metrics_{datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
        calculator.db.collection('youtube_collection_logs').document(doc_id).set(log_data)


if __name__ == "__main__":
    main()