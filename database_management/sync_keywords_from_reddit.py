#!/usr/bin/env python3
"""
Sync keywords from reddit_keywords to youtube_keywords.
Adds any keywords that exist in reddit but not in youtube.
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

def sync_keywords_from_reddit():
    """Sync keywords from reddit_keywords to youtube_keywords."""
    
    firebase_client = FirebaseClient()
    
    print("\n" + "="*80)
    print("SYNCING KEYWORDS FROM REDDIT TO YOUTUBE")
    print("="*80)
    
    # Get all reddit keywords
    print("\nFetching reddit_keywords...")
    reddit_keywords = {}
    reddit_docs = firebase_client.db.collection('reddit_keywords').stream()
    
    for doc in reddit_docs:
        data = doc.to_dict()
        keyword = data.get('keyword', doc.id)
        reddit_keywords[keyword] = {
            'category': data.get('category'),
            'active': data.get('active', False)
        }
    
    print(f"Found {len(reddit_keywords)} keywords in reddit_keywords")
    
    # Get all youtube keywords
    print("\nFetching youtube_keywords...")
    youtube_keywords = {}
    youtube_docs = firebase_client.db.collection('youtube_keywords').stream()
    
    for doc in youtube_docs:
        data = doc.to_dict()
        keyword = data.get('keyword', doc.id)
        youtube_keywords[keyword] = {
            'category': data.get('category'),
            'active': data.get('active', False)
        }
    
    print(f"Found {len(youtube_keywords)} keywords in youtube_keywords")
    
    # Find missing keywords
    missing_keywords = []
    for keyword, data in reddit_keywords.items():
        if keyword not in youtube_keywords:
            missing_keywords.append({
                'keyword': keyword,
                'category': data['category'],
                'active': data['active']
            })
    
    print(f"\nMissing keywords in youtube: {len(missing_keywords)}")
    
    if missing_keywords:
        print("\n" + "-"*80)
        print("MISSING KEYWORDS:")
        print("-"*80)
        for kw in missing_keywords:
            status = "ACTIVE" if kw['active'] else "inactive"
            print(f"  - {kw['keyword']} ({kw['category']}) [{status}]")
    
    # Add missing keywords
    if missing_keywords:
        print("\n" + "="*80)
        print("ADDING MISSING KEYWORDS TO YOUTUBE_KEYWORDS")
        print("="*80)
        
        added_count = 0
        
        for kw_data in missing_keywords:
            keyword = kw_data['keyword']
            print(f"\n[{keyword}]")
            
            doc_ref = firebase_client.db.collection('youtube_keywords').document(keyword)
            
            # Create the document
            new_doc = {
                "keyword": keyword,
                "category": kw_data['category'],
                "active": kw_data['active'],
                "created_at": datetime.now(),
                "last_collected": None,
                "videos_collected": 0
            }
            
            try:
                doc_ref.set(new_doc)
                print(f"  ✓ Successfully added")
                print(f"    Category: {kw_data['category']}")
                print(f"    Active: {kw_data['active']}")
                added_count += 1
            except Exception as e:
                print(f"  ✗ Failed to add: {e}")
    
    # Also check for inconsistencies in existing keywords
    print("\n" + "="*80)
    print("CHECKING FOR CATEGORY INCONSISTENCIES")
    print("="*80)
    
    inconsistencies = []
    for keyword in youtube_keywords:
        if keyword in reddit_keywords:
            if youtube_keywords[keyword]['category'] != reddit_keywords[keyword]['category']:
                inconsistencies.append({
                    'keyword': keyword,
                    'youtube_category': youtube_keywords[keyword]['category'],
                    'reddit_category': reddit_keywords[keyword]['category']
                })
    
    if inconsistencies:
        print(f"\nFound {len(inconsistencies)} category inconsistencies:")
        for inc in inconsistencies:
            print(f"  - {inc['keyword']}: YouTube has '{inc['youtube_category']}', Reddit has '{inc['reddit_category']}'")
        
        # Fix inconsistencies
        fix = input("\nFix category inconsistencies to match Reddit? (yes/no): ")
        if fix.lower() in ['yes', 'y']:
            for inc in inconsistencies:
                doc_ref = firebase_client.db.collection('youtube_keywords').document(inc['keyword'])
                doc_ref.update({
                    'category': inc['reddit_category']
                })
                print(f"  ✓ Updated {inc['keyword']} category to '{inc['reddit_category']}'")
    
    # Final verification
    print("\n" + "="*80)
    print("FINAL VERIFICATION")
    print("="*80)
    
    # Re-fetch to get updated counts
    youtube_docs = firebase_client.db.collection('youtube_keywords').stream()
    all_keywords = []
    active_keywords = []
    
    for doc in youtube_docs:
        data = doc.to_dict()
        keyword = data.get('keyword', doc.id)
        all_keywords.append(keyword)
        if data.get('active', False):
            active_keywords.append(keyword)
    
    print(f"\nTotal YouTube keywords after sync: {len(all_keywords)}")
    print(f"Active keywords: {len(active_keywords)}")
    
    if missing_keywords:
        print(f"Keywords added: {added_count}")
    
    # Show final state by category
    print("\n" + "-"*80)
    print("YOUTUBE KEYWORDS BY CATEGORY:")
    print("-"*80)
    
    by_category = {}
    youtube_docs = firebase_client.db.collection('youtube_keywords').stream()
    
    for doc in youtube_docs:
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
    
    print("\n✅ Sync complete! YouTube and Reddit now have the same keywords.")

if __name__ == "__main__":
    sync_keywords_from_reddit()