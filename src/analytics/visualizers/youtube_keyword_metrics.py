#!/usr/bin/env python3
"""
View YouTube keyword metrics including interval and daily metrics.
Shows current status, velocity, acceleration, and historical data.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from tabulate import tabulate

# Add project path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))

# Import Firebase client
from src.utils.firebase_client_enhanced import FirebaseClient


def format_number(num):
    """Format large numbers with K/M/B suffixes"""
    if num >= 1_000_000_000:
        return f"{num/1_000_000_000:.1f}B"
    elif num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def view_keyword_metrics(keyword_filter=None, show_history=False):
    """View metrics for YouTube keywords"""
    
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    print("=" * 100)
    print("YOUTUBE KEYWORD METRICS")
    print("=" * 100)
    
    # Get keywords
    keywords_ref = db.collection('youtube_keywords')
    if keyword_filter:
        keywords_ref = keywords_ref.where('keyword', '==', keyword_filter)
    else:
        keywords_ref = keywords_ref.where('active', '==', True)
    
    keywords = list(keywords_ref.stream())
    
    if not keywords:
        print("No keywords found")
        return
    
    # Prepare table data
    table_data = []
    
    for keyword_doc in keywords:
        keyword_data = keyword_doc.to_dict()
        keyword = keyword_data.get('keyword', keyword_data.get('name', keyword_doc.id))
        category = keyword_data.get('category', 'uncategorized')
        
        # Get current metrics
        current = keyword_data.get('current_metrics', {})
        video_count = current.get('video_count', 0)
        views_count = current.get('views_count', 0)
        velocity = current.get('velocity', 0)
        acceleration = current.get('acceleration', 0)
        
        # Get rolling metrics
        rolling = keyword_data.get('rolling_metrics', {})
        hourly_avg = rolling.get('1_hour', {}).get('avg_velocity', 0)
        daily_avg = rolling.get('24_hours', {}).get('avg_velocity', 0)
        
        # Get historical peaks
        peaks = keyword_data.get('historical_peaks', {})
        max_velocity = peaks.get('max_velocity', 0)
        
        table_data.append([
            keyword,
            category,
            video_count,
            format_number(views_count),
            f"{velocity:.1f}",
            f"{acceleration:.2f}",
            f"{hourly_avg:.1f}",
            f"{daily_avg:.1f}",
            f"{max_velocity:.1f}"
        ])
    
    # Print summary table
    headers = ["Keyword", "Category", "Videos", "Views", "Velocity", "Accel", "1h Avg", "24h Avg", "Peak Vel"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    # Show detailed history if requested
    if show_history and keyword_filter:
        print(f"\n\nDETAILED HISTORY FOR: {keyword_filter}")
        print("-" * 100)
        
        keyword_id = keywords[0].id
        
        # Get recent interval metrics
        print("\nRECENT INTERVAL METRICS (Last 10):")
        interval_ref = (db.collection('youtube_keywords')
                       .document(keyword_id)
                       .collection('interval_metrics')
                       .order_by('timestamp', direction='DESCENDING')
                       .limit(10))
        
        interval_data = []
        for doc in interval_ref.stream():
            metric = doc.to_dict()
            timestamp = metric.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            
            interval_data.append([
                timestamp.strftime('%Y-%m-%d %H:%M'),
                metric.get('video_count', 0),
                format_number(metric.get('views_count', 0)),
                metric.get('videos_found_in_search', 0),
                f"{metric.get('velocity', 0):.2f}",
                f"{metric.get('acceleration', 0):.3f}"
            ])
        
        headers = ["Timestamp", "Videos", "Views", "New", "Velocity", "Acceleration"]
        print(tabulate(interval_data, headers=headers, tablefmt="simple"))
        
        # Get recent daily metrics
        print("\n\nRECENT DAILY METRICS (Last 7 days):")
        daily_ref = (db.collection('youtube_keywords')
                    .document(keyword_id)
                    .collection('daily_metrics')
                    .order_by('date', direction='DESCENDING')
                    .limit(7))
        
        daily_data = []
        for doc in daily_ref.stream():
            metric = doc.to_dict()
            
            daily_data.append([
                metric.get('date'),
                metric.get('video_count', 0),
                format_number(metric.get('views_count', 0)),
                metric.get('videos_found_in_day', 0),
                f"{metric.get('velocity', 0)}",
                f"{metric.get('acceleration', 0)}"
            ])
        
        headers = ["Date", "Videos", "Views", "New/Day", "Velocity", "Acceleration"]
        print(tabulate(daily_data, headers=headers, tablefmt="simple"))
    
    # Show category summary
    print("\n\nCATEGORY SUMMARY:")
    print("-" * 50)
    
    category_counts = {}
    category_videos = {}
    category_views = {}
    
    for keyword_doc in keywords:
        keyword_data = keyword_doc.to_dict()
        category = keyword_data.get('category', 'uncategorized')
        current = keyword_data.get('current_metrics', {})
        
        category_counts[category] = category_counts.get(category, 0) + 1
        category_videos[category] = category_videos.get(category, 0) + current.get('video_count', 0)
        category_views[category] = category_views.get(category, 0) + current.get('views_count', 0)
    
    cat_data = []
    for category in sorted(category_counts.keys()):
        cat_data.append([
            category,
            category_counts[category],
            category_videos[category],
            format_number(category_views[category])
        ])
    
    headers = ["Category", "Keywords", "Total Videos", "Total Views"]
    print(tabulate(cat_data, headers=headers, tablefmt="simple"))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View YouTube keyword metrics')
    parser.add_argument('--keyword', type=str, help='Filter by specific keyword')
    parser.add_argument('--history', action='store_true', help='Show detailed history')
    
    args = parser.parse_args()
    
    view_keyword_metrics(args.keyword, args.history)