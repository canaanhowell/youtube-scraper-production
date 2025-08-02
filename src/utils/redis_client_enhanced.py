#!/usr/bin/env python3
"""
Enhanced Redis Client with Native Connection Support
Supports both native Redis connections and Upstash REST API fallback
"""

import os
import json
import logging
import requests
import time
from typing import Optional, Any, Dict
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClientEnhanced:
    """Enhanced Redis client with native connection and REST API fallback"""
    
    def __init__(self):
        self.redis_url = os.environ.get('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN')
        
        # Try to import and configure native Redis client
        self.native_client = None
        self.use_native = False
        
        # Attempt native Redis connection
        if self._setup_native_client():
            self.use_native = True
            self.enabled = True
            logger.info("Redis client initialized with NATIVE connection (high performance)")
        elif self.redis_url and self.redis_token:
            self.enabled = True
            logger.info("Redis client initialized with REST API fallback")
        else:
            logger.warning("Redis credentials not found - Redis disabled")
            self.enabled = False
    
    def _setup_native_client(self) -> bool:
        """Setup native Redis client connection"""
        try:
            import redis
            
            # Parse Upstash Redis URL for native connection
            if self.redis_url and self.redis_token:
                # Extract host and port from REST URL
                # Example: https://gusc1-capital-mole-32245.upstash.io
                # Convert to: gusc1-capital-mole-32245.upstash.io:6379
                host = self.redis_url.replace('https://', '').replace('http://', '')
                port = 6379
                
                # Create connection pool with retry logic
                pool = redis.ConnectionPool(
                    host=host,
                    port=port,
                    password=self.redis_token,
                    decode_responses=True,
                    socket_connect_timeout=10,
                    socket_timeout=10,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                
                self.native_client = redis.Redis(connection_pool=pool)
                
                # Test connection
                self.native_client.ping()
                logger.info(f"Native Redis connection established to {host}:{port}")
                return True
                
        except ImportError:
            logger.info("redis-py not installed, using REST API")
            return False
        except Exception as e:
            logger.warning(f"Native Redis connection failed: {e}, falling back to REST API")
            self.native_client = None
            return False
    
    def _make_rest_request(self, command: list) -> Optional[Any]:
        """Make a request to Upstash Redis REST API (fallback)"""
        if not self.enabled:
            return None
        
        try:
            headers = {
                'Authorization': f'Bearer {self.redis_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.post(
                f'{self.redis_url}',
                headers=headers,
                json=command,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result')
            else:
                logger.error(f"Redis REST request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Redis REST request error: {e}")
            return None
    
    def _execute_with_fallback(self, native_operation, rest_command: list):
        """Execute operation with native client and REST fallback"""
        if not self.enabled:
            return None
        
        if self.use_native and self.native_client:
            try:
                return native_operation()
            except Exception as e:
                logger.warning(f"Native Redis operation failed: {e}, trying REST fallback")
                self.use_native = False  # Disable native for this session
        
        # Use REST API fallback
        return self._make_rest_request(rest_command)
    
    def exists(self, key: str) -> int:
        """Check if key exists"""
        def native_op():
            return self.native_client.exists(key)
        
        result = self._execute_with_fallback(native_op, ['EXISTS', key])
        return result if result is not None else 0
    
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration"""
        def native_op():
            return self.native_client.setex(key, seconds, value)
        
        result = self._execute_with_fallback(native_op, ['SETEX', key, str(seconds), value])
        return result == 'OK' or result is True
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        def native_op():
            return self.native_client.get(key)
        
        return self._execute_with_fallback(native_op, ['GET', key])
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        def native_op():
            return bool(self.native_client.delete(key))
        
        result = self._execute_with_fallback(native_op, ['DEL', key])
        return bool(result) if result is not None else False
    
    def keys(self, pattern: str = '*') -> list:
        """Get keys matching pattern"""
        def native_op():
            return self.native_client.keys(pattern)
        
        result = self._execute_with_fallback(native_op, ['KEYS', pattern])
        return result if result else []
    
    def ttl(self, key: str) -> int:
        """Get time to live for key"""
        def native_op():
            return self.native_client.ttl(key)
        
        result = self._execute_with_fallback(native_op, ['TTL', key])
        return result if result is not None else -2
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on existing key"""
        def native_op():
            return self.native_client.expire(key, seconds)
        
        result = self._execute_with_fallback(native_op, ['EXPIRE', key, str(seconds)])
        return bool(result)
    
    def ping(self) -> bool:
        """Test Redis connection"""
        def native_op():
            return self.native_client.ping()
        
        result = self._execute_with_fallback(native_op, ['PING'])
        return result == 'PONG' or result is True
    
    def flushdb(self) -> bool:
        """Clear all keys in current database (use with caution)"""
        def native_op():
            return self.native_client.flushdb()
        
        result = self._execute_with_fallback(native_op, ['FLUSHDB'])
        return result == 'OK' or result is True
    
    def info(self) -> Dict[str, Any]:
        """Get Redis server information"""
        def native_op():
            return self.native_client.info()
        
        result = self._execute_with_fallback(native_op, ['INFO'])
        return result if isinstance(result, dict) else {}
    
    def is_native_connected(self) -> bool:
        """Check if native connection is active"""
        return self.use_native and self.native_client is not None
    
    def get_connection_type(self) -> str:
        """Get current connection type for monitoring"""
        if self.is_native_connected():
            return "native"
        elif self.enabled:
            return "rest_api"
        else:
            return "disabled"


# Maintain backward compatibility with existing code
class RedisClient(RedisClientEnhanced):
    """Backward compatible Redis client (uses enhanced version)"""
    pass


if __name__ == "__main__":
    # Test the enhanced Redis client
    logging.basicConfig(level=logging.INFO)
    
    client = RedisClientEnhanced()
    
    print(f"Redis connection type: {client.get_connection_type()}")
    print(f"Redis enabled: {client.enabled}")
    
    if client.enabled:
        # Test basic operations
        test_key = "test_enhanced_client"
        
        print(f"Setting test key...")
        client.setex(test_key, 60, "test_value")
        
        print(f"Getting test key: {client.get(test_key)}")
        print(f"Key exists: {client.exists(test_key)}")
        print(f"TTL: {client.ttl(test_key)}")
        
        print(f"Deleting test key: {client.delete(test_key)}")
        print(f"Key exists after delete: {client.exists(test_key)}")
        
        if client.is_native_connected():
            print("✅ Native Redis connection working!")
        else:
            print("🔄 Using REST API fallback")