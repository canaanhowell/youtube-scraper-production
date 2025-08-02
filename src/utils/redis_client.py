import os
import json
import logging
import requests
from typing import Optional, Any
from datetime import timedelta

logger = logging.getLogger(__name__)

class RedisClient:
    """Redis client using Upstash REST API for caching"""
    
    def __init__(self):
        self.redis_url = os.environ.get('UPSTASH_REDIS_REST_URL')
        self.redis_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN')
        
        if not self.redis_url or not self.redis_token:
            logger.warning("Redis credentials not found in environment variables")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Redis client initialized with Upstash REST API")
    
    def _make_request(self, command: list) -> Optional[Any]:
        """Make a request to Upstash Redis REST API"""
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
                json=command
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('result')
            else:
                logger.error(f"Redis request failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Redis request error: {e}")
            return None
    
    def exists(self, key: str) -> int:
        """Check if key exists"""
        result = self._make_request(['EXISTS', key])
        return result if result is not None else 0
    
    def setex(self, key: str, seconds: int, value: str) -> bool:
        """Set key with expiration"""
        result = self._make_request(['SETEX', key, str(seconds), value])
        return result == 'OK' if result else False
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        return self._make_request(['GET', key])
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        result = self._make_request(['DEL', key])
        return bool(result) if result is not None else False
    
    def keys(self, pattern: str = '*') -> list:
        """Get keys matching pattern"""
        result = self._make_request(['KEYS', pattern])
        return result if result else []
    
    def ttl(self, key: str) -> int:
        """Get time to live for key"""
        result = self._make_request(['TTL', key])
        return result if result is not None else -2