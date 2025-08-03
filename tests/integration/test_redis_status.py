#!/usr/bin/env python3
"""Test Redis connection status"""
import os
import sys
import time

# Load environment
sys.path.insert(0, '/opt/youtube_scraper')
from src.utils.env_loader import load_env
load_env()

# Now test Redis
from src.utils.redis_client_enhanced import RedisClientEnhanced

print("Testing Redis Enhanced Client...")
print("=" * 50)

client = RedisClientEnhanced()
print(f"Redis enabled: {client.enabled}")
print(f"Using native client: {client.use_native}")
print(f"Redis URL: {os.environ.get('UPSTASH_REDIS_REST_URL', 'Not set')[:50]}...")

if client.enabled:
    print("\nPerformance test (20 operations):")
    
    # Test operations
    start = time.time()
    for i in range(20):
        result = client.is_duplicate(f"perf_test_{i}")
    end = time.time()
    
    total_time = (end - start) * 1000
    avg_time = total_time / 20
    
    print(f"Total time: {total_time:.1f}ms")
    print(f"Average time per operation: {avg_time:.1f}ms")
    print(f"Operations per second: {20 / (end - start):.0f}")
    
    # Connection type
    if client.use_native:
        print("\n✅ Using NATIVE Redis connection (high performance)")
    else:
        print("\n⚠️  Using REST API fallback (Upstash doesn't support native connections)")
        print("This is expected behavior - Upstash is a REST-only service")
else:
    print("\n❌ Redis is not enabled")