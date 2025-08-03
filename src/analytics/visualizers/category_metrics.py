#!/usr/bin/env python3
"""
View YouTube Category Metrics
Display aggregated metrics for YouTube categories with time windows
"""
import os
import sys
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.utils.firebase_client_enhanced import FirebaseClient


def format_number(num):
    """Format large numbers with K/M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def view_category_metrics():
    """View aggregated metrics for YouTube categories"""
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    print("=" * 80)
    print("YOUTUBE CATEGORY METRICS VIEWER")
    print("=" * 80)
    
    # Get all categories
    categories_ref = db.collection('youtube_categories')
    categories = list(categories_ref.stream())
    
    if not categories:
        print("No categories found in youtube_categories collection")
        return
    
    for cat_doc in categories:
        category = cat_doc.id
        cat_data = cat_doc.to_dict()
        
        print(f"\n📊 CATEGORY: {category}")
        print("-" * 60)
        
        # Display main category info
        print(f"Total Keywords: {cat_data.get('total_keywords', 0)}")
        print(f"Active Keywords: {', '.join(cat_data.get('active_keywords', []))}")
        
        latest = cat_data.get('latest_metrics', {})
        if latest:
            print(f"\nLatest Metrics:")
            print(f"  - Total Videos: {format_number(latest.get('total_videos', 0))}")
            print(f"  - Total Views: {format_number(latest.get('total_views', 0))}")
            print(f"  - Avg Views/Video: {format_number(int(latest.get('avg_views_per_video', 0)))}")
            print(f"  - Daily Velocity: {latest.get('daily_velocity', 0)} videos/day")
        
        # Get today's daily metrics
        today = datetime.now().strftime('%Y-%m-%d')
        daily_ref = db.collection('youtube_categories')\
            .document(category)\
            .collection('daily_metrics')\
            .document(today)
        
        daily_doc = daily_ref.get()
        if daily_doc.exists:
            daily_data = daily_doc.to_dict()
            print(f"\n📅 Today's Metrics ({today}):")
            print(f"  - Videos Added Today: {daily_data.get('videos_added_today', 0)}")
            
            # Show keyword breakdown
            keyword_metrics = daily_data.get('keyword_metrics', {})
            if keyword_metrics:
                print("\n  Keyword Performance:")
                for kw, metrics in keyword_metrics.items():
                    print(f"    • {kw}:")
                    print(f"      - Videos: {format_number(metrics.get('total_videos', 0))}")
                    print(f"      - Views: {format_number(metrics.get('total_views', 0))}")
                    print(f"      - Added Today: {metrics.get('videos_added_today', 0)}")
        
        # Display time windows
        print(f"\n📈 Time Window Metrics:")
        time_windows = ['7d', '30d', '90d', '365d']
        
        for window in time_windows:
            window_ref = db.collection('youtube_categories')\
                .document(category)\
                .collection('time_windows')\
                .document(window)
            
            window_doc = window_ref.get()
            if window_doc.exists:
                window_data = window_doc.to_dict()
                print(f"\n  {window} Window:")
                print(f"    - Date Range: {window_data.get('start_date')} to {window_data.get('end_date')}")
                print(f"    - Total Videos: {format_number(window_data.get('total_videos', 0))}")
                print(f"    - Videos Added: {window_data.get('videos_added_in_window', 0)}")
                print(f"    - Avg Daily Velocity: {window_data.get('avg_daily_velocity', 0):.1f} videos/day")
                print(f"    - Growth Rate: {window_data.get('growth_rate', 0)*100:.1f}%")
                print(f"    - Trend: {window_data.get('trend_direction', 'unknown').upper()}")
                
                # Show top performing keyword
                top_kw = window_data.get('top_performing_keyword')
                if top_kw:
                    print(f"    - Top Keyword: {top_kw['keyword']} ({format_number(top_kw['metrics']['total_views'])} views)")
        
        print("\n" + "=" * 80)


if __name__ == "__main__":
    view_category_metrics()