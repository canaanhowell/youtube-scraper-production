#!/usr/bin/env python3
"""
YouTube Scraper Direct - Non-Docker Version
Scrapes YouTube search results with anti-detection measures
"""

import os
import sys
import json
import asyncio
import logging
import random
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

# Import Playwright
from playwright.async_api import async_playwright, Page, BrowserContext

# Setup logging
logger = logging.getLogger('youtube_scraper')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import our modules
from scripts.upstash_client import UpstashClient
from scripts.firebase_client import FirebaseClient


class YouTubeScraperDirect:
    """YouTube scraper for direct VM usage"""
    
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        
        # Initialize clients
        self.redis_client = UpstashClient()
        self.firebase_client = FirebaseClient()
        
        # Session tracking
        self.session_id = os.environ.get('SESSION_ID', datetime.now().strftime('%Y%m%d_%H%M%S'))
        self.current_session = {
            'start_time': datetime.now().isoformat(),
            'videos_collected': 0,
            'duplicates_skipped': 0
        }
        
        # Anti-detection settings
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 14.2.1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        
        logger.info(f"YouTube scraper initialized - Session: {self.session_id}")
    
    async def setup_browser(self, headless: bool = True):
        """Set up browser with anti-detection measures"""
        playwright = await async_playwright().start()
        
        # Random user agent and viewport
        user_agent = random.choice(self.user_agents)
        viewport = {
            'width': random.choice([1920, 1680, 1440, 1366]),
            'height': random.choice([1080, 1050, 900, 768])
        }
        
        logger.info(f"Using viewport: {viewport}, UA: {user_agent[:50]}...")
        
        self.browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-notifications',
                '--disable-geolocation',
                '--disable-infobars',
                '--mute-audio'
            ]
        )
        
        # Create context with anti-detection settings
        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale='en-US',
            timezone_id='America/New_York',
            device_scale_factor=random.choice([1, 1.25, 1.5]),
            has_touch=random.choice([True, False]),
            color_scheme=random.choice(['light', 'dark'])
        )
        
        # Add anti-detection scripts
        await self.context.add_init_script("""
            // Override automation detection
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Override permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)
        
        self.page = await self.context.new_page()
        
        # Set extra headers
        await self.page.set_extra_http_headers({
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1'
        })
        
        logger.info("Browser setup complete with anti-detection measures")
    
    async def human_like_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Add human-like delay between actions"""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)
    
    async def random_mouse_movement(self):
        """Simulate random mouse movements"""
        if self.page:
            try:
                for _ in range(random.randint(2, 5)):
                    x = random.randint(100, 800)
                    y = random.randint(100, 600)
                    await self.page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.1, 0.3))
            except:
                pass
    
    async def human_like_scroll(self):
        """Simulate human-like scrolling"""
        if self.page:
            try:
                # Random scroll distance
                scroll_y = random.randint(200, 500)
                
                # Smooth scroll
                await self.page.evaluate(f"""
                    window.scrollBy({{
                        top: {scroll_y},
                        behavior: 'smooth'
                    }});
                """)
                
                await asyncio.sleep(random.uniform(0.5, 1.5))
            except:
                pass
    
    def build_youtube_search_url(self, query: str, last_24h: bool = True) -> str:
        """Build YouTube search URL with filters"""
        base_url = "https://www.youtube.com/results"
        params = {
            'search_query': query,
        }
        
        if last_24h:
            params['sp'] = 'EgIIAw%3D%3D'  # Last 24 hours filter
        
        query_string = '&'.join([f"{k}={v}" for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    async def extract_video_data(self) -> List[Dict[str, Any]]:
        """Extract video data from search results"""
        videos = []
        
        try:
            # Wait for results to load
            await self.page.wait_for_selector('ytd-video-renderer', timeout=10000)
            
            # Extract video data
            video_data = await self.page.evaluate("""
                () => {
                    const videos = [];
                    const videoElements = document.querySelectorAll('ytd-video-renderer');
                    
                    videoElements.forEach(el => {
                        try {
                            const titleEl = el.querySelector('#video-title');
                            const channelEl = el.querySelector('#channel-name a');
                            const viewsEl = el.querySelector('#metadata-line span:first-child');
                            const timeEl = el.querySelector('#metadata-line span:nth-child(2)');
                            const thumbnailEl = el.querySelector('ytd-thumbnail img');
                            const durationEl = el.querySelector('ytd-thumbnail #time-status #text');
                            
                            if (titleEl && titleEl.href) {
                                const videoId = titleEl.href.split('v=')[1]?.split('&')[0] || 
                                              titleEl.href.split('/shorts/')[1]?.split('?')[0];
                                
                                if (videoId) {
                                    videos.push({
                                        video_id: videoId,
                                        title: titleEl.textContent.trim(),
                                        url: titleEl.href,
                                        channel_name: channelEl?.textContent.trim() || 'Unknown',
                                        channel_url: channelEl?.href || '',
                                        views: viewsEl?.textContent.trim() || '0 views',
                                        uploaded: timeEl?.textContent.trim() || 'Unknown',
                                        thumbnail: thumbnailEl?.src || '',
                                        duration: durationEl?.textContent.trim() || '0:00',
                                        is_short: titleEl.href.includes('/shorts/')
                                    });
                                }
                            }
                        } catch (e) {
                            console.error('Error extracting video:', e);
                        }
                    });
                    
                    return videos;
                }
            """)
            
            videos = video_data
            logger.info(f"Extracted {len(videos)} videos from current page")
            
        except Exception as e:
            logger.error(f"Error extracting video data: {e}")
        
        return videos
    
    async def check_duplicate(self, video_id: str, keyword: str) -> bool:
        """Check if video is duplicate using Redis"""
        if self.redis_client.enabled:
            # Check if video already exists for this keyword
            exists = self.redis_client.sismember(f"youtube:keyword:{keyword}:videos", video_id)
            if exists:
                return True
            
            # Check global video set
            global_exists = self.redis_client.exists(f"youtube:video:{video_id}")
            return bool(global_exists)
        
        return False
    
    async def process_videos(self, videos: List[Dict[str, Any]], keyword: str) -> List[Dict[str, Any]]:
        """Process videos: check duplicates, add metadata, upload to Firebase"""
        processed_videos = []
        
        for video in videos:
            video_id = video['video_id']
            
            # Check for duplicates
            if await self.check_duplicate(video_id, keyword):
                self.current_session['duplicates_skipped'] += 1
                logger.debug(f"Skipping duplicate: {video_id}")
                continue
            
            # Add metadata
            video['keyword'] = keyword
            video['session_id'] = self.session_id
            video['collected_at'] = datetime.now().isoformat()
            video['vpn_ip'] = os.environ.get('CURRENT_VPN_IP', 'unknown')
            
            # Process video ID for Firebase (handle shorts)
            firebase_video_id = video_id.replace('/', '_')
            
            # Upload to Firebase
            try:
                self.firebase_client.upload_video(keyword, firebase_video_id, video)
                
                # Mark as processed in Redis
                if self.redis_client.enabled:
                    # Add to keyword set
                    self.redis_client.sadd(f"youtube:keyword:{keyword}:videos", video_id)
                    
                    # Add to global set with metadata
                    self.redis_client.setex(
                        f"youtube:video:{video_id}",
                        self.redis_client.video_ttl,
                        json.dumps({'keyword': keyword, 'collected_at': video['collected_at']})
                    )
                    
                    # Update session progress
                    self.redis_client.increment_session_progress(self.session_id, keyword)
                
                processed_videos.append(video)
                self.current_session['videos_collected'] += 1
                
            except Exception as e:
                logger.error(f"Error processing video {video_id}: {e}")
        
        logger.info(f"Processed {len(processed_videos)} new videos, skipped {self.current_session['duplicates_skipped']} duplicates")
        return processed_videos
    
    async def scrape_search_24h(self, keyword: str, max_videos: int = 100) -> Dict[str, Any]:
        """Scrape YouTube search results for last 24 hours"""
        logger.info(f"Starting scrape for keyword: {keyword} (max: {max_videos} videos)")
        
        try:
            # Setup browser if not already
            if not self.browser:
                await self.setup_browser()
            
            # Build search URL
            url = self.build_youtube_search_url(keyword, last_24h=True)
            logger.info(f"Navigating to: {url}")
            
            # Navigate to YouTube
            await self.page.goto(url, wait_until='networkidle')
            await self.human_like_delay(2000, 3000)
            
            # Handle cookie consent if present
            try:
                cookie_button = await self.page.wait_for_selector(
                    'button[aria-label*="Accept all"]', 
                    timeout=3000
                )
                if cookie_button:
                    await cookie_button.click()
                    await self.human_like_delay()
            except:
                pass
            
            all_videos = []
            scroll_attempts = 0
            max_scrolls = 20  # Limit scrolling attempts
            
            while len(all_videos) < max_videos and scroll_attempts < max_scrolls:
                # Extract videos from current view
                videos = await self.extract_video_data()
                
                # Process new videos
                new_videos = []
                for video in videos:
                    if video['video_id'] not in [v['video_id'] for v in all_videos]:
                        new_videos.append(video)
                
                if new_videos:
                    # Process and check duplicates
                    processed = await self.process_videos(new_videos, keyword)
                    all_videos.extend(processed)
                    
                    logger.info(f"Total collected: {len(all_videos)}/{max_videos}")
                
                # Check if we have enough
                if len(all_videos) >= max_videos:
                    break
                
                # Scroll for more results
                await self.human_like_scroll()
                await self.random_mouse_movement()
                await self.human_like_delay(1000, 2000)
                
                scroll_attempts += 1
                
                # Check if we've reached the end
                end_of_results = await self.page.evaluate("""
                    () => {
                        const messages = document.querySelectorAll('yt-formatted-string');
                        for (const msg of messages) {
                            if (msg.textContent.includes('No more results') || 
                                msg.textContent.includes('End of results')) {
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                
                if end_of_results:
                    logger.info("Reached end of search results")
                    break
            
            # Clean up
            await self.browser.close()
            self.browser = None
            
            return {
                'success': True,
                'keyword': keyword,
                'videos': all_videos[:max_videos],  # Ensure we don't exceed max
                'total_collected': len(all_videos),
                'duplicates_skipped': self.current_session['duplicates_skipped']
            }
            
        except Exception as e:
            logger.error(f"Error scraping YouTube: {e}")
            if self.browser:
                await self.browser.close()
                self.browser = None
            
            return {
                'success': False,
                'keyword': keyword,
                'videos': [],
                'error': str(e)
            }


if __name__ == "__main__":
    # Test the scraper
    async def test():
        logging.basicConfig(level=logging.INFO)
        
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        scraper = YouTubeScraperDirect()
        results = await scraper.scrape_search_24h("python tutorial", max_videos=10)
        
        print(f"\nTest Results:")
        print(f"Success: {results['success']}")
        print(f"Videos collected: {len(results['videos'])}")
        
        if results['videos']:
            print("\nFirst video:")
            print(json.dumps(results['videos'][0], indent=2))
    
    asyncio.run(test())