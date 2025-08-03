"""
Test configuration and shared fixtures for YouTube scraper tests.
"""
import pytest
import os
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
import tempfile
import shutil

# Add the parent directory to sys.path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

@pytest.fixture
def mock_env():
    """Mock environment variables for testing"""
    env_vars = {
        'GOOGLE_SERVICE_KEY_PATH': '/mock/path/to/service-key.json',
        'UPSTASH_REDIS_REST_URL': 'https://mock-redis.upstash.io',
        'UPSTASH_REDIS_REST_TOKEN': 'mock_token_12345',
        'SURFSHARK_PRIVATE_KEY': 'mock_private_key',
        'SURFSHARK_ADDRESS': 'mock.surfshark.address',
        'VPN_SERVER': 'us-nyc.prod.surfshark.com'
    }
    
    # Store original values
    original_env = {}
    for key, value in env_vars.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield env_vars
    
    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

@pytest.fixture
def mock_firebase_client():
    """Mock Firebase client for testing"""
    mock_client = Mock()
    mock_client.get_keywords.return_value = ['python', 'machine learning', 'api testing']
    mock_client.save_video.return_value = True
    mock_client.log_collection_run.return_value = 'mock_log_id_123'
    return mock_client

@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing"""
    mock_client = Mock()
    mock_client.is_duplicate.return_value = False
    mock_client.mark_as_collected.return_value = True
    mock_client.get_health.return_value = {'status': 'healthy'}
    return mock_client

@pytest.fixture
def sample_video_data():
    """Sample video data for testing"""
    return {
        'id': 'dQw4w9WgXcQ',
        'title': 'Never Gonna Give You Up',
        'channel': 'RickAstleyVEVO',
        'channel_id': 'UCuAXFkgsw1L7xaCfnd5JJOw',
        'duration': '3:32',
        'views': '1.2B views',
        'published': '12 years ago',
        'description': 'The official video for "Never Gonna Give You Up"',
        'thumbnail_url': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg',
        'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
        'collected_at': '2025-08-02T19:30:00Z'
    }

@pytest.fixture
def sample_youtube_html():
    """Sample YouTube HTML response for testing"""
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>YouTube</title></head>
    <body>
        <script>
            var ytInitialData = {
                "contents": {
                    "twoColumnSearchResultsRenderer": {
                        "primaryContents": {
                            "sectionListRenderer": {
                                "contents": [{
                                    "itemSectionRenderer": {
                                        "contents": [{
                                            "videoRenderer": {
                                                "videoId": "dQw4w9WgXcQ",
                                                "title": {"runs": [{"text": "Never Gonna Give You Up"}]},
                                                "ownerText": {"runs": [{"text": "RickAstleyVEVO"}]},
                                                "lengthText": {"simpleText": "3:32"},
                                                "viewCountText": {"simpleText": "1.2B views"},
                                                "publishedTimeText": {"simpleText": "12 years ago"},
                                                "detailedMetadataSnippets": [{"snippetText": {"runs": [{"text": "Official video"}]}}],
                                                "thumbnails": [{"url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"}]
                                            }
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                }
            };
        </script>
    </body>
    </html>
    '''

@pytest.fixture
def temp_log_dir():
    """Temporary directory for log files during testing"""
    temp_dir = tempfile.mkdtemp()
    log_dir = Path(temp_dir) / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    yield log_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_docker_compose():
    """Mock docker compose operations"""
    mock_subprocess = Mock()
    mock_subprocess.return_value.returncode = 0
    mock_subprocess.return_value.stdout = "Container started successfully"
    mock_subprocess.return_value.stderr = ""
    return mock_subprocess

@pytest.fixture
def performance_test_config():
    """Configuration for performance tests"""
    return {
        'max_concurrent_keywords': 10,
        'test_duration_seconds': 60,
        'ramp_up_time_seconds': 10,
        'target_response_time_ms': 5000,
        'acceptable_error_rate_percent': 5,
        'memory_threshold_mb': 512,
        'cpu_threshold_percent': 80
    }

@pytest.fixture
def load_test_keywords():
    """Keywords for load testing"""
    return [
        'python programming',
        'machine learning',
        'api development',
        'docker containers',
        'microservices',
        'cloud computing',
        'data science',
        'artificial intelligence',
        'web development',
        'software engineering'
    ]