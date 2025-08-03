#!/usr/bin/env python3
"""
Database migration tools for YouTube Scraper
Handles schema changes, data migrations, and backup/restore operations for Firebase/Firestore
"""

import json
import time
import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter


@dataclass
class MigrationRecord:
    """Records a database migration"""
    migration_id: str
    version: str
    description: str
    executed_at: datetime
    execution_time: float
    affected_collections: List[str]
    affected_documents: int
    rollback_data: Optional[str] = None


class FirestoreMigrationManager:
    """Manages Firestore database migrations"""
    
    def __init__(self, service_account_path: str, project_id: str):
        self.project_id = project_id
        self.service_account_path = service_account_path
        self.db = None
        self.logger = logging.getLogger(__name__)
        self.migrations_collection = 'system_migrations'
        
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase connection"""
        try:
            if not firebase_admin._apps:
                cred = credentials.Certificate(self.service_account_path)
                firebase_admin.initialize_app(cred, {
                    'projectId': self.project_id
                })
            
            self.db = firestore.client()
            self.logger.info("Firebase initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize Firebase: {e}")
            raise
    
    def create_migration_record(self, migration: MigrationRecord):
        """Store migration record in Firestore"""
        try:
            doc_ref = self.db.collection(self.migrations_collection).document(migration.migration_id)
            doc_ref.set(asdict(migration), merge=True)
            self.logger.info(f"Migration record created: {migration.migration_id}")
        except Exception as e:
            self.logger.error(f"Failed to create migration record: {e}")
            raise
    
    def get_migration_history(self) -> List[MigrationRecord]:
        """Get list of all executed migrations"""
        try:
            docs = self.db.collection(self.migrations_collection).order_by('executed_at').stream()
            migrations = []
            
            for doc in docs:
                data = doc.to_dict()
                migration = MigrationRecord(**data)
                migrations.append(migration)
            
            return migrations
            
        except Exception as e:
            self.logger.error(f"Failed to get migration history: {e}")
            return []
    
    def migration_exists(self, migration_id: str) -> bool:
        """Check if migration has already been executed"""
        try:
            doc = self.db.collection(self.migrations_collection).document(migration_id).get()
            return doc.exists
        except Exception as e:
            self.logger.error(f"Failed to check migration existence: {e}")
            return False


class YouTubeScraperMigrations:
    """Specific migrations for YouTube Scraper schema"""
    
    def __init__(self, manager: FirestoreMigrationManager):
        self.manager = manager
        self.db = manager.db
        self.logger = logging.getLogger(__name__)
    
    def migrate_001_add_video_categories(self):
        """Migration 001: Add category field to existing videos"""
        migration_id = "001_add_video_categories"
        
        if self.manager.migration_exists(migration_id):
            self.logger.info(f"Migration {migration_id} already executed")
            return
        
        start_time = time.time()
        affected_docs = 0
        rollback_data = []
        
        try:
            # Get all video collections (by keyword)
            collections = self.db.collections()
            video_collections = [col for col in collections if col.id.startswith('youtube_videos_')]
            
            for collection in video_collections:
                keyword = collection.id.replace('youtube_videos_', '')
                videos = collection.stream()
                
                for video_doc in videos:
                    video_data = video_doc.to_dict()
                    
                    # Store original data for rollback
                    rollback_data.append({
                        'collection': collection.id,
                        'document': video_doc.id,
                        'original_data': video_data
                    })
                    
                    # Add category field if missing
                    if 'category' not in video_data:
                        video_data['category'] = self._infer_category_from_keyword(keyword)
                        video_data['migration_updated'] = datetime.now()
                        
                        video_doc.reference.update(video_data)
                        affected_docs += 1
            
            execution_time = time.time() - start_time
            
            # Record migration
            migration = MigrationRecord(
                migration_id=migration_id,
                version="1.0.1",
                description="Add category field to existing video documents",
                executed_at=datetime.now(),
                execution_time=execution_time,
                affected_collections=[col.id for col in video_collections],
                affected_documents=affected_docs,
                rollback_data=json.dumps(rollback_data[:100])  # Store sample for rollback
            )
            
            self.manager.create_migration_record(migration)
            self.logger.info(f"Migration {migration_id} completed: {affected_docs} documents updated")
            
        except Exception as e:
            self.logger.error(f"Migration {migration_id} failed: {e}")
            raise
    
    def migrate_002_restructure_analytics_data(self):
        """Migration 002: Restructure analytics data for better querying"""
        migration_id = "002_restructure_analytics_data"
        
        if self.manager.migration_exists(migration_id):
            self.logger.info(f"Migration {migration_id} already executed")
            return
        
        start_time = time.time()
        affected_docs = 0
        
        try:
            # Move old analytics data to new structure
            old_analytics = self.db.collection('analytics_data').stream()
            
            for doc in old_analytics:
                data = doc.to_dict()
                
                # Create new document structure
                new_structure = {
                    'keyword': data.get('keyword'),
                    'metrics': {
                        'total_videos': data.get('video_count', 0),
                        'avg_views': data.get('average_views', 0),
                        'total_views': data.get('total_views', 0)
                    },
                    'time_window': data.get('time_period', '7d'),
                    'created_at': data.get('timestamp', datetime.now()),
                    'migrated_from': doc.id
                }
                
                # Store in new collection
                self.db.collection('youtube_analytics').add(new_structure)
                affected_docs += 1
            
            execution_time = time.time() - start_time
            
            migration = MigrationRecord(
                migration_id=migration_id,
                version="1.1.0",
                description="Restructure analytics data for improved querying",
                executed_at=datetime.now(),
                execution_time=execution_time,
                affected_collections=['analytics_data', 'youtube_analytics'],
                affected_documents=affected_docs
            )
            
            self.manager.create_migration_record(migration)
            self.logger.info(f"Migration {migration_id} completed: {affected_docs} documents migrated")
            
        except Exception as e:
            self.logger.error(f"Migration {migration_id} failed: {e}")
            raise
    
    def migrate_003_add_performance_indexes(self):
        """Migration 003: Add performance indexes for common queries"""
        migration_id = "003_add_performance_indexes"
        
        if self.manager.migration_exists(migration_id):
            self.logger.info(f"Migration {migration_id} already executed")
            return
        
        start_time = time.time()
        
        try:
            # Note: Firestore indexes are typically created via Firebase Console or CLI
            # This migration documents the required indexes
            
            required_indexes = [
                {
                    'collection': 'youtube_videos',
                    'fields': ['published_at', 'view_count'],
                    'description': 'Index for time-based view count queries'
                },
                {
                    'collection': 'youtube_analytics',
                    'fields': ['keyword', 'created_at'],
                    'description': 'Index for keyword analytics queries'
                },
                {
                    'collection': 'youtube_categories',
                    'fields': ['category', 'last_updated'],
                    'description': 'Index for category-based queries'
                }
            ]
            
            # Create index documentation
            index_doc = {
                'required_indexes': required_indexes,
                'created_at': datetime.now(),
                'instructions': 'Create these indexes in Firebase Console for optimal performance'
            }
            
            self.db.collection('system_indexes').document('required_indexes').set(index_doc)
            
            execution_time = time.time() - start_time
            
            migration = MigrationRecord(
                migration_id=migration_id,
                version="1.2.0",
                description="Document required performance indexes",
                executed_at=datetime.now(),
                execution_time=execution_time,
                affected_collections=['system_indexes'],
                affected_documents=1
            )
            
            self.manager.create_migration_record(migration)
            self.logger.info(f"Migration {migration_id} completed: Index requirements documented")
            
        except Exception as e:
            self.logger.error(f"Migration {migration_id} failed: {e}")
            raise
    
    def migrate_004_cleanup_duplicate_videos(self):
        """Migration 004: Remove duplicate video entries"""
        migration_id = "004_cleanup_duplicate_videos"
        
        if self.manager.migration_exists(migration_id):
            self.logger.info(f"Migration {migration_id} already executed")
            return
        
        start_time = time.time()
        affected_docs = 0
        
        try:
            # Find and remove duplicates based on video_id
            video_collections = [col for col in self.db.collections() if col.id.startswith('youtube_videos')]
            
            for collection in video_collections:
                seen_videos = set()
                duplicates = []
                
                videos = collection.stream()
                for video_doc in videos:
                    video_data = video_doc.to_dict()
                    video_id = video_data.get('video_id')
                    
                    if video_id in seen_videos:
                        duplicates.append(video_doc.reference)
                    else:
                        seen_videos.add(video_id)
                
                # Delete duplicates
                for duplicate_ref in duplicates:
                    duplicate_ref.delete()
                    affected_docs += 1
            
            execution_time = time.time() - start_time
            
            migration = MigrationRecord(
                migration_id=migration_id,
                version="1.3.0",
                description="Remove duplicate video entries",
                executed_at=datetime.now(),
                execution_time=execution_time,
                affected_collections=[col.id for col in video_collections],
                affected_documents=affected_docs
            )
            
            self.manager.create_migration_record(migration)
            self.logger.info(f"Migration {migration_id} completed: {affected_docs} duplicates removed")
            
        except Exception as e:
            self.logger.error(f"Migration {migration_id} failed: {e}")
            raise
    
    def _infer_category_from_keyword(self, keyword: str) -> str:
        """Infer video category from keyword"""
        # Simple category mapping - extend as needed
        category_mapping = {
            'tech': 'Technology',
            'ai': 'Technology',
            'programming': 'Technology',
            'coding': 'Technology',
            'startup': 'Business',
            'entrepreneur': 'Business',
            'marketing': 'Business',
            'finance': 'Business',
            'health': 'Health & Fitness',
            'fitness': 'Health & Fitness',
            'cooking': 'Food & Cooking',
            'travel': 'Travel',
            'music': 'Music',
            'gaming': 'Gaming',
            'education': 'Education',
            'tutorial': 'Education'
        }
        
        keyword_lower = keyword.lower()
        for key, category in category_mapping.items():
            if key in keyword_lower:
                return category
        
        return 'General'


class DatabaseBackupManager:
    """Manages database backups and restores"""
    
    def __init__(self, manager: FirestoreMigrationManager, backup_dir: Path):
        self.manager = manager
        self.db = manager.db
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
    
    def create_full_backup(self) -> str:
        """Create full database backup"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"firestore_backup_{timestamp}.json"
        
        try:
            backup_data = {
                'timestamp': timestamp,
                'collections': {}
            }
            
            # Backup all collections
            collections = self.db.collections()
            for collection in collections:
                collection_data = []
                docs = collection.stream()
                
                for doc in docs:
                    doc_data = doc.to_dict()
                    doc_data['_document_id'] = doc.id
                    collection_data.append(doc_data)
                
                backup_data['collections'][collection.id] = collection_data
                self.logger.info(f"Backed up collection {collection.id}: {len(collection_data)} documents")
            
            # Save to file
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            self.logger.info(f"Full backup created: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Backup failed: {e}")
            raise
    
    def create_collection_backup(self, collection_name: str) -> str:
        """Create backup of specific collection"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = self.backup_dir / f"{collection_name}_backup_{timestamp}.json"
        
        try:
            collection_ref = self.db.collection(collection_name)
            docs = collection_ref.stream()
            
            backup_data = {
                'timestamp': timestamp,
                'collection': collection_name,
                'documents': []
            }
            
            for doc in docs:
                doc_data = doc.to_dict()
                doc_data['_document_id'] = doc.id
                backup_data['documents'].append(doc_data)
            
            with open(backup_file, 'w') as f:
                json.dump(backup_data, f, indent=2, default=str)
            
            self.logger.info(f"Collection backup created: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            self.logger.error(f"Collection backup failed: {e}")
            raise
    
    def restore_from_backup(self, backup_file: str, dry_run: bool = True):
        """Restore database from backup file"""
        backup_path = Path(backup_file)
        
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        try:
            with open(backup_path, 'r') as f:
                backup_data = json.load(f)
            
            if 'collections' in backup_data:
                # Full backup restore
                self._restore_full_backup(backup_data, dry_run)
            else:
                # Collection backup restore
                self._restore_collection_backup(backup_data, dry_run)
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            raise
    
    def _restore_full_backup(self, backup_data: Dict, dry_run: bool):
        """Restore full backup"""
        collections = backup_data.get('collections', {})
        
        for collection_name, documents in collections.items():
            self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Restoring collection {collection_name}: {len(documents)} documents")
            
            if not dry_run:
                collection_ref = self.db.collection(collection_name)
                
                for doc_data in documents:
                    doc_id = doc_data.pop('_document_id', None)
                    if doc_id:
                        collection_ref.document(doc_id).set(doc_data)
    
    def _restore_collection_backup(self, backup_data: Dict, dry_run: bool):
        """Restore single collection backup"""
        collection_name = backup_data.get('collection')
        documents = backup_data.get('documents', [])
        
        self.logger.info(f"{'[DRY RUN] ' if dry_run else ''}Restoring collection {collection_name}: {len(documents)} documents")
        
        if not dry_run:
            collection_ref = self.db.collection(collection_name)
            
            for doc_data in documents:
                doc_id = doc_data.pop('_document_id', None)
                if doc_id:
                    collection_ref.document(doc_id).set(doc_data)


class MigrationRunner:
    """Orchestrates database migrations"""
    
    def __init__(self, service_account_path: str, project_id: str, backup_dir: Path):
        self.manager = FirestoreMigrationManager(service_account_path, project_id)
        self.migrations = YouTubeScraperMigrations(self.manager)
        self.backup_manager = DatabaseBackupManager(self.manager, backup_dir)
        self.logger = logging.getLogger(__name__)
    
    def run_all_migrations(self, create_backup: bool = True):
        """Run all pending migrations"""
        if create_backup:
            self.logger.info("Creating backup before migrations...")
            backup_file = self.backup_manager.create_full_backup()
            self.logger.info(f"Backup created: {backup_file}")
        
        # List of all migrations
        migration_methods = [
            self.migrations.migrate_001_add_video_categories,
            self.migrations.migrate_002_restructure_analytics_data,
            self.migrations.migrate_003_add_performance_indexes,
            self.migrations.migrate_004_cleanup_duplicate_videos
        ]
        
        for migration_method in migration_methods:
            try:
                self.logger.info(f"Running migration: {migration_method.__name__}")
                migration_method()
            except Exception as e:
                self.logger.error(f"Migration {migration_method.__name__} failed: {e}")
                raise
        
        self.logger.info("All migrations completed successfully")
    
    def show_migration_status(self):
        """Display migration history and status"""
        history = self.manager.get_migration_history()
        
        if not history:
            print("No migrations have been executed yet.")
            return
        
        print("\nMigration History:")
        print("-" * 80)
        print(f"{'ID':<25} {'Version':<10} {'Executed':<20} {'Duration':<10} {'Docs':<8}")
        print("-" * 80)
        
        for migration in history:
            executed_str = migration.executed_at.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{migration.migration_id:<25} {migration.version:<10} {executed_str:<20} "
                  f"{migration.execution_time:<10.2f} {migration.affected_documents:<8}")
        
        print("-" * 80)
        print(f"Total migrations executed: {len(history)}")


def main():
    """CLI interface for database migrations"""
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Scraper Database Migration Tool')
    parser.add_argument('--service-account', required=True, help='Path to Firebase service account JSON')
    parser.add_argument('--project-id', required=True, help='Firebase project ID')
    parser.add_argument('--backup-dir', type=Path, default=Path('/opt/youtube_scraper/backups/database'),
                       help='Directory for database backups')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Migration commands
    migrate_parser = subparsers.add_parser('migrate', help='Run migrations')
    migrate_parser.add_argument('--no-backup', action='store_true', help='Skip backup before migration')
    
    # Status command
    subparsers.add_parser('status', help='Show migration status')
    
    # Backup commands
    backup_parser = subparsers.add_parser('backup', help='Create database backup')
    backup_parser.add_argument('--collection', help='Backup specific collection only')
    
    # Restore command
    restore_parser = subparsers.add_parser('restore', help='Restore from backup')
    restore_parser.add_argument('--backup-file', required=True, help='Path to backup file')
    restore_parser.add_argument('--dry-run', action='store_true', help='Show what would be restored without doing it')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    runner = MigrationRunner(args.service_account, args.project_id, args.backup_dir)
    
    if args.command == 'migrate':
        runner.run_all_migrations(create_backup=not args.no_backup)
    
    elif args.command == 'status':
        runner.show_migration_status()
    
    elif args.command == 'backup':
        if args.collection:
            backup_file = runner.backup_manager.create_collection_backup(args.collection)
        else:
            backup_file = runner.backup_manager.create_full_backup()
        print(f"Backup created: {backup_file}")
    
    elif args.command == 'restore':
        runner.backup_manager.restore_from_backup(args.backup_file, args.dry_run)
        if args.dry_run:
            print("Dry run completed. Use --no-dry-run to actually restore.")
        else:
            print("Restore completed successfully.")


if __name__ == "__main__":
    main()