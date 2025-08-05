#!/usr/bin/env python3
"""
Safe Firebase Client Wrapper
Prevents creation of documents with auto-generated hash IDs in youtube_collection_logs
"""

import re
from datetime import datetime
from typing import Dict, Any, Optional
from google.cloud import firestore

from .firebase_client import FirebaseClient


class SafeFirebaseClient(FirebaseClient):
    """
    Enhanced Firebase client that prevents hash document IDs in youtube_collection_logs.
    
    This wrapper intercepts all writes to youtube_collection_logs and ensures
    document IDs follow the timestamp format.
    """
    
    def __init__(self):
        super().__init__()
        self._original_collection = self.db.collection
        
        # Wrap the collection method
        self.db.collection = self._safe_collection
    
    def _is_valid_log_id(self, doc_id: str) -> bool:
        """
        Check if a document ID is valid for youtube_collection_logs.
        Valid IDs should contain underscores and follow timestamp patterns.
        """
        if not doc_id:
            return False
        
        # Must contain underscores or dashes
        if '_' not in doc_id and '-' not in doc_id:
            return False
        
        # Should not look like a hash (16-28 alphanumeric characters only)
        if re.match(r'^[a-zA-Z0-9]{16,28}$', doc_id):
            return False
        
        return True
    
    def _safe_collection(self, collection_path: str):
        """
        Wrapper for collection() method that intercepts youtube_collection_logs writes.
        """
        if collection_path == 'youtube_collection_logs':
            return SafeCollectionReference(self._original_collection(collection_path), self)
        else:
            return self._original_collection(collection_path)
    
    def log_collection_run(self, collection_stats: Dict[str, Any]) -> str:
        """
        Override parent method to ensure proper validation.
        """
        # Always create a proper timestamp ID
        timestamp = datetime.utcnow()
        doc_id = timestamp.strftime("%Y-%m-%d_%H-%M-%S_UTC")
        
        # Double validation
        if not self._is_valid_log_id(doc_id):
            self.logger.error(f"Generated invalid document ID: {doc_id}")
            # Force a valid format
            doc_id = f"forced_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
        
        # Call parent method which now has validation
        return super().log_collection_run(collection_stats)


class SafeCollectionReference:
    """
    Safe wrapper for Firestore CollectionReference that prevents auto-generated IDs.
    """
    
    def __init__(self, collection_ref, safe_client: SafeFirebaseClient):
        self._collection_ref = collection_ref
        self._safe_client = safe_client
    
    def document(self, document_id: Optional[str] = None):
        """
        Wrapper for document() method that prevents auto-generated IDs.
        """
        if document_id is None:
            # Generate a proper timestamp ID
            timestamp = datetime.utcnow()
            document_id = f"auto_{timestamp.strftime('%Y-%m-%d_%H-%M-%S-%f')}_UTC"
            self._safe_client.logger.warning(
                f"youtube_collection_logs document() called without ID. "
                f"Generated timestamp ID: {document_id}"
            )
        elif not self._safe_client._is_valid_log_id(document_id):
            # Invalid ID provided
            old_id = document_id
            timestamp = datetime.utcnow()
            document_id = f"fixed_{timestamp.strftime('%Y-%m-%d_%H-%M-%S-%f')}_UTC"
            self._safe_client.logger.error(
                f"youtube_collection_logs document() called with invalid ID: {old_id}. "
                f"Replaced with: {document_id}"
            )
        
        return self._collection_ref.document(document_id)
    
    def add(self, document_data: Dict[str, Any]):
        """
        Override add() to use timestamp-based IDs instead of auto-generated ones.
        """
        # Generate a proper timestamp ID
        timestamp = datetime.utcnow()
        doc_id = f"add_{timestamp.strftime('%Y-%m-%d_%H-%M-%S-%f')}_UTC"
        
        self._safe_client.logger.warning(
            f"youtube_collection_logs.add() called (which creates hash IDs). "
            f"Using document() with timestamp ID instead: {doc_id}"
        )
        
        # Use document() with explicit ID instead of add()
        return self.document(doc_id).set(document_data)
    
    # Proxy all other methods to the original collection reference
    def __getattr__(self, name):
        return getattr(self._collection_ref, name)