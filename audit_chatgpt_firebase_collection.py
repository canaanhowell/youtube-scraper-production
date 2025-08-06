#!/usr/bin/env python3
"""
Audit the ChatGPT videos in Firebase collection youtube_videos/chatgpt/videos 
to check for duplicates and analyze collection patterns.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone
from collections import defaultdict, Counter
import json

# Add project to path
sys.path.append(str(Path(__file__).parent))

# Import Firebase client directly
import firebase_admin
from firebase_admin import credentials, firestore

def setup_firebase():
    """Initialize Firebase with explicit credentials"""
    service_account_path = "/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json"
    
    if not os.path.exists(service_account_path):
        raise FileNotFoundError(f"Service account file not found: {service_account_path}")
    
    try:
        # Check if Firebase app is already initialized
        try:
            firebase_admin.get_app()
            print("Firebase app already initialized")
        except ValueError:
            # Initialize Firebase
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print("Firebase app initialized successfully")
        
        # Get Firestore client
        db = firestore.client()
        print("Firebase client ready")
        return db
        
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        raise

def analyze_chatgpt_collection(db):
    """Analyze the ChatGPT video collection for duplicates and patterns"""
    
    print("=" * 80)
    print("CHATGPT FIREBASE COLLECTION AUDIT")
    print("=" * 80)
    print()
    
    # Get videos from the chatgpt collection
    print("🔍 Retrieving videos from youtube_videos/chatgpt/videos...")
    videos_ref = db.collection('youtube_videos').document('chatgpt').collection('videos')
    
    try:
        all_videos = list(videos_ref.stream())
        print(f"✅ Successfully retrieved {len(all_videos)} video documents")
    except Exception as e:
        print(f"❌ Failed to retrieve videos: {e}")
        return
    
    if not all_videos:
        print("⚠️  No videos found in the collection!")
        return
    
    print()
    print("📊 BASIC STATISTICS")
    print("-" * 40)
    print(f"Total video documents: {len(all_videos)}")
    
    # Analyze video data
    video_ids = []
    titles = []
    collected_dates = []
    channels = []
    video_data = []
    
    print("\n🔄 Processing video data...")
    for doc in all_videos:
        doc_data = doc.to_dict()
        video_ids.append(doc.id)
        
        # Extract key fields
        title = doc_data.get('title', 'No title')
        titles.append(title)
        
        channel = doc_data.get('channel', 'Unknown channel')
        channels.append(channel)
        
        # Handle collected_at timestamp
        collected_at = doc_data.get('collected_at')
        if collected_at:
            # Convert Firestore timestamp to datetime if needed
            if hasattr(collected_at, 'seconds'):
                collected_date = datetime.fromtimestamp(collected_at.seconds, tz=timezone.utc)
            elif isinstance(collected_at, datetime):
                collected_date = collected_at
            else:
                try:
                    collected_date = datetime.fromisoformat(str(collected_at).replace('Z', '+00:00'))
                except:
                    collected_date = None
        else:
            collected_date = None
        
        collected_dates.append(collected_date)
        
        # Store full video data for analysis
        video_data.append({
            'id': doc.id,
            'title': title,
            'channel': channel,
            'collected_at': collected_date,
            'original_video_id': doc_data.get('original_video_id', doc.id),
            'views': doc_data.get('views', 'Unknown'),
            'upload_date': doc_data.get('upload_date', 'Unknown'),
            'url': doc_data.get('url', ''),
            'session_id': doc_data.get('session_id', 'Unknown')
        })
    
    # 1. Check for duplicate video IDs
    print("\n🔍 DUPLICATE ANALYSIS")
    print("-" * 40)
    
    unique_video_ids = set(video_ids)
    print(f"Unique video IDs: {len(unique_video_ids)}")
    print(f"Total documents: {len(video_ids)}")
    
    if len(unique_video_ids) < len(video_ids):
        duplicate_count = len(video_ids) - len(unique_video_ids)
        print(f"❌ Found {duplicate_count} duplicate video IDs!")
        
        # Find specific duplicates
        id_counts = Counter(video_ids)
        duplicates = {vid_id: count for vid_id, count in id_counts.items() if count > 1}
        
        print("\nDuplicate video IDs:")
        for vid_id, count in duplicates.items():
            print(f"  • {vid_id}: {count} occurrences")
    else:
        print("✅ No duplicate video IDs found")
    
    # 2. Check for videos with same title but different IDs
    print("\n📝 TITLE DUPLICATE ANALYSIS")
    print("-" * 40)
    
    title_to_ids = defaultdict(list)
    for i, title in enumerate(titles):
        title_to_ids[title].append(video_ids[i])
    
    title_duplicates = {title: ids for title, ids in title_to_ids.items() if len(ids) > 1}
    
    if title_duplicates:
        print(f"⚠️  Found {len(title_duplicates)} titles with multiple video IDs:")
        for title, ids in list(title_duplicates.items())[:10]:  # Show first 10
            print(f"  • \"{title[:60]}{'...' if len(title) > 60 else ''}\"")
            print(f"    Video IDs: {', '.join(ids[:5])}{'...' if len(ids) > 5 else ''}")
        
        if len(title_duplicates) > 10:
            print(f"    ... and {len(title_duplicates) - 10} more")
    else:
        print("✅ No title duplicates found")
    
    # 3. Date range analysis
    print("\n📅 COLLECTION DATE ANALYSIS")
    print("-" * 40)
    
    valid_dates = [d for d in collected_dates if d is not None]
    
    if valid_dates:
        earliest_date = min(valid_dates)
        latest_date = max(valid_dates)
        
        print(f"Earliest collection: {earliest_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Latest collection: {latest_date.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Date range span: {(latest_date - earliest_date).days} days")
        print(f"Videos with valid dates: {len(valid_dates)} / {len(collected_dates)}")
        
        # Group by date for pattern analysis
        dates_by_day = defaultdict(int)
        for date in valid_dates:
            day_key = date.strftime('%Y-%m-%d')
            dates_by_day[day_key] += 1
        
        print(f"\nDaily collection counts (top 10 days):")
        sorted_days = sorted(dates_by_day.items(), key=lambda x: x[1], reverse=True)[:10]
        for day, count in sorted_days:
            print(f"  • {day}: {count} videos")
        
    else:
        print("⚠️  No valid collection dates found")
    
    # 4. Channel analysis
    print("\n📺 CHANNEL ANALYSIS")
    print("-" * 40)
    
    channel_counts = Counter(channels)
    unique_channels = len(channel_counts)
    print(f"Unique channels: {unique_channels}")
    
    print(f"\nTop 10 channels by video count:")
    for channel, count in channel_counts.most_common(10):
        print(f"  • {channel}: {count} videos")
    
    # 5. Session analysis
    print("\n🔗 SESSION ANALYSIS")
    print("-" * 40)
    
    session_ids = [v['session_id'] for v in video_data]
    session_counts = Counter(session_ids)
    unique_sessions = len(session_counts)
    print(f"Unique sessions: {unique_sessions}")
    
    print(f"\nTop 10 sessions by video count:")
    for session_id, count in session_counts.most_common(10):
        print(f"  • {session_id}: {count} videos")
    
    # 6. Suspicious patterns analysis
    print("\n🚨 SUSPICIOUS PATTERNS")
    print("-" * 40)
    
    suspicious_patterns = []
    
    # Check for excessive duplicates from same session
    for session_id, count in session_counts.items():
        if count > 100:  # Threshold for suspicious activity
            suspicious_patterns.append(f"Session {session_id} has {count} videos (unusually high)")
    
    # Check for videos collected at exact same time
    if valid_dates:
        timestamp_counts = Counter(d.strftime('%Y-%m-%d %H:%M:%S') for d in valid_dates)
        exact_time_duplicates = [(ts, count) for ts, count in timestamp_counts.items() if count > 50]
        
        for timestamp, count in exact_time_duplicates:
            suspicious_patterns.append(f"{count} videos collected at exact time: {timestamp}")
    
    # Check for identical video URLs
    urls = [v['url'] for v in video_data if v['url']]
    url_counts = Counter(urls)
    url_duplicates = [(url, count) for url, count in url_counts.items() if count > 1]
    
    if url_duplicates:
        suspicious_patterns.append(f"Found {len(url_duplicates)} URLs with multiple entries")
    
    if suspicious_patterns:
        for pattern in suspicious_patterns:
            print(f"  ⚠️  {pattern}")
    else:
        print("✅ No suspicious patterns detected")
    
    # 7. Summary report
    print("\n" + "=" * 80)
    print("AUDIT SUMMARY")
    print("=" * 80)
    print(f"📊 Total videos collected: {len(all_videos)}")
    print(f"🆔 Unique video IDs: {len(unique_video_ids)}")
    print(f"🔄 Duplicate video IDs: {len(video_ids) - len(unique_video_ids)}")
    print(f"📝 Titles with multiple IDs: {len(title_duplicates)}")
    print(f"📅 Date range: {(latest_date - earliest_date).days if valid_dates else 'N/A'} days")
    print(f"📺 Unique channels: {unique_channels}")
    print(f"🔗 Unique sessions: {unique_sessions}")
    print(f"🚨 Suspicious patterns: {len(suspicious_patterns)}")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS")
    print("-" * 40)
    
    if len(video_ids) > len(unique_video_ids):
        print("• ⚠️  Remove duplicate video ID entries")
    
    if title_duplicates:
        print("• 🔍 Investigate videos with same titles but different IDs")
    
    if suspicious_patterns:
        print("• 🚨 Review and address suspicious collection patterns")
    
    if len(valid_dates) < len(collected_dates):
        print("• 📅 Fix missing or invalid collection timestamps")
    
    print("• ✅ Overall collection appears healthy" if not (len(video_ids) > len(unique_video_ids) or title_duplicates or suspicious_patterns) else "")
    
    print("\n🎯 Audit completed successfully!")

def main():
    """Main function to run the audit"""
    try:
        print("🚀 Starting ChatGPT Firebase Collection Audit...")
        print(f"📅 Audit date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Initialize Firebase
        db = setup_firebase()
        
        # Run the analysis
        analyze_chatgpt_collection(db)
        
    except Exception as e:
        print(f"❌ Audit failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()