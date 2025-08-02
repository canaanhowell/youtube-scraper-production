import os
import sys
import logging
import requests
import json
from typing import Any, Optional, Dict, List
from datetime import datetime, timedelta

# Add project path to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from utils.env_loader import load_env
load_env()

# Set up logging
from utils.logging_config import setup_logging
logger, network_logger = setup_logging()


class UpstashClient:
    """Upstash Redis REST API client for YouTube scraper caching"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network_logger = logging.getLogger('network')
        
        # Get Upstash credentials from environment
        self.redis_url = os.environ.get('UPSTASH_REDIS_REST_URL') or os.environ.get('REDIS_URL')
        self.redis_token = os.environ.get('UPSTASH_REDIS_REST_TOKEN') or os.environ.get('REDIS_TOKEN')
        
        if not self.redis_url or not self.redis_token:
            self.logger.warning("Upstash Redis credentials not found in environment variables")
            self.redis_url = None
            self.redis_token = None
            self.enabled = False
        else:
            # Ensure URL has https://
            if not self.redis_url.startswith('http'):
                self.redis_url = f'https://{self.redis_url}'
            
            self.enabled = True
            self.logger.info("Upstash Redis client initialized")
            
        # Cache TTLs (in seconds)
        self.video_ttl = 24 * 60 * 60  # 24 hours for video deduplication
        self.session_ttl = 2 * 60 * 60  # 2 hours for session data
        self.vpn_ttl = 60 * 60  # 1 hour for VPN IP tracking
        
    def _make_request(self, command: list) -> Any:
        """Make a request to Upstash Redis REST API"""
        if not self.enabled:
            return None
            
        try:
            # Prepare the command
            url = self.redis_url
            headers = {
                'Authorization': f'Bearer {self.redis_token}',
                'Content-Type': 'application/json'
            }
            
            # Log the request
            self.network_logger.info(f"Upstash Redis command: {command[0]}")
            
            # Make the request
            response = requests.post(
                url,
                headers=headers,
                json=command
            )
            
            response.raise_for_status()
            
            # Parse response
            result = response.json()
            return result.get('result')
            
        except Exception as e:
            self.logger.error(f"Upstash Redis request failed: {e}")
            return None
    
    def get(self, key: str) -> Optional[str]:
        """Get a value from Redis"""
        result = self._make_request(['GET', key])
        return result
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value in Redis with optional TTL"""
        command = ['SET', key, value]
        if ttl:
            command.extend(['EX', str(ttl)])
        
        result = self._make_request(command)
        return result == 'OK'
    
    def setex(self, key: str, ttl: int, value: str) -> bool:
        """Set a value with expiration"""
        result = self._make_request(['SETEX', key, str(ttl), value])
        return result == 'OK'
    
    def exists(self, key: str) -> bool:
        """Check if a key exists in Redis"""
        result = self._make_request(['EXISTS', key])
        return bool(result)
    
    def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on a key"""
        result = self._make_request(['EXPIRE', key, str(ttl)])
        return bool(result)
    
    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        result = self._make_request(['DEL', key])
        return bool(result)
    
    def sadd(self, key: str, *members: str) -> int:
        """Add members to a set"""
        command = ['SADD', key] + list(members)
        result = self._make_request(command)
        return int(result) if result is not None else 0
    
    def sismember(self, key: str, member: str) -> bool:
        """Check if member exists in set"""
        result = self._make_request(['SISMEMBER', key, member])
        return bool(result)
    
    def smembers(self, key: str) -> List[str]:
        """Get all members of a set"""
        result = self._make_request(['SMEMBERS', key])
        return result if result else []
    
    def scard(self, key: str) -> int:
        """Get cardinality of a set"""
        result = self._make_request(['SCARD', key])
        return int(result) if result is not None else 0
    
    def srem(self, key: str, *members: str) -> int:
        """Remove members from a set"""
        command = ['SREM', key] + list(members)
        result = self._make_request(command)
        return int(result) if result is not None else 0
    
    def hset(self, key: str, field: str, value: str) -> int:
        """Set field in hash"""
        result = self._make_request(['HSET', key, field, value])
        return int(result) if result is not None else 0
    
    def hget(self, key: str, field: str) -> Optional[str]:
        """Get field from hash"""
        result = self._make_request(['HGET', key, field])
        return result
    
    def hincrby(self, key: str, field: str, increment: int) -> int:
        """Increment hash field by integer"""
        result = self._make_request(['HINCRBY', key, field, str(increment)])
        return int(result) if result is not None else 0
    
    def hgetall(self, key: str) -> Dict[str, str]:
        """Get all fields and values from hash"""
        result = self._make_request(['HGETALL', key])
        if not result:
            return {}
        
        # Convert flat list to dict
        hash_dict = {}
        for i in range(0, len(result), 2):
            if i + 1 < len(result):
                hash_dict[result[i]] = result[i + 1]
        return hash_dict
    
    def rpush(self, key: str, *values: str) -> int:
        """Push values to end of list"""
        command = ['RPUSH', key] + list(values)
        result = self._make_request(command)
        return int(result) if result is not None else 0
    
    def lpop(self, key: str) -> Optional[str]:
        """Pop value from beginning of list"""
        result = self._make_request(['LPOP', key])
        return result
    
    def lrange(self, key: str, start: int, stop: int) -> List[str]:
        """Get range of elements from list"""
        result = self._make_request(['LRANGE', key, str(start), str(stop)])
        return result if result else []
    
    def llen(self, key: str) -> int:
        """Get length of list"""
        result = self._make_request(['LLEN', key])
        return int(result) if result is not None else 0
    
    def ltrim(self, key: str, start: int, stop: int) -> bool:
        """Trim list to specified range"""
        result = self._make_request(['LTRIM', key, str(start), str(stop)])
        return result == 'OK'
    
    # YouTube-specific helper methods
    
    def mark_video_collected(self, video_id: str) -> bool:
        """Mark a video as collected with 24-hour TTL"""
        return self.setex(f"youtube:24h:videos:{video_id}", self.video_ttl, "1")
    
    def is_video_collected(self, video_id: str) -> bool:
        """Check if video was already collected"""
        return self.exists(f"youtube:24h:videos:{video_id}")
    
    def update_session_progress(self, session_id: str, keyword: str, count: int = 1) -> int:
        """Update collection progress for a session and keyword"""
        return self.hincrby(f"youtube:session:{session_id}:collected", keyword, count)
    
    def get_session_progress(self, session_id: str, keyword: str) -> int:
        """Get collection progress for a session and keyword"""
        result = self.hget(f"youtube:session:{session_id}:collected", keyword)
        return int(result) if result else 0
    
    def get_all_session_progress(self, session_id: str) -> Dict[str, int]:
        """Get all keyword progress for a session"""
        progress = self.hgetall(f"youtube:session:{session_id}:collected")
        return {k: int(v) for k, v in progress.items()}
    
    def add_to_upload_queue(self, video_data: Dict[str, Any]) -> int:
        """Add video to upload queue"""
        return self.rpush("youtube:upload:queue", json.dumps(video_data))
    
    def get_upload_batch(self, batch_size: int = 100) -> List[Dict[str, Any]]:
        """Get batch of videos from upload queue"""
        batch = []
        for _ in range(batch_size):
            video_json = self.lpop("youtube:upload:queue")
            if video_json:
                try:
                    batch.append(json.loads(video_json))
                except json.JSONDecodeError:
                    self.logger.error(f"Failed to parse video JSON: {video_json}")
            else:
                break
        return batch
    
    def get_upload_queue_size(self) -> int:
        """Get size of upload queue"""
        return self.llen("youtube:upload:queue")