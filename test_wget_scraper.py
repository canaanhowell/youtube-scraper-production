#!/usr/bin/env python3
"""Test wget scraper method to see how many videos it finds"""

import subprocess
import re
import json

def test_wget_scraper(keyword):
    """Test wget scraper with the fixed filter"""
    
    # Build search URL with corrected last hour filter
    search_url = f'https://www.youtube.com/results?search_query={keyword.replace(" ", "+")}&sp=EgQIARAB'
    print(f"🔍 Testing wget scraper for '{keyword}'")
    print(f"URL: {search_url}")
    
    # Use wget to fetch the page
    result = subprocess.run([
        'wget', '--timeout=45', '--tries=2',
        '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        '-qO-', search_url
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Failed to fetch page")
        return
    
    html_content = result.stdout
    print(f"✅ Retrieved {len(html_content)} characters")
    
    # Extract ytInitialData
    match = re.search(r'var ytInitialData = ({.*?});', html_content, re.DOTALL)
    if not match:
        print("❌ ytInitialData not found")
        return
    
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse JSON: {e}")
        return
    
    # Navigate through the data structure
    videos = []
    contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
    
    for section in contents:
        items = section.get('itemSectionRenderer', {}).get('contents', [])
        
        for item in items:
            if 'videoRenderer' in item:
                video_renderer = item['videoRenderer']
                
                # Extract basic info
                video_id = video_renderer.get('videoId', '')
                title_runs = video_renderer.get('title', {}).get('runs', [])
                title = ' '.join(run.get('text', '') for run in title_runs) if title_runs else ''
                
                # Extract publish time
                publish_time = video_renderer.get('publishedTimeText', {}).get('simpleText', '')
                
                if video_id:
                    videos.append({
                        'id': video_id,
                        'title': title[:60] + '...' if len(title) > 60 else title,
                        'publish_time': publish_time
                    })
    
    print(f"\n📊 Found {len(videos)} videos:")
    
    # Check for duplicate IDs
    video_ids = [v['id'] for v in videos]
    unique_ids = set(video_ids)
    
    print(f"📊 Unique video IDs: {len(unique_ids)}")
    if len(video_ids) != len(unique_ids):
        print(f"⚠️  Found duplicates! {len(video_ids)} total, {len(unique_ids)} unique")
        # Find duplicates
        from collections import Counter
        id_counts = Counter(video_ids)
        for vid_id, count in id_counts.items():
            if count > 1:
                print(f"  - ID '{vid_id}' appears {count} times")
    
    for i, video in enumerate(videos):
        print(f"  {i+1}. [{video['id']}] {video['title']} ({video['publish_time']})")
    
    return videos

if __name__ == "__main__":
    test_wget_scraper("chatgpt")