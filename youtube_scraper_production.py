#!/usr/bin/env python3
import os
import sys
import json
import time
import re
import logging
import subprocess
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

class YouTubeScraperProduction:
    def __init__(self):
        # Load environment
        load_env()
        
        # Initialize clients
        self.firebase = FirebaseClient()
        self.redis = RedisClient()
        
        # Container name for VPN
        self.container_name = "youtube-vpn"
        
        logger.info("Production YouTube scraper initialized")
    
    def scrape_keyword(self, keyword: str, max_videos: int = 1000) -> Dict:
        """Scrape YouTube for a keyword and save to Firebase"""
        try:
            logger.info(f"Starting scrape for keyword: {keyword}")
            start_time = datetime.utcnow()
            
            # Build YouTube search URL with 24-hour filter
            search_url = f'https://www.youtube.com/results?search_query={keyword.replace(" ", "+")}&sp=EgIIAQ%253D%253D'
            logger.info(f"Search URL: {search_url}")
            
            # Get page content through VPN container
            html_content = self._fetch_youtube_page(search_url)
            if not html_content:
                logger.error(f"Failed to fetch content for {keyword}")
                return {'keyword': keyword, 'videos': [], 'error': 'Failed to fetch content'}
            
            # Extract videos from HTML using ytInitialData
            videos = self._extract_videos_from_initial_data(html_content, keyword)
            logger.info(f"Extracted {len(videos)} total videos")
            
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
    
    def _extract_videos_from_initial_data(self, html_content: str, keyword: str) -> List[Dict]:
        """Extract video data from YouTube's ytInitialData"""
        videos = []
        
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
                        video_data = self._parse_video_renderer(item['videoRenderer'], keyword)
                        if video_data:
                            videos.append(video_data)
            
            logger.info(f"Extracted {len(videos)} videos from ytInitialData")
            return videos
            
        except Exception as e:
            logger.error(f"Error extracting videos: {e}", exc_info=True)
            return []
    
    def _parse_video_renderer(self, video_renderer: Dict, keyword: str) -> Optional[Dict]:
        """Parse a videoRenderer object into our video data format"""
        try:
            video_id = video_renderer.get('videoId', '')
            if not video_id:
                return None
            
            # Extract title
            title_runs = video_renderer.get('title', {}).get('runs', [])
            title = ' '.join(run.get('text', '') for run in title_runs) if title_runs else ''
            
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
            key = f"video:{video_id}"
            return self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking duplicate: {e}")
            return False
    
    def _mark_as_collected(self, video_id: str):
        """Mark video as collected in Redis"""
        if not self.redis.enabled:
            return
        
        try:
            key = f"video:{video_id}"
            # Store for 24 hours (86400 seconds) for better deduplication across longer runs
            self.redis.setex(key, 86400, "1")
        except Exception as e:
            logger.error(f"Error marking video: {e}")
    
    def _save_to_firebase(self, keyword: str, video_data: Dict) -> bool:
        """Save video to Firebase"""
        try:
            # Ensure video_id is clean (no /shorts/ prefix)
            video_id = video_data['id'].replace('shorts/', '').replace('/shorts/', '')
            video_data['id'] = video_id
            
            # Store in Firebase
            self.firebase.db.collection('youtube_videos').document(keyword).collection('videos').document(video_id).set(video_data)
            
            logger.debug(f"Saved video {video_id} to Firebase")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to Firebase: {e}")
            return False