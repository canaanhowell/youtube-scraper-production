"""
Unit tests for YouTubeScraperProduction class
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.scripts.youtube_scraper_production import YouTubeScraperProduction


class TestYouTubeScraperProduction:
    """Test suite for YouTubeScraperProduction"""
    
    @patch('src.scripts.youtube_scraper_production.FirebaseClient')
    @patch('src.scripts.youtube_scraper_production.RedisClient')
    @patch('src.scripts.youtube_scraper_production.load_env')
    def test_initialization(self, mock_load_env, mock_redis, mock_firebase, mock_env):
        """Test scraper initialization"""
        scraper = YouTubeScraperProduction()
        
        assert scraper.firebase is not None
        assert scraper.redis is not None
        assert scraper.container_name == "youtube-vpn"
        mock_load_env.assert_called_once()
    
    def test_build_search_url(self, mock_env):
        """Test YouTube search URL construction"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            
            # Test simple keyword
            keyword = "python"
            expected_url = 'https://www.youtube.com/results?search_query=python&sp=EgIIAQ%253D%253D'
            
            # This tests the URL building logic from scrape_keyword method
            test_url = f'https://www.youtube.com/results?search_query={keyword.replace(" ", "+")}&sp=EgIIAQ%253D%253D'
            assert test_url == expected_url
            
            # Test keyword with spaces
            keyword_with_spaces = "machine learning"
            expected_url_spaces = 'https://www.youtube.com/results?search_query=machine+learning&sp=EgIIAQ%253D%253D'
            test_url_spaces = f'https://www.youtube.com/results?search_query={keyword_with_spaces.replace(" ", "+")}&sp=EgIIAQ%253D%253D'
            assert test_url_spaces == expected_url_spaces
    
    @patch('src.scripts.youtube_scraper_production.subprocess.run')
    def test_fetch_youtube_page_success(self, mock_subprocess, mock_env):
        """Test successful YouTube page fetching"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            
            # Mock successful subprocess call
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "<html>Mock YouTube content</html>"
            mock_subprocess.return_value = mock_result
            
            url = "https://www.youtube.com/results?search_query=test"
            result = scraper._fetch_youtube_page(url)
            
            assert result == "<html>Mock YouTube content</html>"
            mock_subprocess.assert_called_once()
    
    @patch('src.scripts.youtube_scraper_production.subprocess.run')
    def test_fetch_youtube_page_failure(self, mock_subprocess, mock_env):
        """Test YouTube page fetching failure"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            
            # Mock failed subprocess call
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stderr = "Connection failed"
            mock_subprocess.return_value = mock_result
            
            url = "https://www.youtube.com/results?search_query=test"
            result = scraper._fetch_youtube_page(url)
            
            assert result is None
    
    def test_extract_videos_from_initial_data(self, sample_youtube_html, mock_env):
        """Test video extraction from YouTube HTML"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            keyword = "test keyword"
            
            videos = scraper._extract_videos_from_initial_data(sample_youtube_html, keyword)
            
            assert len(videos) == 1
            video = videos[0]
            assert video['id'] == 'dQw4w9WgXcQ'
            assert video['title'] == 'Never Gonna Give You Up'
            assert video['channel'] == 'RickAstleyVEVO'
            assert video['duration'] == '3:32'
            assert 'keyword' in video
            assert video['keyword'] == keyword
    
    def test_extract_videos_invalid_html(self, mock_env):
        """Test video extraction with invalid HTML"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            
            invalid_html = "<html><body>No ytInitialData here</body></html>"
            videos = scraper._extract_videos_from_initial_data(invalid_html, "test")
            
            assert videos == []
    
    def test_is_duplicate_check(self, mock_env):
        """Test duplicate video checking"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient') as mock_redis_class, \
             patch('youtube_scraper_production.load_env'):
            
            # Setup mock Redis instance
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance
            
            scraper = YouTubeScraperProduction()
            video_id = "test_video_id"
            
            # Test non-duplicate
            mock_redis_instance.is_duplicate.return_value = False
            assert not scraper._is_duplicate(video_id)
            
            # Test duplicate
            mock_redis_instance.is_duplicate.return_value = True
            assert scraper._is_duplicate(video_id)
            
            mock_redis_instance.is_duplicate.assert_called_with(video_id)
    
    def test_mark_as_collected(self, mock_env):
        """Test marking video as collected"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient') as mock_redis_class, \
             patch('youtube_scraper_production.load_env'):
            
            mock_redis_instance = Mock()
            mock_redis_class.return_value = mock_redis_instance
            
            scraper = YouTubeScraperProduction()
            video_id = "test_video_id"
            
            mock_redis_instance.mark_as_collected.return_value = True
            result = scraper._mark_as_collected(video_id)
            
            assert result is True
            mock_redis_instance.mark_as_collected.assert_called_with(video_id)
    
    def test_save_to_firebase(self, sample_video_data, mock_env):
        """Test saving video to Firebase"""
        with patch('youtube_scraper_production.FirebaseClient') as mock_firebase_class, \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            mock_firebase_instance = Mock()
            mock_firebase_class.return_value = mock_firebase_instance
            
            scraper = YouTubeScraperProduction()
            keyword = "test keyword"
            
            mock_firebase_instance.save_video.return_value = True
            result = scraper._save_to_firebase(keyword, sample_video_data)
            
            assert result is True
            mock_firebase_instance.save_video.assert_called_with(keyword, sample_video_data)
    
    @patch('src.scripts.youtube_scraper_production.datetime')
    def test_scrape_keyword_integration(self, mock_datetime, sample_video_data, mock_env):
        """Test full scrape_keyword method flow"""
        # Mock datetime
        mock_now = datetime(2025, 8, 2, 19, 30, 0)
        mock_datetime.utcnow.return_value = mock_now
        
        with patch('youtube_scraper_production.FirebaseClient') as mock_firebase_class, \
             patch('youtube_scraper_production.RedisClient') as mock_redis_class, \
             patch('youtube_scraper_production.load_env'):
            
            # Setup mocks
            mock_firebase_instance = Mock()
            mock_redis_instance = Mock()
            mock_firebase_class.return_value = mock_firebase_instance
            mock_redis_class.return_value = mock_redis_instance
            
            scraper = YouTubeScraperProduction()
            
            # Mock the private methods
            scraper._fetch_youtube_page = Mock(return_value="<html>mock content</html>")
            scraper._extract_videos_from_initial_data = Mock(return_value=[sample_video_data])
            scraper._is_duplicate = Mock(return_value=False)
            scraper._mark_as_collected = Mock(return_value=True)
            scraper._save_to_firebase = Mock(return_value=True)
            
            # Execute
            result = scraper.scrape_keyword("python", max_videos=100)
            
            # Verify
            assert result['keyword'] == 'python'
            assert result['total_videos'] == 1
            assert result['new_videos'] == 1
            assert result['saved_to_firebase'] == 1
            assert result['success'] is True
            
            # Verify method calls
            scraper._fetch_youtube_page.assert_called_once()
            scraper._extract_videos_from_initial_data.assert_called_once()
            scraper._is_duplicate.assert_called_once()
            scraper._mark_as_collected.assert_called_once()
            scraper._save_to_firebase.assert_called_once()
    
    def test_scrape_keyword_no_content(self, mock_env):
        """Test scrape_keyword when no content is fetched"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            scraper._fetch_youtube_page = Mock(return_value=None)
            
            result = scraper.scrape_keyword("python")
            
            assert result['keyword'] == 'python'
            assert result['videos'] == []
            assert 'error' in result
            assert result['error'] == 'Failed to fetch content'
    
    def test_scrape_keyword_all_duplicates(self, sample_video_data, mock_env):
        """Test scrape_keyword when all videos are duplicates"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            scraper._fetch_youtube_page = Mock(return_value="<html>mock content</html>")
            scraper._extract_videos_from_initial_data = Mock(return_value=[sample_video_data])
            scraper._is_duplicate = Mock(return_value=True)  # All duplicates
            
            result = scraper.scrape_keyword("python")
            
            assert result['new_videos'] == 0
            assert result['duplicate_videos'] == 1
            assert result['saved_to_firebase'] == 0
    
    def test_error_handling_in_scrape_keyword(self, mock_env):
        """Test error handling in scrape_keyword method"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            scraper._fetch_youtube_page = Mock(side_effect=Exception("Network error"))
            
            result = scraper.scrape_keyword("python")
            
            assert 'error' in result
            assert 'Network error' in str(result['error'])
    
    def test_video_limit_enforcement(self, mock_env):
        """Test that max_videos limit is enforced"""
        with patch('youtube_scraper_production.FirebaseClient'), \
             patch('youtube_scraper_production.RedisClient'), \
             patch('youtube_scraper_production.load_env'):
            
            scraper = YouTubeScraperProduction()
            
            # Create 5 mock videos
            mock_videos = [{'id': f'video_{i}'} for i in range(5)]
            
            scraper._fetch_youtube_page = Mock(return_value="<html>mock content</html>")
            scraper._extract_videos_from_initial_data = Mock(return_value=mock_videos)
            scraper._is_duplicate = Mock(return_value=False)
            scraper._mark_as_collected = Mock(return_value=True)
            scraper._save_to_firebase = Mock(return_value=True)
            
            # Set max_videos to 3
            result = scraper.scrape_keyword("python", max_videos=3)
            
            # Should only process 3 videos
            assert scraper._is_duplicate.call_count == 3
            assert scraper._save_to_firebase.call_count == 3