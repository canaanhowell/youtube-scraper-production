import os
import json
import time
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WireGuardManager:
    def __init__(self):
        self.private_key = os.getenv('SURFSHARK_PRIVATE_KEY', '6KFmgM+5j6xlQdRDX1z0XRF889eXooyUHnCLlVn4lW8=')
        self.address = os.getenv('SURFSHARK_ADDRESS', '10.14.0.2/16')
        self.wg_config_dir = Path('/etc/wireguard')
        self.wg_config_dir.mkdir(exist_ok=True)
        
        # Import server list
        from src.config.surfshark_servers import servers
        self.servers = servers
        
        # Track used servers
        self.used_servers = set()
        self.used_ips = set()
        self.current_server = None
        
        logger.info(f"WireGuard manager initialized with {len(self.servers)} US servers")
    
    def generate_config(self, server: Dict[str, str]) -> str:
        """Generate WireGuard configuration"""
        return f"""[Interface]
PrivateKey = {self.private_key}
Address = {self.address}
DNS = 1.1.1.1, 8.8.8.8

[Peer]
PublicKey = {server['public_key']}
Endpoint = {server['endpoint']}
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""
    
    def disconnect_current(self):
        """Disconnect current WireGuard connection"""
        if self.current_server:
            logger.info("Disconnecting current WireGuard connection...")
            try:
                subprocess.run(['wg-quick', 'down', 'wg0'], capture_output=True, text=True)
            except:
                pass
            self.current_server = None
    
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
            
            # Use wg-quick for simplicity
            result = subprocess.run(['wg-quick', 'up', 'wg0'], capture_output=True, text=True)
            
            if result.returncode \!= 0:
                logger.error(f"Failed to connect: {result.stderr}")
                return False
            
            # Wait for connection to stabilize
            time.sleep(3)
            
            # Verify connection and get IP
            ip_info = self.verify_connection()
            if ip_info:
                self.current_server = server
                self.used_servers.add(server['name'])
                self.used_ips.add(ip_info.get('ip'))
                logger.info(f"✓ Connected to {server['name']} - IP: {ip_info.get('ip')} ({ip_info.get('city')}, {ip_info.get('region')})")
                return True
            else:
                logger.error("Connection verification failed")
                self.disconnect_current()
                return False
                
        except Exception as e:
            logger.error(f"Connection error: {e}")
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
            logger.error(f"Failed to verify connection: {e}")
        return None
    
    def get_available_servers(self) -> List[Dict[str, str]]:
        """Get list of servers that haven't been used yet"""
        return [s for s in self.servers if s['name'] not in self.used_servers]
    
    def rotate(self) -> bool:
        """Rotate to a new server"""
        available = self.get_available_servers()
        
        if not available:
            logger.warning("No unused servers available - consider clearing cache")
            return False
        
        # Try to connect to a new server
        import random
        random.shuffle(available)
        
        for server in available[:3]:  # Try up to 3 servers
            if self.connect(server):
                return True
        
        return False
    
    def clear_cache(self):
        """Clear the VPN cache - used after each batch"""
        self.used_servers.clear()
        self.used_ips.clear()
        logger.info("VPN cache cleared - all servers available again")
    
    def __del__(self):
        """Cleanup on deletion"""
        self.disconnect_current()
