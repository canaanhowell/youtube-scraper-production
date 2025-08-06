#!/usr/bin/env python3
"""
Detailed analysis of ChatGPT collection including quoted vs regular collections
and deep dive into duplicate titles and patterns.
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
        return db
        
    except Exception as e:
        print(f"Failed to initialize Firebase: {e}")
        raise

def analyze_collections(db):
    """Compare regular 'chatgpt' and quoted '\"chatgpt\"' collections"""
    
    print("=" * 80)
    print("DETAILED CHATGPT COLLECTIONS ANALYSIS")
    print("=" * 80)
    print()
    
    # Check for both collections
    collections_to_check = ['chatgpt', '"chatgpt"']
    collection_data = {}
    
    for collection_name in collections_to_check:
        print(f"🔍 Checking collection: youtube_videos/{collection_name}/videos")
        try:
            videos_ref = db.collection('youtube_videos').document(collection_name).collection('videos')
            videos = list(videos_ref.stream())
            collection_data[collection_name] = {
                'videos': videos,
                'count': len(videos),
                'video_ids': set(doc.id for doc in videos)
            }
            print(f"✅ Found {len(videos)} videos in '{collection_name}' collection")
        except Exception as e:
            print(f"❌ Error accessing '{collection_name}': {e}")
            collection_data[collection_name] = {'videos': [], 'count': 0, 'video_ids': set()}
        print()
    
    # Analyze overlap between collections
    if collection_data['chatgpt']['count'] > 0 and collection_data['"chatgpt"']['count'] > 0:
        regular_ids = collection_data['chatgpt']['video_ids']
        quoted_ids = collection_data['"chatgpt"']['video_ids']
        
        common_ids = regular_ids.intersection(quoted_ids)
        regular_only = regular_ids - quoted_ids
        quoted_only = quoted_ids - regular_ids
        
        print("📊 COLLECTION OVERLAP ANALYSIS")
        print("-" * 50)
        print(f"Videos in 'chatgpt': {len(regular_ids)}")
        print(f"Videos in '\"chatgpt\"': {len(quoted_ids)}")
        print(f"Common videos: {len(common_ids)}")
        print(f"Only in 'chatgpt': {len(regular_only)}")
        print(f"Only in '\"chatgpt\"': {len(quoted_only)}")
        
        if len(quoted_only) > 0:
            print(f"\n⚠️  Found {len(quoted_only)} videos only in quoted collection!")
            print("These videos might need to be merged to the regular collection.")
        
        if len(common_ids) > 0:
            print(f"\n🔄 {len(common_ids)} videos exist in both collections (potential duplicates)")
    
    # Focus on the main collection for detailed analysis
    main_collection = 'chatgpt' if collection_data['chatgpt']['count'] > 0 else '"chatgpt"'
    videos = collection_data[main_collection]['videos']
    
    if not videos:
        print("❌ No videos found in any collection!")
        return
    
    print(f"\n🎯 DETAILED ANALYSIS OF '{main_collection}' COLLECTION")
    print("-" * 60)
    
    # Process all video data
    video_data = []
    for doc in videos:
        doc_data = doc.to_dict()
        
        # Handle collected_at timestamp
        collected_at = doc_data.get('collected_at')
        if collected_at:
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
        
        video_data.append({
            'id': doc.id,
            'title': doc_data.get('title', 'No title'),
            'channel': doc_data.get('channel', 'Unknown channel'),
            'collected_at': collected_date,
            'original_video_id': doc_data.get('original_video_id', doc.id),
            'views': doc_data.get('views', 'Unknown'),
            'upload_date': doc_data.get('upload_date', 'Unknown'),
            'url': doc_data.get('url', ''),
            'session_id': doc_data.get('session_id', 'Unknown'),
            'container': doc_data.get('container', 'Unknown'),
            'vpn_location': doc_data.get('vpn_location', 'Unknown')
        })
    
    # Analyze title duplicates in detail
    print(f"\n📝 DETAILED TITLE DUPLICATE ANALYSIS")
    print("-" * 50)
    
    title_to_videos = defaultdict(list)
    for video in video_data:
        title_to_videos[video['title']].append(video)
    
    title_duplicates = {title: videos for title, videos in title_to_videos.items() if len(videos) > 1}
    
    print(f"Found {len(title_duplicates)} titles with multiple videos")
    
    if title_duplicates:
        print(f"\nDetailed analysis of title duplicates:")
        
        for i, (title, duplicate_videos) in enumerate(sorted(title_duplicates.items(), key=lambda x: len(x[1]), reverse=True)[:10]):
            print(f"\n{i+1}. \"{title[:80]}{'...' if len(title) > 80 else ''}\"")
            print(f"   {len(duplicate_videos)} occurrences:")
            
            for video in duplicate_videos:
                print(f"   • ID: {video['id']}")
                print(f"     URL: {video['url'][:60]}{'...' if len(video['url']) > 60 else ''}")
                print(f"     Collected: {video['collected_at'].strftime('%Y-%m-%d %H:%M:%S') if video['collected_at'] else 'Unknown'}")
                print(f"     Views: {video['views']}")
                print(f"     Upload Date: {video['upload_date']}")
                print()
    
    # Time pattern analysis
    print(f"\n⏰ TIME PATTERN ANALYSIS")
    print("-" * 50)
    
    valid_dates = [v['collected_at'] for v in video_data if v['collected_at']]
    
    if valid_dates:
        # Analyze collection by hour
        hourly_counts = defaultdict(int)
        for date in valid_dates:
            hour_key = date.strftime('%Y-%m-%d %H:00')
            hourly_counts[hour_key] += 1
        
        print("Collection patterns by hour (top 15):")
        sorted_hours = sorted(hourly_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        for hour, count in sorted_hours:
            print(f"  • {hour}: {count} videos")
        
        # Look for suspicious time clustering
        print(f"\n🚨 Suspicious time clustering:")
        minute_counts = defaultdict(int)
        for date in valid_dates:
            minute_key = date.strftime('%Y-%m-%d %H:%M')
            minute_counts[minute_key] += 1
        
        suspicious_minutes = [(minute, count) for minute, count in minute_counts.items() if count > 20]
        for minute, count in sorted(suspicious_minutes, key=lambda x: x[1], reverse=True)[:10]:
            print(f"  ⚠️  {minute}: {count} videos (unusually high for single minute)")
    
    # URL pattern analysis
    print(f"\n🔗 URL PATTERN ANALYSIS")
    print("-" * 50)
    
    urls = [v['url'] for v in video_data if v['url']]
    url_counts = Counter(urls)
    duplicate_urls = [(url, count) for url, count in url_counts.items() if count > 1]
    
    print(f"Total URLs: {len(urls)}")
    print(f"Unique URLs: {len(set(urls))}")
    print(f"Duplicate URLs: {len(duplicate_urls)}")
    
    if duplicate_urls:
        print(f"\nTop duplicate URLs:")
        for url, count in sorted(duplicate_urls, key=lambda x: x[1], reverse=True)[:5]:
            print(f"  • {count}x: {url[:70]}{'...' if len(url) > 70 else ''}")
    
    # Container and VPN analysis
    print(f"\n🖥️  CONTAINER & VPN ANALYSIS")
    print("-" * 50)
    
    containers = [v['container'] for v in video_data]
    vpn_locations = [v['vpn_location'] for v in video_data]
    
    container_counts = Counter(containers)
    vpn_counts = Counter(vpn_locations)
    
    print(f"Container distribution:")
    for container, count in container_counts.most_common():
        print(f"  • {container}: {count} videos")
    
    print(f"\nVPN location distribution:")
    for vpn, count in vpn_counts.most_common():
        print(f"  • {vpn}: {count} videos")
    
    # Generate recommendations
    print(f"\n💡 DETAILED RECOMMENDATIONS")
    print("-" * 50)
    
    recommendations = []
    
    if len(title_duplicates) > 0:
        recommendations.append(f"🔍 Investigate {len(title_duplicates)} titles with multiple IDs - these may be legitimate different videos or actual duplicates")
    
    if duplicate_urls:
        recommendations.append(f"🔗 Review {len(duplicate_urls)} duplicate URLs - these are likely true duplicates that should be removed")
    
    if len(collection_data['"chatgpt"']['video_ids']) > 0:
        recommendations.append(f"🔄 Consider merging videos from quoted collection to main collection")
    
    if len([c for c in container_counts if c != 'Unknown']) > 1:
        recommendations.append(f"📊 Multiple containers detected - ensure this is intentional")
    
    suspicious_minutes = [(minute, count) for minute, count in minute_counts.items() if count > 20] if 'minute_counts' in locals() else []
    if suspicious_minutes:
        recommendations.append(f"⏰ Review time clustering patterns - {len(suspicious_minutes)} minutes with >20 videos")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec}")
    
    if not recommendations:
        print("✅ No major issues detected - collection appears healthy")
    
    print("\n🎯 Detailed analysis completed!")

def main():
    """Main function to run the detailed analysis"""
    try:
        print("🚀 Starting Detailed ChatGPT Collection Analysis...")
        print(f"📅 Analysis date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Initialize Firebase
        db = setup_firebase()
        
        # Run the analysis
        analyze_collections(db)
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()