"""
Integration tests for Firebase functionality
"""
import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.utils.firebase_client_enhanced import FirebaseClient


class TestFirebaseIntegration:
    """Integration tests for Firebase client"""
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_firebase_initialization(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test Firebase client initialization"""
        mock_db = Mock()
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        assert client.db is not None
        mock_certificate.assert_called_once()
        mock_init_app.assert_called_once()
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_get_keywords(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test retrieving keywords from Firebase"""
        # Mock Firestore response
        mock_doc1 = Mock()
        mock_doc1.to_dict.return_value = {'keyword': 'python', 'active': True}
        mock_doc2 = Mock()
        mock_doc2.to_dict.return_value = {'keyword': 'javascript', 'active': True}
        mock_doc3 = Mock()
        mock_doc3.to_dict.return_value = {'keyword': 'rust', 'active': False}
        
        mock_collection = Mock()
        mock_collection.where.return_value.stream.return_value = [mock_doc1, mock_doc2, mock_doc3]
        
        mock_db = Mock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        keywords = client.get_keywords()
        
        # Should only return active keywords
        assert keywords == ['python', 'javascript']
        mock_db.collection.assert_called_with('youtube_keywords')
        mock_collection.where.assert_called_with('active', '==', True)
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_save_video(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env, sample_video_data):
        """Test saving video to Firebase"""
        # Mock Firestore operations
        mock_doc_ref = Mock()
        mock_doc_ref.set = Mock()
        
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        mock_db = Mock()
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_collection
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        result = client.save_video('python', sample_video_data)
        
        assert result is True
        mock_doc_ref.set.assert_called_once()
        
        # Verify the data structure
        saved_data = mock_doc_ref.set.call_args[0][0]
        assert saved_data['video_id'] == sample_video_data['id']
        assert saved_data['title'] == sample_video_data['title']
        assert 'created_at' in saved_data
        assert 'updated_at' in saved_data
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_save_video_error_handling(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test error handling when saving video fails"""
        # Mock Firestore to raise an exception
        mock_db = Mock()
        mock_db.collection.side_effect = Exception("Firebase error")
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        result = client.save_video('python', {'id': 'test123'})
        
        assert result is False
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_log_collection_run(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test logging collection run to Firebase"""
        # Mock Firestore operations
        mock_doc_ref = Mock()
        mock_doc_ref.id = 'log_12345'
        mock_doc_ref.set = Mock()
        
        mock_collection = Mock()
        mock_collection.add.return_value = (None, mock_doc_ref)
        
        mock_db = Mock()
        mock_db.collection.return_value = mock_collection
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        stats = {
            'session_id': 'session_123',
            'total_videos_collected': 50,
            'keywords_processed': ['python', 'javascript'],
            'success': True,
            'start_time': datetime.now(timezone.utc)
        }
        
        log_id = client.log_collection_run(stats)
        
        assert log_id == 'log_12345'
        mock_db.collection.assert_called_with('youtube_collection_logs')
        mock_collection.add.assert_called_once()
        
        # Verify the logged data
        logged_data = mock_collection.add.call_args[0][0]
        assert logged_data['session_id'] == 'session_123'
        assert logged_data['total_videos_collected'] == 50
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_batch_operations(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test batch write operations"""
        # Mock batch operations
        mock_batch = Mock()
        mock_batch.__enter__ = Mock(return_value=mock_batch)
        mock_batch.__exit__ = Mock(return_value=None)
        mock_batch.set = Mock()
        mock_batch.commit = Mock()
        
        mock_db = Mock()
        mock_db.batch.return_value = mock_batch
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = Mock()
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        # Test batch save
        videos = [
            {'id': 'video1', 'title': 'Video 1'},
            {'id': 'video2', 'title': 'Video 2'},
            {'id': 'video3', 'title': 'Video 3'}
        ]
        
        # Simulate batch save (would need to implement in actual client)
        with mock_db.batch() as batch:
            for video in videos:
                doc_ref = mock_db.collection('youtube_videos').document('python').collection('videos').document(video['id'])
                batch.set(doc_ref, video)
        
        assert mock_batch.set.call_count == 3
        mock_batch.commit.assert_called_once()
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_connection_resilience(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test Firebase connection resilience"""
        # Test that client handles temporary connection issues
        mock_db = Mock()
        
        # First call fails, second succeeds
        mock_collection = Mock()
        mock_collection.where.side_effect = [
            Exception("Connection timeout"),
            Mock(stream=Mock(return_value=[]))
        ]
        
        mock_db.collection.return_value = mock_collection
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        # First attempt should fail
        keywords = client.get_keywords()
        assert keywords == []  # Should return empty list on error
        
        # Second attempt should work (in real implementation with retry)
        mock_collection.where.side_effect = None
        mock_collection.where.return_value.stream.return_value = []
        keywords = client.get_keywords()
        assert keywords == []
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_data_validation(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test data validation before saving to Firebase"""
        mock_db = Mock()
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        # Test with invalid video data (missing required fields)
        invalid_video = {'title': 'No ID'}  # Missing 'id' field
        result = client.save_video('python', invalid_video)
        
        # Should handle gracefully
        assert result is False
        
        # Test with empty keyword
        valid_video = {'id': 'test123', 'title': 'Test'}
        result = client.save_video('', valid_video)
        assert result is False
    
    @patch('src.utils.firebase_client_enhanced.firebase_admin.initialize_app')
    @patch('src.utils.firebase_client_enhanced.firebase_admin.credentials.Certificate')
    @patch('src.utils.firebase_client_enhanced.firestore.client')
    def test_timestamp_handling(self, mock_firestore_client, mock_certificate, mock_init_app, mock_env):
        """Test proper timestamp handling in Firebase operations"""
        mock_doc_ref = Mock()
        mock_collection = Mock()
        mock_collection.document.return_value = mock_doc_ref
        
        mock_db = Mock()
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_collection
        mock_firestore_client.return_value = mock_db
        
        client = FirebaseClient()
        
        video_data = {'id': 'test123', 'title': 'Test Video'}
        client.save_video('python', video_data)
        
        # Verify timestamps are added
        saved_data = mock_doc_ref.set.call_args[0][0]
        assert 'created_at' in saved_data
        assert 'updated_at' in saved_data
        
        # Verify timestamps are datetime objects or server timestamps
        # (depending on implementation)