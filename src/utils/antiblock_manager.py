"""
Anti-detection and anti-block utilities for YouTube scraping
Adapted from X app's anti-block strategies
"""

import time
import random
import asyncio
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger('youtube_scraper.antiblock')


class SmartDelay:
    """Intelligent delay system with human-like patterns"""
    
    def __init__(self):
        self.base_delay = 1.5  # Base delay in seconds
        self.action_history = []
        self.last_long_pause = time.time()
        
    async def wait(self, action_type: str = 'scroll'):
        """Wait with human-like delays"""
        # Base delay with randomization
        delay = self.base_delay + random.uniform(0, 2)
        
        # Adjust delay based on action type
        if action_type == 'search':
            delay += random.uniform(1, 3)
        elif action_type == 'click':
            delay += random.uniform(0.5, 1.5)
        elif action_type == 'type':
            # Typing delay per character
            delay = random.uniform(0.05, 0.15)
            
        # Occasional long pause (human behavior)
        current_time = time.time()
        if current_time - self.last_long_pause > 300:  # Every 5 minutes
            if random.random() < 0.1:  # 10% chance
                delay += random.uniform(5, 15)
                self.last_long_pause = current_time
                logger.info("Taking a long pause (human behavior)")
                
        # Progressive slowdown if many recent actions
        recent_actions = len([a for a in self.action_history 
                            if current_time - a < 60])  # Last minute
        if recent_actions > 10:
            delay *= 1.5
            logger.debug(f"Slowing down due to {recent_actions} recent actions")
            
        await asyncio.sleep(delay)
        self.action_history.append(current_time)
        
        # Clean old history
        self.action_history = [a for a in self.action_history 
                              if current_time - a < 300]  # Keep last 5 minutes


class AdaptiveRateLimiter:
    """Adaptive rate limiting based on response patterns"""
    
    def __init__(self):
        self.request_times = []
        self.error_count = 0
        self.last_error_time = None
        self.backoff_factor = 1.0
        
    async def check_rate_limit(self):
        """Check if we should proceed with request"""
        current_time = time.time()
        
        # Clean old request times
        self.request_times = [t for t in self.request_times 
                             if current_time - t < 60]
        
        # Calculate current rate
        requests_per_minute = len(self.request_times)
        
        # Adaptive limits
        if self.error_count > 0:
            # Exponential backoff on errors
            wait_time = min(60, 2 ** self.error_count * self.backoff_factor)
            if self.last_error_time and current_time - self.last_error_time < wait_time:
                remaining = wait_time - (current_time - self.last_error_time)
                logger.warning(f"Rate limited. Waiting {remaining:.1f}s...")
                await asyncio.sleep(remaining)
                
        # YouTube seems more lenient, but let's be careful
        if requests_per_minute > 30:
            logger.warning("Approaching rate limit, slowing down...")
            await asyncio.sleep(2)
            
        self.request_times.append(current_time)
        
    def record_success(self):
        """Record successful request"""
        self.error_count = max(0, self.error_count - 1)
        self.backoff_factor = max(1.0, self.backoff_factor * 0.9)
        
    def record_error(self):
        """Record failed request"""
        self.error_count += 1
        self.last_error_time = time.time()
        self.backoff_factor = min(5.0, self.backoff_factor * 1.2)
        logger.warning(f"Error recorded. Count: {self.error_count}, Backoff: {self.backoff_factor}")


class MouseSimulator:
    """Simulate human-like mouse movements"""
    
    @staticmethod
    async def human_like_hover(page, element):
        """Move mouse to element with human-like movement"""
        try:
            # Get element position
            box = await element.bounding_box()
            if not box:
                return
                
            # Add some randomness to target position
            x = box['x'] + box['width'] * random.uniform(0.3, 0.7)
            y = box['y'] + box['height'] * random.uniform(0.3, 0.7)
            
            # Move mouse with some intermediate points
            current_x, current_y = 0, 0
            steps = random.randint(2, 4)
            
            for i in range(steps):
                # Intermediate point with some curve
                next_x = current_x + (x - current_x) * (i + 1) / steps
                next_y = current_y + (y - current_y) * (i + 1) / steps
                
                # Add slight randomness
                next_x += random.uniform(-5, 5)
                next_y += random.uniform(-5, 5)
                
                await page.mouse.move(next_x, next_y)
                await asyncio.sleep(random.uniform(0.01, 0.03))
                
                current_x, current_y = next_x, next_y
                
            # Final position
            await page.mouse.move(x, y)
            
        except Exception as e:
            logger.debug(f"Mouse simulation error: {e}")


class ScrollBehavior:
    """Human-like scrolling patterns"""
    
    @staticmethod
    async def human_scroll(page, direction: str = 'down'):
        """Perform human-like scroll"""
        # Scroll distance with variability
        base_distance = 300 if direction == 'down' else -300
        distance = base_distance + random.randint(-100, 100)
        
        # Sometimes scroll smoothly, sometimes in chunks
        if random.random() < 0.7:  # 70% smooth scroll
            steps = random.randint(3, 7)
            for _ in range(steps):
                await page.evaluate(f'window.scrollBy(0, {distance / steps})')
                await asyncio.sleep(random.uniform(0.01, 0.05))
        else:  # 30% instant scroll
            await page.evaluate(f'window.scrollBy(0, {distance})')
            
        # Random pause after scroll
        await asyncio.sleep(random.uniform(0.5, 1.5))
        
    @staticmethod
    async def read_pause(page):
        """Simulate reading pause"""
        # Get current viewport content
        in_viewport = await page.evaluate('''
            () => {
                const elements = document.elementsFromPoint(
                    window.innerWidth / 2, 
                    window.innerHeight / 2
                );
                return elements.length;
            }
        ''')
        
        # Longer pause if there's content to "read"
        if in_viewport > 5:
            await asyncio.sleep(random.uniform(2, 5))
        else:
            await asyncio.sleep(random.uniform(0.5, 1.5))


class BlockDetector:
    """Detect various forms of blocking or rate limiting"""
    
    def __init__(self):
        self.indicators = {
            'captcha': [
                'recaptcha',
                'captcha',
                'challenge',
                'verify you\'re human',
                'suspicious activity'
            ],
            'rate_limit': [
                'too many requests',
                'slow down',
                'try again later',
                'rate limit',
                'quota exceeded'
            ],
            'blocked': [
                'blocked',
                'banned',
                'suspended',
                'violation',
                'terms of service'
            ]
        }
        
    async def check_for_blocks(self, page) -> Optional[str]:
        """Check page for blocking indicators"""
        try:
            # Get page content
            content = await page.content()
            content_lower = content.lower()
            
            # Check URL for indicators
            url = page.url
            if 'sorry' in url or 'blocked' in url:
                return 'blocked'
                
            # Check for various block types
            for block_type, keywords in self.indicators.items():
                for keyword in keywords:
                    if keyword in content_lower:
                        logger.warning(f"Detected {block_type}: {keyword}")
                        return block_type
                        
            # Check for specific YouTube blocks
            if 'youtube.com/sorry' in url:
                return 'rate_limit'
                
            # Check if results are loading
            video_count = await page.query_selector_all('ytd-video-renderer')
            if len(video_count) == 0 and 'search' in url:
                # Wait a bit more
                await asyncio.sleep(3)
                video_count = await page.query_selector_all('ytd-video-renderer')
                if len(video_count) == 0:
                    logger.warning("No search results found - possible shadow ban")
                    return 'no_results'
                    
            return None
            
        except Exception as e:
            logger.error(f"Error checking for blocks: {e}")
            return None


class BrowserFingerprint:
    """Randomize browser fingerprint"""
    
    @staticmethod
    def get_random_viewport() -> Dict[str, int]:
        """Get random realistic viewport size"""
        viewports = [
            {'width': 1920, 'height': 1080},  # Full HD
            {'width': 1366, 'height': 768},   # Common laptop
            {'width': 1536, 'height': 864},   # Surface
            {'width': 1440, 'height': 900},   # MacBook
            {'width': 1680, 'height': 1050},  # Larger screen
            {'width': 2560, 'height': 1440},  # 2K
        ]
        return random.choice(viewports)
        
    @staticmethod
    def get_random_user_agent() -> str:
        """Get random user agent"""
        user_agents = [
            # Chrome on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            # Firefox on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0',
            # Chrome on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            # Safari on Mac
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            # Edge on Windows
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0'
        ]
        return random.choice(user_agents)
        
    @staticmethod
    def get_random_locale() -> Tuple[str, str]:
        """Get random locale and timezone"""
        locales = [
            ('en-US', 'America/New_York'),
            ('en-US', 'America/Chicago'),
            ('en-US', 'America/Los_Angeles'),
            ('en-GB', 'Europe/London'),
            ('en-CA', 'America/Toronto'),
            ('en-AU', 'Australia/Sydney'),
        ]
        return random.choice(locales)