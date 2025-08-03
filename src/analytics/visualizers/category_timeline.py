#!/usr/bin/env python3
"""
View YouTube Category Timeline Data
Shows daily snapshots for graphing timeline data
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
    return str(int(num))


def view_timeline_data(category: str = 'ai_media_generation', window: str = '7d'):
    """View timeline data for a specific category and time window"""
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    print(f"=" * 80)
    print(f"YOUTUBE CATEGORY TIMELINE - {category} ({window})")
    print(f"=" * 80)
    
    # Get snapshots for the specified window
    snapshots_ref = db.collection('youtube_categories')\
        .document(category)\
        .collection(f'daily_snapshots_{window}')\
        .order_by('date')
    
    snapshots = list(snapshots_ref.stream())
    
    if not snapshots:
        print(f"No snapshot data found for {category}/{window}")
        return
    
    print(f"\nFound {len(snapshots)} daily snapshots\n")
    
    # Display timeline data
    print(f"{'Date':<12} {'Total Videos':<15} {'Total Views':<15} {'Added':<10} {'Velocity':<10}")
    print("-" * 70)
    
    # Track trends
    prev_videos = 0
    prev_views = 0
    
    for snapshot_doc in snapshots:
        data = snapshot_doc.to_dict()
        date = data.get('date', 'Unknown')
        total_videos = data.get('total_videos', 0)
        total_views = data.get('total_views', 0)
        added = data.get('videos_added', 0)
        velocity = data.get('velocity', 0)
        
        # Calculate daily changes
        video_change = total_videos - prev_videos if prev_videos > 0 else 0
        view_change = total_views - prev_views if prev_views > 0 else 0
        
        # Format with trend indicators
        video_trend = f"(+{video_change})" if video_change > 0 else ""
        view_trend = f"(+{format_number(view_change)})" if view_change > 0 else ""
        
        print(f"{date:<12} {total_videos:<15} {format_number(total_views):<15} "
              f"{added:<10} {velocity:<10.2f}")
        
        # Update previous values
        prev_videos = total_videos
        prev_views = total_views
    
    # Show keyword breakdown for the latest snapshot
    print(f"\n{'='*70}")
    print("KEYWORD BREAKDOWN (Latest Snapshot)")
    print(f"{'='*70}\n")
    
    if snapshots:
        latest_data = snapshots[-1].to_dict()
        keywords_data = latest_data.get('keywords_data', {})
        
        print(f"{'Keyword':<20} {'Videos':<12} {'Views':<12} {'Avg Views':<12} {'Added Today':<12}")
        print("-" * 70)
        
        for keyword, metrics in keywords_data.items():
            videos = metrics.get('videos', 0)
            views = metrics.get('views', 0)
            avg_views = metrics.get('avg_views', 0)
            added = metrics.get('added_today', 0)
            
            print(f"{keyword:<20} {videos:<12} {format_number(views):<12} "
                  f"{format_number(avg_views):<12} {added:<12}")
    
    # Show mini chart
    print(f"\n{'='*70}")
    print("VIDEO GROWTH CHART (ASCII)")
    print(f"{'='*70}\n")
    
    if snapshots:
        # Get max video count for scaling
        max_videos = max(doc.to_dict().get('total_videos', 0) for doc in snapshots)
        
        if max_videos > 0:
            for snapshot_doc in snapshots[-10:]:  # Last 10 days
                data = snapshot_doc.to_dict()
                date = data.get('date', 'Unknown')[-5:]  # MM-DD
                videos = data.get('total_videos', 0)
                
                # Create bar
                bar_length = int((videos / max_videos) * 40)
                bar = "█" * bar_length
                
                print(f"{date} |{bar:<40} {videos}")


def main():
    """Main function to demonstrate timeline viewing"""
    # View different time windows
    windows = ['7d', '30d', '90d']
    
    for window in windows:
        view_timeline_data('ai_media_generation', window)
        print("\n" + "="*80 + "\n")
        
        if window != '90d':
            input("Press Enter to view next time window...")


if __name__ == "__main__":
    # You can run with specific parameters or use main() for demo
    import sys
    if len(sys.argv) > 2:
        view_timeline_data(sys.argv[1], sys.argv[2])
    else:
        view_timeline_data('ai_media_generation', '7d')