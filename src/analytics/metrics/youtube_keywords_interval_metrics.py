#!/usr/bin/env python3
"""
Collect interval metrics for YouTube keywords.
This tracks video counts and views over time, calculating velocity and acceleration.
Designed to run hourly after YouTube collection completes.
VM-compatible version.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import time
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

# Import our modules
from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeIntervalMetricsCollector:
    def __init__(self):
        self.firebase_client = FirebaseClient()
        self.db = self.firebase_client.db
        self.collection_timeout = 300  # 5 minutes max per keyword
        
    def collect_all_keywords(self):
        """Collect interval metrics for all active YouTube keywords"""
        
        logger.info("Starting YouTube interval metrics collection")
        start_time = datetime.now(timezone.utc)
        
        # Get all active keywords
        keywords_ref = self.db.collection('youtube_keywords').where('active', '==', True)
        keywords = list(keywords_ref.stream())
        
        results = {
            'keywords_processed': 0,
            'metrics_created': 0,
            'errors': 0,
            'start_time': start_time.isoformat(),
            'keywords': {}
        }
        
        for keyword_doc in keywords:
            keyword_data = keyword_doc.to_dict()
            keyword = keyword_data.get('keyword', keyword_data.get('name'))
            keyword_id = keyword_doc.id
            
            if not keyword:
                logger.warning(f"Skipping keyword doc {keyword_id} - no keyword field")
                continue
                
            try:
                logger.info(f"\nProcessing keyword: {keyword}")
                metric_data = self._collect_keyword_metrics(keyword_id, keyword)
                
                if metric_data:
                    results['keywords'][keyword] = {
                        'video_count': metric_data.get('video_count', 0),
                        'views_count': metric_data.get('views_count', 0),
                        'velocity': metric_data.get('velocity', 0),
                        'videos_found_in_search': metric_data.get('videos_found_in_search', 0)
                    }
                    results['metrics_created'] += 1
                
                results['keywords_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing {keyword}: {e}")
                results['errors'] += 1
                results['keywords'][keyword] = {'error': str(e)}
        
        # Calculate total duration
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        results['duration_seconds'] = duration
        results['end_time'] = end_time.isoformat()
        
        # Log summary
        logger.info(f"\nInterval metrics collection complete:")
        logger.info(f"  Keywords processed: {results['keywords_processed']}")
        logger.info(f"  Metrics created: {results['metrics_created']}")
        logger.info(f"  Errors: {results['errors']}")
        logger.info(f"  Duration: {duration:.1f} seconds")
        
        return results
    
    def _collect_keyword_metrics(self, keyword_id: str, keyword: str) -> Optional[Dict]:
        """Collect metrics for a single keyword"""
        
        collection_start = time.time()
        
        # Get current video count and views from youtube_videos collection
        videos_ref = (self.db.collection('youtube_videos')
                     .document(keyword)
                     .collection('videos'))
        
        all_videos = []
        total_views = 0
        
        # Get all videos to count total and sum views
        for doc in videos_ref.stream():
            if time.time() - collection_start > self.collection_timeout:
                logger.warning(f"Timeout reached for {keyword}, using partial data")
                break
                
            video_data = doc.to_dict()
            all_videos.append(doc.id)
            
            # Extract views count, handling various formats
            views = video_data.get('views', 0)
            if isinstance(views, str):
                # Handle "1.2K views", "1M views", etc.
                views_str = views.replace(',', '').replace(' views', '').replace(' view', '')
                if 'K' in views_str:
                    try:
                        total_views += int(float(views_str.replace('K', '')) * 1000)
                    except:
                        pass
                elif 'M' in views_str:
                    try:
                        total_views += int(float(views_str.replace('M', '')) * 1000000)
                    except:
                        pass
                else:
                    try:
                        total_views += int(views_str)
                    except:
                        pass
            elif isinstance(views, (int, float)):
                total_views += int(views)
        
        video_count = len(all_videos)
        
        # Get the previous interval metric
        interval_ref = (self.db.collection('youtube_keywords')
                       .document(keyword_id)
                       .collection('interval_metrics')
                       .order_by('timestamp', direction='DESCENDING')
                       .limit(1))
        
        previous_metrics = list(interval_ref.stream())
        
        # Calculate new videos found since last check
        videos_found_in_search = 0
        if previous_metrics:
            prev_data = previous_metrics[0].to_dict()
            prev_count = prev_data.get('video_count', 0)
            videos_found_in_search = max(0, video_count - prev_count)
        else:
            # First metric, all videos are new
            videos_found_in_search = video_count
        
        # Create new interval metric
        timestamp = datetime.now(timezone.utc)
        interval_metric = {
            'timestamp': timestamp,
            'timestamp_str': timestamp.isoformat(),
            'video_count': video_count,
            'views_count': total_views,
            'videos_found_in_search': videos_found_in_search,
            'created_at': timestamp,
            'updated_at': timestamp
        }
        
        # Calculate velocity and acceleration
        if previous_metrics:
            prev_data = previous_metrics[0].to_dict()
            
            # Get time difference in hours
            prev_timestamp = prev_data.get('timestamp')
            if isinstance(prev_timestamp, str):
                prev_timestamp = datetime.fromisoformat(prev_timestamp.replace('Z', '+00:00'))
            
            time_diff_hours = (timestamp - prev_timestamp).total_seconds() / 3600
            
            if time_diff_hours > 0:
                # Velocity: videos per hour
                velocity = videos_found_in_search / time_diff_hours
                interval_metric['velocity'] = round(velocity, 2)
                
                # Acceleration: change in velocity per hour
                prev_velocity = prev_data.get('velocity', 0)
                acceleration = (velocity - prev_velocity) / time_diff_hours
                interval_metric['acceleration'] = round(acceleration, 3)
            else:
                interval_metric['velocity'] = 0
                interval_metric['acceleration'] = 0
                
            interval_metric['previous_video_count'] = prev_data.get('video_count', 0)
        else:
            # First metric
            interval_metric['velocity'] = 0
            interval_metric['acceleration'] = 0
            interval_metric['previous_video_count'] = 0
        
        # Save interval metric
        doc_id = timestamp.strftime('%Y%m%d_%H%M%S')
        interval_metrics_ref = (self.db.collection('youtube_keywords')
                               .document(keyword_id)
                               .collection('interval_metrics'))
        
        interval_metrics_ref.document(doc_id).set(interval_metric)
        
        # Update main keyword document with current metrics
        keyword_update = {
            'current_metrics': {
                'video_count': video_count,
                'views_count': total_views,
                'velocity': interval_metric.get('velocity', 0),
                'acceleration': interval_metric.get('acceleration', 0),
                'last_updated': timestamp
            },
            'last_interval_collection': timestamp
        }
        
        self.db.collection('youtube_keywords').document(keyword_id).update(keyword_update)
        
        logger.info(f"  Video count: {video_count}")
        logger.info(f"  Total views: {total_views:,}")
        logger.info(f"  New videos: {videos_found_in_search}")
        logger.info(f"  Velocity: {interval_metric.get('velocity', 0):.2f} videos/hour")
        logger.info(f"  Acceleration: {interval_metric.get('acceleration', 0):.3f} videos/hour²")
        
        return interval_metric
    
    def calculate_rolling_metrics(self):
        """Calculate rolling averages for all keywords"""
        logger.info("\nCalculating rolling metrics for all keywords")
        
        keywords_ref = self.db.collection('youtube_keywords').where('active', '==', True)
        keywords = list(keywords_ref.stream())
        
        for keyword_doc in keywords:
            keyword_data = keyword_doc.to_dict()
            keyword = keyword_data.get('keyword', keyword_data.get('name'))
            keyword_id = keyword_doc.id
            
            if not keyword:
                continue
                
            try:
                self._calculate_keyword_rolling_metrics(keyword_id, keyword)
            except Exception as e:
                logger.error(f"Error calculating rolling metrics for {keyword}: {e}")
    
    def _calculate_keyword_rolling_metrics(self, keyword_id: str, keyword: str):
        """Calculate rolling averages for a single keyword"""
        
        now = datetime.now(timezone.utc)
        
        # Define time windows
        windows = {
            '1_hour': now - timedelta(hours=1),
            '6_hours': now - timedelta(hours=6),
            '24_hours': now - timedelta(hours=24),
            '7_days': now - timedelta(days=7)
        }
        
        rolling_metrics = {}
        
        for window_name, start_time in windows.items():
            # Get metrics within this window
            metrics_ref = (self.db.collection('youtube_keywords')
                          .document(keyword_id)
                          .collection('interval_metrics')
                          .where('timestamp', '>=', start_time)
                          .order_by('timestamp'))
            
            metrics = list(metrics_ref.stream())
            
            if metrics:
                # Calculate averages
                velocities = [m.to_dict().get('velocity', 0) for m in metrics]
                accelerations = [m.to_dict().get('acceleration', 0) for m in metrics]
                
                rolling_metrics[window_name] = {
                    'avg_velocity': sum(velocities) / len(velocities),
                    'avg_acceleration': sum(accelerations) / len(accelerations),
                    'max_velocity': max(velocities),
                    'min_velocity': min(velocities),
                    'sample_count': len(metrics)
                }
        
        # Update keyword document with rolling metrics
        if rolling_metrics:
            self.db.collection('youtube_keywords').document(keyword_id).update({
                'rolling_metrics': rolling_metrics,
                'rolling_metrics_updated': now
            })
            
            logger.info(f"  Updated rolling metrics for {keyword}")


def main():
    """Main function to run interval metrics collection"""
    collector = YouTubeIntervalMetricsCollector()
    
    # Collect interval metrics
    results = collector.collect_all_keywords()
    
    # Calculate rolling metrics
    collector.calculate_rolling_metrics()
    
    # Save collection log
    log_data = {
        'type': 'youtube_interval_metrics',
        'timestamp': datetime.now(timezone.utc),
        'results': results
    }
    
    collector.db.collection('youtube_collection_logs').add(log_data)
    
    return results


if __name__ == "__main__":
    main()