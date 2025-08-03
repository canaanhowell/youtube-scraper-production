#\!/usr/bin/env python3
import re
import json
import subprocess

# Get sample HTML
url = 'https://www.youtube.com/results?search_query=midjourney&sp=EgIIAw%253D%253D'
result = subprocess.run([
    'docker', 'exec', 'youtube-vpn',
    'wget', '-qO-', url
], capture_output=True, text=True)

html = result.stdout

# Look for ytInitialData
match = re.search(r'var ytInitialData = ({.*?});', html, re.DOTALL)
if match:
    try:
        data = json.loads(match.group(1))
        
        # Navigate through the data structure to find videos
        contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
        
        videos_found = []
        
        for section in contents:
            items = section.get('itemSectionRenderer', {}).get('contents', [])
            
            for item in items:
                if 'videoRenderer' in item:
                    video = item['videoRenderer']
                    video_id = video.get('videoId', '')
                    
                    # Extract title
                    title_runs = video.get('title', {}).get('runs', [])
                    title = title_runs[0].get('text', '') if title_runs else ''
                    
                    # Extract duration
                    duration = video.get('lengthText', {}).get('simpleText', '')
                    
                    # Extract views
                    view_count = video.get('viewCountText', {}).get('simpleText', '')
                    
                    # Extract publish time
                    publish_time = video.get('publishedTimeText', {}).get('simpleText', '')
                    
                    if video_id and title:
                        videos_found.append({
                            'id': video_id,
                            'title': title,
                            'duration': duration,
                            'views': view_count,
                            'published': publish_time
                        })
        
        print(f'Found {len(videos_found)} videos using ytInitialData')
        for i, video in enumerate(videos_found[:5]):
            print(f'{i+1}. {video["title"][:60]}... ({video["id"]})')
            
    except json.JSONDecodeError as e:
        print(f'Failed to parse JSON: {e}')
else:
    print('ytInitialData not found in HTML')
