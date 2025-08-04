"""
Unit tests for YouTubeCollectionManager class
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone
import subprocess

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from youtube_collection_manager import YouTubeCollectionManager


class TestYouTubeCollectionManager:
    """Test suite for YouTubeCollectionManager"""
    
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_initialization(self, mock_load_env, mock_firebase, mock_redis, mock_scraper, mock_env):
        """Test collection manager initialization"""
        manager = YouTubeCollectionManager()
        
        assert manager.firebase is not None
        assert manager.redis is not None
        assert manager.scraper is not None
        assert manager.container_name == 'youtube-vpn'
        assert manager.session_id.startswith('session_')
        assert len(manager.all_servers) == 80  # Should have 80 servers
        assert manager.max_vpn_attempts_per_keyword == 3
        mock_load_env.assert_called_once()
    
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_get_surfshark_servers(self, mock_load_env, mock_firebase, mock_redis, mock_scraper, mock_env):
        """Test Surfshark server list generation"""
        manager = YouTubeCollectionManager()
        servers = manager._get_surfshark_servers()
        
        # Check we have 80 servers
        assert len(servers) == 80
        
        # Check format is correct (no numbers)
        for server in servers:
            assert server.endswith('.prod.surfshark.com')
            assert not any(char.isdigit() for char in server.split('-')[1])  # No digits in city part
        
        # Check some expected servers are present
        expected_servers = [
            'us-nyc.prod.surfshark.com',
            'us-lax.prod.surfshark.com',
            'us-chi.prod.surfshark.com'
        ]
        for expected in expected_servers:
            assert expected in servers
    
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_rotate_vpn_server_success(self, mock_load_env, mock_firebase, mock_redis, 
                                      mock_scraper, mock_subprocess, mock_env):
        """Test successful VPN server rotation"""
        manager = YouTubeCollectionManager()
        
        # Mock subprocess responses
        mock_subprocess.return_value = Mock(returncode=0, stdout='', stderr='')
        
        # Mock wait_for_vpn_connection
        manager.wait_for_vpn_connection = Mock(return_value=True)
        
        result = manager.rotate_vpn_server('us-nyc.prod.surfshark.com')
        
        assert result is True
        assert 'us-nyc.prod.surfshark.com' in manager.working_servers
        assert 'us-nyc.prod.surfshark.com' not in manager.untested_servers
        
        # Verify subprocess calls
        calls = mock_subprocess.call_args_list
        assert len(calls) == 2  # docker compose down, docker compose up
        assert calls[0][0][0] == ['docker', 'compose', 'down']
        assert calls[1][0][0] == ['docker', 'compose', 'up', '-d']
    
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_rotate_vpn_server_failure(self, mock_load_env, mock_firebase, mock_redis, 
                                      mock_scraper, mock_subprocess, mock_env):
        """Test failed VPN server rotation"""
        manager = YouTubeCollectionManager()
        
        # Mock failed docker compose down
        mock_subprocess.return_value = Mock(returncode=1, stdout='', stderr='Container error')
        
        result = manager.rotate_vpn_server('us-nyc.prod.surfshark.com')
        
        assert result is False
        assert 'us-nyc.prod.surfshark.com' in manager.failed_servers
        assert 'us-nyc.prod.surfshark.com' not in manager.working_servers
    
    @patch('src.scripts.youtube_collection_manager.json.loads')
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_wait_for_vpn_connection_success(self, mock_load_env, mock_firebase, mock_redis, 
                                            mock_scraper, mock_subprocess, mock_json, mock_env):
        """Test successful VPN connection wait"""
        manager = YouTubeCollectionManager()
        
        # Mock successful connection check
        mock_subprocess.return_value = Mock(
            returncode=0, 
            stdout='{"city": "New York", "ip": "1.2.3.4"}'
        )
        mock_json.return_value = {"city": "New York", "ip": "1.2.3.4"}
        
        result = manager.wait_for_vpn_connection(timeout=30)
        
        assert result is True
        mock_subprocess.assert_called()
    
    @patch('src.scripts.youtube_collection_manager.time.time')
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_wait_for_vpn_connection_timeout(self, mock_load_env, mock_firebase, mock_redis, 
                                           mock_scraper, mock_subprocess, mock_time, mock_env):
        """Test VPN connection timeout"""
        manager = YouTubeCollectionManager()
        
        # Mock time progression
        start_time = 1000
        mock_time.side_effect = [start_time, start_time + 10, start_time + 20, start_time + 130]
        
        # Mock failed connection checks
        mock_subprocess.return_value = Mock(returncode=1)
        
        result = manager.wait_for_vpn_connection(timeout=120)
        
        assert result is False
    
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_get_next_available_server(self, mock_load_env, mock_firebase, mock_redis, 
                                     mock_scraper, mock_env):
        """Test server selection logic"""
        manager = YouTubeCollectionManager()
        
        # Set up server health tracking
        manager.working_servers = {'us-nyc.prod.surfshark.com', 'us-lax.prod.surfshark.com'}
        manager.failed_servers = {'us-chi.prod.surfshark.com'}
        manager.untested_servers = {'us-dal.prod.surfshark.com', 'us-mia.prod.surfshark.com'}
        
        # Test: Should prefer working servers
        server = manager.get_next_available_server()
        assert server in manager.working_servers
        
        # Test: Should exclude specific servers
        server = manager.get_next_available_server(exclude_servers={'us-nyc.prod.surfshark.com'})
        assert server != 'us-nyc.prod.surfshark.com'
        
        # Test: Should use untested when no working available
        server = manager.get_next_available_server(
            exclude_servers={'us-nyc.prod.surfshark.com', 'us-lax.prod.surfshark.com'}
        )
        assert server in manager.untested_servers
        
        # Test: Should return None when no servers available
        server = manager.get_next_available_server(
            exclude_servers=manager.working_servers | manager.untested_servers
        )
        assert server is None
    
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_process_keyword_with_retry_success(self, mock_load_env, mock_firebase, 
                                               mock_redis, mock_scraper, mock_env):
        """Test successful keyword processing with retry logic"""
        manager = YouTubeCollectionManager()
        
        # Mock successful VPN rotation and scraping
        manager.rotate_vpn_server = Mock(return_value=True)
        mock_scraper_instance = Mock()
        mock_scraper_instance.scrape_keyword.return_value = {
            'saved_to_firebase': 10,
            'success': True
        }
        manager.scraper = mock_scraper_instance
        
        result = manager.process_keyword_with_retry('python programming')
        
        assert result == 10
        assert manager.collection_stats['videos_per_keyword']['python programming'] == 10
        assert manager.collection_stats['total_videos_collected'] == 10
        manager.rotate_vpn_server.assert_called_once()
        mock_scraper_instance.scrape_keyword.assert_called_once_with('python programming', max_videos=100)
    
    @patch('src.scripts.youtube_collection_manager.time.sleep')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_process_keyword_with_retry_vpn_failures(self, mock_load_env, mock_firebase, 
                                                    mock_redis, mock_scraper, mock_sleep, mock_env):
        """Test keyword processing with VPN failures and retries"""
        manager = YouTubeCollectionManager()
        
        # Mock VPN failures then success
        manager.rotate_vpn_server = Mock(side_effect=[False, False, True])
        mock_scraper_instance = Mock()
        mock_scraper_instance.scrape_keyword.return_value = {
            'saved_to_firebase': 5,
            'success': True
        }
        manager.scraper = mock_scraper_instance
        
        result = manager.process_keyword_with_retry('machine learning')
        
        assert result == 5
        assert manager.rotate_vpn_server.call_count == 3
        # Check exponential backoff was applied
        mock_sleep.assert_has_calls([call(1), call(2)])
    
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_process_keyword_with_retry_all_failures(self, mock_load_env, mock_firebase, 
                                                    mock_redis, mock_scraper, mock_env):
        """Test keyword processing when all VPN attempts fail"""
        manager = YouTubeCollectionManager()
        
        # Mock all VPN attempts failing
        manager.rotate_vpn_server = Mock(return_value=False)
        
        with pytest.raises(Exception) as exc_info:
            manager.process_keyword_with_retry('api development')
        
        assert 'Failed to connect to any VPN server' in str(exc_info.value)
        assert manager.rotate_vpn_server.call_count == 3
    
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_run_method_success(self, mock_load_env, mock_firebase_class, mock_redis, 
                               mock_scraper, mock_subprocess, mock_env):
        """Test full run method execution"""
        # Setup mocks
        mock_firebase_instance = Mock()
        mock_firebase_instance.get_keywords.return_value = ['python', 'javascript', 'docker']
        mock_firebase_instance.log_collection_run.return_value = 'log_id_123'
        mock_firebase_class.return_value = mock_firebase_instance
        
        manager = YouTubeCollectionManager()
        manager.process_keyword_with_retry = Mock(side_effect=[10, 15, 8])
        
        # Capture sys.exit
        with pytest.raises(SystemExit) as exc_info:
            manager.run()
        
        # Should exit with 0 (success)
        assert exc_info.value.code == 0
        
        # Verify all keywords were processed
        assert manager.process_keyword_with_retry.call_count == 3
        assert manager.collection_stats['total_videos_collected'] == 33
        assert manager.collection_stats['success'] is True
        assert manager.collection_stats['success_rate'] == 100.0
        
        # Verify Firebase logging
        mock_firebase_instance.log_collection_run.assert_called_once()
    
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_run_method_partial_failure(self, mock_load_env, mock_firebase_class, mock_redis, 
                                      mock_scraper, mock_subprocess, mock_env):
        """Test run method with some keyword failures"""
        # Setup mocks
        mock_firebase_instance = Mock()
        mock_firebase_instance.get_keywords.return_value = ['python', 'javascript', 'docker', 'api']
        mock_firebase_instance.log_collection_run.return_value = 'log_id_123'
        mock_firebase_class.return_value = mock_firebase_instance
        
        manager = YouTubeCollectionManager()
        # 2 successes, 2 failures = 50% success rate
        manager.process_keyword_with_retry = Mock(
            side_effect=[10, Exception('Network error'), 8, Exception('VPN error')]
        )
        
        # Capture sys.exit
        with pytest.raises(SystemExit) as exc_info:
            manager.run()
        
        # Should exit with 0 (50% success rate meets threshold)
        assert exc_info.value.code == 0
        
        assert manager.collection_stats['success_rate'] == 50.0
        assert manager.collection_stats['success'] is True
        assert len(manager.collection_stats['errors']) == 2
    
    @patch('src.scripts.youtube_collection_manager.subprocess.run')
    @patch('src.scripts.youtube_collection_manager.YouTubeScraperProduction')
    @patch('src.scripts.youtube_collection_manager.RedisClient')
    @patch('src.scripts.youtube_collection_manager.FirebaseClient')
    @patch('src.scripts.youtube_collection_manager.load_env')
    def test_finalize_collection(self, mock_load_env, mock_firebase_class, mock_redis, 
                                mock_scraper, mock_subprocess, mock_env):
        """Test collection finalization"""
        # Setup mocks
        mock_firebase_instance = Mock()
        mock_firebase_instance.log_collection_run.return_value = 'log_id_123'
        mock_firebase_class.return_value = mock_firebase_instance
        
        manager = YouTubeCollectionManager()
        manager.collection_stats['total_videos_collected'] = 25
        manager.collection_stats['keywords_processed'] = ['python', 'javascript']
        manager.collection_stats['success'] = True
        
        # Test finalization
        with pytest.raises(SystemExit):
            manager._finalize_collection()
        
        # Verify Firebase logging
        mock_firebase_instance.log_collection_run.assert_called_once()
        log_data = mock_firebase_instance.log_collection_run.call_args[0][0]
        assert log_data['total_videos_collected'] == 25
        assert 'duration_seconds' in log_data
        assert 'end_time' in log_data
        
        # Verify docker compose down was called
        mock_subprocess.assert_called_with(
            ['docker', 'compose', 'down'],
            cwd=manager.docker_compose_path.parent,
            capture_output=True
        )