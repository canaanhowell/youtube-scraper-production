#!/usr/bin/env python3
"""
Test VPN IP Rotation with Cache Clearing
Verifies that rotating through Surfshark servers provides diverse IP addresses
"""

import os
import sys
import json
import time
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vpn_ip_rotation_test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VPNIPRotationTester:
    """Test VPN IP diversity across Surfshark servers"""
    
    def __init__(self):
        self.container_name = 'youtube-vpn'
        self.docker_compose_path = Path('/opt/youtube_app/docker-compose.yml')
        self.results = {
            'start_time': datetime.now().isoformat(),
            'servers': {},
            'summary': {}
        }
        
        # Get list of servers to test
        self.servers = self._get_surfshark_servers()
        
    def _get_surfshark_servers(self) -> List[str]:
        """Get list of Surfshark US servers (24 verified locations)"""
        us_locations = [
            'nyc', 'lax', 'chi', 'dal', 'mia', 'atl', 'sea', 'den', 'phx',
            'bos', 'sfo', 'las', 'hou', 'orl', 'kan', 'clt', 'tpa', 'stl',
            'slc', 'buf', 'ltm', 'dtw', 'bdn', 'rag'
        ]
        return [f"us-{location}.prod.surfshark.com" for location in us_locations]
    
    def clear_gluetun_cache(self):
        """Clear Gluetun's internal cache to force fresh connections"""
        logger.info("Clearing Gluetun cache...")
        try:
            # Remove Gluetun's data volume to clear any cached server info
            subprocess.run(
                ['docker', 'volume', 'rm', '-f', 'youtube_scraper_vpn-data'],
                capture_output=True,
                text=True
            )
            logger.info("Gluetun cache cleared")
        except Exception as e:
            logger.warning(f"Could not clear cache volume: {e}")
    
    def stop_vpn_container(self):
        """Stop and remove VPN container completely"""
        logger.info("Stopping VPN container...")
        try:
            # Stop container
            subprocess.run(
                ['docker', 'compose', 'down', '-v'],  # -v removes volumes
                cwd=self.docker_compose_path.parent,
                capture_output=True,
                text=True
            )
            time.sleep(3)
            
            # Force remove container if still exists
            subprocess.run(
                ['docker', 'rm', '-f', self.container_name],
                capture_output=True,
                text=True
            )
            
            # Clear cache
            self.clear_gluetun_cache()
            
            logger.info("VPN container stopped and cache cleared")
        except Exception as e:
            logger.error(f"Error stopping container: {e}")
    
    def start_vpn_with_server(self, server: str) -> bool:
        """Start VPN with specific server"""
        logger.info(f"Starting VPN with server: {server}")
        try:
            env = os.environ.copy()
            env['VPN_SERVER'] = server
            
            result = subprocess.run(
                ['docker', 'compose', 'up', '-d'],
                cwd=self.docker_compose_path.parent,
                env=env,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                logger.error(f"Failed to start container: {result.stderr}")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error starting VPN: {e}")
            return False
    
    def get_current_ip(self, max_attempts: int = 12) -> Dict[str, str]:
        """Get current IP info from VPN connection"""
        for attempt in range(max_attempts):
            try:
                result = subprocess.run(
                    ['docker', 'exec', self.container_name, 
                     'wget', '-q', '-O', '-', 'https://ipinfo.io/json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    ip_info = json.loads(result.stdout)
                    logger.info(f"Connected: {ip_info.get('city', 'Unknown')} - IP: {ip_info.get('ip', 'Unknown')}")
                    return ip_info
                    
            except Exception as e:
                logger.debug(f"Connection check attempt {attempt + 1} failed: {e}")
            
            time.sleep(10)
        
        logger.error("Failed to get IP info")
        return {}
    
    def test_server_ips(self, server: str, rotations: int = 5) -> Dict[str, any]:
        """Test a single server multiple times to check IP diversity"""
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing server: {server}")
        logger.info(f"{'='*60}")
        
        server_results = {
            'server': server,
            'rotations': rotations,
            'ips': [],
            'unique_ips': set(),
            'ip_details': []
        }
        
        for i in range(rotations):
            logger.info(f"\nRotation {i + 1}/{rotations} for {server}")
            
            # Stop container and clear cache
            self.stop_vpn_container()
            time.sleep(5)  # Give system time to clean up
            
            # Start VPN with server
            if not self.start_vpn_with_server(server):
                logger.error(f"Failed to start VPN for rotation {i + 1}")
                continue
            
            # Get IP info
            ip_info = self.get_current_ip()
            if ip_info and 'ip' in ip_info:
                ip = ip_info['ip']
                server_results['ips'].append(ip)
                server_results['unique_ips'].add(ip)
                server_results['ip_details'].append({
                    'rotation': i + 1,
                    'ip': ip,
                    'city': ip_info.get('city', 'Unknown'),
                    'region': ip_info.get('region', 'Unknown'),
                    'org': ip_info.get('org', 'Unknown')
                })
                
                # Log if we got a repeated IP
                if server_results['ips'].count(ip) > 1:
                    logger.warning(f"⚠️  Repeated IP detected: {ip} (seen {server_results['ips'].count(ip)} times)")
                else:
                    logger.info(f"✅ New unique IP: {ip}")
            else:
                logger.error(f"Failed to get IP for rotation {i + 1}")
        
        # Convert set to list for JSON serialization
        server_results['unique_ips'] = list(server_results['unique_ips'])
        server_results['unique_count'] = len(server_results['unique_ips'])
        server_results['reuse_rate'] = 1 - (server_results['unique_count'] / len(server_results['ips'])) if server_results['ips'] else 0
        
        return server_results
    
    def run_full_test(self, servers_to_test: List[str] = None, rotations_per_server: int = 5):
        """Run full IP rotation test"""
        servers = servers_to_test or self.servers
        
        logger.info(f"Starting VPN IP Rotation Test")
        logger.info(f"Testing {len(servers)} servers with {rotations_per_server} rotations each")
        logger.info(f"Total connections to test: {len(servers) * rotations_per_server}")
        
        all_unique_ips = set()
        
        for i, server in enumerate(servers):
            logger.info(f"\nTesting server {i + 1}/{len(servers)}: {server}")
            
            try:
                results = self.test_server_ips(server, rotations_per_server)
                self.results['servers'][server] = results
                
                # Add to global unique IP set
                all_unique_ips.update(results['unique_ips'])
                
                # Log progress
                logger.info(f"Server {server} results:")
                logger.info(f"  - Unique IPs: {results['unique_count']}/{rotations_per_server}")
                logger.info(f"  - IP reuse rate: {results['reuse_rate']:.1%}")
                
            except Exception as e:
                logger.error(f"Error testing server {server}: {e}")
                self.results['servers'][server] = {'error': str(e)}
        
        # Calculate summary statistics
        self.calculate_summary(all_unique_ips)
        
        # Save results
        self.save_results()
        
        # Stop VPN after tests
        self.stop_vpn_container()
    
    def calculate_summary(self, all_unique_ips: Set[str]):
        """Calculate summary statistics"""
        total_servers = len(self.results['servers'])
        successful_servers = sum(1 for s in self.results['servers'].values() if 'error' not in s)
        total_connections = sum(len(s.get('ips', [])) for s in self.results['servers'].values())
        
        # IP diversity by server
        ip_counts_by_server = {}
        for server, data in self.results['servers'].items():
            if 'unique_count' in data:
                ip_counts_by_server[server] = data['unique_count']
        
        self.results['summary'] = {
            'end_time': datetime.now().isoformat(),
            'total_servers_tested': total_servers,
            'successful_servers': successful_servers,
            'total_connections': total_connections,
            'total_unique_ips': len(all_unique_ips),
            'average_ips_per_server': sum(ip_counts_by_server.values()) / len(ip_counts_by_server) if ip_counts_by_server else 0,
            'servers_with_single_ip': sum(1 for count in ip_counts_by_server.values() if count == 1),
            'servers_with_multiple_ips': sum(1 for count in ip_counts_by_server.values() if count > 1),
            'overall_ip_diversity_ratio': len(all_unique_ips) / total_connections if total_connections > 0 else 0
        }
        
        # Find servers with best and worst IP diversity
        if ip_counts_by_server:
            sorted_servers = sorted(ip_counts_by_server.items(), key=lambda x: x[1], reverse=True)
            self.results['summary']['best_servers'] = sorted_servers[:5]
            self.results['summary']['worst_servers'] = sorted_servers[-5:]
    
    def save_results(self):
        """Save test results to file"""
        output_file = f'vpn_ip_rotation_results_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"\nResults saved to: {output_file}")
        
        # Print summary
        summary = self.results['summary']
        logger.info("\n" + "="*60)
        logger.info("VPN IP ROTATION TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total servers tested: {summary['total_servers_tested']}")
        logger.info(f"Successful tests: {summary['successful_servers']}")
        logger.info(f"Total connections made: {summary['total_connections']}")
        logger.info(f"Total unique IPs found: {summary['total_unique_ips']}")
        logger.info(f"Average IPs per server: {summary['average_ips_per_server']:.2f}")
        logger.info(f"Overall IP diversity: {summary['overall_ip_diversity_ratio']:.1%}")
        logger.info(f"Servers with only 1 IP: {summary['servers_with_single_ip']}")
        logger.info(f"Servers with multiple IPs: {summary['servers_with_multiple_ips']}")
        
        if 'best_servers' in summary:
            logger.info("\nBest servers (most IP diversity):")
            for server, count in summary['best_servers']:
                logger.info(f"  - {server}: {count} unique IPs")


def main():
    """Run VPN IP rotation test"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test VPN IP rotation diversity')
    parser.add_argument('--servers', nargs='+', help='Specific servers to test')
    parser.add_argument('--rotations', type=int, default=5, help='Rotations per server (default: 5)')
    parser.add_argument('--quick', action='store_true', help='Quick test with 3 servers, 3 rotations each')
    
    args = parser.parse_args()
    
    # Load environment
    sys.path.insert(0, '/opt/youtube_app')
    from src.utils.env_loader import load_env
    load_env()
    
    # Create tester
    tester = VPNIPRotationTester()
    
    if args.quick:
        # Quick test with subset
        logger.info("Running quick test (3 servers, 3 rotations each)")
        tester.run_full_test(servers_to_test=tester.servers[:3], rotations_per_server=3)
    elif args.servers:
        # Test specific servers
        tester.run_full_test(servers_to_test=args.servers, rotations_per_server=args.rotations)
    else:
        # Full test
        tester.run_full_test(rotations_per_server=args.rotations)


if __name__ == "__main__":
    main()