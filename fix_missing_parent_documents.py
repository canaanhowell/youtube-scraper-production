#!/usr/bin/env python3
"""
Fix missing parent documents in youtube_videos collection
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
    print("Fixing missing parent documents in youtube_videos collection...")
    
    fc = FirebaseClient()
    
    # Get all active keywords
    keywords_ref = fc.db.collection('youtube_keywords').where('active', '==', True)
    keywords = list(keywords_ref.stream())
    
    print(f"\nFound {len(keywords)} active keywords")
    
    fixed_count = 0
    already_exists = 0
    
    for keyword_doc in keywords:
        keyword_data = keyword_doc.to_dict()
        keyword = keyword_data.get('keyword', keyword_data.get('name', keyword_doc.id))
        
        # Check if parent document exists
        parent_ref = fc.db.collection('youtube_videos').document(keyword)
        parent_doc = parent_ref.get()
        
        if not parent_doc.exists:
            print(f"\n❌ Missing parent document for '{keyword}'")
            
            # Create the parent document
            try:
                parent_ref.set({
                    'keyword': keyword,
                    'created_at': datetime.now(timezone.utc),
                    'updated_at': datetime.now(timezone.utc),
                    'note': 'Parent document for videos subcollection',
                    'category': keyword_data.get('category', 'unknown')
                })
                print(f"   ✅ Created parent document for '{keyword}'")
                fixed_count += 1
                
                # Check if there are any videos in the subcollection
                videos_count = len(list(parent_ref.collection('videos').limit(1).stream()))
                print(f"   Videos in subcollection: {videos_count}")
                
            except Exception as e:
                print(f"   ❌ Failed to create parent document: {e}")
        else:
            already_exists += 1
            # Check video count
            videos_count = len(list(parent_ref.collection('videos').limit(100).stream()))
            print(f"✅ '{keyword}' parent exists - Videos: {videos_count}")
    
    print(f"\n\nSummary:")
    print(f"  Fixed: {fixed_count} missing parent documents")
    print(f"  Already existed: {already_exists}")
    print(f"  Total: {len(keywords)}")
    
    # Now verify that video saving works
    if fixed_count > 0:
        print("\n\nTesting video save after fix...")
        
        from src.scripts.youtube_scraper_production import YouTubeScraperProduction
        scraper = YouTubeScraperProduction()
        
        # Test with chatgpt
        test_video = {
            'id': 'TEST_AFTER_FIX',
            'title': 'Test Video After Parent Document Fix',
            'url': 'https://youtube.com/watch?v=TEST_AFTER_FIX',
            'channel_name': 'Test Channel',
            'view_count': '1,000 views',
            'duration': '5:00',
            'published_time': '1 hour ago',
            'thumbnail_url': 'https://example.com/thumb.jpg',
            'collected_at': datetime.now(timezone.utc).isoformat(),
            'keyword': 'chatgpt'
        }
        
        try:
            result = scraper._save_to_firebase('chatgpt', test_video)
            print(f"Test save result: {result}")
            
            # Verify it was saved
            doc = fc.db.collection('youtube_videos').document('chatgpt').collection('videos').document('TEST_AFTER_FIX').get()
            
            if doc.exists:
                print("✅ Video save works correctly now!")
                # Clean up
                doc.reference.delete()
            else:
                print("❌ Video still not saving - different issue")
                
        except Exception as e:
            print(f"❌ Error testing save: {e}")

if __name__ == "__main__":
    main()