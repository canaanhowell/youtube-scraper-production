#!/usr/bin/env python3
"""
Check for keywords with underscores or other formatting issues
"""

import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    print("Checking keyword formats for search issues...")
    
    fc = FirebaseClient()
    
    # Get all active keywords
    keywords_ref = fc.db.collection('youtube_keywords').where('active', '==', True)
    keywords = list(keywords_ref.stream())
    
    print(f"\nFound {len(keywords)} active keywords\n")
    
    problematic_keywords = []
    
    for keyword_doc in keywords:
        keyword_data = keyword_doc.to_dict()
        keyword = keyword_data.get('keyword', keyword_data.get('name', keyword_doc.id))
        doc_id = keyword_doc.id
        
        issues = []
        
        # Check for underscores
        if '_' in keyword:
            issues.append("Contains underscore(s)")
        
        # Check for quotes
        if '"' in keyword or "'" in keyword:
            issues.append("Contains quotes")
        
        # Check if document ID doesn't match keyword
        if doc_id != keyword:
            issues.append(f"Doc ID mismatch: '{doc_id}' vs '{keyword}'")
        
        if issues:
            problematic_keywords.append({
                'keyword': keyword,
                'doc_id': doc_id,
                'issues': issues
            })
            print(f"❌ '{keyword}' (ID: {doc_id})")
            for issue in issues:
                print(f"   - {issue}")
            print()
        else:
            print(f"✅ '{keyword}'")
    
    # Check youtube_videos collection for mismatches
    print("\n\nChecking youtube_videos collection for duplicates/mismatches...")
    
    videos_collection = fc.db.collection('youtube_videos')
    all_video_docs = list(videos_collection.stream())
    
    print(f"\nFound {len(all_video_docs)} documents in youtube_videos\n")
    
    # Group by normalized keyword
    keyword_variations = {}
    
    for doc in all_video_docs:
        doc_id = doc.id
        doc_data = doc.to_dict()
        
        # Normalize the keyword (remove underscores, lowercase)
        normalized = doc_id.lower().replace('_', ' ').replace('"', '').strip()
        
        if normalized not in keyword_variations:
            keyword_variations[normalized] = []
        
        keyword_variations[normalized].append({
            'doc_id': doc_id,
            'video_count': len(list(doc.reference.collection('videos').limit(100).stream()))
        })
    
    # Find duplicates
    print("Duplicate keyword variations found:")
    for normalized, variations in keyword_variations.items():
        if len(variations) > 1:
            print(f"\n'{normalized}' has {len(variations)} variations:")
            for var in variations:
                print(f"  - '{var['doc_id']}' ({var['video_count']} videos)")
    
    # Recommendations
    print("\n\nRECOMMENDATIONS:")
    print("1. Keywords with underscores should be converted to spaces")
    print("2. Keywords with quotes should have quotes removed")
    print("3. Document IDs should match the keyword exactly")
    print("4. Duplicate variations should be merged")
    
    if problematic_keywords:
        print(f"\n\n{len(problematic_keywords)} keywords need fixing:")
        for pk in problematic_keywords:
            suggested = pk['keyword'].replace('_', ' ').replace('"', '').strip()
            if suggested != pk['keyword']:
                print(f"  '{pk['keyword']}' → '{suggested}'")

if __name__ == "__main__":
    main()