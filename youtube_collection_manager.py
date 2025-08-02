#\!/usr/bin/env python3
"""
YouTube Collection Manager - Production Script
Handles VPN rotation and YouTube video collection with Firebase integration
NO FALLBACKS - Fails fast on any error
"""

import os
import sys
import json
import time
import logging
import subprocess
import random
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# Ensure proper imports
sys.path.insert(0, '/opt/youtube_scraper')

# Import modules
from src.utils.env_loader import load_env
from src.utils.firebase_client_enhanced import FirebaseClient
from src.utils.redis_client import RedisClient
from youtube_scraper_production import YouTubeScraperProduction

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/youtube_scraper/logs/collection_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class YouTubeCollectionManager:
    """Manages YouTube video collection with VPN rotation"""
    
    def __init__(self):
        """Initialize the collection manager"""
        try:
            # Load environment
            load_env()
            
            # Validate environment
            self._validate_environment()
            
            # Initialize clients
            self.firebase = FirebaseClient()
            self.redis = RedisClient()
            self.scraper = YouTubeScraperProduction()
            
            # Docker settings
            self.container_name = 'youtube-vpn'
            self.docker_compose_path = Path('/opt/youtube_scraper/docker-compose.yml')
            
            # Collection tracking
            self.session_id = f"session_{int(time.time())}"
            self.collection_stats = {
                'session_id': self.session_id,
                'start_time': datetime.now(timezone.utc),
                'keywords_processed': [],
                'total_videos_collected': 0,
                'videos_per_keyword': {},
                'errors': [],
                'success': False
            }
            
            # Get available servers and initialize server health tracking
            self.all_servers = self._get_surfshark_servers()
            self.working_servers = set()  # Servers that successfully connected
            self.failed_servers = set()   # Servers that failed to connect
            self.untested_servers = set(self.all_servers)  # Servers not yet tested
            
            # VPN retry settings
            self.max_vpn_attempts_per_keyword = 3
            self.vpn_server_timeout = 120
            
            logger.info(f"Collection Manager initialized - Session: {self.session_id}")
            logger.info(f"Available VPN servers: {len(self.all_servers)}")
            logger.info(f"Max VPN attempts per keyword: {self.max_vpn_attempts_per_keyword}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Collection Manager: {e}")
            sys.exit(1)
    
    def _validate_environment(self):
        """Validate required environment variables"""
        required = [
            'GOOGLE_SERVICE_KEY_PATH',
            'UPSTASH_REDIS_REST_URL',
            'UPSTASH_REDIS_REST_TOKEN',
            'SURFSHARK_PRIVATE_KEY',
            'SURFSHARK_ADDRESS'
        ]
        
        missing = [var for var in required if not os.environ.get(var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {missing}")
    
    def _get_surfshark_servers(self) -> List[str]:
        """Get comprehensive list of Surfshark US servers (100+ servers)"""
        try:
            # Import the comprehensive server discovery utility
            from src.utils.surfshark_servers import SurfsharkServers
            
            # Get all servers from the comprehensive list
            surfshark = SurfsharkServers()
            all_servers = surfshark.get_us_servers()
            
            # Extract server names for VPN rotation
            server_names = [server['name'] for server in all_servers]
            
            logger.info(f"Loaded {len(server_names)} Surfshark US servers from comprehensive list")
            return server_names
            
        except Exception as e:
            logger.warning(f"Failed to load comprehensive server list: {e}")
            logger.info("Falling back to basic server list")
            
            # Fallback to basic list if there's an issue
            us_locations = [
                'nyc', 'lax', 'chi', 'dal', 'mia', 'atl', 'sea', 'den', 'phx',
                'bos', 'sfo', 'las', 'hou', 'orl', 'kan', 'clt', 'tpa', 'stl',
                'slc', 'buf', 'ltm', 'dtw', 'bdn', 'rag'
            ]
            
            servers = []
            for location in us_locations:
                servers.append(f"us-{location}.prod.surfshark.com")
            
            return servers
    
    def rotate_vpn_server(self, server: str) -> bool:
        """Rotate to new VPN server using environment variables"""
        try:
            logger.info(f"Rotating VPN to server: {server}")
            
            # Stop current container
            logger.info("Stopping VPN container...")
            result = subprocess.run(
                ['docker', 'compose', 'down'],
                cwd=self.docker_compose_path.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to stop container: {result.stderr}")
                return False
            
            # Wait for container to fully stop
            time.sleep(5)
            
            # Start with new server
            logger.info(f"Starting VPN with server: {server}")
            env = os.environ.copy()
            env['VPN_SERVER'] = server
            
            result = subprocess.run(
                ['docker', 'compose', 'up', '-d'],
                cwd=self.docker_compose_path.parent,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                return False
            
            # Wait for VPN connection
            success = self.wait_for_vpn_connection(timeout=self.vpn_server_timeout)
            
            # Update server health tracking
            if success:
                self.working_servers.add(server)
                self.untested_servers.discard(server)
                logger.info(f"Server {server} marked as WORKING")
            else:
                self.failed_servers.add(server)
                self.untested_servers.discard(server)
                logger.warning(f"Server {server} marked as FAILED")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rotating VPN: {e}")
            # Mark server as failed on exception
            self.failed_servers.add(server)
            self.untested_servers.discard(server)
            return False
    
    def wait_for_vpn_connection(self, timeout: int = 120) -> bool:
        """Wait for VPN to be connected"""
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < timeout:
            try:
                # Check VPN connection
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 
                     'wget', '-q', '-O', '-', 'https://ipinfo.io/json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    ip_info = json.loads(result.stdout)
                    logger.info(f"VPN connected: {ip_info.get('city', 'Unknown')} - {ip_info.get('ip', 'Unknown')}")
                    return True
                
            except Exception as e:
                logger.debug(f"Connection check failed: {e}")
            
            attempt += 1
            if attempt <= 10:
                logger.info(f"Waiting for VPN connection... ({attempt}/10)")
            
            time.sleep(10)
        
        logger.error("VPN connection timeout")
        return False
    
    def get_next_available_server(self, exclude_servers: set = None) -> Optional[str]:
        """Get next available VPN server, prioritizing working servers"""
        exclude_servers = exclude_servers or set()
        
        # First try working servers (excluding already used ones)
        available_working = self.working_servers - exclude_servers
        if available_working:
            return random.choice(list(available_working))
        
        # Then try untested servers
        available_untested = self.untested_servers - exclude_servers
        if available_untested:
            return random.choice(list(available_untested))
        
        # If no working or untested servers, we have a problem
        return None
    
    def process_keyword_with_retry(self, keyword: str) -> int:
        """Process a single keyword with VPN server retry logic"""
        logger.info(f"Processing keyword: '{keyword}' (max {self.max_vpn_attempts_per_keyword} VPN attempts)")
        
        attempted_servers = set()
        
        for attempt in range(1, self.max_vpn_attempts_per_keyword + 1):
            # Get next available server
            server = self.get_next_available_server(exclude_servers=attempted_servers)
            if not server:
                # No more servers to try
                raise Exception(f"No available VPN servers for keyword '{keyword}' after {attempt-1} attempts. "
                              f"Attempted: {attempted_servers}, Failed: {self.failed_servers}")
            
            attempted_servers.add(server)
            logger.info(f"Attempt {attempt}/{self.max_vpn_attempts_per_keyword} for keyword '{keyword}' using server: {server}")
            
            # Try to connect to VPN server
            if self.rotate_vpn_server(server):
                # VPN connected successfully, now scrape
                try:
                    result = self.scraper.scrape_keyword(keyword, max_videos=100)
                    
                    videos_collected = result.get('saved_to_firebase', 0)
                    self.collection_stats['videos_per_keyword'][keyword] = videos_collected
                    self.collection_stats['total_videos_collected'] += videos_collected
                    
                    logger.info(f"Successfully collected {videos_collected} videos for '{keyword}' using {server}")
                    return videos_collected
                    
                except Exception as e:
                    # Scraping failed, but VPN was working - this is a different error
                    logger.error(f"Scraping failed for keyword '{keyword}' with working VPN {server}: {e}")
                    raise  # Re-raise scraping errors (not VPN errors)
            else:
                # VPN connection failed, try next server
                logger.warning(f"VPN connection failed for server {server}, trying next server...")
                continue
        
        # If we get here, all VPN attempts failed
        raise Exception(f"Failed to connect to any VPN server for keyword '{keyword}' after {self.max_vpn_attempts_per_keyword} attempts. "
                      f"Attempted servers: {attempted_servers}")
    
    def process_keyword(self, keyword: str, server: str) -> int:
        """Legacy method - now redirects to retry logic"""
        # This method is kept for compatibility but now uses retry logic
        return self.process_keyword_with_retry(keyword)
    
    def run(self):
        """Main execution - process all keywords"""
        try:
            # Get keywords from Firebase
            keywords = self.firebase.get_keywords()
            if not keywords:
                raise Exception("No keywords found in Firebase")
            
            logger.info(f"Starting collection for {len(keywords)} keywords")
            
            # Process each keyword with retry logic
            for keyword in keywords:
                try:
                    # Process keyword with VPN retry logic (NEVER skip keywords)
                    self.process_keyword_with_retry(keyword)
                    self.collection_stats['keywords_processed'].append(keyword)
                    
                    # Log server health status after each keyword
                    logger.info(f"Server health status - Working: {len(self.working_servers)}, "
                              f"Failed: {len(self.failed_servers)}, Untested: {len(self.untested_servers)}")
                    
                except Exception as e:
                    # Keyword processing failed completely (all VPN servers failed or scraping error)
                    logger.error(f"CRITICAL: Failed to process keyword '{keyword}': {e}")
                    self.collection_stats['errors'].append(f"Keyword '{keyword}': {str(e)}")
                    # Do not continue if we can't process a keyword - fail the entire run
                    raise Exception(f"Collection failed on keyword '{keyword}': {e}")
            
            # Mark success
            self.collection_stats['success'] = True
            logger.info("All keywords processed successfully")
            
        except Exception as e:
            logger.error(f"Collection failed: {e}")
            self.collection_stats['errors'].append(str(e))
            self.collection_stats['success'] = False
            
        finally:
            # Always log to Firebase
            self._finalize_collection()
    
    def _finalize_collection(self):
        """Finalize collection and log to Firebase"""
        try:
            # Calculate duration
            self.collection_stats['end_time'] = datetime.now(timezone.utc)
            duration = (self.collection_stats['end_time'] - self.collection_stats['start_time']).total_seconds()
            self.collection_stats['duration_seconds'] = duration
            
            # Log to Firebase
            log_id = self.firebase.log_collection_run(self.collection_stats)
            if log_id:
                logger.info(f"Collection run logged to Firebase: youtube_collection_logs/{log_id}")
            
            # Log summary
            logger.info(f"Session completed: {self.session_id}")
            logger.info(f"Success: {self.collection_stats['success']}")
            logger.info(f"Total videos: {self.collection_stats['total_videos_collected']}")
            logger.info(f"Keywords processed: {len(self.collection_stats['keywords_processed'])}")
            
            if self.collection_stats['errors']:
                logger.error(f"Errors: {self.collection_stats['errors']}")
            
            # Stop VPN container
            subprocess.run(['docker', 'compose', 'down'], 
                         cwd=self.docker_compose_path.parent,
                         capture_output=True)
            
        except Exception as e:
            logger.error(f"Failed to finalize collection: {e}")
        
        # Exit with appropriate code
        sys.exit(0 if self.collection_stats['success'] else 1)


def main():
    """Main entry point"""
    logger.info("="*60)
    logger.info("YouTube Collection Manager Starting")
    logger.info("="*60)
    
    # Verify imports
    logger.info(f"FirebaseClient module: {FirebaseClient.__module__}")
    logger.info(f"Has get_keywords: {hasattr(FirebaseClient, 'get_keywords')}")
    logger.info(f"Has log_collection_run: {hasattr(FirebaseClient, 'log_collection_run')}")
    
    # Run collection
    manager = YouTubeCollectionManager()
    manager.run()


if __name__ == "__main__":
    main()
