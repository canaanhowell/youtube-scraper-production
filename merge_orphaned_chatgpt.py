#!/usr/bin/env python3
"""
Merge orphaned ChatGPT videos collection into main collection

This script merges the 577 videos from youtube_videos/"chatgpt"/videos 
into the main youtube_videos/chatgpt/videos collection.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone
import traceback

# Set Firebase credentials path
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
os.environ['FIRESTORE_PROJECT_ID'] = 'ai-tracker-466821'

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.firebase_client import FirebaseClient

def count_videos_in_collection(fc, collection_path):
    """Count videos in a collection"""
    try:
        if '"' in collection_path:
            # Orphaned collection path
            doc_ref = fc.db.collection('youtube_videos').document(collection_path)
        else:
            # Regular collection path  
            doc_ref = fc.db.collection('youtube_videos').document(collection_path)
        
        videos = list(doc_ref.collection('videos').stream())
        return len(videos), videos
    except Exception as e:
        print(f"Error counting videos in {collection_path}: {e}")
        return 0, []

def merge_orphaned_chatgpt(fc):
    """Merge videos from orphaned collection to main collection"""
    
    print("="*80)
    print("ORPHANED CHATGPT VIDEO COLLECTION MERGE")
    print("="*80)
    print()
    
    # Collection paths
    orphaned_path = '"chatgpt"'  # The orphaned collection with quotes
    main_path = 'chatgpt'        # The main collection
    keyword = 'chatgpt'
    
    print(f"Source (orphaned): youtube_videos/{orphaned_path}/videos")
    print(f"Target (main):     youtube_videos/{main_path}/videos")
    print(f"Keyword:           {keyword}")
    print()
    
    # Step 1: Count videos in both collections
    print("STEP 1: Analyzing current collections...")
    print("-" * 50)
    
    orphaned_count, orphaned_videos = count_videos_in_collection(fc, orphaned_path)
    main_count, main_videos = count_videos_in_collection(fc, main_path)
    
    print(f"Orphaned collection videos: {orphaned_count}")
    print(f"Main collection videos:     {main_count}")
    print()
    
    if orphaned_count == 0:
        print("❌ No videos found in orphaned collection. Nothing to merge.")
        return
    
    if orphaned_count != 577:
        print(f"⚠️  WARNING: Expected 577 videos but found {orphaned_count}")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print("Merge cancelled.")
            return
    
    # Step 2: Ensure main collection parent document exists
    print("STEP 2: Ensuring main collection structure...")
    print("-" * 50)
    
    main_ref = fc.db.collection('youtube_videos').document(main_path)
    if not main_ref.get().exists:
        main_ref.set({
            'keyword': keyword,
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'note': 'Parent document for videos subcollection'
        })
        print(f"✅ Created parent document: {main_path}")
    else:
        print(f"✅ Parent document exists: {main_path}")
    print()
    
    # Step 3: Check for duplicates
    print("STEP 3: Checking for duplicate video IDs...")
    print("-" * 50)
    
    # Create set of existing video IDs in main collection
    existing_video_ids = set()
    for video_doc in main_videos:
        existing_video_ids.add(video_doc.id)
    
    # Check orphaned videos for duplicates
    duplicates = []
    videos_to_merge = []
    
    for video_doc in orphaned_videos:
        video_id = video_doc.id
        if video_id in existing_video_ids:
            duplicates.append(video_id)
        else:
            videos_to_merge.append(video_doc)
    
    print(f"Videos in orphaned collection:    {len(orphaned_videos)}")
    print(f"Duplicates found in main:         {len(duplicates)}")
    print(f"Unique videos to merge:           {len(videos_to_merge)}")
    print()
    
    if duplicates:
        print("Sample duplicate video IDs:")
        for dup_id in duplicates[:5]:  # Show first 5 duplicates
            print(f"  - {dup_id}")
        if len(duplicates) > 5:
            print(f"  ... and {len(duplicates) - 5} more")
        print()
    
    # Step 4: Perform the merge
    print("STEP 4: Merging unique videos...")
    print("-" * 50)
    
    if len(videos_to_merge) == 0:
        print("✅ No unique videos to merge. All videos already exist in main collection.")
    else:
        print(f"Merging {len(videos_to_merge)} unique videos...")
        
        batch_size = 50
        merged_count = 0
        errors = []
        
        # Process in batches
        for i in range(0, len(videos_to_merge), batch_size):
            batch = videos_to_merge[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(videos_to_merge) + batch_size - 1) // batch_size
            
            print(f"  Processing batch {batch_num}/{total_batches} ({len(batch)} videos)...")
            
            try:
                # Use Firestore batch for atomic operations
                db_batch = fc.db.batch()
                
                for video_doc in batch:
                    video_id = video_doc.id
                    video_data = video_doc.to_dict()
                    
                    # Create reference in main collection
                    target_ref = main_ref.collection('videos').document(video_id)
                    db_batch.set(target_ref, video_data)
                
                # Commit batch
                db_batch.commit()
                merged_count += len(batch)
                print(f"    ✅ Merged {len(batch)} videos (Total: {merged_count}/{len(videos_to_merge)})")
                
            except Exception as e:
                error_msg = f"Batch {batch_num} failed: {e}"
                errors.append(error_msg)
                print(f"    ❌ {error_msg}")
        
        print()
        print(f"Merge Results:")
        print(f"  Successfully merged: {merged_count}")
        print(f"  Errors:             {len(errors)}")
        
        if errors:
            print("\nErrors encountered:")
            for error in errors:
                print(f"  - {error}")
    
    # Step 5: Verify merge was successful
    print()
    print("STEP 5: Verifying merge results...")
    print("-" * 50)
    
    # Recount main collection
    final_main_count, final_main_videos = count_videos_in_collection(fc, main_path)
    expected_count = main_count + len(videos_to_merge)
    
    print(f"Main collection before merge:  {main_count}")
    print(f"Videos merged:                 {len(videos_to_merge)}")
    print(f"Expected final count:          {expected_count}")
    print(f"Actual final count:            {final_main_count}")
    
    if final_main_count == expected_count:
        print("✅ Merge verification successful!")
        merge_successful = True
    else:
        print("❌ Merge verification failed!")
        merge_successful = False
        
    print()
    
    # Step 6: Clean up orphaned collection (only if merge was successful)
    print("STEP 6: Cleaning up orphaned collection...")
    print("-" * 50)
    
    if merge_successful and len(errors) == 0:
        print("Deleting orphaned collection...")
        try:
            # Delete all videos first
            orphaned_ref = fc.db.collection('youtube_videos').document(orphaned_path)
            
            print(f"  Deleting {len(orphaned_videos)} videos...")
            batch_size = 100
            deleted_count = 0
            
            for i in range(0, len(orphaned_videos), batch_size):
                batch = orphaned_videos[i:i+batch_size]
                db_batch = fc.db.batch()
                
                for video_doc in batch:
                    db_batch.delete(video_doc.reference)
                
                db_batch.commit()
                deleted_count += len(batch)
                print(f"    Deleted {deleted_count}/{len(orphaned_videos)} videos...")
            
            # Delete parent document
            orphaned_ref.delete()
            print(f"  ✅ Deleted parent document: {orphaned_path}")
            print(f"  ✅ Successfully cleaned up orphaned collection")
            
        except Exception as e:
            print(f"  ❌ Error during cleanup: {e}")
            print("  ⚠️  Manual cleanup may be required")
    else:
        print("⚠️  Skipping cleanup due to merge errors or verification failure")
        print("   Please review the merge results before manually cleaning up")
    
    # Step 7: Final summary
    print()
    print("="*80)
    print("MERGE OPERATION SUMMARY")
    print("="*80)
    
    print(f"Operation:                    Merge orphaned ChatGPT videos")
    print(f"Source collection:            youtube_videos/{orphaned_path}/videos")  
    print(f"Target collection:            youtube_videos/{main_path}/videos")
    print(f"Videos in orphaned:           {orphaned_count}")
    print(f"Videos in main (before):      {main_count}")
    print(f"Duplicates found:             {len(duplicates)}")
    print(f"Videos merged:                {len(videos_to_merge)}")
    print(f"Final main collection count:  {final_main_count}")
    print(f"Merge successful:             {'Yes' if merge_successful else 'No'}")
    print(f"Cleanup performed:            {'Yes' if merge_successful and len(errors) == 0 else 'No'}")
    print(f"Errors encountered:           {len(errors)}")
    
    if duplicates:
        print()
        print("NOTE: Duplicate videos were skipped during merge.")
        print("This is expected behavior to prevent data duplication.")
    
    print()
    print("="*80)

def main():
    """Main function"""
    try:
        print("Initializing Firebase connection...")
        fc = FirebaseClient()
        print("✅ Firebase connection established")
        print()
        
        merge_orphaned_chatgpt(fc)
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()