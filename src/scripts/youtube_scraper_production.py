#!/usr/bin/env python3
import os
import sys
import json
import time
import re
import logging
import subprocess
import asyncio
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Add project to path
sys.path.append(str(Path(__file__).parent))

# Import our modules
from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient
from src.utils.redis_client_enhanced import RedisClientEnhanced as RedisClient

# Set up enhanced logging
try:
    from src.utils.logging_config_enhanced import setup_logging
    logger, network_logger = setup_logging(log_level="INFO", console_output=True)
except ImportError:
    # Fallback to basic logging if enhanced config not available
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('/opt/youtube_app/logs/scraper.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    network_logger = logging.getLogger('network')

# Playwright imports for pagination
try:
    from playwright.async_api import async_playwright, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("Playwright not available - pagination disabled")

class YouTubeScraperProduction:
    def __init__(self, container_name: str = "youtube-vpn", instance_id: int = 1):
        # Load environment
        load_env()
        
        # Initialize clients
        self.firebase = FirebaseClient()
        self.redis = RedisClient()
        
        # Container name for VPN
        self.container_name = container_name
        # Instance ID for Redis key namespacing
        self.instance_id = instance_id
        
        # Title filtering configuration
        self.strict_title_filter = os.getenv('YOUTUBE_STRICT_TITLE_FILTER', 'true').lower() == 'true'
        
        # Pagination configuration
        self.enable_pagination = os.getenv('YOUTUBE_ENABLE_PAGINATION', 'false').lower() == 'true'
        self.max_scroll_attempts = int(os.getenv('YOUTUBE_MAX_SCROLL_ATTEMPTS', '10'))
        
        logger.info(f"Production YouTube scraper initialized (strict_title_filter={self.strict_title_filter}, pagination={self.enable_pagination})")
    
    def scrape_keyword(self, keyword: str, exact_match: bool = True, max_videos: int = 1000) -> Dict:
        """Scrape YouTube for a keyword and save to Firebase"""
        try:
            logger.info(f"Starting scrape for keyword: {keyword} (exact_match={exact_match}, pagination={'enabled' if self.enable_pagination else 'disabled'})")
            start_time = datetime.utcnow()
            
            # Build YouTube search URL with last hour filter AND sort by upload date
            # sp=CAISBAgBEAE%253D = Sort by upload date + Last hour (URL encoded)
            # sp=EgQIARAB = Last hour only (no sort)
            search_url = f'https://www.youtube.com/results?search_query={keyword.replace(" ", "+")}&sp=CAISBAgBEAE%253D'
            logger.info(f"Search URL: {search_url}")
            
            # Choose scraping method based on pagination setting
            if self.enable_pagination and PLAYWRIGHT_AVAILABLE:
                # Use Playwright with pagination
                videos, filtered_count = asyncio.run(self._scrape_with_pagination(search_url, keyword, exact_match, max_videos))
            else:
                # Use traditional wget method (single page)
                html_content = self._fetch_youtube_page(search_url)
                if not html_content:
                    logger.error(f"Failed to fetch content for {keyword}")
                    return {'keyword': keyword, 'videos': [], 'error': 'Failed to fetch content'}
                
                # Extract videos from HTML using ytInitialData
                videos, filtered_count = self._extract_videos_from_initial_data(html_content, keyword, exact_match)
            
            logger.info(f"Extracted {len(videos)} videos matching keyword (filtered out {filtered_count} videos)")
            
            # Filter duplicates using Redis
            new_videos = []
            duplicate_count = 0
            
            for video in videos[:max_videos]:
                if not self._is_duplicate(video['id']):
                    new_videos.append(video)
                    self._mark_as_collected(video['id'])
                else:
                    duplicate_count += 1
            
            logger.info(f"Found {len(new_videos)} new videos, {duplicate_count} duplicates")
            
            # Save to Firebase
            saved_count = 0
            failed_saves = 0
            
            for video in new_videos:
                try:
                    if self._save_to_firebase(keyword, video):
                        saved_count += 1
                    else:
                        failed_saves += 1
                except Exception as e:
                    logger.error(f"Error saving video {video['id']}: {e}")
                    failed_saves += 1
            
            end_time = datetime.utcnow()
            duration = (end_time - start_time).total_seconds()
            
            result = {
                'keyword': keyword,
                'total_found': len(videos),
                'filtered_out': filtered_count,
                'new_videos': len(new_videos),
                'duplicates': duplicate_count,
                'saved_to_firebase': saved_count,
                'failed_saves': failed_saves,
                'duration_seconds': duration,
                'timestamp': end_time.isoformat(),
                'success': saved_count > 0
            }
            
            # Update keyword collection timestamp
            try:
                self.firebase.update_keyword_collection_timestamp(keyword, end_time)
            except Exception as e:
                logger.warning(f"Failed to update keyword timestamp for {keyword}: {e}")

            logger.info(f"✓ Completed {keyword}: {saved_count} videos saved to Firebase in {duration:.1f}s")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping {keyword}: {e}", exc_info=True)
            return {
                'keyword': keyword, 
                'videos': [], 
                'error': str(e),
                'success': False
            }
    
    def _fetch_youtube_page(self, url: str) -> Optional[str]:
        """Fetch YouTube page through VPN container"""
        try:
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'wget', '--timeout=45', '--tries=2',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                '-qO-', url
            ], capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0 and result.stdout:
                logger.info(f"Retrieved {len(result.stdout)} characters")
                return result.stdout
            else:
                logger.error(f"Failed to fetch page: return code {result.returncode}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("Page fetch timeout")
            return None
        except Exception as e:
            logger.error(f"Error fetching page: {e}")
            return None
    
    def _extract_videos_from_initial_data(self, html_content: str, keyword: str, exact_match: bool = True) -> tuple[List[Dict], int]:
        """Extract video data from YouTube's ytInitialData
        
        Returns:
            tuple: (list of videos, count of filtered videos)
        """
        videos = []
        filtered_count = 0
        
        try:
            # Find ytInitialData in the HTML
            match = re.search(r'var ytInitialData = ({.*?});', html_content, re.DOTALL)
            if not match:
                logger.error("ytInitialData not found in HTML")
                return []
            
            # Parse JSON data
            try:
                data = json.loads(match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse ytInitialData JSON: {e}")
                return []
            
            # Navigate through the data structure
            contents = data.get('contents', {}).get('twoColumnSearchResultsRenderer', {}).get('primaryContents', {}).get('sectionListRenderer', {}).get('contents', [])
            
            for section in contents:
                items = section.get('itemSectionRenderer', {}).get('contents', [])
                
                for item in items:
                    if 'videoRenderer' in item:
                        video_data = self._parse_video_renderer(item['videoRenderer'], keyword, exact_match)
                        if video_data:
                            if video_data == 'filtered':
                                filtered_count += 1
                            else:
                                videos.append(video_data)
            
            logger.info(f"Extracted {len(videos)} videos from ytInitialData (filtered {filtered_count})")
            return videos, filtered_count
            
        except Exception as e:
            logger.error(f"Error extracting videos: {e}", exc_info=True)
            return [], 0
    
    def _parse_video_renderer(self, video_renderer: Dict, keyword: str, exact_match: bool = True) -> Optional[Dict]:
        """Parse a videoRenderer object into our video data format"""
        try:
            video_id = video_renderer.get('videoId', '')
            if not video_id:
                return None
            
            # Extract title
            title_runs = video_renderer.get('title', {}).get('runs', [])
            title = ' '.join(run.get('text', '') for run in title_runs) if title_runs else ''
            
            # Check if title contains keyword (if strict filtering is enabled)
            if self.strict_title_filter and not self._title_contains_keyword(title, keyword, exact_match):
                logger.debug(f"Filtered out video: '{title}' (keyword: '{keyword}', exact_match: {exact_match})")
                return 'filtered'
            
            # Extract thumbnail URL
            thumbnails = video_renderer.get('thumbnail', {}).get('thumbnails', [])
            thumbnail_url = thumbnails[-1].get('url', '') if thumbnails else ''
            
            # Extract duration
            duration = video_renderer.get('lengthText', {}).get('simpleText', '')
            
            # Extract view count
            view_count_text = video_renderer.get('viewCountText', {}).get('simpleText', '')
            
            # Extract publish time
            publish_time = video_renderer.get('publishedTimeText', {}).get('simpleText', '')
            
            # Extract channel info
            channel_runs = video_renderer.get('ownerText', {}).get('runs', [])
            channel_name = channel_runs[0].get('text', '') if channel_runs else ''
            
            # Build video data
            video_data = {
                'id': video_id,
                'title': title,
                'url': f'https://www.youtube.com/watch?v={video_id}',
                'thumbnail_url': thumbnail_url,
                'duration': duration,
                'view_count': view_count_text,
                'published_time': publish_time,
                'channel_name': channel_name,
                'keyword': keyword,
                'collected_at': datetime.utcnow().isoformat(),
                'source': 'youtube_scraper_production'
            }
            
            return video_data
            
        except Exception as e:
            logger.error(f"Error parsing video renderer: {e}")
            return None
    
    def _is_duplicate(self, video_id: str) -> bool:
        """Check if video is already collected using Redis"""
        if not self.redis.enabled:
            return False
        
        try:
            key = f"instance_{self.instance_id}:video:{video_id}"
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    def _mark_as_collected(self, video_id: str):
        """Mark video as collected in Redis"""
        if not self.redis.enabled:
            return
        
        try:
            key = f"instance_{self.instance_id}:video:{video_id}"
            # Store for 24 hours (86400 seconds) for better deduplication across longer runs
            self.redis.setex(key, 86400, "1")
        except Exception as e:
            logger.error(f"Error marking video: {e}")
    
    def _title_contains_keyword(self, title: str, keyword: str, exact_match: bool = True) -> bool:
        """
        Check if the title contains the keyword based on exact_match setting.
        
        When exact_match=True:
        - Keywords must appear as a complete unit (spaces/dashes/no-spaces are interchangeable)
        - "Brain Map" matches "brain map", "brainmap", "brain-map"
        
        When exact_match=False:
        - All words from keyword must appear somewhere in title (any order)
        - "Master AI" matches "I am master of virtual AI"
        
        Args:
            title: Video title
            keyword: Search keyword
            exact_match: If True, use exact phrase matching. If False, match all words anywhere.
            
        Returns:
            bool: True if keyword matches according to exact_match rules
        """
        # Convert to lowercase for case-insensitive comparison
        title_lower = title.lower()
        keyword_lower = keyword.lower()
        
        if exact_match:
            # Check for exact phrase match
            if keyword_lower in title_lower:
                return True
            
            # For multi-word keywords, also check hyphenated and no-space versions
            if ' ' in keyword_lower:
                # Check hyphenated version: "brain map" -> "brain-map"
                hyphenated_keyword = keyword_lower.replace(' ', '-')
                if hyphenated_keyword in title_lower:
                    return True
                
                # Check no-space version: "brain map" -> "brainmap"
                no_space_keyword = keyword_lower.replace(' ', '')
                if no_space_keyword in title_lower:
                    return True
        else:
            # Non-exact match: all words must be present somewhere in title
            keyword_words = keyword_lower.split()
            for word in keyword_words:
                if word not in title_lower:
                    return False
            return True
        
        return False
    
    def _save_to_firebase(self, keyword: str, video_data: Dict) -> bool:
        """Save video to Firebase"""
        try:
            # Ensure video_id is clean (no /shorts/ prefix)
            video_id = video_data['id'].replace('shorts/', '').replace('/shorts/', '')
            video_data['id'] = video_id
            
            # Check if video already exists (by video_id)
            videos_ref = self.firebase.db.collection('youtube_videos').document(keyword).collection('videos')
            existing = videos_ref.where('id', '==', video_id).limit(1).stream()
            if any(existing):
                logger.debug(f"Video {video_id} already exists, skipping")
                return False
            
            # Ensure parent document exists (required for subcollections)
            parent_ref = self.firebase.db.collection('youtube_videos').document(keyword)
            if not parent_ref.get().exists:
                parent_ref.set({
                    'keyword': keyword,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow(),
                    'note': 'Parent document for videos subcollection'
                })
                logger.debug(f"Created parent document for keyword: {keyword}")
            
            # Create timestamp-based document ID for efficient time-range queries
            collected_at = datetime.utcnow()
            # Use ISO 8601 timestamp as document ID for efficient interval metrics
            doc_id = collected_at.isoformat() + 'Z'  # Format: 2025-08-10T18:30:02.249361Z
            
            # Update collected_at to match document ID timestamp
            video_data['collected_at'] = collected_at.isoformat()
            
            # Store in Firebase with timestamp as document ID
            self.firebase.db.collection('youtube_videos').document(keyword).collection('videos').document(doc_id).set(video_data)
            
            logger.debug(f"Saved video {video_id} to Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Firebase: {e}")
            return False

    async def _scrape_with_pagination(self, search_url: str, keyword: str, exact_match: bool, max_videos: int) -> tuple[List[Dict], int]:
        """Scrape YouTube with pagination using Playwright through VPN container"""
        videos = []
        filtered_count = 0
        
        try:
            # Use docker exec to run Playwright inside the VPN container
            playwright_script = self._generate_playwright_script(search_url, keyword, exact_match, max_videos)
            
            # Write the script to a temporary file
            script_path = "/tmp/youtube_pagination_script.py"
            with open(script_path, 'w') as f:
                f.write(playwright_script)
            
            # Copy script to container and execute
            subprocess.run([
                'docker', 'cp', script_path, f'{self.container_name}:/tmp/youtube_pagination_script.py'
            ], check=True)
            
            # Execute the Playwright script inside the VPN container
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'python3', '/tmp/youtube_pagination_script.py'
            ], capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0 and result.stdout:
                # Parse the JSON result
                try:
                    data = json.loads(result.stdout)
                    videos = data.get('videos', [])
                    filtered_count = data.get('filtered_count', 0)
                    logger.info(f"Pagination scraping successful: {len(videos)} videos, {filtered_count} filtered")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse Playwright output: {e}")
                    return [], 0
            else:
                logger.error(f"Playwright scraping failed: {result.stderr}")
                return [], 0
                
        except Exception as e:
            logger.error(f"Error in pagination scraping: {e}")
            return [], 0
        
        return videos, filtered_count
    
    def _generate_playwright_script(self, search_url: str, keyword: str, exact_match: bool, max_videos: int) -> str:
        """Generate a Playwright script for pagination scraping"""
        return f'''#!/usr/bin/env python3
import asyncio
import json
import re
import random
from playwright.async_api import async_playwright

async def scrape_with_pagination():
    videos = []
    filtered_count = 0
    
    async with async_playwright() as p:
        # Launch browser with anti-detection
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            ]
        )
        
        try:
            page = await browser.new_page()
            
            # Set viewport and extra headers
            await page.set_viewport_size({{"width": 1920, "height": 1080}})
            await page.set_extra_http_headers({{
                'Accept-Language': 'en-US,en;q=0.9'
            }})
            
            # Navigate to search URL
            await page.goto("{search_url}", wait_until="networkidle", timeout=60000)
            await asyncio.sleep(random.uniform(2, 4))
            
            # Handle cookie consent if present
            try:
                cookie_button = await page.wait_for_selector(
                    'button[aria-label*="Accept"], button[aria-label*="cookies"], tp-yt-paper-button:has-text("Accept")',
                    timeout=5000
                )
                if cookie_button:
                    await cookie_button.click()
                    await asyncio.sleep(2)
            except:
                pass
            
            scroll_attempts = 0
            max_scrolls = {self.max_scroll_attempts}
            last_video_count = 0
            no_new_videos_count = 0
            
            while len(videos) < {max_videos} and scroll_attempts < max_scrolls:
                # Extract videos from current view
                current_videos = await extract_videos_from_page(page, "{keyword}")
                
                # Process new videos
                new_videos = []
                for video in current_videos:
                    # Check if we already have this video
                    if not any(v['id'] == video['id'] for v in videos):
                        if video.get('filtered'):
                            filtered_count += 1
                        else:
                            new_videos.append(video)
                
                videos.extend(new_videos)
                
                # Check if we found new videos
                if len(videos) == last_video_count:
                    no_new_videos_count += 1
                    if no_new_videos_count >= 3:  # Stop if no new videos for 3 scrolls
                        break
                else:
                    no_new_videos_count = 0
                    last_video_count = len(videos)
                
                # Check if we have enough
                if len(videos) >= {max_videos}:
                    break
                
                # Scroll for more results
                await page.evaluate("""() => {{
                    window.scrollBy(0, window.innerHeight * 0.8);
                }}""")
                
                # Human-like delay
                await asyncio.sleep(random.uniform(1.5, 3.0))
                scroll_attempts += 1
            
        finally:
            await browser.close()
    
    # Return results as JSON
    result = {{
        'videos': videos[:{max_videos}],
        'filtered_count': filtered_count
    }}
    print(json.dumps(result))

async def extract_videos_from_page(page, keyword):
    """Extract video data from current page view"""
    videos = []
    strict_filter = {str(self.strict_title_filter).lower()}
    
    try:
        # Get all video elements
        video_elements = await page.query_selector_all('div[class*="ytd-video-renderer"]')
        
        for element in video_elements:
            try:
                # Extract video ID from link
                link_element = await element.query_selector('a#video-title')
                if not link_element:
                    continue
                    
                href = await link_element.get_attribute('href')
                if not href or '/watch?v=' not in href:
                    continue
                    
                video_id = href.split('/watch?v=')[1].split('&')[0]
                
                # Extract title
                title = await link_element.get_attribute('title')
                if not title:
                    title = await link_element.inner_text()
                
                # Check title filtering - exact phrase match
                if strict_filter == 'true':
                    title_lower = title.lower()
                    keyword_lower = keyword.lower()
                    
                    # Check exact phrase or hyphenated version
                    exact_match = (keyword_lower in title_lower or 
                                 ((' ' in keyword_lower) and keyword_lower.replace(' ', '-') in title_lower))
                    
                    if not exact_match:
                        videos.append({{'id': video_id, 'filtered': True}})
                        continue
                
                # Extract other data
                duration_element = await element.query_selector('span.ytd-thumbnail-overlay-time-status-renderer')
                duration = await duration_element.inner_text() if duration_element else ''
                
                view_count_element = await element.query_selector('span.inline-metadata-item')
                view_count = await view_count_element.inner_text() if view_count_element else ''
                
                # Extract channel info
                channel_element = await element.query_selector('a.yt-simple-endpoint.style-scope.yt-formatted-string')
                channel_name = await channel_element.inner_text() if channel_element else ''
                
                # Extract publish time
                publish_element = await element.query_selector('span.inline-metadata-item:nth-child(2)')
                published_time = await publish_element.inner_text() if publish_element else ''
                
                # Extract thumbnail
                thumbnail_element = await element.query_selector('img')
                thumbnail_url = await thumbnail_element.get_attribute('src') if thumbnail_element else ''
                
                video_data = {{
                    'id': video_id,
                    'title': title,
                    'url': f'https://www.youtube.com/watch?v={{video_id}}',
                    'thumbnail_url': thumbnail_url,
                    'duration': duration,
                    'view_count': view_count,
                    'published_time': published_time,
                    'channel_name': channel_name,
                    'keyword': keyword,
                    'collected_at': '{{__import__("datetime").datetime.utcnow().isoformat()}}',
                    'source': 'youtube_scraper_production_paginated'
                }}
                
                videos.append(video_data)
                
            except Exception as e:
                continue
                
    except Exception as e:
        pass
    
    return videos

if __name__ == "__main__":
    asyncio.run(scrape_with_pagination())
'''