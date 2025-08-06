#!/usr/bin/env python3
"""Verify that category snapshots are sorted by video_count"""

import os
import sys

# Add project path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from src.utils.firebase_client import FirebaseClient

def verify_sorting():
    # Initialize Firebase client
    fc = FirebaseClient()
    db = fc.db
    
    # Check ai_media_generation category for Aug 5 data
    category = 'ai_media_generation'
    date = '2025-08-05'
    
    print(f"Verifying sorting for {category} on {date}")
    print("=" * 80)
    
    # Check the 30-day snapshot
    doc_ref = (db.collection('youtube_categories')
              .document(category)
              .collection('daily_snapshots_30d')
              .document(date))
    
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        keywords_data = data.get('keywords', [])
        
        # Check if it's the old format (dict) or new format (array)
        if isinstance(keywords_data, dict):
            print("WARNING: Keywords stored in old dictionary format")
            # Convert dict to list for display
            keywords_list = [(k, v) for k, v in keywords_data.items()]
        else:
            # New array format
            keywords_list = [(kw.get('keyword', ''), kw) for kw in keywords_data]
        
        print(f"Found {len(keywords_list)} keywords in {category}/daily_snapshots_30d/{date}:")
        print("\nKeywords sorted by video_count:")
        
        # Print keywords in order they appear
        for i, (keyword, kw_data) in enumerate(keywords_list):
            video_count = kw_data.get('video_count', 0)
            new_videos = kw_data.get('new_videos_in_day', 0)
            velocity = kw_data.get('velocity', 0)
            print(f"{i+1:2d}. {keyword:<20} | Videos: {video_count:5d} | New: {new_videos:4d} | Velocity: {velocity:6.1f}")
        
        # Verify if properly sorted
        video_counts = [kw[1].get('video_count', 0) for kw in keywords_list]
        is_sorted = all(video_counts[i] >= video_counts[i+1] for i in range(len(video_counts)-1))
        
        print(f"\n✅ Sorting verification: {'PASSED - Keywords are sorted by video_count descending' if is_sorted else 'FAILED - Keywords are NOT properly sorted'}")
        
        # Also check all_youtube aggregate
        print("\n" + "=" * 80)
        print("Checking all_youtube aggregate...")
        
        all_doc_ref = (db.collection('youtube_categories')
                      .document('all_youtube')
                      .collection('daily_snapshots_30d')
                      .document(date))
        
        all_doc = all_doc_ref.get()
        
        if all_doc.exists:
            all_data = all_doc.to_dict()
            all_keywords = all_data.get('keywords', [])
            
            # Check format
            if isinstance(all_keywords, dict):
                print("WARNING: all_youtube keywords in old dictionary format")
                keywords_list = list(all_keywords.items())
            else:
                keywords_list = [(kw.get('keyword', ''), kw) for kw in all_keywords]
            
            print(f"\nFound {len(keywords_list)} keywords in all_youtube aggregate")
            print("Top 10 keywords by video_count:")
            
            # Show top 10
            for i, (keyword, kw_data) in enumerate(keywords_list[:10]):
                video_count = kw_data.get('video_count', 0)
                print(f"{i+1:2d}. {keyword:<20} | Videos: {video_count:5d}")
    else:
        print(f"No snapshot found for {date}")

if __name__ == "__main__":
    verify_sorting()