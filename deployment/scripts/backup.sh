#!/bin/bash

# YouTube Scraper Backup Script
# Creates comprehensive backups of the application and data

set -e

# Configuration
DEPLOYMENT_PATH="/opt/youtube_scraper"
BACKUP_BASE_DIR="$DEPLOYMENT_PATH/backups"
LOG_FILE="$DEPLOYMENT_PATH/logs/backup.log"
RETENTION_DAYS=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $level in
        INFO)  echo -e "${GREEN}[INFO]${NC} $message" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC} $message" ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $message" ;;
        DEBUG) echo -e "${BLUE}[DEBUG]${NC} $message" ;;
    esac
    
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

# Error handler
error_exit() {
    log ERROR "$1"
    exit 1
}

# Create backup directory structure
setup_backup_dir() {
    local backup_name="$1"
    local backup_dir="$BACKUP_BASE_DIR/$backup_name"
    
    mkdir -p "$backup_dir"/{application,config,data,logs}
    echo "$backup_dir"
}

# Backup application code
backup_application() {
    local backup_dir="$1"
    
    log INFO "Backing up application code..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Create application backup
    tar -czf "$backup_dir/application/youtube-scraper-app.tar.gz" \
        --exclude='logs/*' \
        --exclude='venv/*' \
        --exclude='backups/*' \
        --exclude='tmp/*' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.git' \
        src/ \
        requirements.txt \
        docker-compose.yml \
        youtube_*.py \
        deployment/ \
        tests/ \
        docs/ 2>/dev/null || true
    
    # Backup virtual environment requirements
    if [ -d "venv" ]; then
        source venv/bin/activate
        pip freeze > "$backup_dir/application/requirements-freeze.txt"
        deactivate
    fi
    
    log INFO "Application backup completed"
}

# Backup configuration files
backup_configuration() {
    local backup_dir="$1"
    
    log INFO "Backing up configuration files..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Backup environment files
    if [ -f ".env" ]; then
        cp .env "$backup_dir/config/env-backup"
    fi
    
    # Backup service files
    if [ -d "/etc/systemd/system" ]; then
        for service in youtube-scraper youtube-analytics; do
            if [ -f "/etc/systemd/system/$service.service" ]; then
                sudo cp "/etc/systemd/system/$service.service" "$backup_dir/config/" 2>/dev/null || true
            fi
        done
    fi
    
    # Backup cron jobs
    crontab -l > "$backup_dir/config/crontab-backup.txt" 2>/dev/null || echo "No crontab found" > "$backup_dir/config/crontab-backup.txt"
    
    # Backup nginx config if exists
    if [ -f "/etc/nginx/sites-available/youtube-scraper" ]; then
        sudo cp "/etc/nginx/sites-available/youtube-scraper" "$backup_dir/config/" 2>/dev/null || true
    fi
    
    log INFO "Configuration backup completed"
}

# Backup data files
backup_data() {
    local backup_dir="$1"
    
    log INFO "Backing up data files..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Backup any local data files
    if [ -d "data" ]; then
        tar -czf "$backup_dir/data/local-data.tar.gz" data/ 2>/dev/null || true
    fi
    
    # Backup category mapping
    if [ -f "src/config/category_mapping.json" ]; then
        cp "src/config/category_mapping.json" "$backup_dir/data/"
    fi
    
    # Export Firebase data (if possible)
    if [ -f ".env" ] && grep -q "GOOGLE_SERVICE_KEY_PATH" .env; then
        log INFO "Attempting to export Firebase data..."
        source venv/bin/activate 2>/dev/null || true
        python3 -c "
import sys, os, json
sys.path.insert(0, '.')
try:
    from src.utils.env_loader import load_env
    from src.utils.firebase_client_enhanced import FirebaseClient
    load_env()
    
    # Export keywords and basic stats
    client = FirebaseClient()
    
    # This is a basic export - implement full export based on your needs
    print('Firebase export would go here')
    
except Exception as e:
    print(f'Firebase export failed: {e}')
" > "$backup_dir/data/firebase-export.log" 2>&1 || true
    fi
    
    log INFO "Data backup completed"
}

# Backup logs
backup_logs() {
    local backup_dir="$1"
    
    log INFO "Backing up logs..."
    
    cd "$DEPLOYMENT_PATH"
    
    if [ -d "logs" ]; then
        # Backup recent logs (last 7 days)
        find logs/ -name "*.log" -mtime -7 -exec tar -czf "$backup_dir/logs/recent-logs.tar.gz" {} + 2>/dev/null || true
        
        # Backup critical logs completely
        for critical_log in "app.log" "error.log" "deployment.log"; do
            if [ -f "logs/$critical_log" ]; then
                cp "logs/$critical_log" "$backup_dir/logs/" 2>/dev/null || true
            fi
        done
    fi
    
    # Backup systemd journal logs
    for service in youtube-scraper youtube-analytics; do
        journalctl -u "$service" --since "7 days ago" > "$backup_dir/logs/$service-journal.log" 2>/dev/null || true
    done
    
    log INFO "Logs backup completed"
}

# Create backup metadata
create_backup_metadata() {
    local backup_dir="$1"
    local backup_type="$2"
    
    log INFO "Creating backup metadata..."
    
    cat > "$backup_dir/backup-info.json" << EOF
{
    "backup_name": "$(basename "$backup_dir")",
    "backup_type": "$backup_type",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)",
    "hostname": "$(hostname)",
    "user": "$(whoami)",
    "deployment_path": "$DEPLOYMENT_PATH",
    "git_commit": "$(cd "$DEPLOYMENT_PATH" && git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(cd "$DEPLOYMENT_PATH" && git branch --show-current 2>/dev/null || echo 'unknown')",
    "system_info": {
        "os": "$(uname -s)",
        "kernel": "$(uname -r)",
        "architecture": "$(uname -m)",
        "uptime": "$(uptime -p)"
    },
    "services_status": {
$(for service in youtube-scraper youtube-analytics; do
    if systemctl is-active --quiet "$service"; then
        echo "        \"$service\": \"active\","
    else
        echo "        \"$service\": \"inactive\","
    fi
done | sed '$ s/,$//')
    },
    "disk_usage": "$(df -h "$DEPLOYMENT_PATH" | tail -1 | awk '{print $5}')",
    "backup_size": "$(du -sh "$backup_dir" | cut -f1)"
}
EOF
    
    log INFO "Backup metadata created"
}

# Cleanup old backups
cleanup_old_backups() {
    log INFO "Cleaning up old backups..."
    
    # Remove backups older than retention period
    find "$BACKUP_BASE_DIR" -name "backup-*" -type d -mtime +"$RETENTION_DAYS" -exec rm -rf {} \; 2>/dev/null || true
    
    # Keep only the last 10 backups regardless of age
    local backup_count=$(ls -1 "$BACKUP_BASE_DIR" | grep "^backup-" | wc -l)
    if [ "$backup_count" -gt 10 ]; then
        local excess=$((backup_count - 10))
        ls -1t "$BACKUP_BASE_DIR" | grep "^backup-" | tail -"$excess" | while read old_backup; do
            rm -rf "$BACKUP_BASE_DIR/$old_backup"
            log INFO "Removed old backup: $old_backup"
        done
    fi
    
    log INFO "Cleanup completed"
}

# Verify backup integrity
verify_backup() {
    local backup_dir="$1"
    
    log INFO "Verifying backup integrity..."
    
    local errors=0
    
    # Check if main backup file exists
    if [ ! -f "$backup_dir/application/youtube-scraper-app.tar.gz" ]; then
        log ERROR "Application backup file missing"
        ((errors++))
    fi
    
    # Check backup metadata
    if [ ! -f "$backup_dir/backup-info.json" ]; then
        log ERROR "Backup metadata missing"
        ((errors++))
    fi
    
    # Verify tar files can be read
    for tar_file in $(find "$backup_dir" -name "*.tar.gz"); do
        if ! tar -tzf "$tar_file" > /dev/null 2>&1; then
            log ERROR "Corrupted backup file: $tar_file"
            ((errors++))
        fi
    done
    
    if [ "$errors" -eq 0 ]; then
        log INFO "Backup verification passed"
        return 0
    else
        log ERROR "Backup verification failed with $errors errors"
        return 1
    fi
}

# Full backup function
create_full_backup() {
    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_dir=$(setup_backup_dir "$backup_name")
    
    log INFO "Starting full backup: $backup_name"
    
    # Create all backups
    backup_application "$backup_dir"
    backup_configuration "$backup_dir"
    backup_data "$backup_dir"
    backup_logs "$backup_dir"
    
    # Create metadata
    create_backup_metadata "$backup_dir" "full"
    
    # Verify backup
    if verify_backup "$backup_dir"; then
        log INFO "Full backup completed successfully: $backup_dir"
        echo "$backup_dir"
    else
        error_exit "Backup verification failed"
    fi
}

# Quick backup function (application only)
create_quick_backup() {
    local backup_name="quick-backup-$(date +%Y%m%d-%H%M%S)"
    local backup_dir=$(setup_backup_dir "$backup_name")
    
    log INFO "Starting quick backup: $backup_name"
    
    # Quick backup - application and config only
    backup_application "$backup_dir"
    backup_configuration "$backup_dir"
    
    # Create metadata
    create_backup_metadata "$backup_dir" "quick"
    
    # Verify backup
    if verify_backup "$backup_dir"; then
        log INFO "Quick backup completed successfully: $backup_dir"
        echo "$backup_dir"
    else
        error_exit "Quick backup verification failed"
    fi
}

# List available backups
list_backups() {
    log INFO "Available backups:"
    
    if [ -d "$BACKUP_BASE_DIR" ]; then
        for backup in $(ls -1t "$BACKUP_BASE_DIR" | grep "^backup-\|^quick-backup-"); do
            local backup_path="$BACKUP_BASE_DIR/$backup"
            local backup_date=$(date -r "$backup_path" '+%Y-%m-%d %H:%M:%S')
            local backup_size=$(du -sh "$backup_path" | cut -f1)
            
            echo "  $backup - $backup_date ($backup_size)"
            
            # Show backup info if available
            if [ -f "$backup_path/backup-info.json" ]; then
                local backup_type=$(jq -r '.backup_type' "$backup_path/backup-info.json" 2>/dev/null || echo "unknown")
                echo "    Type: $backup_type"
            fi
        done
    else
        echo "  No backups found"
    fi
}

# Main function
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$BACKUP_BASE_DIR"
    
    case "${1:-full}" in
        full)
            create_full_backup
            cleanup_old_backups
            ;;
        quick)
            create_quick_backup
            ;;
        list)
            list_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        verify)
            if [ -n "$2" ]; then
                verify_backup "$BACKUP_BASE_DIR/$2"
            else
                error_exit "Please specify backup name to verify"
            fi
            ;;
        *)
            echo "Usage: $0 {full|quick|list|cleanup|verify <backup_name>}"
            echo "  full    - Create complete backup (default)"
            echo "  quick   - Create quick backup (app + config only)"
            echo "  list    - List available backups"
            echo "  cleanup - Remove old backups"
            echo "  verify  - Verify backup integrity"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"