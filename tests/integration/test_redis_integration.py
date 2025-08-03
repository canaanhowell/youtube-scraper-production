"""
Integration tests for Redis functionality
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
import json
import time

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.redis_client_enhanced import RedisClientEnhanced


class TestRedisIntegration:
    """Integration tests for Redis client"""
    
    @patch('src.utils.redis_client_enhanced.redis.ConnectionPool')
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_redis_initialization_native(self, mock_redis_class, mock_pool_class, mock_env):
        """Test Redis client initialization with native connection"""
        # Mock successful native connection
        mock_pool = Mock()
        mock_pool_class.return_value = mock_pool
        
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        assert client.use_native is True
        assert client.native_client is not None
        mock_redis_instance.ping.assert_called_once()
    
    @patch('src.utils.redis_client_enhanced.redis.ConnectionPool')
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_redis_fallback_to_rest(self, mock_redis_class, mock_pool_class, mock_env):
        """Test Redis client fallback to REST API"""
        # Mock failed native connection
        mock_redis_instance = Mock()
        mock_redis_instance.ping.side_effect = Exception("Connection failed")
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        assert client.use_native is False
        assert client.native_client is None
    
    @patch('src.utils.redis_client_enhanced.requests.post')
    def test_is_duplicate_rest_api(self, mock_post, mock_env):
        """Test duplicate checking via REST API"""
        # Mock REST API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": 1}  # 1 means exists
        mock_post.return_value = mock_response
        
        client = RedisClientEnhanced()
        client.use_native = False  # Force REST API usage
        
        result = client.is_duplicate("video123")
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify the request format
        call_args = mock_post.call_args
        assert "EXISTS" in call_args[1]['json'][0]
        assert "yt:video123" in call_args[1]['json'][1]
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_is_duplicate_native(self, mock_redis_class, mock_env):
        """Test duplicate checking via native client"""
        # Mock native Redis
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.return_value = 1  # 1 means exists
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        result = client.is_duplicate("video456")
        
        assert result is True
        mock_redis_instance.exists.assert_called_with("yt:video456")
    
    @patch('src.utils.redis_client_enhanced.requests.post')
    def test_mark_as_collected_rest_api(self, mock_post, mock_env):
        """Test marking video as collected via REST API"""
        # Mock REST API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "OK"}
        mock_post.return_value = mock_response
        
        client = RedisClientEnhanced()
        client.use_native = False  # Force REST API usage
        
        result = client.mark_as_collected("video789")
        
        assert result is True
        mock_post.assert_called_once()
        
        # Verify the request includes TTL
        call_args = mock_post.call_args
        assert "SETEX" in call_args[1]['json'][0]
        assert "yt:video789" in call_args[1]['json'][1]
        assert 86400 in call_args[1]['json'][2]  # 24 hours TTL
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_mark_as_collected_native(self, mock_redis_class, mock_env):
        """Test marking video as collected via native client"""
        # Mock native Redis
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.setex.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        result = client.mark_as_collected("video101")
        
        assert result is True
        mock_redis_instance.setex.assert_called_with(
            "yt:video101",
            86400,  # 24 hours
            "1"
        )
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_connection_pool_reuse(self, mock_redis_class, mock_env):
        """Test that connection pool is reused for performance"""
        # Mock native Redis with connection pool
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.connection_pool = Mock()
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        # Multiple operations should use same connection pool
        client.is_duplicate("video1")
        client.is_duplicate("video2")
        client.mark_as_collected("video3")
        
        # Verify operations were performed
        assert mock_redis_instance.exists.call_count == 2
        assert mock_redis_instance.setex.call_count == 1
    
    @patch('src.utils.redis_client_enhanced.requests.post')
    def test_error_handling_rest_api(self, mock_post, mock_env):
        """Test error handling for REST API failures"""
        # Mock failed REST API call
        mock_post.side_effect = Exception("Network error")
        
        client = RedisClientEnhanced()
        client.use_native = False
        
        # Should handle errors gracefully
        result = client.is_duplicate("video_error")
        assert result is False  # Default to not duplicate on error
        
        result = client.mark_as_collected("video_error")
        assert result is False  # Return False on error
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_error_handling_native(self, mock_redis_class, mock_env):
        """Test error handling for native client failures"""
        # Mock Redis with errors
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.side_effect = Exception("Redis error")
        mock_redis_instance.setex.side_effect = Exception("Redis error")
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        # Should handle errors gracefully
        result = client.is_duplicate("video_error")
        assert result is False
        
        result = client.mark_as_collected("video_error")
        assert result is False
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_ttl_configuration(self, mock_redis_class, mock_env):
        """Test TTL is properly set to 24 hours"""
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        # Verify TTL is set to 24 hours (86400 seconds)
        assert client.ttl_seconds == 86400
        
        client.mark_as_collected("test_video")
        mock_redis_instance.setex.assert_called_with(
            "yt:test_video",
            86400,
            "1"
        )
    
    @patch('src.utils.redis_client_enhanced.redis.Redis')
    def test_performance_native_vs_rest(self, mock_redis_class, mock_env):
        """Test performance characteristics of native vs REST"""
        # This test documents expected performance differences
        mock_redis_instance = Mock()
        mock_redis_instance.ping.return_value = True
        mock_redis_instance.exists.return_value = 0
        mock_redis_instance.setex.return_value = True
        mock_redis_class.return_value = mock_redis_instance
        
        client = RedisClientEnhanced()
        
        # Native client should be available
        assert client.use_native is True
        
        # Simulate batch operations
        start_time = time.time()
        for i in range(10):
            client.is_duplicate(f"perf_test_{i}")
            client.mark_as_collected(f"perf_test_{i}")
        native_time = time.time() - start_time
        
        # Native should complete quickly (mocked, so nearly instant)
        assert native_time < 1.0
        
        # Verify all operations were called
        assert mock_redis_instance.exists.call_count == 10
        assert mock_redis_instance.setex.call_count == 10
    
    def test_get_health(self, mock_env):
        """Test health check functionality"""
        with patch('src.utils.redis_client_enhanced.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_instance.ping.return_value = True
            mock_redis_instance.info.return_value = {
                'redis_version': '7.0.0',
                'connected_clients': 5,
                'used_memory_human': '10M'
            }
            mock_redis_class.return_value = mock_redis_instance
            
            client = RedisClientEnhanced()
            health = client.get_health()
            
            assert health['status'] == 'healthy'
            assert health['connection_type'] == 'native'
            assert 'latency_ms' in health
            
        # Test with REST API fallback
        with patch('src.utils.redis_client_enhanced.redis.Redis') as mock_redis_class:
            mock_redis_instance = Mock()
            mock_redis_instance.ping.side_effect = Exception("Connection failed")
            mock_redis_class.return_value = mock_redis_instance
            
            client = RedisClientEnhanced()
            health = client.get_health()
            
            assert health['status'] == 'healthy'
            assert health['connection_type'] == 'rest'