#!/usr/bin/env python3
"""
Restore ghost keywords in youtube_keywords collection.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from src.utils.env_loader import load_env
load_env()

from src.utils.firebase_client import FirebaseClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_and_restore_youtube_keywords():
    """Check for ghost documents in youtube_keywords and restore them."""
    
    firebase_client = FirebaseClient()
    
    # First, check what keywords exist
    print("\n" + "="*80)
    print("CHECKING YOUTUBE_KEYWORDS COLLECTION")
    print("="*80)
    
    existing_keywords = []
    all_docs = firebase_client.db.collection('youtube_keywords').stream()
    
    for doc in all_docs:
        data = doc.to_dict()
        keyword = data.get('keyword', doc.id)
        active = data.get('active', False)
        existing_keywords.append(keyword)
        
    print(f"Found {len(existing_keywords)} keywords in youtube_keywords")
    print(f"Keywords: {', '.join(sorted(existing_keywords))}")
    
    # Check specifically for claude and dalle
    keywords_to_check = ["claude", "dalle"]
    ghost_keywords = []
    
    print("\n" + "="*80)
    print("CHECKING FOR GHOST DOCUMENTS")
    print("="*80)
    
    for keyword in keywords_to_check:
        print(f"\n[{keyword}]")
        
        doc_ref = firebase_client.db.collection('youtube_keywords').document(keyword)
        doc = doc_ref.get()
        
        if doc.exists:
            print(f"  ✓ Document exists with data")
        else:
            print(f"  ✗ Document does not exist (no data)")
            
            # Check for subcollections
            has_subcollections = False
            
            # Check collection_logs
            try:
                logs = doc_ref.collection('collection_logs').limit(1).stream()
                if sum(1 for _ in logs) > 0:
                    print(f"    → Found 'collection_logs' subcollection!")
                    has_subcollections = True
            except Exception:
                pass
            
            # Check other potential subcollections
            for subcoll in ['interval_metrics', 'daily_metrics']:
                try:
                    docs = doc_ref.collection(subcoll).limit(1).stream()
                    if sum(1 for _ in docs) > 0:
                        print(f"    → Found '{subcoll}' subcollection!")
                        has_subcollections = True
                except Exception:
                    pass
            
            if has_subcollections:
                ghost_keywords.append(keyword)
    
    # Restore ghost keywords
    if ghost_keywords:
        print("\n" + "="*80)
        print("RESTORING GHOST KEYWORDS")
        print("="*80)
        
        keywords_to_restore = []
        
        if "claude" in ghost_keywords:
            keywords_to_restore.append({
                "keyword": "claude",
                "category": "ai_chatbots",
                "active": True
            })
        
        if "dalle" in ghost_keywords:
            keywords_to_restore.append({
                "keyword": "dalle",
                "category": "ai_media_generation",
                "active": True
            })
        
        restored_count = 0
        
        for kw_data in keywords_to_restore:
            keyword = kw_data["keyword"]
            print(f"\n[{keyword}]")
            
            doc_ref = firebase_client.db.collection('youtube_keywords').document(keyword)
            
            # Create the parent document
            new_doc = {
                "keyword": keyword,
                "category": kw_data["category"],
                "active": kw_data["active"],
                "created_at": datetime.now(),
                "last_collected": None,
                "videos_collected": 0
            }
            
            try:
                doc_ref.set(new_doc)
                print(f"  ✓ Successfully restored")
                print(f"    Category: {kw_data['category']}")
                print(f"    Active: {kw_data['active']}")
                restored_count += 1
            except Exception as e:
                print(f"  ✗ Failed to restore: {e}")
        
        # Verify restoration
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)
        
        all_docs = firebase_client.db.collection('youtube_keywords').stream()
        all_keywords = []
        active_keywords = []
        
        for doc in all_docs:
            data = doc.to_dict()
            keyword = data.get('keyword', doc.id)
            all_keywords.append(keyword)
            if data.get('active', False):
                active_keywords.append(keyword)
        
        print(f"\nTotal keywords after restoration: {len(all_keywords)}")
        print(f"Active keywords: {len(active_keywords)}")
        print(f"Keywords restored: {restored_count}")
        
        print("\n" + "-"*80)
        print("ALL YOUTUBE KEYWORDS:")
        print("-"*80)
        
        # Group by category
        by_category = {}
        for doc in firebase_client.db.collection('youtube_keywords').stream():
            data = doc.to_dict()
            category = data.get('category', 'unknown')
            keyword = data.get('keyword', doc.id)
            active = data.get('active', False)
            
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(f"{keyword} {'[ACTIVE]' if active else '[inactive]'}")
        
        for category, keywords in sorted(by_category.items()):
            print(f"\n{category}:")
            for kw in sorted(keywords):
                print(f"  - {kw}")
    else:
        print("\n✅ No ghost documents found for claude or dalle in youtube_keywords")
        
        # Check if they exist as regular documents
        if "claude" not in existing_keywords:
            print("\n⚠️  'claude' doesn't exist at all in youtube_keywords")
        if "dalle" not in existing_keywords:
            print("⚠️  'dalle' doesn't exist at all in youtube_keywords")

if __name__ == "__main__":
    check_and_restore_youtube_keywords()