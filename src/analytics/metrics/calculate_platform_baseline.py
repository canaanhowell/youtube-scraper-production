#!/usr/bin/env python3
"""
Calculate platform-wide baseline metrics for YouTube.
This calculates the average daily videos across all keywords to establish a baseline
for normalized velocity calculations.
"""

import os
import sys
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import numpy as np

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import environment loader and Firebase client
from src.utils.env_loader import load_env
load_env()

from src.utils.firebase_client import FirebaseClient

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PlatformBaselineCalculator:
    def __init__(self):
        self.fb_client = FirebaseClient()
        self.platform_name = "youtube"
        self.metric_type = "videos_per_day"
    
    def calculate_baseline(self, days: int = 30) -> Dict:
        """
        Calculate platform baseline for the specified number of days.
        
        Args:
            days: Number of days to calculate baseline for (default: 30)
            
        Returns:
            Dictionary containing baseline metrics
        """
        logger.info(f"Calculating {days}-day baseline for {self.platform_name}")
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get all active keywords
        keywords = self.fb_client.get_keywords()
        logger.info(f"Found {len(keywords)} active keywords")
        
        # Collect daily video counts
        daily_totals = {}
        keyword_count = 0
        
        for keyword_data in keywords:
            keyword_name = keyword_data.get('keyword')
            
            logger.info(f"Processing keyword: {keyword_name}")
            
            # Get daily video counts for this keyword
            daily_videos = self._get_daily_videos_for_keyword(
                keyword_name, start_date, end_date
            )
            
            # Add to daily totals
            for date_str, video_count in daily_videos.items():
                if date_str not in daily_totals:
                    daily_totals[date_str] = 0
                daily_totals[date_str] += video_count
            
            keyword_count += 1
        
        # Calculate statistics
        if daily_totals:
            daily_values = list(daily_totals.values())
            baseline = np.mean(daily_values)
            std_dev = np.std(daily_values)
            
            # Calculate percentiles
            p25 = np.percentile(daily_values, 25)
            p50 = np.percentile(daily_values, 50)  # median
            p75 = np.percentile(daily_values, 75)
            
            result = {
                'platform': self.platform_name,
                'metric_type': self.metric_type,
                f'baseline_{days}d': round(baseline, 2),
                f'std_dev_{days}d': round(std_dev, 2),
                f'median_{days}d': round(p50, 2),
                f'p25_{days}d': round(p25, 2),
                f'p75_{days}d': round(p75, 2),
                'last_updated': datetime.now(timezone.utc),
                'calculation_details': {
                    'total_items': sum(daily_values),
                    'days_calculated': len(daily_totals),
                    'keywords_included': keyword_count,
                    'missing_days': days - len(daily_totals),
                    'date_range': {
                        'start': start_date.isoformat(),
                        'end': end_date.isoformat()
                    }
                }
            }
            
            logger.info(f"Baseline calculation complete:")
            logger.info(f"  {days}-day average: {baseline:.2f} videos/day")
            logger.info(f"  Standard deviation: {std_dev:.2f}")
            logger.info(f"  Median: {p50:.2f}")
            logger.info(f"  Total videos: {sum(daily_values)}")
            
            return result
        else:
            logger.warning("No data found for baseline calculation")
            return None
    
    def _get_daily_videos_for_keyword(
        self, keyword: str, start_date: datetime, end_date: datetime
    ) -> Dict[str, int]:
        """
        Get daily video counts for a keyword within date range.
        
        Returns:
            Dictionary mapping date strings to video counts
        """
        daily_videos = {}
        
        try:
            # Check if keyword has daily_metrics subcollection
            keyword_ref = self.fb_client.db.collection('youtube_keywords').document(keyword)
            daily_metrics_ref = keyword_ref.collection('daily_metrics')
            
            # Try to get daily metrics first
            try:
                metrics = list(
                    daily_metrics_ref
                    .where('timestamp', '>=', start_date)
                    .where('timestamp', '<=', end_date)
                    .stream()
                )
                
                if metrics:
                    # Use daily metrics if available
                    for metric_doc in metrics:
                        data = metric_doc.to_dict()
                        date_str = metric_doc.id  # Document ID is the date
                        videos_found = data.get('videos_found_in_day', 0)
                        daily_videos[date_str] = videos_found
                    return daily_videos
            except:
                pass
            
            # Fallback: Count videos directly from video collection
            videos_ref = self.fb_client.db.collection('youtube_videos').document(keyword).collection('videos')
            
            # Get videos in date range
            videos = list(
                videos_ref
                .where('published_at', '>=', start_date)
                .where('published_at', '<=', end_date)
                .stream()
            )
            
            # Count videos by day
            for video_doc in videos:
                video_data = video_doc.to_dict()
                published_at = video_data.get('published_at')
                
                if published_at:
                    if isinstance(published_at, str):
                        published_at = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    
                    date_str = published_at.strftime('%Y-%m-%d')
                    daily_videos[date_str] = daily_videos.get(date_str, 0) + 1
                    
        except Exception as e:
            logger.error(f"Error getting videos for keyword {keyword}: {e}")
        
        return daily_videos
    
    def update_platform_metrics_collection(self):
        """
        Calculate baselines for multiple time periods and update platform_metrics collection.
        """
        logger.info("Updating platform_metrics collection")
        
        # Calculate baselines for different periods
        baseline_30d = self.calculate_baseline(days=30)
        baseline_7d = self.calculate_baseline(days=7)
        
        if not baseline_30d or not baseline_7d:
            logger.error("Failed to calculate baselines")
            return
        
        # Merge results
        platform_doc = {
            'platform': self.platform_name,
            'metric_type': self.metric_type,
            'baseline_30d': baseline_30d['baseline_30d'],
            'baseline_7d': baseline_7d['baseline_7d'],
            'std_dev_30d': baseline_30d['std_dev_30d'],
            'std_dev_7d': baseline_7d['std_dev_7d'],
            'median_30d': baseline_30d['median_30d'],
            'median_7d': baseline_7d['median_7d'],
            'last_updated': datetime.now(timezone.utc),
            'calculation_details': {
                '30d': baseline_30d['calculation_details'],
                '7d': baseline_7d['calculation_details']
            }
        }
        
        # Update or create document
        try:
            doc_ref = self.fb_client.db.collection('platform_metrics').document(self.platform_name)
            doc_ref.set(platform_doc)
            logger.info(f"Successfully updated platform_metrics for {self.platform_name}")
            
            # Log the update
            log_data = {
                'timestamp': datetime.now(timezone.utc),
                'script': 'calculate_platform_baseline.py',
                'platform': self.platform_name,
                'baseline_30d': platform_doc['baseline_30d'],
                'baseline_7d': platform_doc['baseline_7d'],
                'success': True
            }
            self.fb_client.db.collection('youtube_collection_logs').add(log_data)
            
        except Exception as e:
            logger.error(f"Failed to update platform_metrics: {e}")


def main():
    """Main execution function"""
    calculator = PlatformBaselineCalculator()
    
    # Update platform metrics collection
    calculator.update_platform_metrics_collection()
    
    # Also display current baseline
    baseline = calculator.calculate_baseline(days=30)
    if baseline:
        print("\nCurrent Platform Baseline:")
        print(f"  Platform: {baseline['platform']}")
        print(f"  30-day average: {baseline['baseline_30d']} videos/day")
        print(f"  Standard deviation: {baseline['std_dev_30d']}")
        print(f"  Keywords included: {baseline['calculation_details']['keywords_included']}")


if __name__ == "__main__":
    main()