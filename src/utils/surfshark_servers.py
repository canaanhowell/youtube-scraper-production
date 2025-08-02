#!/usr/bin/env python3
"""
Surfshark Server Discovery
Fetches and manages Surfshark WireGuard server configurations
"""

import os
import json
import logging
import requests
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class SurfsharkServers:
    """Manages Surfshark server discovery and configuration"""
    
    def __init__(self):
        self.cache_file = Path("/opt/youtube_scraper/surfshark_servers.json")
        self.servers = []
        self.load_servers()
    
    def load_servers(self):
        """Load servers from cache or use default list"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.servers = json.load(f)
                logger.info(f"Loaded {len(self.servers)} servers from cache")
                return
            except Exception as e:
                logger.error(f"Error loading server cache: {e}")
        
        # Use default US servers
        self.servers = self.get_default_us_servers()
        self.save_cache()
    
    def save_cache(self):
        """Save servers to cache file"""
        try:
            self.cache_file.parent.mkdir(exist_ok=True)
            with open(self.cache_file, 'w') as f:
                json.dump(self.servers, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving server cache: {e}")
    
    def get_default_us_servers(self) -> List[Dict[str, str]]:
        """Get comprehensive list of US Surfshark servers"""
        # This is an extended list of US Surfshark servers
        # Public key is the same for all Surfshark servers
        public_key = "Ik9pPCyMJKno1RVHnf+4HhqT8se3kfWJZL7EqVEN5Xk="
        
        servers = []
        
        # Major US cities with multiple servers
        us_locations = {
            "nyc": ["84.17.35.107", "37.61.213.19", "212.102.40.78", "138.199.60.177"],
            "lax": ["138.199.35.8", "23.105.128.54", "104.200.130.31", "212.102.53.79"],
            "chi": ["138.199.42.136", "89.40.183.34", "181.214.87.3", "212.102.54.14"],
            "mia": ["89.38.227.188", "38.86.98.102", "104.156.229.120", "173.245.72.59"],
            "dal": ["209.107.210.106", "209.107.216.77", "104.156.240.84", "198.105.110.151"],
            "sea": ["104.200.135.171", "104.200.135.186", "198.23.141.231", "104.156.245.57"],
            "den": ["23.105.136.132", "198.105.122.145", "23.105.128.215", "185.174.99.228"],
            "atl": ["185.203.218.83", "173.245.202.42", "96.44.188.13", "173.245.218.45"],
            "phx": ["23.19.128.208", "185.203.219.132", "173.245.72.215", "96.44.158.5"],
            "slc": ["185.174.99.204", "23.19.128.241", "69.75.60.13", "185.93.0.91"],
            "bos": ["185.203.218.173", "23.105.192.13", "198.44.134.203", "162.19.139.10"],
            "was": ["104.200.151.82", "185.203.218.202", "173.245.207.5", "69.75.41.85"],
            "sfo": ["173.245.49.17", "173.245.49.26", "173.245.49.86", "198.23.150.158"],
            "hou": ["96.44.189.154", "198.105.111.50", "209.107.214.107", "173.245.194.107"],
            "orl": ["173.245.217.82", "173.245.195.65", "185.180.12.91", "96.44.142.19"],
            "ltm": ["143.244.42.77", "143.244.42.81", "143.244.42.97", "143.244.42.17"],
            "dtw": ["181.215.184.82", "212.102.44.87", "212.102.44.66", "212.102.44.97"],
            "las": ["181.215.164.154", "181.215.164.139", "181.215.164.190", "181.215.164.170"],
            "buf": ["143.244.49.179", "143.244.49.208", "143.244.49.233", "143.244.49.168"],
            "tpa": ["104.156.225.219", "104.156.225.165", "104.156.224.245", "104.156.225.60"],
        }
        
        # Generate server configurations
        for city, ips in us_locations.items():
            for i, ip in enumerate(ips):
                server = {
                    "name": f"us-{city}-{i+1}.prod.surfshark.com",
                    "city": city.upper(),
                    "public_key": public_key,
                    "endpoint": f"{ip}:51820",
                    "ip": ip
                }
                servers.append(server)
        
        logger.info(f"Generated {len(servers)} US server configurations")
        return servers
    
    def get_us_servers(self) -> List[Dict[str, str]]:
        """Get all US servers"""
        return self.servers
    
    def get_servers_by_city(self, city: str) -> List[Dict[str, str]]:
        """Get servers for a specific city"""
        city = city.lower()
        return [s for s in self.servers if city in s['name']]
    
    def get_random_servers(self, count: int = 10) -> List[Dict[str, str]]:
        """Get random selection of servers"""
        import random
        return random.sample(self.servers, min(count, len(self.servers)))
    
    def update_servers_from_api(self):
        """Update server list from Surfshark API (if available)"""
        # This would connect to Surfshark's API to get the latest server list
        # For now, we use the hardcoded list
        pass


if __name__ == "__main__":
    # Test the server discovery
    logging.basicConfig(level=logging.INFO)
    
    servers = SurfsharkServers()
    
    print(f"Total US servers: {len(servers.get_us_servers())}")
    print(f"\nServers in NYC: {len(servers.get_servers_by_city('nyc'))}")
    print(f"Servers in LAX: {len(servers.get_servers_by_city('lax'))}")
    
    print("\nRandom 5 servers:")
    for server in servers.get_random_servers(5):
        print(f"  - {server['name']} ({server['city']}) - {server['ip']}")