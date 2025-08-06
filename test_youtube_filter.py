#!/usr/bin/env python3
"""
Test YouTube filter parameters to see if they're working correctly
"""

import sys
import json
import re
import subprocess
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def test_filter_parameters():
    """Test different YouTube filter parameters"""
    
    print("🔍 Testing YouTube Filter Parameters")
    print("=" * 50)
    
    # Test different filter combinations
    filters = {
        "No filter": "",
        "Last hour (old)": "sp=EgQIARAB", 
        "Last hour + Sort by date (current)": "sp=CAISBAgBEAE%253D",
        "Last hour + Sort by date (decoded)": "sp=CAISBAgBEAE="
    }
    
    keyword = "chatgpt"
    
    for filter_name, filter_param in filters.items():
        print(f"\n🧪 Testing: {filter_name}")
        print(f"   Filter: {filter_param}")
        
        # Build URL
        if filter_param:
            url = f'https://www.youtube.com/results?search_query={keyword}&{filter_param}'
        else:
            url = f'https://www.youtube.com/results?search_query={keyword}'
        
        print(f"   URL: {url}")
        
        # Fetch with wget through VPN
        html_content = fetch_youtube_page(url)
        
        if html_content:
            videos = extract_videos_from_html(html_content, keyword)
            print(f"   ✅ Found {len(videos)} videos")
            
            # Analyze publish times
            if videos:
                print("   📅 Publish times:")
                for i, video in enumerate(videos[:5]):  # Show first 5
                    publish_time = video.get('published_time', 'Unknown')
                    title = video.get('title', 'Unknown')[:50] + "..."
                    print(f"      {i+1}. {publish_time} - {title}")
        else:
            print("   ❌ Failed to fetch content")
        
        print()

def fetch_youtube_page(url):
    """Fetch YouTube page through VPN container"""
    try:
        result = subprocess.run([
            'docker', 'exec', 'youtube-vpn',
            'wget', '--timeout=45', '--tries=2',
            '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            '-qO-', url
        ], capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and result.stdout:
            print(f"      Retrieved {len(result.stdout)} characters")
            return result.stdout
        else:
            print(f"      Failed: return code {result.returncode}")
            if result.stderr:
                print(f"      Error: {result.stderr[:200]}")
            return None
            
    except subprocess.TimeoutExpired:
        print("      Timeout")
        return None
    except Exception as e:
        print(f"      Error: {e}")
        return None

def extract_videos_from_html(html_content, keyword):
    """Extract video data from YouTube HTML"""
    videos = []
    
    try:
        # Find ytInitialData in the HTML
        match = re.search(r'var ytInitialData = ({.*?});', html_content, re.DOTALL)
        if not match:
            print("      ❌ ytInitialData not found")
            return []
        
        # Parse JSON data
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            print(f"      ❌ JSON parse error: {e}")
            return []
        
        # Navigate through the data structure
        contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
        
        for section in contents:
            items = section.get('itemSectionRenderer', {}).get('contents', [])
            
            for item in items:
                if 'videoRenderer' in item:
                    video_data = parse_video_renderer(item['videoRenderer'], keyword)
                    if video_data:
                        videos.append(video_data)
        
        return videos
        
    except Exception as e:
        print(f"      ❌ Extraction error: {e}")
        return []

def parse_video_renderer(video_renderer, keyword):
    """Parse a videoRenderer object"""
    try:
        video_id = video_renderer.get('videoId', '')
        if not video_id:
            return None
        
        # Extract title
        title_runs = video_renderer.get('title', {}).get('runs', [])
        title = ' '.join(run.get('text', '') for run in title_runs) if title_runs else ''
        
        # Extract publish time
        publish_time = video_renderer.get('publishedTimeText', {}).get('simpleText', '')
        
        # Extract channel info
        channel_runs = video_renderer.get('ownerText', {}).get('runs', [])
        channel_name = channel_runs[0].get('text', '') if channel_runs else ''
        
        # Extract view count
        view_count_text = video_renderer.get('viewCountText', {}).get('simpleText', '')
        
        return {
            'id': video_id,
            'title': title,
            'published_time': publish_time,
            'channel_name': channel_name,
            'view_count': view_count_text,
            'keyword': keyword
        }
        
    except Exception as e:
        return None

def analyze_recent_collections():
    """Analyze recent video collections from Firebase"""
    
    print("\n🔍 Analyzing Recent Collections from Firebase")
    print("=" * 50)
    
    try:
        fc = FirebaseClient()
        
        # Get recent videos from chatgpt collection
        videos_ref = fc.db.collection('youtube_videos').document('chatgpt').collection('videos')
        
        # Get recent videos (last 50)
        recent_videos = []
        for doc in videos_ref.order_by('collected_at', direction='DESCENDING').limit(50).stream():
            video_data = doc.to_dict()
            recent_videos.append(video_data)
        
        if not recent_videos:
            print("❌ No recent videos found in Firebase")
            return
        
        print(f"✅ Found {len(recent_videos)} recent videos")
        
        # Analyze publish times
        print("\n📅 Recent video publish times:")
        for i, video in enumerate(recent_videos[:10]):  # Show first 10
            collected_at = video.get('collected_at', 'Unknown')
            published_time = video.get('published_time', 'Unknown')
            title = video.get('title', 'Unknown')[:50] + "..."
            
            print(f"   {i+1}. Collected: {collected_at}")
            print(f"      Published: {published_time}")
            print(f"      Title: {title}")
            print()
        
        # Check for old videos (more than 1 hour)
        print("\n🚨 Checking for videos older than 1 hour:")
        old_videos = []
        
        for video in recent_videos:
            published_time = video.get('published_time', '')
            if published_time:
                if is_video_old(published_time):
                    old_videos.append(video)
        
        if old_videos:
            print(f"❌ Found {len(old_videos)} videos older than 1 hour:")
            for video in old_videos[:5]:  # Show first 5
                published_time = video.get('published_time', 'Unknown')
                title = video.get('title', 'Unknown')[:50] + "..."
                print(f"   - {published_time}: {title}")
        else:
            print("✅ All recent videos are within 1 hour")
        
    except Exception as e:
        print(f"❌ Error analyzing collections: {e}")
        import traceback
        traceback.print_exc()

def is_video_old(published_time):
    """Check if video is older than 1 hour based on published_time text"""
    
    published_time = published_time.lower()
    
    # Check for minutes (should be fresh)
    if 'minute' in published_time or 'min' in published_time:
        return False
    
    # Check for hours
    if 'hour' in published_time:
        # Extract number of hours
        import re
        hour_match = re.search(r'(\d+)\s*hour', published_time)
        if hour_match:
            hours = int(hour_match.group(1))
            return hours > 1
        else:
            # If it just says "1 hour ago" or similar, it's borderline
            return '1 hour' not in published_time
    
    # Check for days, weeks, months, years (definitely old)
    old_indicators = ['day', 'week', 'month', 'year']
    return any(indicator in published_time for indicator in old_indicators)

def test_manual_search():
    """Manually test the current filter with a direct search"""
    
    print("\n🔍 Manual Filter Test")
    print("=" * 50)
    
    # Use current filter from the scraper
    search_url = 'https://www.youtube.com/results?search_query=chatgpt&sp=CAISBAgBEAE%253D'
    
    print(f"Testing URL: {search_url}")
    
    html_content = fetch_youtube_page(search_url)
    
    if html_content:
        videos = extract_videos_from_html(html_content, "chatgpt")
        
        print(f"✅ Retrieved {len(videos)} videos")
        
        if videos:
            print("\n📋 Video Analysis:")
            
            fresh_count = 0
            old_count = 0
            
            for i, video in enumerate(videos):
                published_time = video.get('published_time', 'Unknown')
                title = video.get('title', 'Unknown')[:60] + "..."
                
                is_old = is_video_old(published_time)
                status = "🚨 OLD" if is_old else "✅ FRESH"
                
                if is_old:
                    old_count += 1
                else:
                    fresh_count += 1
                
                print(f"   {i+1:2d}. {status} | {published_time:15s} | {title}")
            
            print(f"\n📊 Summary:")
            print(f"   Fresh videos (≤1 hour): {fresh_count}")
            print(f"   Old videos (>1 hour):   {old_count}")
            print(f"   Total:                  {len(videos)}")
            
            if old_count > 0:
                print(f"\n🚨 ISSUE DETECTED: {old_count} videos are older than 1 hour!")
                print("   The YouTube filter may not be working correctly.")
            else:
                print(f"\n✅ SUCCESS: All videos are within 1 hour!")
    else:
        print("❌ Failed to fetch content")

def main():
    """Main test function"""
    
    print("🧪 YouTube Filter Investigation")
    print("=" * 80)
    
    # Test 1: Different filter parameters
    test_filter_parameters()
    
    # Test 2: Analyze recent Firebase collections
    analyze_recent_collections()
    
    # Test 3: Manual test of current filter
    test_manual_search()
    
    print("\n" + "=" * 80)
    print("Investigation Complete")

if __name__ == "__main__":
    main()