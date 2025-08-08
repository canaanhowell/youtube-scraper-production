#!/usr/bin/env python3
"""
Inspect the current YouTube categories structure to understand what needs to be migrated.
"""

import os
import sys
import json

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, parent_dir)
sys.path.insert(0, os.path.join(parent_dir, 'src'))

# Load environment variables
from utils.env_loader import load_env
load_env()

# Import Firebase client
from utils.firebase_client_enhanced import FirebaseClient

def inspect_youtube_categories_structure():
    """Inspect the current YouTube categories structure"""
    
    firebase = FirebaseClient()
    db = firebase.db
    
    print(f"\n🔍 INSPECTING YOUTUBE CATEGORIES STRUCTURE")
    print("=" * 80)
    
    # Get all YouTube categories
    categories_ref = db.collection('youtube_categories')
    categories = list(categories_ref.stream())
    
    print(f"Found {len(categories)} YouTube categories:")
    
    for category_doc in categories:
        category_id = category_doc.id
        category_data = category_doc.to_dict()
        
        print(f"\n📁 Category: {category_id}")
        print(f"   Structure: {category_data.get('structure_version', 'unknown')}")
        
        # Show main document size
        doc_size = len(json.dumps(category_data, default=str))
        print(f"   Size: ~{doc_size:,} bytes ({doc_size/1024:.1f}KB)")
        
        # Check for time windows in main document
        time_windows = ['7_days', '30_days', '90_days', 'all_time']
        for window in time_windows:
            if window in category_data:
                window_data = category_data[window]
                if isinstance(window_data, dict):
                    keyword_count = window_data.get('total_keywords', 0) if 'total_keywords' in window_data else len(window_data.get('keywords', []))
                    print(f"   {window}: {keyword_count} keywords (aggregated)")
                elif isinstance(window_data, list):
                    print(f"   {window}: {len(window_data)} keywords (array)")
                else:
                    print(f"   {window}: {type(window_data).__name__}")
        
        # Check for subcollections
        print(f"   Subcollections:")
        
        # Check for existing time_windows subcollection
        time_windows_ref = categories_ref.document(category_id).collection('time_windows')
        time_windows_docs = list(time_windows_ref.stream())
        
        if time_windows_docs:
            print(f"     time_windows: {len(time_windows_docs)} documents")
            for doc in time_windows_docs:
                doc_data = doc.to_dict()
                keyword_count = len(doc_data.get('keywords', []))
                print(f"       {doc.id}: {keyword_count} keywords")
        else:
            print(f"     time_windows: None")
        
        # Check for daily subcollections
        for window in time_windows:
            daily_ref = categories_ref.document(category_id).collection(f'{window}_daily')
            daily_docs = list(daily_ref.limit(1).stream())
            if daily_docs:
                print(f"     {window}_daily: exists (sample doc found)")
            else:
                print(f"     {window}_daily: None")
    
    print(f"\n💡 ANALYSIS:")
    print(f"   Current structure appears to be using:")
    print(f"   - Main documents with time window data")
    print(f"   - Daily subcollections for historical data")
    print(f"   - Need to create time_windows subcollections like Reddit")
    
    print(f"\n🎯 MIGRATION NEEDED:")
    print(f"   1. Create time_windows subcollections with top 5 keywords per window")
    print(f"   2. Streamline main documents to only essential metrics:")
    print(f"      - velocity, acceleration, video_count, avg_videos_per_day") 
    print(f"   3. Add total_keywords field at document root level")
    print(f"   4. Update daily metrics calculator to maintain both structures")


if __name__ == '__main__':
    inspect_youtube_categories_structure()