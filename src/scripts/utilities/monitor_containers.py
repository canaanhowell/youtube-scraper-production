#!/usr/bin/env python3
"""
Container Resource Monitoring Script
Monitors Docker container resource usage and alerts on high usage
"""

import subprocess
import json
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/youtube_scraper/logs/container_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContainerMonitor:
    """Monitor Docker container resources"""
    
    def __init__(self):
        self.warning_thresholds = {
            'memory_percent': 80,  # Warn at 80% memory usage
            'cpu_percent': 200,    # Warn at 200% CPU usage (2 cores)
        }
        self.critical_thresholds = {
            'memory_percent': 90,  # Critical at 90% memory usage
            'cpu_percent': 300,    # Critical at 300% CPU usage
        }
    
    def get_container_stats(self, container_name: str) -> Optional[Dict]:
        """Get container resource statistics"""
        try:
            # Get container stats in JSON format
            result = subprocess.run(
                ['docker', 'stats', container_name, '--no-stream', '--format', 'json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                stats = json.loads(result.stdout.strip())
                return self._parse_stats(stats)
            else:
                logger.warning(f"Failed to get stats for container {container_name}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout getting stats for container {container_name}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse container stats JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting container stats: {e}")
            return None
    
    def _parse_stats(self, stats: Dict) -> Dict:
        """Parse and normalize container stats"""
        try:
            # Parse memory usage
            memory_usage = stats.get('MemUsage', '0B / 0B')
            memory_parts = memory_usage.split(' / ')
            memory_used = self._parse_bytes(memory_parts[0])
            memory_limit = self._parse_bytes(memory_parts[1]) if len(memory_parts) > 1 else 0
            
            # Parse CPU usage
            cpu_percent = float(stats.get('CPUPerc', '0%').rstrip('%'))
            
            # Parse memory percentage
            memory_percent = float(stats.get('MemPerc', '0%').rstrip('%'))
            
            # Parse network I/O
            net_io = stats.get('NetIO', '0B / 0B')
            net_parts = net_io.split(' / ')
            net_rx = self._parse_bytes(net_parts[0])
            net_tx = self._parse_bytes(net_parts[1]) if len(net_parts) > 1 else 0
            
            # Parse block I/O
            block_io = stats.get('BlockIO', '0B / 0B')
            block_parts = block_io.split(' / ')
            block_read = self._parse_bytes(block_parts[0])
            block_write = self._parse_bytes(block_parts[1]) if len(block_parts) > 1 else 0
            
            return {
                'name': stats.get('Name', 'unknown'),
                'container_id': stats.get('Container', 'unknown'),
                'cpu_percent': cpu_percent,
                'memory_used_bytes': memory_used,
                'memory_limit_bytes': memory_limit,
                'memory_percent': memory_percent,
                'network_rx_bytes': net_rx,
                'network_tx_bytes': net_tx,
                'block_read_bytes': block_read,
                'block_write_bytes': block_write,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing container stats: {e}")
            return {}
    
    def _parse_bytes(self, byte_str: str) -> int:
        """Parse byte string like '1.5GB' to bytes"""
        if not byte_str or byte_str == '0B':
            return 0
        
        # Remove trailing 'B' and split number from unit
        byte_str = byte_str.rstrip('B')
        
        units = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
        
        # Find the unit
        unit = ''
        number_str = byte_str
        for u in units:
            if byte_str.endswith(u):
                unit = u
                number_str = byte_str[:-1]
                break
        
        try:
            number = float(number_str)
            multiplier = units.get(unit, 1)
            return int(number * multiplier)
        except ValueError:
            return 0
    
    def check_thresholds(self, stats: Dict) -> List[str]:
        """Check if stats exceed warning/critical thresholds"""
        alerts = []
        
        if not stats:
            return alerts
        
        name = stats.get('name', 'unknown')
        cpu_percent = stats.get('cpu_percent', 0)
        memory_percent = stats.get('memory_percent', 0)
        
        # Check CPU thresholds
        if cpu_percent >= self.critical_thresholds['cpu_percent']:
            alerts.append(f"CRITICAL: Container {name} CPU usage: {cpu_percent:.1f}%")
        elif cpu_percent >= self.warning_thresholds['cpu_percent']:
            alerts.append(f"WARNING: Container {name} CPU usage: {cpu_percent:.1f}%")
        
        # Check memory thresholds
        if memory_percent >= self.critical_thresholds['memory_percent']:
            alerts.append(f"CRITICAL: Container {name} memory usage: {memory_percent:.1f}%")
        elif memory_percent >= self.warning_thresholds['memory_percent']:
            alerts.append(f"WARNING: Container {name} memory usage: {memory_percent:.1f}%")
        
        return alerts
    
    def monitor_containers(self, container_names: List[str], duration_minutes: int = 5):
        """Monitor containers for specified duration"""
        logger.info(f"Starting container monitoring for {duration_minutes} minutes")
        logger.info(f"Monitoring containers: {', '.join(container_names)}")
        
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        while time.time() < end_time:
            for container_name in container_names:
                stats = self.get_container_stats(container_name)
                if stats:
                    # Log current stats
                    logger.info(
                        f"Container {stats['name']}: "
                        f"CPU: {stats['cpu_percent']:.1f}%, "
                        f"Memory: {stats['memory_percent']:.1f}% "
                        f"({stats['memory_used_bytes']//1024//1024}MB), "
                        f"Net: ↓{stats['network_rx_bytes']//1024//1024}MB "
                        f"↑{stats['network_tx_bytes']//1024//1024}MB"
                    )
                    
                    # Check for alerts
                    alerts = self.check_thresholds(stats)
                    for alert in alerts:
                        logger.warning(alert)
                else:
                    logger.warning(f"Could not get stats for container: {container_name}")
            
            # Wait before next check
            time.sleep(30)  # Check every 30 seconds
        
        logger.info("Container monitoring completed")
    
    def get_container_health(self, container_name: str) -> Dict:
        """Get container health status"""
        try:
            result = subprocess.run(
                ['docker', 'inspect', container_name, '--format', '{{json .State}}'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                state = json.loads(result.stdout.strip())
                return {
                    'running': state.get('Running', False),
                    'status': state.get('Status', 'unknown'),
                    'health': state.get('Health', {}).get('Status', 'none'),
                    'restart_count': state.get('RestartCount', 0),
                    'started_at': state.get('StartedAt', ''),
                    'finished_at': state.get('FinishedAt', '')
                }
            else:
                return {'error': f"Container {container_name} not found"}
                
        except Exception as e:
            return {'error': str(e)}


def main():
    """Main monitoring function"""
    monitor = ContainerMonitor()
    
    # Containers to monitor
    containers = ['youtube-vpn']
    
    # Check if containers exist first
    for container in containers:
        health = monitor.get_container_health(container)
        if 'error' in health:
            logger.error(f"Container {container}: {health['error']}")
        else:
            logger.info(f"Container {container}: {health['status']} (health: {health['health']})")
    
    # Monitor for 5 minutes
    monitor.monitor_containers(containers, duration_minutes=5)


if __name__ == "__main__":
    main()