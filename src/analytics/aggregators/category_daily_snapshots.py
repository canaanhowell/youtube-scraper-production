#!/usr/bin/env python3
"""
[DEPRECATED] Use youtube_daily_metrics_unified.py instead.

YouTube Category Daily Snapshots Generator
Creates subcollections with daily data points for each time window
Structure:
    youtube_categories/{category}/daily_snapshots_24h/{date}
    youtube_categories/{category}/daily_snapshots_7d/{date}
    youtube_categories/{category}/daily_snapshots_30d/{date}

DEPRECATED: This script has been replaced by youtube_daily_metrics_unified.py which
handles both keyword daily metrics and category snapshots in a single unified process.
"""
import os
import sys
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any
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


class YouTubeDailySnapshotGenerator:
    """Generates daily snapshot data for YouTube categories"""
    
    def __init__(self):
        self.firebase_client = FirebaseClient()
        self.db = self.firebase_client.db
        
    def get_videos_by_date(self, keyword: str, target_date: datetime) -> Dict[str, Any]:
        """Get video metrics for a specific date"""
        # For this implementation, we'll count videos collected up to the target date
        # In a real scenario, you'd track when videos were published or collected
        
        videos_ref = self.db.collection('youtube_videos')\
            .document(keyword)\
            .collection('videos')
        
        all_videos = list(videos_ref.stream())
        
        # Count videos and views up to target date
        video_count = 0
        total_views = 0
        videos_on_date = 0  # Videos added on this specific date
        
        for video_doc in all_videos:
            video_data = video_doc.to_dict()
            
            # Parse collection date
            collected_at = video_data.get('collected_at')
            if collected_at:
                if hasattr(collected_at, 'timestamp'):
                    collected_date = datetime.fromtimestamp(collected_at.timestamp()).date()
                elif isinstance(collected_at, str):
                    try:
                        collected_date = datetime.fromisoformat(
                            collected_at.replace('Z', '+00:00')
                        ).date()
                    except:
                        # If we can't parse, assume it's old
                        collected_date = datetime(2020, 1, 1).date()
                else:
                    collected_date = datetime(2020, 1, 1).date()
                
                # Count if collected before or on target date
                if collected_date <= target_date.date():
                    video_count += 1
                    
                    # Count views
                    views = video_data.get('views') or video_data.get('view_count', 0)
                    if isinstance(views, str):
                        if views.lower() == 'no views':
                            views = 0
                        else:
                            try:
                                views = int(views.replace(',', '').replace('views', '').strip())
                            except:
                                views = 0
                    total_views += views
                    
                    # Count if added on this specific date
                    if collected_date == target_date.date():
                        videos_on_date += 1
        
        return {
            'cumulative_videos': video_count,
            'cumulative_views': total_views,
            'videos_added_today': videos_on_date,
            'avg_views': round(total_views / video_count, 2) if video_count > 0 else 0
        }
    
    def generate_daily_snapshots(self, category: str, keywords: List[Dict[str, Any]]):
        """Generate daily snapshots for all time windows"""
        logger.info(f"Generating daily snapshots for {category}")
        
        # Define time windows and their corresponding days
        time_windows = {
            '7d': 7,
            '30d': 30,
            '90d': 90
        }
        
        now = datetime.now()
        
        for window_name, days in time_windows.items():
            logger.info(f"  Processing {window_name} window ({days} days)")
            
            # Create subcollection reference
            snapshots_ref = self.db.collection('youtube_categories')\
                .document(category)\
                .collection(f'daily_snapshots_{window_name}')
            
            # Generate data for each day in the window
            for day_offset in range(days):
                target_date = now - timedelta(days=day_offset)
                date_str = target_date.strftime('%Y-%m-%d')
                
                # Aggregate data for all keywords on this date
                daily_data = {
                    'date': date_str,
                    'timestamp': target_date,
                    'window': window_name,
                    'category': category,
                    'total_videos': 0,
                    'total_views': 0,
                    'videos_added': 0,
                    'keywords_data': {}
                }
                
                # Process each keyword
                for kw_info in keywords:
                    keyword = kw_info['keyword']
                    
                    # Get metrics for this date
                    metrics = self.get_videos_by_date(keyword, target_date)
                    
                    # Add to totals
                    daily_data['total_videos'] += metrics['cumulative_videos']
                    daily_data['total_views'] += metrics['cumulative_views']
                    daily_data['videos_added'] += metrics['videos_added_today']
                    
                    # Store keyword-specific data
                    daily_data['keywords_data'][keyword] = {
                        'videos': metrics['cumulative_videos'],
                        'views': metrics['cumulative_views'],
                        'added_today': metrics['videos_added_today'],
                        'avg_views': metrics['avg_views']
                    }
                
                # Calculate daily velocity (videos added per day over the window)
                if day_offset == 0:
                    # For today, use videos added today
                    daily_data['velocity'] = daily_data['videos_added']
                else:
                    # For historical days, calculate average over the period
                    daily_data['velocity'] = round(daily_data['total_videos'] / (day_offset + 1), 2)
                
                # Store the snapshot
                doc_ref = snapshots_ref.document(date_str)
                doc_ref.set(daily_data)
                
                if day_offset % 5 == 0:  # Log progress every 5 days
                    logger.info(f"    Processed {date_str}: {daily_data['total_videos']} videos, "
                              f"{daily_data['total_views']} views")
            
            logger.info(f"  ✅ Completed {window_name} snapshots")
    
    def run(self):
        """Run the snapshot generation for all categories"""
        logger.info("Starting daily snapshot generation...")
        
        # Get all keywords grouped by category
        keywords_ref = self.db.collection('youtube_keywords')
        keywords_docs = keywords_ref.where('active', '==', True).stream()
        
        # Group by category
        categories = defaultdict(list)
        
        for doc in keywords_docs:
            doc_id = doc.id
            data = doc.to_dict()
            category = data.get('category', 'uncategorized')
            
            keyword_info = {
                'keyword': data.get('keyword') or data.get('name') or doc_id,
                'doc_id': doc_id
            }
            categories[category].append(keyword_info)
        
        logger.info(f"Found {len(categories)} categories with active keywords")
        
        # Process each category
        for category, keywords in categories.items():
            try:
                self.generate_daily_snapshots(category, keywords)
                logger.info(f"✅ Completed snapshots for {category}")
            except Exception as e:
                logger.error(f"❌ Error processing {category}: {e}")
                import traceback
                traceback.print_exc()
        
        logger.info("\nDaily snapshot generation complete!")


if __name__ == "__main__":
    generator = YouTubeDailySnapshotGenerator()
    generator.run()