#!/usr/bin/env python3
"""
Monitor VPN IP Usage During Collection Runs
Tracks IP addresses used and alerts on excessive reuse
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vpn_ip_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VPNIPMonitor:
    """Monitor VPN IP usage patterns"""
    
    def __init__(self):
        self.container_name = 'youtube-vpn'
        self.monitoring_file = Path('vpn_ip_usage.json')
        self.load_history()
        
    def load_history(self):
        """Load IP usage history"""
        if self.monitoring_file.exists():
            try:
                with open(self.monitoring_file, 'r') as f:
                    self.history = json.load(f)
            except:
                self.history = self._create_new_history()
        else:
            self.history = self._create_new_history()
    
    def _create_new_history(self):
        """Create new history structure"""
        return {
            'start_date': datetime.now().isoformat(),
            'total_connections': 0,
            'unique_ips': set(),
            'ip_usage': defaultdict(int),
            'server_ips': defaultdict(list),
            'sessions': []
        }
    
    def save_history(self):
        """Save IP usage history"""
        # Convert sets and defaultdicts for JSON serialization
        save_data = {
            'start_date': self.history['start_date'],
            'total_connections': self.history['total_connections'],
            'unique_ips': list(self.history['unique_ips']),
            'ip_usage': dict(self.history['ip_usage']),
            'server_ips': dict(self.history['server_ips']),
            'sessions': self.history['sessions']
        }
        
        with open(self.monitoring_file, 'w') as f:
            json.dump(save_data, f, indent=2)
    
    def get_current_vpn_info(self) -> dict:
        """Get current VPN connection info"""
        try:
            # Get current server from docker inspect
            result = subprocess.run(
                ['docker', 'inspect', self.container_name],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)[0]
                env_vars = data['Config']['Env']
                
                # Find VPN_SERVER or SERVER_HOSTNAMES
                current_server = None
                for var in env_vars:
                    if var.startswith('SERVER_HOSTNAMES=') or var.startswith('VPN_SERVER='):
                        current_server = var.split('=', 1)[1]
                        break
                
                # Get current IP
                ip_result = subprocess.run(
                    ['docker', 'exec', self.container_name,
                     'wget', '-q', '-O', '-', 'https://ipinfo.io/json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if ip_result.returncode == 0:
                    ip_info = json.loads(ip_result.stdout)
                    return {
                        'server': current_server,
                        'ip': ip_info.get('ip'),
                        'city': ip_info.get('city'),
                        'region': ip_info.get('region'),
                        'org': ip_info.get('org'),
                        'timestamp': datetime.now().isoformat()
                    }
        except Exception as e:
            logger.error(f"Error getting VPN info: {e}")
        
        return None
    
    def record_connection(self, vpn_info: dict):
        """Record a VPN connection"""
        if not vpn_info or not vpn_info.get('ip'):
            return
        
        ip = vpn_info['ip']
        server = vpn_info.get('server', 'unknown')
        
        # Update history
        self.history['total_connections'] += 1
        self.history['unique_ips'].add(ip)
        self.history['ip_usage'][ip] += 1
        
        # Track IPs per server
        if server not in self.history['server_ips']:
            self.history['server_ips'][server] = []
        if ip not in self.history['server_ips'][server]:
            self.history['server_ips'][server].append(ip)
        
        # Check for excessive reuse
        usage_count = self.history['ip_usage'][ip]
        if usage_count > 5:
            logger.warning(f"⚠️  IP {ip} has been used {usage_count} times!")
        
        # Log the connection
        logger.info(f"VPN Connection: {server} -> {ip} ({vpn_info.get('city', 'Unknown')})")
        logger.info(f"  Usage count for this IP: {usage_count}")
        logger.info(f"  Total unique IPs so far: {len(self.history['unique_ips'])}")
    
    def monitor_session(self, session_name: str = None):
        """Monitor a collection session"""
        session = {
            'name': session_name or f"session_{int(time.time())}",
            'start_time': datetime.now().isoformat(),
            'connections': [],
            'unique_ips': set()
        }
        
        logger.info(f"Starting VPN IP monitoring for session: {session['name']}")
        
        try:
            while True:
                # Check if container is running
                result = subprocess.run(
                    ['docker', 'ps', '--filter', f'name={self.container_name}', '--format', '{{.Names}}'],
                    capture_output=True,
                    text=True
                )
                
                if self.container_name not in result.stdout:
                    logger.info("VPN container not running, waiting...")
                    time.sleep(10)
                    continue
                
                # Get current VPN info
                vpn_info = self.get_current_vpn_info()
                if vpn_info and vpn_info['ip']:
                    # Check if this is a new connection
                    if not session['connections'] or session['connections'][-1]['ip'] != vpn_info['ip']:
                        session['connections'].append(vpn_info)
                        session['unique_ips'].add(vpn_info['ip'])
                        self.record_connection(vpn_info)
                        
                        # Save after each new connection
                        self.save_history()
                
                # Check every 30 seconds
                time.sleep(30)
                
        except KeyboardInterrupt:
            logger.info("\nMonitoring stopped by user")
        finally:
            # Save session summary
            session['end_time'] = datetime.now().isoformat()
            session['total_connections'] = len(session['connections'])
            session['unique_ips'] = list(session['unique_ips'])
            session['ip_reuse_rate'] = 1 - (len(session['unique_ips']) / session['total_connections'] if session['total_connections'] > 0 else 0)
            
            self.history['sessions'].append(session)
            self.save_history()
            
            # Print session summary
            self.print_session_summary(session)
    
    def print_session_summary(self, session: dict):
        """Print session summary"""
        logger.info("\n" + "="*60)
        logger.info(f"SESSION SUMMARY: {session['name']}")
        logger.info("="*60)
        logger.info(f"Duration: {session['start_time']} to {session.get('end_time', 'ongoing')}")
        logger.info(f"Total connections: {session['total_connections']}")
        logger.info(f"Unique IPs used: {len(session['unique_ips'])}")
        logger.info(f"IP reuse rate: {session.get('ip_reuse_rate', 0):.1%}")
        
        if session['connections']:
            # Count IPs per server
            server_ips = defaultdict(set)
            for conn in session['connections']:
                server_ips[conn.get('server', 'unknown')].add(conn['ip'])
            
            logger.info("\nIPs per server:")
            for server, ips in sorted(server_ips.items()):
                logger.info(f"  {server}: {len(ips)} unique IPs")
    
    def print_overall_stats(self):
        """Print overall IP usage statistics"""
        logger.info("\n" + "="*60)
        logger.info("OVERALL VPN IP USAGE STATISTICS")
        logger.info("="*60)
        logger.info(f"Monitoring since: {self.history['start_date']}")
        logger.info(f"Total connections: {self.history['total_connections']}")
        logger.info(f"Unique IPs used: {len(self.history['unique_ips'])}")
        
        # Most used IPs
        if self.history['ip_usage']:
            sorted_ips = sorted(self.history['ip_usage'].items(), key=lambda x: x[1], reverse=True)
            logger.info("\nMost used IPs:")
            for ip, count in sorted_ips[:10]:
                logger.info(f"  {ip}: {count} times")
        
        # IPs per server
        logger.info("\nUnique IPs per server:")
        for server, ips in sorted(self.history['server_ips'].items()):
            logger.info(f"  {server}: {len(ips)} unique IPs")
        
        # Session summaries
        if self.history['sessions']:
            logger.info(f"\nTotal sessions monitored: {len(self.history['sessions'])}")
            avg_reuse = sum(s.get('ip_reuse_rate', 0) for s in self.history['sessions']) / len(self.history['sessions'])
            logger.info(f"Average IP reuse rate across sessions: {avg_reuse:.1%}")


def main():
    """Main monitoring function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Monitor VPN IP usage')
    parser.add_argument('--session', help='Session name for this monitoring run')
    parser.add_argument('--stats', action='store_true', help='Show overall statistics and exit')
    parser.add_argument('--reset', action='store_true', help='Reset monitoring history')
    
    args = parser.parse_args()
    
    # Load environment
    sys.path.insert(0, '/opt/youtube_scraper')
    from src.utils.env_loader import load_env
    load_env()
    
    # Create monitor
    monitor = VPNIPMonitor()
    
    if args.reset:
        monitor.history = monitor._create_new_history()
        monitor.save_history()
        logger.info("Monitoring history reset")
        return
    
    if args.stats:
        monitor.print_overall_stats()
        return
    
    # Start monitoring
    monitor.monitor_session(args.session)


if __name__ == "__main__":
    main()