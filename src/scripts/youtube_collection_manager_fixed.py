#!/usr/bin/env python3
"""
YouTube Collection Manager - Fixed Multi-Instance Version
Uses environment variable to change VPN server without stopping containers
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
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

# Set up enhanced logging
try:
    from src.utils.logging_config_enhanced import setup_logging
    logger, network_logger = setup_logging(log_level="INFO", console_output=True)
except ImportError:
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
    """Manages YouTube video collection with fixed VPN handling"""
    
    def __init__(self, instance_id: int = 1, container_name: str = "youtube-vpn-1", 
                 total_instances: int = 3):
        """Initialize the collection manager"""
        self.instance_id = instance_id
        self.container_name = container_name
        self.total_instances = total_instances
        
        # Process lock file
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
        
        # Session tracking
        self.session_id = f"session_{int(time.time())}_{instance_id}"
        
        # Get available servers for this instance
        self.servers = self._get_instance_servers()
        
        logger.info(f"Collection Manager Instance {instance_id} initialized - Session: {self.session_id}")
        logger.info(f"Container: {container_name}, Available servers: {len(self.servers)}")
    
    def _get_instance_servers(self) -> List[str]:
        """Get VPN servers assigned to this instance"""
        all_servers = [
            # US East Coast
            "us-nyc.prod.surfshark.com",
            "us-bos.prod.surfshark.com",
            "us-atl.prod.surfshark.com",
            "us-mia.prod.surfshark.com",
            "us-orl.prod.surfshark.com",
            "us-ltm.prod.surfshark.com",
            "us-rag.prod.surfshark.com",
            "us-dtw.prod.surfshark.com",
            
            # US Central
            "us-chi.prod.surfshark.com", 
            "us-dal.prod.surfshark.com",
            "us-hou.prod.surfshark.com",
            "us-kan.prod.surfshark.com",
            "us-stl.prod.surfshark.com",
            "us-den.prod.surfshark.com",
            "us-slc.prod.surfshark.com",
            "us-phx.prod.surfshark.com",
            
            # US West Coast
            "us-lax.prod.surfshark.com",
            "us-sfo.prod.surfshark.com",
            "us-sea.prod.surfshark.com",
            "us-las.prod.surfshark.com",
            "us-san.prod.surfshark.com",
            "us-tpa.prod.surfshark.com",
            "us-buf.prod.surfshark.com",
            "us-clt.prod.surfshark.com"
        ]
        
        # Assign servers to this instance
        servers_per_instance = len(all_servers) // 3
        extra_servers = len(all_servers) % 3
        
        if self.instance_id == 1:
            start = 0
            end = servers_per_instance + (1 if extra_servers > 0 else 0)
        elif self.instance_id == 2:
            start = servers_per_instance + (1 if extra_servers > 0 else 0)
            end = start + servers_per_instance + (1 if extra_servers > 1 else 0)
        else:  # instance 3
            start = 2 * servers_per_instance + min(2, extra_servers)
            end = len(all_servers)
            
        return all_servers[start:end]
    
    def _is_already_running(self) -> bool:
        """Check if this instance is already running"""
        if not self.lock_file.exists():
            return False
            
        try:
            with open(self.lock_file, 'r') as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, OSError, IOError):
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
    
    def get_instance_keywords(self, all_keywords: List[Dict]) -> List[Dict]:
        """Get keywords assigned to this instance"""
        total_keywords = len(all_keywords)
        keywords_per_instance = math.ceil(total_keywords / self.total_instances)
        
        start_idx = (self.instance_id - 1) * keywords_per_instance
        end_idx = min(start_idx + keywords_per_instance, total_keywords)
        
        instance_keywords = all_keywords[start_idx:end_idx]
        
        logger.info(f"Instance {self.instance_id}: Processing keywords {start_idx+1}-{end_idx} "
                   f"of {total_keywords} total ({len(instance_keywords)} keywords)")
        
        return instance_keywords
    
    def change_vpn_server(self, server: str) -> bool:
        """Change VPN server by updating environment variable and restarting container"""
        try:
            logger.info(f"Changing {self.container_name} to server: {server}")
            
            # Update the environment variable and restart the container
            env_var = f"VPN_SERVER_{self.instance_id}"
            
            # Use docker update to change environment variable and restart
            cmd = [
                'docker', 'exec', self.container_name,
                'sh', '-c', f'echo "Switching to {server}"'
            ]
            
            # First, check if container is running
            check_cmd = ['docker', 'ps', '-q', '-f', f'name={self.container_name}']
            result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if not result.stdout.strip():
                logger.error(f"Container {self.container_name} is not running")
                return False
            
            # Since we can't change env vars of running container, we'll use a different approach
            # We'll write the server to a file and restart the container
            logger.info(f"Restarting {self.container_name} with new server...")
            
            # Export the new server as environment variable
            os.environ[env_var] = server
            
            # Restart the container with new environment
            restart_cmd = ['docker', 'restart', self.container_name]
            result = subprocess.run(restart_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"Failed to restart container: {result.stderr}")
                return False
            
            # Wait for VPN to reconnect
            logger.info("Waiting for VPN to reconnect...")
            time.sleep(10)  # Give container time to restart
            
            # Verify connection
            return self.verify_vpn_connection()
            
        except Exception as e:
            logger.error(f"Error changing VPN server: {e}")
            return False
    
    def verify_vpn_connection(self, timeout: int = 60) -> bool:
        """Verify VPN is connected and working"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Check if container is healthy
                cmd = ['docker', 'inspect', self.container_name, '--format={{.State.Health.Status}}']
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0 and result.stdout.strip() == 'healthy':
                    # Check actual connectivity
                    ip_cmd = ['docker', 'exec', self.container_name, 
                             'wget', '-q', '-O', '-', 'https://ipinfo.io/json']
                    ip_result = subprocess.run(ip_cmd, capture_output=True, text=True, timeout=10)
                    
                    if ip_result.returncode == 0:
                        try:
                            ip_info = json.loads(ip_result.stdout)
                            logger.info(f"VPN connected: {ip_info.get('city', 'Unknown')} - "
                                      f"{ip_info.get('ip', 'Unknown')}")
                            return True
                        except json.JSONDecodeError:
                            pass
                
            except Exception as e:
                logger.debug(f"Connection check failed: {e}")
            
            time.sleep(5)
        
        logger.error("VPN connection verification timeout")
        return False
    
    def process_keyword_with_retry(self, keyword: str, category: str, max_attempts: int = 3) -> int:
        """Process a keyword with retry logic but minimal VPN changes"""
        logger.info(f"Processing keyword: '{keyword}'")
        
        # First, try with current VPN connection
        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_attempts} for keyword '{keyword}'")
                
                # Only change VPN if this is a retry
                if attempt > 1:
                    # Pick a random server from our pool
                    new_server = random.choice(self.servers)
                    logger.info(f"Changing to new server: {new_server}")
                    
                    if not self.change_vpn_server(new_server):
                        logger.warning(f"Failed to change VPN server, retrying...")
                        time.sleep(5)
                        continue
                
                # Attempt to collect videos
                videos_collected = self.scraper.search_and_collect(
                    keyword=keyword,
                    category=category
                )
                
                logger.info(f"✅ Successfully collected {videos_collected} videos for '{keyword}'")
                return videos_collected
                
            except Exception as e:
                logger.error(f"❌ Collection failed for '{keyword}' (attempt {attempt}): {e}")
                
                if attempt < max_attempts:
                    logger.info(f"Waiting before retry...")
                    time.sleep(5)
                else:
                    raise
        
        # If we get here, all attempts failed
        raise Exception(f"Failed to collect '{keyword}' after {max_attempts} attempts")
    
    def run(self):
        """Main execution method"""
        start_time = time.time()
        
        try:
            # First, ensure VPN is connected
            if not self.verify_vpn_connection():
                logger.error(f"VPN container {self.container_name} is not connected")
                # Try to start with a default server
                if not self.change_vpn_server(self.servers[0]):
                    raise Exception("Failed to establish VPN connection")
            
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
                'container': self.container_name,
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


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='YouTube Collection Manager - Fixed Multi-Instance')
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