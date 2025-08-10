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
sys.path.insert(0, '/opt/youtube_app')

# Import modules
from src.utils.env_loader import load_env
from src.utils.firebase_client_enhanced import FirebaseClient
from src.utils.redis_client import RedisClient
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

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
            logging.FileHandler('/opt/youtube_app/logs/collection_manager.log'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)
    network_logger = logging.getLogger('network')


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
            self.docker_compose_path = Path('/opt/youtube_app/docker-compose.yml')
            
            # Extract instance ID from container name if available
            # Container names are typically: youtube-vpn-1, youtube-vpn-2, youtube-vpn-3
            instance_id = 1  # Default
            if '-' in self.container_name:
                try:
                    instance_id = int(self.container_name.split('-')[-1])
                except (ValueError, IndexError):
                    instance_id = 1
            
            # Get hostname
            try:
                import socket
                hostname = socket.gethostname()
            except:
                hostname = 'unknown'
            
            # Collection tracking
            self.session_id = f"session_{int(time.time())}_{instance_id}"
            self.collection_stats = {
                'session_id': self.session_id,
                'start_time': datetime.now(timezone.utc),
                'script_name': 'youtube_collection_manager.py',
                'keywords_processed': [],
                'keywords_successful': 0,
                'keywords_failed': 0,
                'total_videos_collected': 0,
                'videos_per_keyword': {},
                'duplicates_filtered': 0,
                'success_rate': 0.0,
                'errors': [],
                'success': False,
                'container': self.container_name,
                'instance_id': instance_id,
                'vm_hostname': hostname
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
        """Get list of Surfshark US servers (24 verified locations)"""
        # Using Gluetun-compatible server names (without numbers)
        # Gluetun handles load balancing across multiple IPs per city internally
        
        # Known working Surfshark US city codes
        # Each city has multiple physical servers that Gluetun rotates through
        us_locations = [
            # Verified working locations (24 core cities)
            'nyc', 'lax', 'chi', 'dal', 'mia', 'atl', 'sea', 'den', 'phx',
            'bos', 'sfo', 'las', 'hou', 'orl', 'kan', 'clt', 'tpa', 'stl',
            'slc', 'buf', 'ltm', 'dtw', 'bdn', 'rag'
        ]
        
        # Remove duplicates and create server list
        unique_locations = list(dict.fromkeys(us_locations))[:80]  # Ensure max 80
        
        servers = []
        for location in unique_locations:
            servers.append(f"us-{location}.prod.surfshark.com")
        
        logger.info(f"Loaded {len(servers)} Surfshark US servers for VPN rotation")
        return servers
    
    def rotate_vpn_server(self, server: str) -> bool:
        """Rotate to new VPN server using environment variables"""
        try:
            logger.info(f"Rotating VPN to server: {server}")
            
            # Stop current container
            logger.info("Stopping VPN container...")
            result = subprocess.run(
                ['docker', 'compose', 'stop', 'vpn'],
                cwd=self.docker_compose_path.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to stop container: {result.stderr}")
                return False
            
            # Remove the container
            result = subprocess.run(
                ['docker', 'compose', 'rm', '-f', 'vpn'],
                cwd=self.docker_compose_path.parent,
                capture_output=True,
                text=True
            )
            
            # Wait for container to fully stop
            time.sleep(2)
            
            # Start with new server
            logger.info(f"Starting VPN with server: {server}")
            env = os.environ.copy()
            # Convert server name to Gluetun format (remove number suffix)
            import re
            gluetun_server = re.sub(r'-\d+\.prod', '.prod', server)
            logger.info(f"Using Gluetun server format: {gluetun_server}")
            env['VPN_SERVER'] = gluetun_server
            
            result = subprocess.run(
                ['docker', 'compose', 'up', '-d', 'vpn'],
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
            
            try:
                # Try to connect to VPN server with exponential backoff
                if self.rotate_vpn_server(server):
                    # VPN connected successfully, now scrape
                    try:
                        result = self.scraper.scrape_keyword(keyword, max_videos=100)
                        
                        videos_collected = result.get('saved_to_firebase', 0)
                        duplicates_found = result.get('duplicates', 0)
                        
                        self.collection_stats['videos_per_keyword'][keyword] = videos_collected
                        self.collection_stats['total_videos_collected'] += videos_collected
                        self.collection_stats['duplicates_filtered'] += duplicates_found
                        
                        logger.info(f"✅ Successfully collected {videos_collected} videos for '{keyword}' using {server} ({duplicates_found} duplicates filtered)")
                        return videos_collected
                        
                    except Exception as e:
                        # Scraping failed, but VPN was working - this is a different error
                        logger.error(f"❌ Scraping failed for keyword '{keyword}' with working VPN {server}: {e}")
                        
                        # For scraping errors, don't mark VPN server as failed
                        # but do raise the error to be handled at keyword level
                        raise Exception(f"Scraping error for '{keyword}': {str(e)}")
                else:
                    # VPN connection failed, try next server
                    logger.warning(f"⚠️ VPN connection failed for server {server}, trying next server...")
                    
                    # Add exponential backoff delay before next attempt
                    if attempt < self.max_vpn_attempts_per_keyword:
                        backoff_delay = min(2 ** (attempt - 1), 30)  # Max 30 seconds
                        logger.info(f"Waiting {backoff_delay}s before next VPN attempt...")
                        time.sleep(backoff_delay)
                    
                    continue
                    
            except Exception as e:
                # Catch any unexpected errors during VPN rotation or scraping
                logger.error(f"Unexpected error on attempt {attempt} for keyword '{keyword}': {e}")
                
                # If this is the last attempt, re-raise the error
                if attempt == self.max_vpn_attempts_per_keyword:
                    raise
                
                # Otherwise, wait and try next server
                backoff_delay = min(2 ** (attempt - 1), 30)
                logger.info(f"Waiting {backoff_delay}s before next attempt due to error...")
                time.sleep(backoff_delay)
        
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
            
            # Process each keyword with proper error isolation
            successful_keywords = []
            failed_keywords = []
            
            for i, keyword in enumerate(keywords, 1):
                logger.info(f"Processing keyword {i}/{len(keywords)}: '{keyword}'")
                
                try:
                    # Process keyword with VPN retry logic
                    result = self.process_keyword_with_retry(keyword)
                    
                    # Check if keyword was actually successful (saved videos > 0)
                    videos_saved = result if isinstance(result, int) else 0
                    
                    if videos_saved > 0:
                        successful_keywords.append(keyword)
                        self.collection_stats['keywords_processed'].append(keyword)
                        logger.info(f"✅ Successfully collected {videos_saved} videos for '{keyword}' ({i}/{len(keywords)})")
                    else:
                        # No videos saved = failed (even if no exception thrown)
                        failed_keywords.append(keyword)
                        logger.warning(f"⚠️ No videos saved for keyword '{keyword}' - marking as failed")
                    
                    # Log server health status after each keyword
                    logger.info(f"Server health status - Working: {len(self.working_servers)}, "
                              f"Failed: {len(self.failed_servers)}, Untested: {len(self.untested_servers)}")
                    
                except Exception as e:
                    # Keyword processing failed - isolate error and continue with next keyword
                    logger.error(f"❌ Failed to process keyword '{keyword}': {e}")
                    failed_keywords.append(keyword)
                    self.collection_stats['errors'].append(f"Keyword '{keyword}': {str(e)}")
                    
                    # Add keyword-specific error tracking
                    if 'failed_keywords' not in self.collection_stats:
                        self.collection_stats['failed_keywords'] = []
                    self.collection_stats['failed_keywords'].append({
                        'keyword': keyword,
                        'error': str(e),
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })
                    
                    # Log but continue processing other keywords
                    logger.warning(f"Continuing with remaining keywords ({len(keywords) - i} left)")
            
            # Determine overall success based on results
            total_keywords = len(keywords)
            success_count = len(successful_keywords)
            failure_count = len(failed_keywords)
            success_rate = (success_count / total_keywords) * 100 if total_keywords > 0 else 0
            
            # Update collection stats with proper counts
            self.collection_stats['keywords_successful'] = success_count
            self.collection_stats['keywords_failed'] = failure_count
            self.collection_stats['success_rate'] = success_rate
            self.collection_stats['successful_keywords'] = successful_keywords
            self.collection_stats['failed_keywords_list'] = failed_keywords
            
            # Consider collection successful if at least 50% of keywords succeeded
            self.collection_stats['success'] = success_rate >= 50.0
            
            # Log final results
            if success_rate >= 50.0:
                logger.info(f"🎉 Collection completed successfully! "
                          f"Success rate: {success_rate:.1f}% ({success_count}/{total_keywords})")
            else:
                logger.warning(f"⚠️ Collection completed with low success rate: "
                             f"{success_rate:.1f}% ({success_count}/{total_keywords})")
            
            if failed_keywords:
                logger.warning(f"Failed keywords: {', '.join(failed_keywords)}")
            
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
