import os
import sys
import logging
import firebase_admin
from firebase_admin import credentials, firestore
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add project path to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
from utils.env_loader import load_env
load_env()

# Set up logging
from utils.logging_config import setup_logging
logger, network_logger = setup_logging()


class FirebaseClient:
    """Firebase client for storing YouTube video data"""
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.network_logger = logging.getLogger('network')
        
        # Get service account path from environment
        service_account_path = os.environ.get('GOOGLE_SERVICE_KEY_PATH') or os.environ.get('GOOGLE_APPLICATION_CREDENTIALS')
        if not service_account_path:
            raise ValueError("GOOGLE_SERVICE_KEY_PATH or GOOGLE_APPLICATION_CREDENTIALS not found in environment variables")
        
        # Clean up path - remove leading backslash if present
        service_account_path = service_account_path.lstrip('\\').lstrip('/')
        
        # Construct full path
        if not os.path.isabs(service_account_path):
            # Relative path - make it relative to project root
            service_account_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                service_account_path
            )
        
        if not os.path.exists(service_account_path):
            raise FileNotFoundError(f"Service account file not found: {service_account_path}")
        
        try:
            # Check if Firebase app is already initialized
            try:
                firebase_admin.get_app()
                self.logger.info("Firebase app already initialized")
            except ValueError:
                # Initialize Firebase
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                self.logger.info("Firebase app initialized")
            
            # Get Firestore client
            self.db = firestore.client()
            self.logger.info("Firebase client ready")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def upload_videos_batch(self, videos: List[Dict[str, Any]], keyword: str) -> bool:
        """Upload a batch of videos to Firebase"""
        try:
            self.logger.info(f"Starting upload of {len(videos)} videos for keyword: {keyword}")
            batch = self.db.batch()
            uploaded_count = 0
            
            for video in videos:
                # Sanitize video ID for Firebase
                video_id = video['video_id']
                if video_id.startswith('/shorts/'):
                    video_id = video_id.replace('/shorts/', 'shorts_')
                video_id = video_id.replace('/', '_')
                
                # Create document reference
                doc_ref = self.db.collection('youtube_videos') \
                    .document(keyword) \
                    .collection('videos') \
                    .document(video_id)
                
                # Prepare video data
                video_data = {
                    'video_id': video_id,
                    'original_video_id': video.get('original_video_id', video['video_id']),
                    'title': video['title'],
                    'channel': video['channel'],
                    'views': video['views'],
                    'upload_date': video['upload_date'],
                    'days_ago': video.get('days_ago', 0),
                    'url': video['url'],
                    'keyword': keyword,
                    'container': video.get('container', 'unknown'),
                    'vpn_location': video.get('vpn_location', 'unknown'),
                    'session_id': video.get('session_id', 'unknown'),
                    'collected_at': firestore.SERVER_TIMESTAMP,
                    'scraped_at': video.get('scraped_at', datetime.now().isoformat())
                }
                
                batch.set(doc_ref, video_data, merge=True)
                uploaded_count += 1
                
                # Commit batch every 500 documents (Firestore limit)
                if uploaded_count % 500 == 0:
                    batch.commit()
                    self.logger.info(f"Committed batch of 500 videos for keyword: {keyword}")
                    batch = self.db.batch()
            
            # Commit remaining documents
            if uploaded_count % 500 != 0:
                batch.commit()
                self.logger.info(f"Committed final batch of {uploaded_count % 500} videos for keyword: {keyword}")
            
            self.network_logger.info(f"✅ Successfully uploaded {uploaded_count} videos to Firebase for keyword: {keyword}")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Failed to upload videos batch for {keyword}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def update_session_stats(self, session_id: str, stats: Dict[str, Any]) -> bool:
        """Update session statistics in Firebase"""
        try:
            doc_ref = self.db.collection('youtube_collection_sessions').document(session_id)
            doc_ref.set({
                **stats,
                'updated_at': firestore.SERVER_TIMESTAMP
            }, merge=True)
            
            self.logger.info(f"Updated session stats for: {session_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to update session stats: {e}")
            return False
    
    def get_video_count(self, keyword: str) -> int:
        """Get the count of videos for a keyword"""
        try:
            # Note: This is an approximation for large collections
            # For exact counts, consider maintaining a counter document
            videos_ref = self.db.collection('youtube_videos') \
                .document(keyword) \
                .collection('videos')
            
            # Get a limited set to check if collection exists
            docs = videos_ref.limit(1).get()
            if not docs:
                return 0
            
            # For accurate count, you'd need to implement a counter
            # This is a simplified version
            self.logger.warning("Exact video count not implemented - returning estimate")
            return -1  # Indicates count not available
            
        except Exception as e:
            self.logger.error(f"Failed to get video count: {e}")
            return -1
    
    def check_video_exists(self, keyword: str, video_id: str) -> bool:
        """Check if a video already exists in Firebase"""
        try:
            doc_ref = self.db.collection('youtube_videos') \
                .document(keyword) \
                .collection('videos') \
                .document(video_id)
            
            doc = doc_ref.get()
            return doc.exists
            
        except Exception as e:
            self.logger.error(f"Failed to check video existence: {e}")
            return False
    
    def log_collection_run(self, collection_stats: Dict[str, Any]) -> str:
        """
        Log a collection run to youtube_collection_logs with readable timestamp as document name
        
        Args:
            collection_stats: Dictionary containing run statistics including:
                - keywords_processed: List of keywords
                - total_videos_collected: Total videos collected
                - videos_per_keyword: Dict of keyword -> video count
                - duration_seconds: Total run duration
                - success: Boolean indicating if run was successful
                - errors: List of any errors encountered
                - session_id: Unique session identifier
                
        Returns:
            Document ID (timestamp) if successful, empty string if failed
        """
        try:
            # Create readable timestamp for document name
            # Format: YYYY-MM-DD_HH-MM-SS_UTC
            timestamp = datetime.utcnow()
            doc_id = timestamp.strftime("%Y-%m-%d_%H-%M-%S_UTC")
            
            # Validation: Ensure we're using a proper timestamp ID, not a hash
            if not doc_id or len(doc_id) < 10 or '_' not in doc_id:
                self.logger.error(f"Invalid document ID format: {doc_id}")
                raise ValueError(f"Document ID must be a timestamp format, got: {doc_id}")
            
            # Prepare log data
            log_data = {
                'timestamp': firestore.SERVER_TIMESTAMP,
                'timestamp_readable': timestamp.isoformat(),
                'timestamp_unix': timestamp.timestamp(),
                'keywords_processed': collection_stats.get('keywords_processed', []),
                'total_videos_collected': collection_stats.get('total_videos_collected', 0),
                'videos_per_keyword': collection_stats.get('videos_per_keyword', {}),
                'duration_seconds': collection_stats.get('duration_seconds', 0),
                'success': collection_stats.get('success', False),
                'errors': collection_stats.get('errors', []),
                'session_id': collection_stats.get('session_id', 'unknown'),
                'vpn_servers_used': collection_stats.get('vpn_servers_used', []),
                'redis_enabled': collection_stats.get('redis_enabled', False),
                'duplicates_filtered': collection_stats.get('duplicates_filtered', 0),
                'container': collection_stats.get('container', 'unknown'),
                'vm_hostname': collection_stats.get('vm_hostname', 'unknown')
            }
            
            # Create document with readable timestamp as ID
            doc_ref = self.db.collection('youtube_collection_logs').document(doc_id)
            doc_ref.set(log_data)
            
            self.logger.info(f"Logged collection run to youtube_collection_logs/{doc_id}")
            return doc_id
            
        except Exception as e:
            self.logger.error(f"Failed to log collection run: {e}")
            import traceback
            traceback.print_exc()
            return ""