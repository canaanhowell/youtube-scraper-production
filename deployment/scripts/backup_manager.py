#!/usr/bin/env python3
"""
Automatic Backup and Rollback Manager
Handles intelligent backups and rollbacks for the YouTube scraper system
"""

import os
import sys
import json
import shutil
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import tarfile
import tempfile

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/backup_manager.log')
    ]
)
logger = logging.getLogger(__name__)

class BackupManager:
    """Manages automatic backups and rollbacks"""
    
    def __init__(self, project_dir: str = "/opt/youtube_app"):
        self.project_dir = Path(project_dir)
        self.backup_dir = Path("/opt/youtube_app_backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.backup_dir / "backup_metadata.json"
        self.max_backups = 10  # Keep last 10 backups
        self.max_age_days = 30  # Keep backups for 30 days
        
    def create_backup(self, backup_type: str = "auto", description: str = None) -> Optional[str]:
        """Create a backup of the current system state"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        logger.info(f"Creating backup: {backup_name}")
        
        try:
            # Create temporary directory for preparation
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_backup_dir = Path(temp_dir) / backup_name
                temp_backup_dir.mkdir()
                
                # Copy project files
                self._copy_project_files(temp_backup_dir)
                
                # Capture system state
                self._capture_system_state(temp_backup_dir)
                
                # Create tar.gz archive
                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(temp_backup_dir, arcname=backup_name)
            
            # Create metadata
            metadata = {
                "name": backup_name,
                "file": str(backup_file),
                "timestamp": timestamp,
                "type": backup_type,
                "description": description or f"Automatic {backup_type} backup",
                "size": backup_file.stat().st_size,
                "git_commit": self._get_git_commit(),
                "services": self._get_active_services()
            }
            
            # Save metadata
            self._save_backup_metadata(metadata)
            
            # Cleanup old backups
            self._cleanup_old_backups()
            
            logger.info(f"✅ Backup created successfully: {backup_file}")
            return str(backup_file)
            
        except Exception as e:
            logger.error(f"❌ Failed to create backup: {e}")
            # Cleanup failed backup file
            if backup_file.exists():
                backup_file.unlink()
            return None
    
    def _copy_project_files(self, backup_dir: Path):
        """Copy important project files to backup"""
        # Files and directories to backup
        important_items = [
            "*.py",
            "src/",
            "config/",
            "deployment/",
            "requirements.txt",
            ".env",
            "*.json",
            "*.yml",
            "*.yaml",
            "*.md",
            "*.txt"
        ]
        
        # Files and directories to exclude
        exclude_items = [
            "venv/",
            "logs/",
            "__pycache__/",
            "*.pyc",
            ".git/",
            "node_modules/",
            "*.log",
            ".pytest_cache/",
            "backup_*"
        ]
        
        project_backup_dir = backup_dir / "project"
        project_backup_dir.mkdir()
        
        # Copy important files
        for item in self.project_dir.iterdir():
            if item.name.startswith('.') and item.name != '.env':
                continue
                
            # Check if item should be excluded
            if any(item.match(pattern) for pattern in exclude_items):
                continue
            
            try:
                if item.is_file():
                    shutil.copy2(item, project_backup_dir)
                elif item.is_dir():
                    # Only copy important directories
                    if item.name in ['src', 'config', 'deployment', 'tests']:
                        shutil.copytree(item, project_backup_dir / item.name)
            except Exception as e:
                logger.warning(f"Could not backup {item}: {e}")
    
    def _capture_system_state(self, backup_dir: Path):
        """Capture current system state"""
        state_dir = backup_dir / "system_state"
        state_dir.mkdir()
        
        try:
            # Capture systemd services
            services_file = state_dir / "services.txt"
            result = subprocess.run(
                ['systemctl', 'list-unit-files', '--type=service'],
                capture_output=True, text=True
            )
            services_file.write_text(result.stdout)
            
            # Capture active services
            active_services_file = state_dir / "active_services.txt"
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=active'],
                capture_output=True, text=True
            )
            active_services_file.write_text(result.stdout)
            
            # Capture installed packages
            packages_file = state_dir / "packages.txt"
            if shutil.which('pip'):
                result = subprocess.run(
                    ['pip', 'list'], capture_output=True, text=True
                )
                packages_file.write_text(result.stdout)
            
            # Capture crontab
            crontab_file = state_dir / "crontab.txt"
            result = subprocess.run(
                ['crontab', '-l'], capture_output=True, text=True
            )
            if result.returncode == 0:
                crontab_file.write_text(result.stdout)
            
        except Exception as e:
            logger.warning(f"Could not capture complete system state: {e}")
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash"""
        try:
            os.chdir(self.project_dir)
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'], 
                capture_output=True, text=True
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _get_active_services(self) -> List[str]:
        """Get list of active YouTube-related services"""
        services = []
        try:
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=active'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'youtube-' in line:
                    service_name = line.split()[0]
                    services.append(service_name)
                    
        except Exception as e:
            logger.warning(f"Could not get active services: {e}")
            
        return services
    
    def _save_backup_metadata(self, metadata: Dict):
        """Save backup metadata"""
        try:
            # Load existing metadata
            all_metadata = []
            if self.metadata_file.exists():
                with open(self.metadata_file, 'r') as f:
                    all_metadata = json.load(f)
            
            # Add new metadata
            all_metadata.append(metadata)
            
            # Save updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(all_metadata, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save backup metadata: {e}")
    
    def _cleanup_old_backups(self):
        """Remove old backups based on count and age limits"""
        try:
            # Load metadata
            if not self.metadata_file.exists():
                return
                
            with open(self.metadata_file, 'r') as f:
                all_metadata = json.load(f)
            
            # Sort by timestamp (newest first)
            all_metadata.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Remove backups beyond count limit
            removed_count = 0
            removed_age = 0
            cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
            
            updated_metadata = []
            
            for i, metadata in enumerate(all_metadata):
                backup_file = Path(metadata['file'])
                backup_date = datetime.strptime(metadata['timestamp'], "%Y%m%d_%H%M%S")
                
                # Keep if within count and age limits
                if i < self.max_backups and backup_date > cutoff_date:
                    updated_metadata.append(metadata)
                else:
                    # Remove backup file
                    if backup_file.exists():
                        backup_file.unlink()
                        if i >= self.max_backups:
                            removed_count += 1
                        else:
                            removed_age += 1
            
            # Save updated metadata
            with open(self.metadata_file, 'w') as f:
                json.dump(updated_metadata, f, indent=2)
            
            if removed_count > 0 or removed_age > 0:
                logger.info(f"Cleaned up {removed_count} old backups (count limit) and {removed_age} aged backups")
                
        except Exception as e:
            logger.error(f"Could not cleanup old backups: {e}")
    
    def list_backups(self) -> List[Dict]:
        """List available backups"""
        try:
            if not self.metadata_file.exists():
                return []
                
            with open(self.metadata_file, 'r') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Could not load backup metadata: {e}")
            return []
    
    def rollback_to_backup(self, backup_name: str = None) -> bool:
        """Rollback to a specific backup (or latest if none specified)"""
        backups = self.list_backups()
        
        if not backups:
            logger.error("No backups available for rollback")
            return False
        
        # Find the backup to restore
        backup_to_restore = None
        
        if backup_name:
            for backup in backups:
                if backup['name'] == backup_name:
                    backup_to_restore = backup
                    break
            
            if not backup_to_restore:
                logger.error(f"Backup '{backup_name}' not found")
                return False
        else:
            # Use latest backup
            backup_to_restore = max(backups, key=lambda x: x['timestamp'])
        
        logger.info(f"Rolling back to backup: {backup_to_restore['name']}")
        
        try:
            # Stop services before rollback
            services_stopped = self._stop_services()
            
            # Create a backup before rollback (just in case)
            logger.info("Creating safety backup before rollback...")
            safety_backup = self.create_backup("pre_rollback", "Safety backup before rollback")
            
            # Extract backup
            backup_file = Path(backup_to_restore['file'])
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False
            
            # Extract to temporary directory first
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract backup
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(temp_path)
                
                # Find the extracted project directory
                extracted_dirs = list(temp_path.iterdir())
                if not extracted_dirs:
                    logger.error("No directories found in backup")
                    return False
                
                project_backup_path = extracted_dirs[0] / "project"
                if not project_backup_path.exists():
                    logger.error("Project directory not found in backup")
                    return False
                
                # Backup current directory (just critical files)
                current_backup_dir = temp_path / "current_backup"
                current_backup_dir.mkdir()
                
                # Preserve logs and some runtime data
                for item in ['logs', '.env', 'venv']:
                    item_path = self.project_dir / item
                    if item_path.exists():
                        if item_path.is_dir():
                            shutil.copytree(item_path, current_backup_dir / item)
                        else:
                            shutil.copy2(item_path, current_backup_dir)
                
                # Remove current project files (except preserved ones)
                for item in self.project_dir.iterdir():
                    if item.name in ['logs', 'venv', '.git']:
                        continue
                    try:
                        if item.is_dir():
                            shutil.rmtree(item)
                        else:
                            item.unlink()
                    except Exception as e:
                        logger.warning(f"Could not remove {item}: {e}")
                
                # Restore from backup
                for item in project_backup_path.iterdir():
                    try:
                        if item.is_dir():
                            shutil.copytree(item, self.project_dir / item.name)
                        else:
                            shutil.copy2(item, self.project_dir)
                    except Exception as e:
                        logger.warning(f"Could not restore {item}: {e}")
                
                # Restore preserved items
                for item in current_backup_dir.iterdir():
                    if not (self.project_dir / item.name).exists():
                        try:
                            if item.is_dir():
                                shutil.copytree(item, self.project_dir / item.name)
                            else:
                                shutil.copy2(item, self.project_dir)
                        except Exception as e:
                            logger.warning(f"Could not restore preserved {item}: {e}")
            
            # Restore services from backup
            self._restore_services(backup_to_restore)
            
            # Restart services
            self._start_services(services_stopped)
            
            logger.info(f"✅ Successfully rolled back to backup: {backup_to_restore['name']}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Rollback failed: {e}")
            return False
    
    def _stop_services(self) -> List[str]:
        """Stop YouTube-related services and return list of stopped services"""
        stopped_services = []
        
        try:
            # Get active YouTube services
            result = subprocess.run(
                ['systemctl', 'list-units', '--type=service', '--state=active'],
                capture_output=True, text=True
            )
            
            for line in result.stdout.split('\n'):
                if 'youtube-' in line:
                    service_name = line.split()[0]
                    try:
                        subprocess.run(['systemctl', 'stop', service_name], check=True)
                        stopped_services.append(service_name)
                        logger.info(f"Stopped service: {service_name}")
                    except Exception as e:
                        logger.warning(f"Could not stop service {service_name}: {e}")
                        
        except Exception as e:
            logger.warning(f"Could not list services: {e}")
            
        return stopped_services
    
    def _start_services(self, services: List[str]):
        """Start specified services"""
        for service_name in services:
            try:
                subprocess.run(['systemctl', 'start', service_name], check=True)
                logger.info(f"Started service: {service_name}")
            except Exception as e:
                logger.warning(f"Could not start service {service_name}: {e}")
    
    def _restore_services(self, backup_metadata: Dict):
        """Restore services that were active in the backup"""
        if 'services' not in backup_metadata:
            return
            
        logger.info("Restoring service configuration...")
        
        # Reload systemd (in case service files changed)
        try:
            subprocess.run(['systemctl', 'daemon-reload'], check=True)
        except Exception as e:
            logger.warning(f"Could not reload systemd: {e}")

def main():
    """Main function for CLI usage"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup and Rollback Manager")
    parser.add_argument('action', choices=['backup', 'rollback', 'list'], 
                       help='Action to perform')
    parser.add_argument('--type', default='manual', 
                       help='Backup type (for backup action)')
    parser.add_argument('--description', 
                       help='Backup description (for backup action)')
    parser.add_argument('--name', 
                       help='Backup name (for rollback action)')
    
    args = parser.parse_args()
    
    manager = BackupManager()
    
    if args.action == 'backup':
        backup_file = manager.create_backup(args.type, args.description)
        if backup_file:
            print(f"✅ Backup created: {backup_file}")
        else:
            print("❌ Backup failed")
            sys.exit(1)
    
    elif args.action == 'rollback':
        success = manager.rollback_to_backup(args.name)
        if success:
            print("✅ Rollback completed successfully")
        else:
            print("❌ Rollback failed")
            sys.exit(1)
    
    elif args.action == 'list':
        backups = manager.list_backups()
        if backups:
            print("\n📋 Available backups:")
            for backup in sorted(backups, key=lambda x: x['timestamp'], reverse=True):
                size_mb = backup.get('size', 0) / (1024 * 1024)
                print(f"  {backup['name']}")
                print(f"    Description: {backup.get('description', 'N/A')}")
                print(f"    Timestamp: {backup['timestamp']}")
                print(f"    Size: {size_mb:.1f} MB")
                print(f"    Git commit: {backup.get('git_commit', 'N/A')}")
                print()
        else:
            print("No backups found")

if __name__ == "__main__":
    main()