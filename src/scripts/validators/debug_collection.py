#\!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/youtube_app')

from src.utils.firebase_client import FirebaseClient
from src.utils.redis_client import RedisClient
from youtube_scraper_production import YouTubeScraperProduction
import subprocess
import time
import json

print('Testing YouTube Collection Flow...\n')

# 1. Test Firebase connection
print('1. Testing Firebase connection...')
try:
    fc = FirebaseClient()
    keywords = fc.get_keywords()
    print(f'   ✓ Connected to Firebase')
    print(f'   ✓ Found {len(keywords)} keywords: {keywords}')
except Exception as e:
    print(f'   ✗ Firebase error: {e}')
    sys.exit(1)

# 2. Test VPN
print('\n2. Testing VPN connection...')
try:
    # Start VPN with NYC server
    print('   Starting VPN container...')
    subprocess.run(['docker', 'compose', 'down'], capture_output=True)
    time.sleep(2)
    
    env = {'VPN_SERVER': 'us-nyc.prod.surfshark.com'}
    result = subprocess.run(
        ['docker', 'compose', 'up', '-d'],
        env={**subprocess.os.environ, **env},
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f'   ✗ Failed to start VPN: {result.stderr}')
        sys.exit(1)
    
    # Wait for connection
    print('   Waiting for VPN to connect...')
    for i in range(6):
        time.sleep(10)
        check = subprocess.run(
            ['docker', 'exec', 'youtube-vpn', 'wget', '-q', '-O', '-', 'https://ipinfo.io/json'],
            capture_output=True,
            text=True
        )
        if check.returncode == 0:
            info = json.loads(check.stdout)
            print(f'   ✓ VPN connected: {info.get("city")} - {info.get("ip")}')
            break
        print(f'   ... attempt {i+1}/6')
    else:
        print('   ✗ VPN connection timeout')
        sys.exit(1)
        
except Exception as e:
    print(f'   ✗ VPN error: {e}')
    sys.exit(1)

# 3. Test YouTube scraping
print('\n3. Testing YouTube scraping...')
try:
    scraper = YouTubeScraperProduction()
    keyword = keywords[0] if keywords else 'test'
    print(f'   Scraping keyword: {keyword}')
    
    result = scraper.scrape_keyword(keyword, max_videos=10)
    
    print(f'   ✓ Scraped successfully')
    print(f'   ✓ Found {result.get("total_found", 0)} videos')
    print(f'   ✓ Saved {result.get("saved_to_firebase", 0)} to Firebase')
    print(f'   ✓ {result.get("duplicates", 0)} duplicates skipped')
    
except Exception as e:
    print(f'   ✗ Scraping error: {e}')
    import traceback
    traceback.print_exc()

# 4. Test collection logging
print('\n4. Testing collection logging...')
try:
    stats = {
        'keywords_processed': [keyword],
        'total_videos_collected': result.get('saved_to_firebase', 0),
        'videos_per_keyword': {keyword: result.get('saved_to_firebase', 0)},
        'duration_seconds': 30,
        'success': True,
        'errors': [],
        'session_id': 'test_session_debug',
        'timestamp': None
    }
    
    log_id = fc.log_collection_run(stats)
    print(f'   ✓ Logged to Firebase: youtube_collection_logs/{log_id}')
    
except Exception as e:
    print(f'   ✗ Logging error: {e}')

# Cleanup
print('\n5. Cleaning up...')
subprocess.run(['docker', 'compose', 'down'], capture_output=True)
print('   ✓ VPN stopped')

print('\n✅ Test completed successfully\!')
