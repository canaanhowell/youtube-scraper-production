#!/usr/bin/env python3
"""Test VPN connection fix"""
import sys
sys.path.insert(0, '/opt/youtube_app')

from youtube_collection_manager import YouTubeCollectionManager

# Initialize manager
print("Initializing YouTube Collection Manager...")
manager = YouTubeCollectionManager()

# Get servers
servers = manager._get_surfshark_servers()
print(f"\nTotal servers: {len(servers)}")
print(f"First 5 servers: {servers[:5]}")

# Test VPN rotation
print(f"\nTesting VPN rotation with server: {servers[0]}")
result = manager.rotate_vpn_server(servers[0])
print(f"VPN rotation result: {result}")

if result:
    print("✅ VPN connection successful!")
else:
    print("❌ VPN connection failed!")