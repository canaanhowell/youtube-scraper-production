#!/usr/bin/env python3
"""
View YouTube category daily snapshots for timeline graphing.
Shows daily aggregated data across different time windows.
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from tabulate import tabulate
import json

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


def view_category_snapshots(category_filter=None, time_window='7d', show_keywords=False):
    """View daily snapshots for YouTube categories"""
    
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    print("=" * 100)
    print(f"YOUTUBE CATEGORY DAILY SNAPSHOTS - {time_window.upper()}")
    print("=" * 100)
    
    # Map time window to subcollection name
    window_map = {
        '7d': 'daily_snapshots_7d',
        '30d': 'daily_snapshots_30d',
        '90d': 'daily_snapshots_90d'
    }
    
    if time_window not in window_map:
        print(f"Invalid time window. Choose from: {', '.join(window_map.keys())}")
        return
    
    subcollection_name = window_map[time_window]
    
    # Get categories
    categories_ref = db.collection('youtube_categories')
    if category_filter:
        categories = [categories_ref.document(category_filter).get()]
    else:
        categories = list(categories_ref.stream())
    
    for cat_doc in categories:
        if not cat_doc.exists:
            continue
            
        category = cat_doc.id
        
        print(f"\n📊 CATEGORY: {category}")
        print("-" * 80)
        
        # Get daily snapshots for this time window
        snapshots_ref = (db.collection('youtube_categories')
                        .document(category)
                        .collection(subcollection_name)
                        .order_by('date', direction='DESCENDING')
                        .limit(10))  # Show last 10 days
        
        snapshots = list(snapshots_ref.stream())
        
        if not snapshots:
            print(f"No snapshots found for {time_window}")
            continue
        
        # Prepare table data
        table_data = []
        
        for snap_doc in reversed(snapshots):  # Show chronologically
            snap_data = snap_doc.to_dict()
            date = snap_data.get('date', snap_doc.id)
            
            # Calculate totals across all keywords
            total_videos = 0
            total_views = 0
            total_velocity = 0
            keyword_count = 0
            
            for keyword, metrics in snap_data.items():
                if isinstance(metrics, dict) and 'post_count' in metrics:
                    keyword_count += 1
                    total_videos += metrics.get('post_count', 0)
                    total_views += metrics.get('total_upvotes', 0)
                    total_velocity += metrics.get('velocity', 0)
            
            avg_velocity = total_velocity / keyword_count if keyword_count > 0 else 0
            
            table_data.append([
                date,
                keyword_count,
                total_videos,
                format_number(total_views),
                f"{avg_velocity:.1f}",
                format_number(total_views // total_videos) if total_videos > 0 else "0"
            ])
        
        headers = ["Date", "Keywords", "Videos", "Total Views", "Avg Velocity", "Avg Views/Video"]
        print(tabulate(table_data, headers=headers, tablefmt="simple"))
        
        # Show keyword breakdown for latest snapshot if requested
        if show_keywords and snapshots:
            latest_snap = snapshots[0].to_dict()
            print(f"\n  Keyword Breakdown for {latest_snap.get('date', snapshots[0].id)}:")
            
            keyword_data = []
            for keyword, metrics in latest_snap.items():
                if isinstance(metrics, dict) and 'post_count' in metrics:
                    keyword_data.append([
                        keyword,
                        metrics.get('post_count', 0),
                        format_number(metrics.get('total_upvotes', 0)),
                        f"{metrics.get('velocity', 0):.1f}",
                        format_number(metrics.get('avg_upvotes', 0))
                    ])
            
            keyword_data.sort(key=lambda x: x[1], reverse=True)  # Sort by video count
            headers = ["Keyword", "Videos", "Views", "Velocity", "Avg Views"]
            print(tabulate(keyword_data, headers=headers, tablefmt="simple", tablealign="right"))
    
    # Show time window comparison
    if not category_filter:
        print("\n\nTIME WINDOW COMPARISON")
        print("-" * 80)
        
        comp_data = []
        
        for window, subcoll in window_map.items():
            total_docs = 0
            categories_with_data = 0
            
            for cat_doc in categories:
                if not cat_doc.exists:
                    continue
                    
                # Check if this category has data in this time window
                snapshots = (db.collection('youtube_categories')
                           .document(cat_doc.id)
                           .collection(subcoll)
                           .limit(1)
                           .get())
                
                if snapshots:
                    categories_with_data += 1
                    # Count total documents
                    count = len(list(db.collection('youtube_categories')
                                   .document(cat_doc.id)
                                   .collection(subcoll)
                                   .stream()))
                    total_docs += count
            
            comp_data.append([
                window,
                categories_with_data,
                total_docs
            ])
        
        headers = ["Time Window", "Categories", "Total Snapshots"]
        print(tabulate(comp_data, headers=headers, tablefmt="simple"))


def export_timeline_data(category, time_window='30d', output_file=None):
    """Export timeline data for graphing"""
    
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    window_map = {
        '7d': 'daily_snapshots_7d',
        '30d': 'daily_snapshots_30d',
        '90d': 'daily_snapshots_90d'
    }
    
    subcollection_name = window_map.get(time_window)
    if not subcollection_name:
        print(f"Invalid time window: {time_window}")
        return
    
    # Get snapshots
    snapshots_ref = (db.collection('youtube_categories')
                    .document(category)
                    .collection(subcollection_name)
                    .order_by('date'))
    
    timeline_data = {
        'category': category,
        'time_window': time_window,
        'data': []
    }
    
    for snap_doc in snapshots_ref.stream():
        snap_data = snap_doc.to_dict()
        date = snap_data.get('date', snap_doc.id)
        
        # Calculate totals
        total_videos = 0
        total_views = 0
        
        for keyword, metrics in snap_data.items():
            if isinstance(metrics, dict) and 'post_count' in metrics:
                total_videos += metrics.get('post_count', 0)
                total_views += metrics.get('total_upvotes', 0)
        
        timeline_data['data'].append({
            'date': date,
            'total_videos': total_videos,
            'total_views': total_views
        })
    
    # Output
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(timeline_data, f, indent=2)
        print(f"Timeline data exported to: {output_file}")
    else:
        print(json.dumps(timeline_data, indent=2))


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='View YouTube category daily snapshots')
    parser.add_argument('--category', type=str, help='Filter by specific category')
    parser.add_argument('--window', type=str, default='7d', 
                        choices=['7d', '30d', '90d'],
                        help='Time window to view')
    parser.add_argument('--keywords', action='store_true', 
                        help='Show keyword breakdown')
    parser.add_argument('--export', type=str, help='Export timeline data for a category')
    parser.add_argument('--output', type=str, help='Output file for export')
    
    args = parser.parse_args()
    
    if args.export:
        export_timeline_data(args.export, args.window, args.output)
    else:
        view_category_snapshots(args.category, args.window, args.keywords)