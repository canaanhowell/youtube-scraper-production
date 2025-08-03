#!/usr/bin/env python3
"""
YouTube Category Metrics Aggregator
Aggregates YouTube video metrics by category with time-windowed views
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from typing import Dict, List, Any, Optional
import logging

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.utils.firebase_client_enhanced import FirebaseClient
from firebase_admin import firestore

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YouTubeCategoryMetricsAggregator:
    """Aggregates YouTube metrics by category with time windows"""
    
    def __init__(self):
        self.firebase_client = FirebaseClient()
        self.db = self.firebase_client.db
        
    def get_categories_and_keywords(self) -> Dict[str, List[Dict]]:
        """Get all categories and their associated keywords"""
        logger.info("Fetching categories and keywords...")
        
        categories = defaultdict(list)
        keywords_ref = self.db.collection('youtube_keywords')
        keywords_docs = keywords_ref.where('active', '==', True).stream()
        
        for doc in keywords_docs:
            doc_id = doc.id
            data = doc.to_dict()
            category = data.get('category', 'uncategorized')
            
            keyword_info = {
                'keyword': data.get('keyword') or data.get('name') or doc_id,
                'doc_id': doc_id,
                'data': data
            }
            categories[category].append(keyword_info)
            
        logger.info(f"Found {len(categories)} categories with keywords")
        for cat, keywords in categories.items():
            logger.info(f"  {cat}: {len(keywords)} keywords")
            
        return dict(categories)
    
    def calculate_daily_metrics(self, category: str, keywords: List[Dict], date: datetime) -> Dict[str, Any]:
        """Calculate daily metrics for a category"""
        date_str = date.strftime('%Y-%m-%d')
        logger.info(f"Calculating daily metrics for {category} on {date_str}")
        
        # Initialize metrics
        daily_metrics = {
            'date': date_str,
            'timestamp': date,
            'category': category,
            'keywords_count': len(keywords),
            'total_videos': 0,
            'total_views': 0,
            'videos_added_today': 0,
            'keyword_metrics': {},
            'top_videos': [],
            'avg_views_per_video': 0,
            'created_at': firestore.SERVER_TIMESTAMP
        }
        
        all_videos = []
        
        # Process each keyword
        for kw_info in keywords:
            keyword = kw_info['keyword']
            logger.info(f"  Processing keyword: {keyword}")
            
            # Get videos for this keyword
            videos_ref = self.db.collection('youtube_videos')\
                .document(keyword)\
                .collection('videos')
            
            # Get all videos (for total count and views)
            videos = list(videos_ref.stream())
            
            if not videos:
                logger.info(f"    No videos found for {keyword}")
                continue
                
            keyword_total_videos = len(videos)
            keyword_total_views = 0
            videos_today = 0
            
            # Process each video
            for video_doc in videos:
                video_data = video_doc.to_dict()
                
                # Add to total views
                # Check both 'views' and 'view_count' fields
                views = video_data.get('views') or video_data.get('view_count', 0)
                
                # Convert views to int if it's a string
                if isinstance(views, str):
                    # Handle "No views" case
                    if views.lower() == 'no views':
                        views = 0
                    else:
                        try:
                            # Remove commas and convert to int
                            views = int(views.replace(',', '').replace('views', '').strip())
                        except:
                            views = 0
                elif views is None:
                    views = 0
                    
                keyword_total_views += views
                
                # Check if video was added today
                collected_at = video_data.get('collected_at')
                if collected_at:
                    if hasattr(collected_at, 'timestamp'):
                        collected_date = datetime.fromtimestamp(
                            collected_at.timestamp(), 
                            tz=timezone.utc
                        ).date()
                        if collected_date == date.date():
                            videos_today += 1
                
                # Collect video info for top videos calculation
                all_videos.append({
                    'keyword': keyword,
                    'title': video_data.get('title', 'Unknown'),
                    'views': views,
                    'channel': video_data.get('channel') or video_data.get('channel_name', 'Unknown'),
                    'url': video_data.get('url', ''),
                    'video_id': video_doc.id
                })
            
            # Store keyword metrics
            daily_metrics['keyword_metrics'][keyword] = {
                'total_videos': keyword_total_videos,
                'total_views': keyword_total_views,
                'videos_added_today': videos_today,
                'avg_views': keyword_total_views / keyword_total_videos if keyword_total_videos > 0 else 0
            }
            
            # Update category totals
            daily_metrics['total_videos'] += keyword_total_videos
            daily_metrics['total_views'] += keyword_total_views
            daily_metrics['videos_added_today'] += videos_today
        
        # Calculate averages
        if daily_metrics['total_videos'] > 0:
            daily_metrics['avg_views_per_video'] = daily_metrics['total_views'] / daily_metrics['total_videos']
        
        # Get top 10 videos by views
        all_videos.sort(key=lambda x: x['views'], reverse=True)
        daily_metrics['top_videos'] = all_videos[:10]
        
        # Calculate velocity (videos per day) - will need historical data
        # For now, we'll use videos_added_today as velocity
        daily_metrics['velocity'] = daily_metrics['videos_added_today']
        
        return daily_metrics
    
    def calculate_time_window_metrics(self, category: str, window_days: int, 
                                    end_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Calculate metrics for a specific time window"""
        if end_date is None:
            end_date = datetime.now(timezone.utc)
            
        start_date = end_date - timedelta(days=window_days)
        window_name = f"{window_days}d"
        
        logger.info(f"Calculating {window_name} metrics for {category}")
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        
        # Get daily metrics for the time window
        daily_metrics_ref = self.db.collection('youtube_categories')\
            .document(category)\
            .collection('daily_metrics')\
            .where('date', '>=', start_date.strftime('%Y-%m-%d'))\
            .where('date', '<=', end_date.strftime('%Y-%m-%d'))\
            .order_by('date')\
            .stream()
        
        daily_metrics_list = list(daily_metrics_ref)
        
        if not daily_metrics_list:
            logger.warning(f"No daily metrics found for {category} in {window_name}")
            return None
        
        # Aggregate metrics
        window_metrics = {
            'window': window_name,
            'window_days': window_days,
            'start_date': start_date.strftime('%Y-%m-%d'),
            'end_date': end_date.strftime('%Y-%m-%d'),
            'category': category,
            'days_with_data': len(daily_metrics_list),
            'total_videos': 0,
            'total_views': 0,
            'videos_added_in_window': 0,
            'avg_daily_velocity': 0,
            'keyword_performance': defaultdict(lambda: {
                'total_videos': 0,
                'total_views': 0,
                'videos_added': 0
            }),
            'growth_rate': 0,
            'trend_direction': 'stable',
            'top_performing_keyword': None,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        # Process daily metrics
        first_day_videos = None
        last_day_videos = None
        
        for doc in daily_metrics_list:
            daily_data = doc.to_dict()
            
            # Update totals
            window_metrics['total_videos'] = daily_data.get('total_videos', 0)  # Latest count
            window_metrics['total_views'] = daily_data.get('total_views', 0)    # Latest count
            window_metrics['videos_added_in_window'] += daily_data.get('videos_added_today', 0)
            
            # Track first and last day for growth calculation
            if first_day_videos is None:
                first_day_videos = daily_data.get('total_videos', 0)
            last_day_videos = daily_data.get('total_videos', 0)
            
            # Aggregate keyword performance
            keyword_metrics = daily_data.get('keyword_metrics', {})
            for keyword, kw_data in keyword_metrics.items():
                window_metrics['keyword_performance'][keyword]['total_videos'] = kw_data.get('total_videos', 0)
                window_metrics['keyword_performance'][keyword]['total_views'] = kw_data.get('total_views', 0)
                window_metrics['keyword_performance'][keyword]['videos_added'] += kw_data.get('videos_added_today', 0)
        
        # Calculate derived metrics
        if window_metrics['days_with_data'] > 0:
            window_metrics['avg_daily_velocity'] = (
                window_metrics['videos_added_in_window'] / window_metrics['days_with_data']
            )
        
        # Calculate growth rate
        if first_day_videos and first_day_videos > 0:
            growth = (last_day_videos - first_day_videos) / first_day_videos
            window_metrics['growth_rate'] = growth
            
            # Determine trend
            if growth > 0.05:  # 5% growth
                window_metrics['trend_direction'] = 'up'
            elif growth < -0.05:  # 5% decline
                window_metrics['trend_direction'] = 'down'
            else:
                window_metrics['trend_direction'] = 'stable'
        
        # Find top performing keyword
        keyword_perf = dict(window_metrics['keyword_performance'])
        if keyword_perf:
            top_keyword = max(keyword_perf.items(), 
                            key=lambda x: x[1]['total_views'])
            window_metrics['top_performing_keyword'] = {
                'keyword': top_keyword[0],
                'metrics': top_keyword[1]
            }
        
        return window_metrics
    
    def update_category_metrics(self, category: str, keywords: List[Dict]):
        """Update all metrics for a category"""
        logger.info(f"\nUpdating metrics for category: {category}")
        
        # Calculate daily metrics for today
        today = datetime.now(timezone.utc)
        daily_metrics = self.calculate_daily_metrics(category, keywords, today)
        
        # Store daily metrics
        daily_doc_id = today.strftime('%Y-%m-%d')
        self.db.collection('youtube_categories')\
            .document(category)\
            .collection('daily_metrics')\
            .document(daily_doc_id)\
            .set(daily_metrics)
        
        logger.info(f"Stored daily metrics for {daily_doc_id}")
        
        # Calculate and store time windows
        time_windows = [7, 30, 90, 365]  # days
        
        for window_days in time_windows:
            window_metrics = self.calculate_time_window_metrics(category, window_days, today)
            
            if window_metrics:
                window_doc_id = f"{window_days}d"
                self.db.collection('youtube_categories')\
                    .document(category)\
                    .collection('time_windows')\
                    .document(window_doc_id)\
                    .set(window_metrics)
                
                logger.info(f"Stored {window_doc_id} window metrics")
        
        # Update main category document
        category_doc = {
            'category_name': category,
            'total_keywords': len(keywords),
            'active_keywords': [kw['keyword'] for kw in keywords],
            'last_daily_calculation': today,
            'last_updated': firestore.SERVER_TIMESTAMP,
            'latest_metrics': {
                'total_videos': daily_metrics['total_videos'],
                'total_views': daily_metrics['total_views'],
                'avg_views_per_video': daily_metrics['avg_views_per_video'],
                'daily_velocity': daily_metrics['velocity']
            }
        }
        
        self.db.collection('youtube_categories')\
            .document(category)\
            .set(category_doc, merge=True)
        
        logger.info(f"Updated main category document")
    
    def run_aggregation(self):
        """Run aggregation for all categories"""
        logger.info("Starting YouTube category metrics aggregation...")
        
        # Get all categories and keywords
        categories = self.get_categories_and_keywords()
        
        if not categories:
            logger.warning("No categories found")
            return
        
        # Process each category
        for category, keywords in categories.items():
            try:
                self.update_category_metrics(category, keywords)
                logger.info(f"✅ Successfully updated metrics for {category}")
            except Exception as e:
                logger.error(f"❌ Error updating metrics for {category}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info("\nAggregation complete!")


if __name__ == "__main__":
    aggregator = YouTubeCategoryMetricsAggregator()
    aggregator.run_aggregation()