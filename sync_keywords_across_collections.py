#!/usr/bin/env python3
"""
Sync keywords across all collections using reddit_keywords as baseline
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    print("Syncing keywords across all collections...")
    print("Using reddit_keywords as the baseline\n")
    
    fc = FirebaseClient()
    
    # Step 1: Get all keywords from reddit_keywords (baseline)
    print("Step 1: Getting baseline from reddit_keywords...")
    reddit_keywords_ref = fc.db.collection('reddit_keywords')
    reddit_keywords = list(reddit_keywords_ref.stream())
    
    baseline_keywords = {}
    for doc in reddit_keywords:
        keyword_data = doc.to_dict()
        keyword = keyword_data.get('keyword', doc.id)
        baseline_keywords[keyword] = {
            'doc_id': doc.id,
            'data': keyword_data,
            'active': keyword_data.get('active', True)
        }
    
    print(f"Found {len(baseline_keywords)} keywords in reddit_keywords:")
    for keyword in sorted(baseline_keywords.keys()):
        active_status = "✓" if baseline_keywords[keyword]['active'] else "✗"
        print(f"  {active_status} {keyword}")
    
    # Step 2: Get current youtube_keywords
    print("\n\nStep 2: Checking youtube_keywords...")
    youtube_keywords_ref = fc.db.collection('youtube_keywords')
    youtube_keywords = list(youtube_keywords_ref.stream())
    
    youtube_keywords_dict = {}
    for doc in youtube_keywords:
        keyword_data = doc.to_dict()
        keyword = keyword_data.get('keyword', doc.id)
        youtube_keywords_dict[doc.id] = {
            'keyword': keyword,
            'data': keyword_data
        }
    
    print(f"Found {len(youtube_keywords_dict)} keywords in youtube_keywords")
    
    # Find mismatches
    youtube_to_fix = []
    youtube_to_add = []
    youtube_to_remove = []
    
    # Check what needs to be added or fixed
    for keyword, baseline_data in baseline_keywords.items():
        if keyword not in youtube_keywords_dict:
            # Check if it exists under a different ID
            found = False
            for yt_id, yt_data in youtube_keywords_dict.items():
                if yt_data['keyword'] == keyword:
                    found = True
                    if yt_id != keyword:
                        youtube_to_fix.append({
                            'old_id': yt_id,
                            'new_id': keyword,
                            'keyword': keyword
                        })
                    break
            
            if not found:
                youtube_to_add.append(keyword)
    
    # Check what needs to be removed
    for yt_id, yt_data in youtube_keywords_dict.items():
        keyword = yt_data['keyword']
        if keyword not in baseline_keywords and yt_id not in baseline_keywords:
            youtube_to_remove.append({
                'doc_id': yt_id,
                'keyword': keyword
            })
    
    print(f"\nChanges needed for youtube_keywords:")
    print(f"  - Add: {len(youtube_to_add)} keywords")
    print(f"  - Fix: {len(youtube_to_fix)} keywords")
    print(f"  - Remove: {len(youtube_to_remove)} keywords")
    
    # Step 3: Check youtube_videos collection
    print("\n\nStep 3: Checking youtube_videos parent documents...")
    youtube_videos_ref = fc.db.collection('youtube_videos')
    youtube_videos = list(youtube_videos_ref.stream())
    
    videos_to_fix = []
    videos_to_merge = {}
    
    for doc in youtube_videos:
        doc_id = doc.id
        doc_data = doc.to_dict()
        keyword = doc_data.get('keyword', doc_id)
        
        # Check if this matches baseline
        if doc_id not in baseline_keywords:
            # Check if the keyword exists in baseline
            if keyword in baseline_keywords:
                if doc_id != keyword:
                    videos_to_fix.append({
                        'old_id': doc_id,
                        'new_id': keyword,
                        'keyword': keyword
                    })
            else:
                # This document shouldn't exist
                video_count = len(list(doc.reference.collection('videos').limit(1000).stream()))
                videos_to_fix.append({
                    'old_id': doc_id,
                    'new_id': None,
                    'keyword': keyword,
                    'video_count': video_count,
                    'remove': True
                })
    
    print(f"\nChanges needed for youtube_videos:")
    print(f"  - Fix/merge: {len(videos_to_fix)} documents")
    
    # Show detailed changes
    if youtube_to_add:
        print(f"\n\nKeywords to ADD to youtube_keywords:")
        for keyword in youtube_to_add:
            print(f"  + {keyword}")
    
    if youtube_to_fix:
        print(f"\n\nKeywords to FIX in youtube_keywords:")
        for fix in youtube_to_fix:
            print(f"  {fix['old_id']} → {fix['new_id']}")
    
    if youtube_to_remove:
        print(f"\n\nKeywords to REMOVE from youtube_keywords:")
        for item in youtube_to_remove:
            print(f"  - {item['keyword']} (ID: {item['doc_id']})")
    
    if videos_to_fix:
        print(f"\n\nVideo collections to FIX:")
        for fix in videos_to_fix:
            if fix.get('remove'):
                print(f"  - Remove: {fix['old_id']} ({fix.get('video_count', 0)} videos)")
            else:
                print(f"  {fix['old_id']} → {fix['new_id']}")
    
    # Ask for confirmation
    total_changes = len(youtube_to_add) + len(youtube_to_fix) + len(youtube_to_remove) + len(videos_to_fix)
    
    if total_changes == 0:
        print("\n✅ All collections are already in sync!")
        return
    
    print(f"\n\nTotal changes to make: {total_changes}")
    print("\nPROCEEDING WITH SYNC...\n")
    
    # Apply changes
    changes_made = 0
    
    # Add missing keywords to youtube_keywords
    for keyword in youtube_to_add:
        try:
            baseline = baseline_keywords[keyword]
            doc_data = {
                'keyword': keyword,
                'active': baseline['active'],
                'category': baseline['data'].get('category', 'unknown'),
                'created_at': datetime.now(timezone.utc),
                'updated_at': datetime.now(timezone.utc),
                'source': baseline['data'].get('source', 'sync_from_reddit')
            }
            fc.db.collection('youtube_keywords').document(keyword).set(doc_data)
            print(f"✅ Added {keyword} to youtube_keywords")
            changes_made += 1
        except Exception as e:
            print(f"❌ Failed to add {keyword}: {e}")
    
    # Fix mismatched IDs in youtube_keywords
    for fix in youtube_to_fix:
        try:
            # Get existing data
            old_doc = fc.db.collection('youtube_keywords').document(fix['old_id']).get()
            if old_doc.exists:
                doc_data = old_doc.to_dict()
                doc_data['keyword'] = fix['keyword']
                doc_data['updated_at'] = datetime.now(timezone.utc)
                
                # Create new document with correct ID
                fc.db.collection('youtube_keywords').document(fix['new_id']).set(doc_data)
                
                # Delete old document
                fc.db.collection('youtube_keywords').document(fix['old_id']).delete()
                
                print(f"✅ Fixed youtube_keywords: {fix['old_id']} → {fix['new_id']}")
                changes_made += 1
        except Exception as e:
            print(f"❌ Failed to fix {fix['old_id']}: {e}")
    
    # Remove keywords not in baseline
    for item in youtube_to_remove:
        try:
            fc.db.collection('youtube_keywords').document(item['doc_id']).delete()
            print(f"✅ Removed {item['keyword']} from youtube_keywords")
            changes_made += 1
        except Exception as e:
            print(f"❌ Failed to remove {item['doc_id']}: {e}")
    
    # Fix youtube_videos parent documents
    for fix in videos_to_fix:
        try:
            if fix.get('remove'):
                # This shouldn't exist
                print(f"⚠️  Found orphaned videos collection: {fix['old_id']} with {fix.get('video_count', 0)} videos")
                print(f"   (Not in baseline - manual cleanup needed)")
            else:
                # Need to merge video collections
                old_ref = fc.db.collection('youtube_videos').document(fix['old_id'])
                new_ref = fc.db.collection('youtube_videos').document(fix['new_id'])
                
                # Get video count
                old_videos = list(old_ref.collection('videos').stream())
                video_count = len(old_videos)
                
                if video_count > 0:
                    print(f"⚠️  Need to merge {video_count} videos from {fix['old_id']} → {fix['new_id']}")
                    print(f"   (Manual merge recommended)")
                else:
                    # No videos, safe to delete
                    old_ref.delete()
                    print(f"✅ Removed empty collection: {fix['old_id']}")
                    changes_made += 1
                    
        except Exception as e:
            print(f"❌ Failed to process {fix['old_id']}: {e}")
    
    print(f"\n\n✅ Sync complete! Made {changes_made} changes.")
    
    # Show current state
    print("\n\nFinal state:")
    
    # Check youtube_keywords again
    youtube_keywords_final = list(fc.db.collection('youtube_keywords').stream())
    print(f"\nyoutube_keywords: {len(youtube_keywords_final)} documents")
    
    # Check if they match baseline
    matching = 0
    for doc in youtube_keywords_final:
        if doc.id in baseline_keywords:
            matching += 1
    
    print(f"Matching baseline: {matching}/{len(baseline_keywords)}")

if __name__ == "__main__":
    main()