#!/usr/bin/env python3
"""
View YouTube Categories with Time Windows
Displays the aggregated metrics in the reddit_categories style structure
"""
import os
import sys
import json

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from src.utils.firebase_client_enhanced import FirebaseClient


def format_number(num):
    """Format large numbers with K/M suffixes"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return str(num)


def view_categories():
    """View YouTube categories with time window structure"""
    firebase_client = FirebaseClient()
    db = firebase_client.db
    
    print("=" * 80)
    print("YOUTUBE CATEGORIES - TIME WINDOW VIEW")
    print("=" * 80)
    
    # Get all categories
    categories_ref = db.collection('youtube_categories')
    categories = list(categories_ref.stream())
    
    for cat_doc in categories:
        category = cat_doc.id
        cat_data = cat_doc.to_dict()
        
        # Skip categories without time window data
        if '24_hours' not in cat_data:
            continue
            
        print(f"\n📊 CATEGORY: {category}")
        print("-" * 60)
        
        # Display each time window
        time_windows = ['90_days', '7_days', '30_days', 'all_time']
        
        for window in time_windows:
            if window not in cat_data:
                continue
                
            window_data = cat_data[window]
            print(f"\n  ⏱️  {window.replace('_', ' ').title()}:")
            
            # Calculate totals for the window
            total_videos = 0
            total_views = 0
            total_velocity = 0
            keyword_count = 0
            
            # Display each keyword's metrics
            for keyword, metrics in window_data.items():
                if isinstance(metrics, dict):
                    keyword_count += 1
                    videos = metrics.get('post_count', 0)
                    views = metrics.get('total_upvotes', 0)
                    velocity = metrics.get('velocity', 0)
                    
                    total_videos += videos
                    total_views += views
                    total_velocity += velocity
                    
                    print(f"    • {keyword}:")
                    print(f"      - Videos: {videos}")
                    print(f"      - Views: {format_number(views)}")
                    print(f"      - Avg Views: {format_number(int(metrics.get('avg_upvotes', 0)))}")
                    print(f"      - Velocity: {velocity} videos/day")
            
            # Display window totals
            if keyword_count > 0:
                print(f"\n    📈 Window Summary:")
                print(f"      - Keywords: {keyword_count}")
                print(f"      - Total Videos: {total_videos}")
                print(f"      - Total Views: {format_number(total_views)}")
                print(f"      - Avg Velocity: {total_velocity/keyword_count:.2f} videos/day")
        
        print("\n" + "=" * 80)
    
    # Also show a compact JSON view for one category
    print("\n📋 JSON Structure Example (ai_media_generation, 90_days only):")
    print("-" * 60)
    
    media_gen_ref = db.collection('youtube_categories').document('ai_media_generation')
    media_gen_doc = media_gen_ref.get()
    
    if media_gen_doc.exists:
        data = media_gen_doc.to_dict()
        if '90_days' in data:
            # Pretty print just the 90_days data
            print(json.dumps({'90_days': data['90_days']}, indent=2))


if __name__ == "__main__":
    view_categories()