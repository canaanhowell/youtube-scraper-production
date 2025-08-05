#!/usr/bin/env python3
"""
YouTube Collection Logger
Comprehensive logging system for YouTube collection runs
"""

import os
import sys
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
import traceback

# Add project path to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .firebase_client import FirebaseClient


@dataclass
class KeywordResult:
    """Result data for a single keyword collection"""
    keyword: str
    videos_found: int = 0
    videos_saved: int = 0
    duplicates_skipped: int = 0
    errors: List[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    containers_used: List[str] = None
    vpn_locations: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.containers_used is None:
            self.containers_used = []
        if self.vpn_locations is None:
            self.vpn_locations = []
    
    @property
    def duration_seconds(self) -> float:
        """Calculate duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (saved/found)"""
        if self.videos_found > 0:
            return self.videos_saved / self.videos_found
        return 0.0


@dataclass 
class CollectionRun:
    """Complete collection run data"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    keywords: List[str] = None
    keyword_results: Dict[str, KeywordResult] = None
    total_videos_found: int = 0
    total_videos_saved: int = 0
    total_duplicates_skipped: int = 0
    global_errors: List[str] = None
    containers_used: List[str] = None
    unique_vpn_locations: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.keyword_results is None:
            self.keyword_results = {}
        if self.global_errors is None:
            self.global_errors = []
        if self.containers_used is None:
            self.containers_used = []
        if self.unique_vpn_locations is None:
            self.unique_vpn_locations = []
    
    @property
    def duration_seconds(self) -> float:
        """Calculate total duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0
    
    @property
    def duration_minutes(self) -> float:
        """Calculate total duration in minutes"""
        return self.duration_seconds / 60.0
    
    @property
    def overall_success_rate(self) -> float:
        """Calculate overall success rate"""
        if self.total_videos_found > 0:
            return self.total_videos_saved / self.total_videos_found
        return 0.0
    
    @property
    def keywords_completed(self) -> int:
        """Number of keywords that were processed"""
        return len([kr for kr in self.keyword_results.values() if kr.end_time is not None])
    
    @property
    def keywords_with_results(self) -> int:
        """Number of keywords that found videos"""
        return len([kr for kr in self.keyword_results.values() if kr.videos_found > 0])


class YouTubeCollectionLogger:
    """
    Comprehensive logging system for YouTube collection runs
    Logs to both Firebase and local files
    """
    
    def __init__(self, session_id: Optional[str] = None):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize Firebase client
        try:
            self.firebase_client = FirebaseClient()
            self.firebase_enabled = True
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase client: {e}")
            self.firebase_enabled = False
        
        # Initialize session
        if session_id is None:
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        self.collection_run = CollectionRun(
            session_id=session_id,
            start_time=datetime.now(timezone.utc)
        )
        
        # Track the Firebase document ID for updates
        self.firebase_doc_id = None
        
        self.logger.info(f"Collection logger initialized for session: {session_id}")
    
    def start_collection(self, keywords: List[str]) -> str:
        """
        Start a new collection run
        
        Args:
            keywords: List of keywords to be processed
            
        Returns:
            session_id: Unique identifier for this collection run
        """
        self.collection_run.keywords = keywords.copy()
        self.collection_run.start_time = datetime.now(timezone.utc)
        
        # Initialize keyword results
        for keyword in keywords:
            self.collection_run.keyword_results[keyword] = KeywordResult(keyword=keyword)
        
        # Log start to Firebase
        if self.firebase_enabled:
            try:
                self._log_to_firebase('collection_started')
            except Exception as e:
                self.logger.error(f"Failed to log collection start to Firebase: {e}")
        
        self.logger.info(f"Collection started for {len(keywords)} keywords: {', '.join(keywords[:5])}...")
        return self.collection_run.session_id
    
    def start_keyword(self, keyword: str) -> None:
        """Mark the start of processing a specific keyword"""
        if keyword not in self.collection_run.keyword_results:
            self.collection_run.keyword_results[keyword] = KeywordResult(keyword=keyword)
        
        self.collection_run.keyword_results[keyword].start_time = datetime.now(timezone.utc)
        self.logger.info(f"Started processing keyword: {keyword}")
    
    def end_keyword(self, keyword: str, videos_found: int = 0, videos_saved: int = 0, 
                   duplicates_skipped: int = 0, containers_used: List[str] = None,
                   vpn_locations: List[str] = None) -> None:
        """
        Mark the end of processing a specific keyword
        
        Args:
            keyword: The keyword that was processed
            videos_found: Total videos found for this keyword
            videos_saved: Videos successfully saved to Firebase  
            duplicates_skipped: Number of duplicate videos skipped
            containers_used: List of container names used for this keyword
            vpn_locations: List of VPN locations used for this keyword
        """
        if keyword not in self.collection_run.keyword_results:
            self.collection_run.keyword_results[keyword] = KeywordResult(keyword=keyword)
        
        keyword_result = self.collection_run.keyword_results[keyword]
        keyword_result.end_time = datetime.now(timezone.utc)
        keyword_result.videos_found = videos_found
        keyword_result.videos_saved = videos_saved
        keyword_result.duplicates_skipped = duplicates_skipped
        
        if containers_used:
            keyword_result.containers_used = containers_used.copy()
            # Add to global containers list
            for container in containers_used:
                if container not in self.collection_run.containers_used:
                    self.collection_run.containers_used.append(container)
        
        if vpn_locations:
            keyword_result.vpn_locations = vpn_locations.copy()
            # Add to global VPN locations list
            for location in vpn_locations:
                if location not in self.collection_run.unique_vpn_locations:
                    self.collection_run.unique_vpn_locations.append(location)
        
        # Update totals
        self._update_totals()
        
        self.logger.info(f"Completed keyword '{keyword}': {videos_saved}/{videos_found} videos saved, "
                        f"{duplicates_skipped} duplicates skipped, "
                        f"{keyword_result.duration_seconds:.1f}s duration")
        
        # Log keyword completion to Firebase
        if self.firebase_enabled:
            try:
                self._log_keyword_to_firebase(keyword)
            except Exception as e:
                self.logger.error(f"Failed to log keyword completion to Firebase: {e}")
    
    def log_keyword_error(self, keyword: str, error: str, exception: Exception = None) -> None:
        """Log an error for a specific keyword"""
        if keyword not in self.collection_run.keyword_results:
            self.collection_run.keyword_results[keyword] = KeywordResult(keyword=keyword)
        
        error_msg = error
        if exception:
            error_msg += f": {str(exception)}"
            error_msg += f"\n{traceback.format_exc()}"
        
        self.collection_run.keyword_results[keyword].errors.append(error_msg)
        self.logger.error(f"Keyword '{keyword}' error: {error}")
    
    def log_global_error(self, error: str, exception: Exception = None) -> None:
        """Log a global collection error"""  
        error_msg = error
        if exception:
            error_msg += f": {str(exception)}"
            error_msg += f"\n{traceback.format_exc()}"
        
        self.collection_run.global_errors.append(error_msg)
        self.logger.error(f"Global error: {error}")
    
    def end_collection(self) -> Dict[str, Any]:
        """
        End the collection run and return summary statistics
        
        Returns:
            Dictionary containing collection summary
        """
        self.collection_run.end_time = datetime.now(timezone.utc)
        
        # Update final totals
        self._update_totals()
        
        # Log completion to Firebase
        if self.firebase_enabled:
            try:
                self._log_to_firebase('collection_completed')
            except Exception as e:
                self.logger.error(f"Failed to log collection completion to Firebase: {e}")
        
        # Generate summary
        summary = self._generate_summary()
        
        self.logger.info(f"Collection completed: {summary['total_videos_saved']} videos saved "
                        f"from {summary['keywords_completed']}/{len(self.collection_run.keywords)} keywords "
                        f"in {summary['duration_minutes']:.1f} minutes")
        
        return summary
    
    def get_current_stats(self) -> Dict[str, Any]:
        """Get current collection statistics"""
        self._update_totals()
        return self._generate_summary()
    
    def _update_totals(self) -> None:
        """Update total counters from keyword results"""
        self.collection_run.total_videos_found = sum(
            kr.videos_found for kr in self.collection_run.keyword_results.values()
        )
        self.collection_run.total_videos_saved = sum(
            kr.videos_saved for kr in self.collection_run.keyword_results.values()
        )
        self.collection_run.total_duplicates_skipped = sum(
            kr.duplicates_skipped for kr in self.collection_run.keyword_results.values()
        )
    
    def _generate_summary(self) -> Dict[str, Any]:
        """Generate collection summary statistics"""
        return {
            'session_id': self.collection_run.session_id,
            'start_time': self.collection_run.start_time.isoformat(),
            'end_time': self.collection_run.end_time.isoformat() if self.collection_run.end_time else None,
            'duration_seconds': self.collection_run.duration_seconds,
            'duration_minutes': self.collection_run.duration_minutes,
            'keywords_total': len(self.collection_run.keywords),
            'keywords_completed': self.collection_run.keywords_completed,
            'keywords_with_results': self.collection_run.keywords_with_results,
            'total_videos_found': self.collection_run.total_videos_found,
            'total_videos_saved': self.collection_run.total_videos_saved,
            'total_duplicates_skipped': self.collection_run.total_duplicates_skipped,
            'overall_success_rate': self.collection_run.overall_success_rate,
            'containers_used': self.collection_run.containers_used,
            'unique_vpn_locations': self.collection_run.unique_vpn_locations,
            'global_errors_count': len(self.collection_run.global_errors),
            'keywords_with_errors': len([kr for kr in self.collection_run.keyword_results.values() if kr.errors])
        }
    
    def _log_to_firebase(self, event_type: str) -> None:
        """Log collection event to Firebase"""
        if not self.firebase_enabled:
            return
        
        doc_data = {
            'session_id': self.collection_run.session_id,
            'event_type': event_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'keywords': self.collection_run.keywords,
            'summary': self._generate_summary()
        }
        
        # Add detailed keyword results for completion event
        if event_type == 'collection_completed':
            keyword_details = {}
            for keyword, result in self.collection_run.keyword_results.items():
                keyword_details[keyword] = {
                    'videos_found': result.videos_found,
                    'videos_saved': result.videos_saved,
                    'duplicates_skipped': result.duplicates_skipped,
                    'duration_seconds': result.duration_seconds,
                    'success_rate': result.success_rate,
                    'errors_count': len(result.errors),
                    'containers_used': result.containers_used,
                    'vpn_locations': result.vpn_locations,
                    'start_time': result.start_time.isoformat() if result.start_time else None,
                    'end_time': result.end_time.isoformat() if result.end_time else None
                }
            doc_data['keyword_results'] = keyword_details
            
            # Add error details if present
            if self.collection_run.global_errors:
                doc_data['global_errors'] = self.collection_run.global_errors
            
            keyword_errors = {}
            for keyword, result in self.collection_run.keyword_results.items():
                if result.errors:
                    keyword_errors[keyword] = result.errors
            if keyword_errors:
                doc_data['keyword_errors'] = keyword_errors
        
        try:
            # Create a proper timestamp-based document ID
            # Format: collection_YYYY-MM-DD_HH-MM-SS_UTC
            timestamp = datetime.now(timezone.utc)
            doc_id = f"collection_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
            
            # Store in youtube_collection_logs collection with timestamp ID
            doc_ref = self.firebase_client.db.collection('youtube_collection_logs').document(doc_id)
            doc_ref.set(doc_data, merge=True)
            
            # Store the document ID for future updates
            if event_type == 'collection_started':
                self.firebase_doc_id = doc_id
            
            self.logger.debug(f"Logged {event_type} to Firebase with ID: {doc_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to log to Firebase: {e}")
            raise
    
    def _log_keyword_to_firebase(self, keyword: str) -> None:
        """Log individual keyword completion to Firebase"""
        if not self.firebase_enabled:
            return
        
        keyword_result = self.collection_run.keyword_results[keyword]
        
        update_data = {
            f'keyword_results.{keyword}': {
                'videos_found': keyword_result.videos_found,
                'videos_saved': keyword_result.videos_saved,
                'duplicates_skipped': keyword_result.duplicates_skipped,
                'duration_seconds': keyword_result.duration_seconds,
                'success_rate': keyword_result.success_rate,
                'errors_count': len(keyword_result.errors),
                'containers_used': keyword_result.containers_used,
                'vpn_locations': keyword_result.vpn_locations,
                'start_time': keyword_result.start_time.isoformat() if keyword_result.start_time else None,
                'end_time': keyword_result.end_time.isoformat() if keyword_result.end_time else None,
                'completed_at': datetime.now(timezone.utc).isoformat()
            },
            'last_updated': datetime.now(timezone.utc).isoformat(),
            'summary': self._generate_summary()
        }
        
        try:
            # Use the stored document ID if available, otherwise create a new one
            if self.firebase_doc_id:
                doc_id = self.firebase_doc_id
            else:
                # Fallback: create a new timestamp-based ID
                timestamp = datetime.now(timezone.utc)
                doc_id = f"keyword_update_{timestamp.strftime('%Y-%m-%d_%H-%M-%S')}_UTC"
                self.logger.warning(f"No stored doc_id, creating new document: {doc_id}")
            
            doc_ref = self.firebase_client.db.collection('youtube_collection_logs').document(doc_id)
            doc_ref.set(update_data, merge=True)
            
            self.logger.debug(f"Logged keyword '{keyword}' completion to Firebase")
            
        except Exception as e:
            self.logger.error(f"Failed to log keyword to Firebase: {e}")
            raise