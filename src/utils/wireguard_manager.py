#!/usr/bin/env python3
"""
WireGuard Manager for Direct VPN YouTube Scraper - Fixed Version
Manages WireGuard connections to Surfshark servers with better DNS handling
"""

import os
import subprocess
import time
import json
import random
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

logger = logging.getLogger(__name__)


class WireGuardManager:
    """Manages WireGuard VPN connections with Surfshark"""
    
    def __init__(self):
        self.current_server = None
        self.current_ip = None
        self.cache_file = Path("/opt/youtube_scraper/vpn_cache.json")
        self.wg_config_dir = Path("/etc/wireguard")
        self.wg_config_dir.mkdir(exist_ok=True)
        
        # Load environment variables
        self.private_key = os.environ.get('SURFSHARK_PRIVATE_KEY', '')
        self.address = os.environ.get('SURFSHARK_ADDRESS', '')
        
        # Load cache
        self.load_cache()
        
        # Surfshark US servers (will be expanded)
        self.us_servers = self.get_surfshark_servers()
        
        logger.info(f"WireGuard manager initialized with {len(self.us_servers)} US servers")
    
    def get_surfshark_servers(self) -> List[Dict[str, str]]:
        """Get comprehensive list of Surfshark US servers (100+ servers)"""
        try:
            # Import the comprehensive server discovery utility
            from .surfshark_servers import SurfsharkServers
            
            # Get all servers from the comprehensive list
            surfshark = SurfsharkServers()
            servers = surfshark.get_us_servers()
            
            logger.info(f"Loaded {len(servers)} Surfshark US servers from comprehensive list")
            return servers
            
        except Exception as e:
            logger.warning(f"Failed to load comprehensive server list: {e}")
            logger.info("Falling back to basic server list")
            
            # Fallback to basic list if there's an issue
            servers = [
                {"name": "us-nyc.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "84.17.35.107:51820"},
                {"name": "us-lax.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "138.199.35.8:51820"},
                {"name": "us-chi.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "138.199.42.136:51820"},
                {"name": "us-mia.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "89.38.227.188:51820"},
                {"name": "us-dal.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "209.107.210.106:51820"},
                {"name": "us-sea.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "104.200.135.171:51820"},
                {"name": "us-den.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "23.105.136.132:51820"},
                {"name": "us-atl.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "185.203.218.83:51820"},
                {"name": "us-phx.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "23.19.128.208:51820"},
                {"name": "us-slc.prod.surfshark.com", "public_key": "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk=", "endpoint": "185.174.99.204:51820"},
            ]
            return servers
    
    def load_cache(self):
        """Load used servers from persistent cache"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache = json.load(f)
                    self.used_servers = set(cache.get('used_servers', []))
                    self.used_ips = set(cache.get('used_ips', []))
                    logger.info(f"Loaded cache: {len(self.used_servers)} used servers, {len(self.used_ips)} used IPs")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                self.used_servers = set()
                self.used_ips = set()
        else:
            self.used_servers = set()
            self.used_ips = set()
    
    def save_cache(self):
        """Save used servers to persistent cache"""
        cache = {
            'used_servers': list(self.used_servers),
            'used_ips': list(self.used_ips),
            'last_updated': time.time(),
            'session_id': os.environ.get('SESSION_ID', 'unknown')
        }
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
            logger.info(f"Saved cache: {len(self.used_servers)} servers, {len(self.used_ips)} IPs")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    def clear_cache(self):
        """Clear the VPN cache - used after each batch"""
        self.used_servers.clear()
        self.used_ips.clear()
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("VPN cache cleared - all servers available again")
    
    def disconnect_current(self):
        """Disconnect current WireGuard connection"""
        try:
            # Check if WireGuard interface exists
            result = subprocess.run(['ip', 'link', 'show', 'wg0'], capture_output=True, text=True)
            if result.returncode == 0:
                logger.info("Disconnecting current WireGuard connection...")
                # Use ip and wg commands instead of wg-quick for more control
                subprocess.run(['ip', 'link', 'del', 'wg0'], capture_output=True)
                time.sleep(2)
            self.current_server = None
            self.current_ip = None
        except Exception as e:
            logger.error(f"Error disconnecting WireGuard: {e}")
    
    def generate_config(self, server: Dict[str, str]) -> str:
        """Generate WireGuard configuration for a server"""
        # Simplified config without DNS to avoid issues
        config = f"""[Interface]
PrivateKey = {self.private_key}
Address = {self.address}

[Peer]
PublicKey = {server['public_key']}
AllowedIPs = 0.0.0.0/0
Endpoint = {server['endpoint']}
PersistentKeepalive = 25
"""
        return config
    
    def connect(self, server: Dict[str, str]) -> bool:
        """Connect to a specific WireGuard server"""
        try:
            # Disconnect current connection
            self.disconnect_current()
            
            # Generate config
            config = self.generate_config(server)
            config_path = self.wg_config_dir / "wg0.conf"
            
            with open(config_path, 'w') as f:
                f.write(config)
            
            # Set permissions
            os.chmod(config_path, 0o600)
            
            logger.info(f"Connecting to {server['name']}...")
            
            # Use manual commands instead of wg-quick for more control
            # Create interface
            subprocess.run(['ip', 'link', 'add', 'dev', 'wg0', 'type', 'wireguard'], capture_output=True)
            
            # Configure interface
            subprocess.run(['wg', 'setconf', 'wg0', str(config_path)], capture_output=True)
            
            # Set IP address
            subprocess.run(['ip', 'address', 'add', self.address, 'dev', 'wg0'], capture_output=True)
            
            # Bring interface up
            subprocess.run(['ip', 'link', 'set', 'up', 'dev', 'wg0'], capture_output=True)
            
            # Add routing
            subprocess.run(['ip', 'route', 'add', 'default', 'dev', 'wg0', 'table', '51820'], capture_output=True)
            subprocess.run(['ip', 'rule', 'add', 'not', 'fwmark', '51820', 'table', '51820'], capture_output=True)
            subprocess.run(['wg', 'set', 'wg0', 'fwmark', '51820'], capture_output=True)
            
            # Wait for connection to stabilize
            time.sleep(5)
            
            # Verify connection and get IP
            ip_info = self.verify_connection()
            if ip_info:
                self.current_server = server['name']
                self.current_ip = ip_info['ip']
                
                # Add to used sets
                self.used_servers.add(server['name'])
                self.used_ips.add(ip_info['ip'])
                self.save_cache()
                
                logger.info(f"Connected to {server['name']} - IP: {ip_info['ip']} ({ip_info.get('city', 'Unknown')})")
                return True
            else:
                logger.error("Connection verification failed")
                self.disconnect_current()
                return False
                
        except Exception as e:
            logger.error(f"Error connecting to {server['name']}: {e}")
            self.disconnect_current()
            return False
    
    def verify_connection(self) -> Optional[Dict[str, str]]:
        """Verify VPN connection and get current IP"""
        try:
            # Use curl as a subprocess for better control
            result = subprocess.run(
                ['curl', '-s', '--max-time', '10', 'https://ipinfo.io/json'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0 and result.stdout:
                return json.loads(result.stdout)
        except Exception as e:
            logger.error(f"Error verifying connection: {e}")
        return None
    
    def get_unused_server(self) -> Optional[Dict[str, str]]:
        """Get a random unused server"""
        available_servers = [s for s in self.us_servers if s['name'] not in self.used_servers]
        
        if not available_servers:
            logger.warning("No unused servers available - clearing cache")
            self.clear_cache()
            available_servers = self.us_servers
        
        if available_servers:
            return random.choice(available_servers)
        return None
    
    def rotate(self) -> Optional[Dict[str, str]]:
        """Rotate to a new unused server"""
        server = self.get_unused_server()
        if server and self.connect(server):
            return {
                'server': self.current_server,
                'ip': self.current_ip,
                'city': self.verify_connection().get('city', 'Unknown') if self.current_ip else 'Unknown'
            }
        return None
    
    def cleanup(self):
        """Cleanup on exit"""
        self.disconnect_current()
        # Clean up routing rules
        try:
            subprocess.run(['ip', 'rule', 'del', 'table', '51820'], capture_output=True)
            subprocess.run(['ip', 'route', 'flush', 'table', '51820'], capture_output=True)
        except:
            pass
        logger.info("WireGuard manager cleanup complete")


if __name__ == "__main__":
    # Test the WireGuard manager
    logging.basicConfig(level=logging.INFO)
    
    # Load .env file
    from dotenv import load_dotenv
    load_dotenv()
    
    manager = WireGuardManager()
    
    # Test rotation
    print("Testing VPN rotation...")
    for i in range(3):
        print(f"\nRotation {i+1}:")
        result = manager.rotate()
        if result:
            print(f"Connected to: {result}")
        else:
            print("Failed to rotate")
        time.sleep(5)
    
    # Cleanup
    manager.cleanup()
    print("\nTest complete!")