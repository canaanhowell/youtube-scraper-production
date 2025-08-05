"""
VPN Server Coordinator - Ensures no two containers use the same server simultaneously
"""
import os
import json
import time
import fcntl
from typing import List, Set, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class VPNCoordinator:
    """Coordinates VPN server usage across multiple containers"""
    
    def __init__(self, instance_id: int, lock_dir: str = "/tmp/vpn_locks"):
        self.instance_id = instance_id
        self.lock_dir = Path(lock_dir)
        self.lock_dir.mkdir(exist_ok=True)
        self.lock_file = self.lock_dir / "vpn_servers.lock"
        self.state_file = self.lock_dir / "vpn_servers.json"
        
        # Divide servers among instances
        self.all_servers = [
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
        self._assign_instance_servers()
        
    def _assign_instance_servers(self):
        """Assign specific servers to each instance to avoid overlap"""
        servers_per_instance = len(self.all_servers) // 3
        extra_servers = len(self.all_servers) % 3
        
        if self.instance_id == 1:
            start = 0
            end = servers_per_instance + (1 if extra_servers > 0 else 0)
        elif self.instance_id == 2:
            start = servers_per_instance + (1 if extra_servers > 0 else 0)
            end = start + servers_per_instance + (1 if extra_servers > 1 else 0)
        else:  # instance 3
            start = 2 * servers_per_instance + min(2, extra_servers)
            end = len(self.all_servers)
            
        self.instance_servers = self.all_servers[start:end]
        logger.info(f"Instance {self.instance_id} assigned {len(self.instance_servers)} servers: {self.instance_servers[:3]}...")
        
    def get_available_servers(self) -> List[str]:
        """Get list of servers available for this instance"""
        with self._get_lock():
            in_use = self._read_in_use_servers()
            available = [s for s in self.instance_servers if s not in in_use]
            logger.info(f"Instance {self.instance_id}: {len(available)} servers available")
            return available
    
    def acquire_server(self, server: str) -> bool:
        """Mark a server as in use by this instance"""
        if server not in self.instance_servers:
            logger.warning(f"Server {server} not assigned to instance {self.instance_id}")
            return False
            
        with self._get_lock():
            in_use = self._read_in_use_servers()
            
            if server in in_use and in_use[server] != self.instance_id:
                logger.warning(f"Server {server} already in use by instance {in_use[server]}")
                return False
                
            in_use[server] = self.instance_id
            self._write_in_use_servers(in_use)
            logger.info(f"Instance {self.instance_id} acquired server {server}")
            return True
    
    def release_server(self, server: str):
        """Release a server from use"""
        with self._get_lock():
            in_use = self._read_in_use_servers()
            if server in in_use and in_use[server] == self.instance_id:
                del in_use[server]
                self._write_in_use_servers(in_use)
                logger.info(f"Instance {self.instance_id} released server {server}")
    
    def release_all_servers(self):
        """Release all servers held by this instance"""
        with self._get_lock():
            in_use = self._read_in_use_servers()
            servers_to_release = [s for s, i in in_use.items() if i == self.instance_id]
            for server in servers_to_release:
                del in_use[server]
            self._write_in_use_servers(in_use)
            logger.info(f"Instance {self.instance_id} released {len(servers_to_release)} servers")
    
    def _get_lock(self):
        """Get file lock for coordination"""
        return FileLock(self.lock_file)
    
    def _read_in_use_servers(self) -> dict:
        """Read currently in-use servers from state file"""
        if not self.state_file.exists():
            return {}
        try:
            with open(self.state_file, 'r') as f:
                data = json.load(f)
                # Clean up stale entries (older than 30 minutes)
                now = time.time()
                return {s: i for s, i in data.items() 
                        if isinstance(i, int) or now - i.get('timestamp', 0) < 1800}
        except:
            return {}
    
    def _write_in_use_servers(self, in_use: dict):
        """Write in-use servers to state file"""
        with open(self.state_file, 'w') as f:
            json.dump(in_use, f)

class FileLock:
    """Simple file-based lock for process coordination"""
    
    def __init__(self, lock_file: Path):
        self.lock_file = lock_file
        self.lock_fd = None
        
    def __enter__(self):
        self.lock_fd = open(self.lock_file, 'w')
        # Wait up to 30 seconds for lock
        for _ in range(30):
            try:
                fcntl.flock(self.lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except IOError:
                time.sleep(1)
        raise TimeoutError("Could not acquire VPN coordinator lock")
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.lock_fd:
            fcntl.flock(self.lock_fd, fcntl.LOCK_UN)
            self.lock_fd.close()