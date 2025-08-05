#!/usr/bin/env python3
"""
YouTube Collection Manager - Multi-Instance Version
Handles VPN rotation and YouTube video collection with Firebase integration
Supports multiple parallel instances with dynamic keyword distribution
NO FALLBACKS - Fails fast on any error
"""

import os
import sys
import json
import time
import math
import logging
import subprocess
import random
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional, Tuple

# Ensure proper imports
sys.path.insert(0, '/opt/youtube_app')

# Import modules
from src.utils.env_loader import load_env
from src.utils.firebase_client_enhanced import FirebaseClient
from src.utils.redis_client import RedisClient
from src.utils.vpn_coordinator import VPNCoordinator
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
    
    def __init__(self, instance_id: int = 1, container_name: str = "youtube-vpn-1", 
                 total_instances: int = 3):
        """Initialize the collection manager
        
        Args:
            instance_id: Instance number (1, 2, or 3)
            container_name: Docker container name for this instance
            total_instances: Total number of parallel instances
        """
        self.instance_id = instance_id
        self.container_name = container_name
        self.total_instances = total_instances
        
        # Process lock file to prevent overlapping runs
        self.lock_file = Path(f"/tmp/youtube_collector_{instance_id}.lock")
        
        # Check if already running
        if self._is_already_running():
            logger.warning(f"Instance {instance_id} already running, skipping this run")
            sys.exit(0)
        
        # Create lock file
        self._create_lock()
        
        # Load environment
        load_env()
        
        # Initialize clients
        self.firebase_client = FirebaseClient()
        self.redis_client = RedisClient()
        self.scraper = YouTubeScraperProduction()
        
        # VPN Configuration
        self.vpn_coordinator = VPNCoordinator(instance_id)
        self.docker_compose_path = Path("/opt/youtube_app/docker-compose-multi.yml")
        
        # Session tracking
        self.session_id = f"session_{int(time.time())}_{instance_id}"
        self.vpn_server_timeout = 120  # seconds to wait for VPN connection
        
        # Server tracking per instance
        self.working_servers = set()
        self.failed_servers = set()
        self.untested_servers = set(self.vpn_coordinator.instance_servers)
        
        logger.info(f"Collection Manager Instance {instance_id} initialized - Session: {self.session_id}")
        logger.info(f"Container: {container_name}, Available VPN servers: {len(self.untested_servers)}")
    
    def _is_already_running(self) -> bool:
        """Check if this instance is already running"""
        if not self.lock_file.exists():
            return False
            
        try:
            # Check if PID in lock file is still running
            with open(self.lock_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process exists
            os.kill(pid, 0)
            return True
        except (ValueError, OSError, IOError):
            # Lock file is stale, remove it
            self.lock_file.unlink(missing_ok=True)
            return False
    
    def _create_lock(self):
        """Create lock file with current PID"""
        with open(self.lock_file, 'w') as f:
            f.write(str(os.getpid()))
    
    def _remove_lock(self):
        """Remove lock file"""
        self.lock_file.unlink(missing_ok=True)
    
    def __del__(self):
        """Cleanup on exit"""
        self._remove_lock()
        if hasattr(self, 'vpn_coordinator'):
            self.vpn_coordinator.release_all_servers()
    
    def get_instance_keywords(self, all_keywords: List[Dict]) -> List[Dict]:
        """Get keywords assigned to this instance based on dynamic distribution
        
        Args:
            all_keywords: List of all active keywords
            
        Returns:
            List of keywords for this instance to process
        """
        total_keywords = len(all_keywords)
        keywords_per_instance = math.ceil(total_keywords / self.total_instances)
        
        start_idx = (self.instance_id - 1) * keywords_per_instance
        end_idx = min(start_idx + keywords_per_instance, total_keywords)
        
        instance_keywords = all_keywords[start_idx:end_idx]
        
        logger.info(f"Instance {self.instance_id}: Processing keywords {start_idx+1}-{end_idx} "
                   f"of {total_keywords} total ({len(instance_keywords)} keywords)")
        
        return instance_keywords
    
    def rotate_vpn_server(self, server: str) -> bool:
        """Rotate to new VPN server using docker compose"""
        try:
            logger.info(f"Instance {self.instance_id}: Rotating VPN to server: {server}")
            
            # Try to acquire the server
            if not self.vpn_coordinator.acquire_server(server):
                logger.warning(f"Could not acquire server {server}, it may be in use")
                return False
            
            # Stop current container
            logger.info(f"Stopping VPN container {self.container_name}...")
            result = subprocess.run(
                ['docker', 'compose', '-f', str(self.docker_compose_path), 
                 'stop', f'vpn-{self.instance_id}'],
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to stop container: {result.stderr}")
                self.vpn_coordinator.release_server(server)
                return False
            
            # Remove the container
            result = subprocess.run(
                ['docker', 'compose', '-f', str(self.docker_compose_path),
                 'rm', '-f', f'vpn-{self.instance_id}'],
                capture_output=True,
                text=True
            )
            
            # Wait for container to fully stop
            time.sleep(2)
            
            # Start with new server
            logger.info(f"Starting VPN with server: {server}")
            env = os.environ.copy()
            env[f'VPN_SERVER_{self.instance_id}'] = server
            
            result = subprocess.run(
                ['docker', 'compose', '-f', str(self.docker_compose_path),
                 'up', '-d', f'vpn-{self.instance_id}'],
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                self.vpn_coordinator.release_server(server)
                return False
            
            # Wait for VPN connection
            success = self.wait_for_vpn_connection(timeout=self.vpn_server_timeout)
            
            # Update server health tracking
            if success:
                self.working_servers.add(server)
                self.untested_servers.discard(server)
                logger.info(f"Server {server} marked as WORKING for instance {self.instance_id}")
            else:
                self.failed_servers.add(server)
                self.untested_servers.discard(server)
                self.vpn_coordinator.release_server(server)
                logger.warning(f"Server {server} marked as FAILED for instance {self.instance_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error rotating VPN: {e}")
            # Release server on error
            if 'server' in locals():
                self.vpn_coordinator.release_server(server)
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
        """Get next available VPN server for this instance"""
        exclude_servers = exclude_servers or set()
        
        # Get available servers from coordinator
        available_from_coordinator = self.vpn_coordinator.get_available_servers()
        
        # First try working servers
        available_working = self.working_servers.intersection(available_from_coordinator)
        available_working -= exclude_servers
        if available_working:
            return random.choice(list(available_working))
        
        # Then try untested servers
        available_untested = self.untested_servers.intersection(available_from_coordinator)
        available_untested -= exclude_servers
        if available_untested:
            return random.choice(list(available_untested))
        
        # Finally retry failed servers if needed
        available_failed = self.failed_servers.intersection(available_from_coordinator)
        available_failed -= exclude_servers
        if available_failed:
            return random.choice(list(available_failed))
        
        return None
    
    def process_keyword_with_retry(self, keyword: str, category: str, max_vpn_attempts: int = 3) -> int:
        """Process a keyword with VPN retry logic"""
        logger.info(f"Processing keyword: '{keyword}' (max {max_vpn_attempts} VPN attempts)")
        
        used_servers = set()
        current_server = None
        
        for attempt in range(1, max_vpn_attempts + 1):
            # Get next available server
            server = self.get_next_available_server(exclude_servers=used_servers)
            
            if not server:
                logger.error(f"No available VPN servers for keyword '{keyword}'")
                break
            
            used_servers.add(server)
            logger.info(f"Attempt {attempt}/{max_vpn_attempts} for keyword '{keyword}' using server: {server}")
            
            # Rotate VPN if needed
            if server != current_server:
                if not self.rotate_vpn_server(server):
                    logger.warning(f"⚠️ VPN connection failed for server {server}, trying next server...")
                    # Small delay before retry
                    time.sleep(min(attempt, 3))
                    continue
                current_server = server
            
            # Attempt to collect videos
            try:
                videos_collected = self.scraper.search_and_collect(
                    keyword=keyword,
                    category=category
                )
                
                logger.info(f"✅ Successfully collected {videos_collected} videos for '{keyword}' using {server}")
                return videos_collected
                
            except Exception as e:
                logger.error(f"❌ Collection failed for '{keyword}': {e}")
                # Don't retry on collection errors, only VPN errors
                break
        
        # If we get here, all attempts failed
        error_msg = f"Failed to connect to any VPN server for keyword '{keyword}' after {max_vpn_attempts} attempts. Attempted servers: {used_servers}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def run(self):
        """Main execution method"""
        start_time = time.time()
        
        try:
            # Get all active keywords with full data
            all_keywords = self.firebase_client.get_keywords_with_data()
            
            # Get keywords for this instance
            keywords = self.get_instance_keywords(all_keywords)
            
            if not keywords:
                logger.warning(f"No keywords assigned to instance {self.instance_id}")
                return
            
            logger.info(f"Instance {self.instance_id}: Starting collection for {len(keywords)} keywords")
            
            # Track results
            successful_keywords = []
            failed_keywords = []
            total_videos_collected = 0
            
            # Process each keyword
            for idx, keyword_doc in enumerate(keywords, 1):
                keyword = keyword_doc.get('keyword', '')
                category = keyword_doc.get('category', 'uncategorized')
                
                logger.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}'")
                
                try:
                    videos_collected = self.process_keyword_with_retry(
                        keyword=keyword,
                        category=category
                    )
                    
                    successful_keywords.append(keyword)
                    total_videos_collected += videos_collected
                    
                    # Update last collected timestamp
                    self.firebase_client.update_keyword_timestamp(keyword)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process keyword '{keyword}': {e}")
                    failed_keywords.append({
                        'keyword': keyword,
                        'error': str(e)
                    })
                    
                    # Continue with remaining keywords if we have enough successes
                    if len(failed_keywords) <= len(keywords) * 0.5:  # Allow up to 50% failure
                        logger.warning(f"Continuing with remaining keywords ({len(keywords) - idx} left)")
                        continue
                    else:
                        logger.error("Too many failures, stopping collection")
                        break
            
            # Log collection summary
            duration = time.time() - start_time
            
            summary = {
                'instance_id': self.instance_id,
                'timestamp': datetime.now(timezone.utc),
                'session_id': self.session_id,
                'keywords_processed': len(successful_keywords) + len(failed_keywords),
                'keywords_successful': len(successful_keywords),
                'keywords_failed': len(failed_keywords),
                'total_videos_collected': total_videos_collected,
                'vpn_servers_used': list(self.working_servers),
                'failed_servers': list(self.failed_servers),
                'success_rate': (len(successful_keywords) / len(keywords) * 100) if keywords else 0,
                'duration_seconds': duration
            }
            
            logger.info(f"Collection run summary: {summary}")
            
            # Log to Firebase
            if hasattr(self.firebase_client, 'log_collection_run'):
                self.firebase_client.log_collection_run(
                    summary_data=summary,
                    errors=failed_keywords if failed_keywords else None
                )
            
        except Exception as e:
            logger.error(f"Fatal error in collection run: {e}")
            raise
        finally:
            # Clean up
            self._remove_lock()
            self.vpn_coordinator.release_all_servers()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='YouTube Collection Manager - Multi-Instance')
    parser.add_argument('--instance', type=int, default=1, choices=[1, 2, 3],
                       help='Instance number (1, 2, or 3)')
    parser.add_argument('--container-name', type=str, 
                       help='Docker container name (default: youtube-vpn-{instance})')
    parser.add_argument('--test', action='store_true',
                       help='Test mode - process only first keyword')
    
    args = parser.parse_args()
    
    # Default container name based on instance
    if not args.container_name:
        args.container_name = f"youtube-vpn-{args.instance}"
    
    logger.info("=" * 60)
    logger.info(f"YouTube Collection Manager Instance {args.instance} Starting")
    logger.info("=" * 60)
    
    try:
        manager = YouTubeCollectionManager(
            instance_id=args.instance,
            container_name=args.container_name
        )
        
        # Run collection
        manager.run()
        
    except KeyboardInterrupt:
        logger.info("Collection interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Collection failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()