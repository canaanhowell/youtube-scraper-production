#!/usr/bin/env python3
"""
YouTube Collection Manager - Simple Multi-Instance Version
Works with pre-configured VPN containers without trying to change servers
"""

import os
import sys
import json
import time
import math
import logging
import subprocess
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional

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
    """Simple collection manager that works with existing VPN containers"""
    
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
        self.scraper = YouTubeScraperProduction(container_name=container_name, instance_id=instance_id)
        
        # Session tracking
        self.session_id = f"session_{int(time.time())}_{instance_id}"
        
        logger.info(f"Collection Manager Instance {instance_id} initialized - Session: {self.session_id}")
        logger.info(f"Using VPN container: {container_name}")
    
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
    
    def verify_vpn_connection(self) -> bool:
        """Verify VPN container is connected"""
        try:
            # Check if container is running
            cmd = ['docker', 'ps', '-q', '-f', f'name={self.container_name}']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if not result.stdout.strip():
                logger.error(f"Container {self.container_name} is not running")
                return False
            
            # Check if healthy
            cmd = ['docker', 'inspect', self.container_name, '--format', '{{.State.Health.Status}}']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            health_status = result.stdout.strip()
            logger.info(f"Container health status: {health_status}")
            
            if result.returncode == 0 and health_status == 'healthy':
                logger.info(f"VPN container {self.container_name} is healthy and ready")
                return True
            
            logger.error(f"VPN container {self.container_name} is not healthy (status: {health_status})")
            return False
            
        except Exception as e:
            logger.error(f"Error verifying VPN connection: {e}")
            return False
    
    def process_keyword(self, keyword: str, category: str, exact_match: bool = True, max_retries: int = 3) -> int:
        """Process a keyword with simple retry logic"""
        logger.info(f"Processing keyword: '{keyword}' (exact_match={exact_match})")
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Attempt {attempt}/{max_retries} for keyword '{keyword}'")
                
                # Collect videos
                result = self.scraper.scrape_keyword(keyword, exact_match=exact_match)
                videos_collected = result.get('saved_to_firebase', 0)
                
                logger.info(f"✅ Successfully collected {videos_collected} videos for '{keyword}'")
                return videos_collected
                
            except Exception as e:
                logger.error(f"❌ Collection failed for '{keyword}' (attempt {attempt}): {e}")
                
                if attempt < max_retries:
                    logger.info(f"Waiting 10 seconds before retry...")
                    time.sleep(10)
                else:
                    raise
        
        # If we get here, all attempts failed
        raise Exception(f"Failed to collect '{keyword}' after {max_retries} attempts")
    
    def run(self):
        """Main execution method"""
        start_time = time.time()
        
        # Initialize tracking variables
        successful_keywords = []
        failed_keywords = []
        total_videos_collected = 0
        videos_per_keyword = {}
        keywords_processed = []
        vpn_servers_used = []
        
        try:
            # Verify VPN is connected
            if not self.verify_vpn_connection():
                raise Exception(f"VPN container {self.container_name} is not connected")
                
            # Track VPN server being used
            vpn_servers_used.append(self.container_name)
            
            # Get all active keywords with full data
            all_keywords = self.firebase_client.get_keywords_with_data()
            
            # Get keywords for this instance
            keywords = self.get_instance_keywords(all_keywords)
            
            if not keywords:
                logger.warning(f"No keywords assigned to instance {self.instance_id}")
                return
            
            logger.info(f"Instance {self.instance_id}: Starting collection for {len(keywords)} keywords")
            
            # Process each keyword
            for idx, keyword_doc in enumerate(keywords, 1):
                keyword = keyword_doc.get('keyword', '')
                category = keyword_doc.get('category', 'uncategorized')
                exact_match = keyword_doc.get('exact_match', True)  # Default to True if not specified
                
                logger.info(f"Processing keyword {idx}/{len(keywords)}: '{keyword}' (exact_match={exact_match})")
                
                try:
                    videos_collected = self.process_keyword(
                        keyword=keyword,
                        category=category,
                        exact_match=exact_match
                    )
                    
                    successful_keywords.append(keyword)
                    keywords_processed.append(keyword)
                    total_videos_collected += videos_collected
                    videos_per_keyword[keyword] = videos_collected
                    
                    # Update last collected timestamp
                    self.firebase_client.update_keyword_timestamp(keyword)
                    
                    # Small delay between keywords
                    if idx < len(keywords):
                        time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ Failed to process keyword '{keyword}': {e}")
                    failed_keywords.append({
                        'keyword': keyword,
                        'error': str(e)
                    })
                    keywords_processed.append(keyword)
                    videos_per_keyword[keyword] = 0
            
            # Log collection summary
            duration = time.time() - start_time
            
            # Determine success
            success = len(successful_keywords) > 0 and (len(successful_keywords) / len(keywords) >= 0.5)
            
            # Get hostname
            try:
                import socket
                hostname = socket.gethostname()
            except:
                hostname = 'unknown'
            
            summary = {
                'timestamp': datetime.now(timezone.utc),
                'timestamp_readable': datetime.now(timezone.utc).isoformat(),
                'timestamp_unix': time.time(),
                'session_id': self.session_id,
                'keywords_processed': keywords_processed,
                'total_videos_collected': total_videos_collected,
                'videos_per_keyword': videos_per_keyword,
                'duration_seconds': duration,
                'success': success,
                'errors': [err['error'] for err in failed_keywords],
                'vpn_servers_used': vpn_servers_used,
                'redis_enabled': True,
                'duplicates_filtered': 0,  # TODO: track this in scraper
                'container': self.container_name,
                'vm_hostname': hostname,
                'instance_id': self.instance_id,
                'keywords_successful': len(successful_keywords),
                'keywords_failed': len(failed_keywords),
                'success_rate': (len(successful_keywords) / len(keywords) * 100) if keywords else 0
            }
            
            logger.info(f"Collection run summary: {summary}")
            
            # Log to Firebase
            if hasattr(self.firebase_client, 'log_collection_run'):
                self.firebase_client.log_collection_run(
                    collection_stats=summary
                )
            
        except Exception as e:
            logger.error(f"Fatal error in collection run: {e}")
            raise
        finally:
            # Clean up
            self._remove_lock()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='YouTube Collection Manager - Simple Multi-Instance')
    parser.add_argument('--instance', type=int, default=1, choices=[1, 2, 3],
                       help='Instance number (1, 2, or 3)')
    parser.add_argument('--container-name', type=str, 
                       help='Docker container name (default: youtube-vpn-{instance})')
    
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