#\!/usr/bin/env python3
import subprocess

url = 'https://www.youtube.com/results?search_query=midjourney'
result = subprocess.run([
    'docker', 'exec', 'youtube-vpn',
    'wget', '-qO-', url
], capture_output=True, text=True)

if result.stdout:
    print(f'HTML length: {len(result.stdout)}')
    
    # Check for different patterns
    patterns = [
        'videoId',
        'watch?v=',
        '/watch?v=',
        'ytInitialData',
        'var ytInitialData',
        'thumbnail',
        'title'
    ]
    
    for pattern in patterns:
        count = result.stdout.count(pattern)
        print(f'{pattern}: {count} occurrences')
        
    # Save sample
    with open('debug_sample.html', 'w') as f:
        f.write(result.stdout[:50000])
    print('\nSaved first 50KB to debug_sample.html')
else:
    print('No output received')
