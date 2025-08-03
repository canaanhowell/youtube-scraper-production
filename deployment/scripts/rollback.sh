#!/bin/bash

# YouTube Scraper Rollback Script
# Restores the system to a previous backup

set -e

# Configuration
DEPLOYMENT_PATH="/opt/youtube_app"
BACKUP_BASE_DIR="$DEPLOYMENT_PATH/backups"
LOG_FILE="$DEPLOYMENT_PATH/logs/rollback.log"
SERVICES=("youtube-scraper" "youtube-analytics")

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

# Check if running as root or with sudo
check_permissions() {
    if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
        error_exit "This script requires root privileges or passwordless sudo access"
    fi
    log INFO "Permission check passed"
}

# List available backups
list_backups() {
    log INFO "Available backups for rollback:"
    
    if [ ! -d "$BACKUP_BASE_DIR" ]; then
        error_exit "Backup directory not found: $BACKUP_BASE_DIR"
    fi
    
    local count=0
    for backup in $(ls -1t "$BACKUP_BASE_DIR" | grep "^backup-\|^quick-backup-"); do
        local backup_path="$BACKUP_BASE_DIR/$backup"
        local backup_date=$(date -r "$backup_path" '+%Y-%m-%d %H:%M:%S')
        local backup_size=$(du -sh "$backup_path" | cut -f1)
        
        echo "[$((++count))] $backup"
        echo "    Date: $backup_date"
        echo "    Size: $backup_size"
        
        # Show backup info if available
        if [ -f "$backup_path/backup-info.json" ]; then
            local backup_type=$(jq -r '.backup_type' "$backup_path/backup-info.json" 2>/dev/null || echo "unknown")
            local git_commit=$(jq -r '.git_commit' "$backup_path/backup-info.json" 2>/dev/null || echo "unknown")
            echo "    Type: $backup_type"
            echo "    Git commit: ${git_commit:0:8}"
        fi
        echo ""
    done
    
    if [ "$count" -eq 0 ]; then
        error_exit "No backups available for rollback"
    fi
}

# Verify backup before rollback
verify_backup() {
    local backup_path="$1"
    
    log INFO "Verifying backup: $(basename "$backup_path")"
    
    # Check if backup directory exists
    if [ ! -d "$backup_path" ]; then
        error_exit "Backup not found: $backup_path"
    fi
    
    # Check for essential backup files
    if [ ! -f "$backup_path/application/youtube-scraper-app.tar.gz" ]; then
        error_exit "Application backup file missing in $backup_path"
    fi
    
    # Verify tar file integrity
    if ! tar -tzf "$backup_path/application/youtube-scraper-app.tar.gz" > /dev/null 2>&1; then
        error_exit "Corrupted application backup file"
    fi
    
    # Check backup metadata
    if [ -f "$backup_path/backup-info.json" ]; then
        local backup_type=$(jq -r '.backup_type' "$backup_path/backup-info.json" 2>/dev/null || echo "unknown")
        local backup_date=$(jq -r '.timestamp' "$backup_path/backup-info.json" 2>/dev/null || echo "unknown")
        log INFO "Backup type: $backup_type, Date: $backup_date"
    else
        log WARN "Backup metadata not found, proceeding anyway"
    fi
    
    log INFO "Backup verification passed"
}

# Create pre-rollback backup
create_pre_rollback_backup() {
    log INFO "Creating pre-rollback backup..."
    
    # Use the backup script to create a quick backup
    if [ -f "$DEPLOYMENT_PATH/deployment/scripts/backup.sh" ]; then
        local pre_rollback_backup=$("$DEPLOYMENT_PATH/deployment/scripts/backup.sh" quick)
        log INFO "Pre-rollback backup created: $pre_rollback_backup"
        echo "$pre_rollback_backup" > "$DEPLOYMENT_PATH/tmp/pre-rollback-backup"
    else
        log WARN "Backup script not found, skipping pre-rollback backup"
    fi
}

# Stop services
stop_services() {
    log INFO "Stopping services for rollback..."
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            log INFO "Stopping $service..."
            sudo systemctl stop "$service"
            
            # Wait for service to stop
            local retries=0
            while systemctl is-active --quiet "$service" && [ $retries -lt 30 ]; do
                sleep 1
                ((retries++))
            done
            
            if systemctl is-active --quiet "$service"; then
                log WARN "$service did not stop gracefully, forcing stop"
                sudo systemctl kill "$service"
            fi
        else
            log INFO "$service is not running"
        fi
    done
    
    log INFO "All services stopped"
}

# Start services
start_services() {
    log INFO "Starting services after rollback..."
    
    for service in "${SERVICES[@]}"; do
        log INFO "Starting $service..."
        sudo systemctl start "$service"
        
        # Wait for service to start
        local retries=0
        while ! systemctl is-active --quiet "$service" && [ $retries -lt 30 ]; do
            sleep 1
            ((retries++))
        done
        
        if systemctl is-active --quiet "$service"; then
            log INFO "$service started successfully"
        else
            log ERROR "$service failed to start"
        fi
    done
}

# Restore application from backup
restore_application() {
    local backup_path="$1"
    
    log INFO "Restoring application from backup..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Extract application backup
    log INFO "Extracting application files..."
    tar -xzf "$backup_path/application/youtube-scraper-app.tar.gz"
    
    # Restore virtual environment if frozen requirements exist
    if [ -f "$backup_path/application/requirements-freeze.txt" ]; then
        log INFO "Restoring virtual environment..."
        
        # Recreate virtual environment
        if [ -d "venv" ]; then
            rm -rf venv
        fi
        python3 -m venv venv
        source venv/bin/activate
        
        # Install exact package versions from backup
        pip install --upgrade pip
        pip install -r "$backup_path/application/requirements-freeze.txt"
        
        deactivate
        log INFO "Virtual environment restored"
    else
        log WARN "No frozen requirements found, using current requirements.txt"
        if [ -d "venv" ]; then
            source venv/bin/activate
            pip install -r requirements.txt
            deactivate
        fi
    fi
    
    log INFO "Application restoration completed"
}

# Restore configuration from backup
restore_configuration() {
    local backup_path="$1"
    
    log INFO "Restoring configuration from backup..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Restore environment file
    if [ -f "$backup_path/config/env-backup" ]; then
        cp "$backup_path/config/env-backup" .env
        log INFO "Environment file restored"
    else
        log WARN "No environment backup found"
    fi
    
    # Restore systemd service files
    for service in youtube-scraper youtube-analytics; do
        if [ -f "$backup_path/config/$service.service" ]; then
            sudo cp "$backup_path/config/$service.service" "/etc/systemd/system/"
            log INFO "Service file restored: $service.service"
        fi
    done
    
    # Reload systemd if service files were restored
    if ls "$backup_path/config/"*.service 1> /dev/null 2>&1; then
        sudo systemctl daemon-reload
        log INFO "Systemd configuration reloaded"
    fi
    
    # Restore crontab
    if [ -f "$backup_path/config/crontab-backup.txt" ]; then
        if ! grep -q "No crontab found" "$backup_path/config/crontab-backup.txt"; then
            crontab "$backup_path/config/crontab-backup.txt"
            log INFO "Crontab restored"
        else
            log INFO "No crontab to restore"
        fi
    fi
    
    log INFO "Configuration restoration completed"
}

# Restore data from backup
restore_data() {
    local backup_path="$1"
    
    log INFO "Restoring data from backup..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Restore local data
    if [ -f "$backup_path/data/local-data.tar.gz" ]; then
        tar -xzf "$backup_path/data/local-data.tar.gz"
        log INFO "Local data restored"
    fi
    
    # Restore category mapping
    if [ -f "$backup_path/data/category_mapping.json" ]; then
        mkdir -p src/config
        cp "$backup_path/data/category_mapping.json" src/config/
        log INFO "Category mapping restored"
    fi
    
    log INFO "Data restoration completed"
}

# Post-rollback verification
verify_rollback() {
    log INFO "Verifying rollback..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Check if services are running
    local failed_services=0
    for service in "${SERVICES[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            log ERROR "Service $service is not running after rollback"
            ((failed_services++))
        fi
    done
    
    # Test application functionality
    if [ -d "venv" ]; then
        source venv/bin/activate
        
        # Test Python imports
        python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from src.analytics.metrics.keywords_interval_metrics import *
    from src.utils.firebase_client_enhanced import FirebaseClient
    print('✓ Core modules import successfully')
except Exception as e:
    print(f'✗ Import error: {e}')
    exit(1)
" && log INFO "Python imports test passed" || {
            log ERROR "Python imports test failed"
            ((failed_services++))
        }
        
        # Test analytics entry point
        python3 src/scripts/collectors/run_analytics.py --help > /dev/null 2>&1 && \
            log INFO "Analytics entry point test passed" || {
            log ERROR "Analytics entry point test failed"
            ((failed_services++))
        }
        
        deactivate
    fi
    
    if [ "$failed_services" -eq 0 ]; then
        log INFO "Rollback verification passed"
        return 0
    else
        log ERROR "Rollback verification failed ($failed_services issues)"
        return 1
    fi
}

# Interactive rollback selection
interactive_rollback() {
    echo "========================================"
    echo "       YOUTUBE SCRAPER ROLLBACK"
    echo "========================================"
    echo ""
    
    list_backups
    
    echo "Enter the backup name to rollback to (or 'q' to quit):"
    read -r backup_choice
    
    if [ "$backup_choice" = "q" ]; then
        log INFO "Rollback cancelled by user"
        exit 0
    fi
    
    local backup_path="$BACKUP_BASE_DIR/$backup_choice"
    if [ ! -d "$backup_path" ]; then
        error_exit "Invalid backup selection: $backup_choice"
    fi
    
    echo ""
    echo "You selected: $backup_choice"
    echo "WARNING: This will stop services and restore the application to this backup."
    echo "Are you sure you want to continue? (yes/no):"
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log INFO "Rollback cancelled by user"
        exit 0
    fi
    
    rollback_to_backup "$backup_path"
}

# Rollback to specific backup
rollback_to_backup() {
    local backup_path="$1"
    
    log INFO "Starting rollback to: $(basename "$backup_path")"
    
    # Verify backup
    verify_backup "$backup_path"
    
    # Create pre-rollback backup
    create_pre_rollback_backup
    
    # Stop services
    stop_services
    
    # Restore from backup
    restore_application "$backup_path"
    restore_configuration "$backup_path"
    restore_data "$backup_path"
    
    # Start services
    start_services
    
    # Verify rollback
    if verify_rollback; then
        log INFO "Rollback completed successfully!"
        echo ""
        echo -e "${GREEN}✅ Rollback completed successfully!${NC}"
        echo "System has been restored to backup: $(basename "$backup_path")"
    else
        log ERROR "Rollback verification failed"
        echo ""
        echo -e "${RED}❌ Rollback completed but verification failed${NC}"
        echo "Please check system status manually"
        exit 1
    fi
}

# Main function
main() {
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Check permissions
    check_permissions
    
    case "${1:-interactive}" in
        interactive)
            interactive_rollback
            ;;
        list)
            list_backups
            ;;
        to)
            if [ -n "$2" ]; then
                rollback_to_backup "$BACKUP_BASE_DIR/$2"
            else
                error_exit "Please specify backup name: $0 to <backup_name>"
            fi
            ;;
        latest)
            local latest_backup=$(ls -1t "$BACKUP_BASE_DIR" | grep "^backup-" | head -1)
            if [ -n "$latest_backup" ]; then
                rollback_to_backup "$BACKUP_BASE_DIR/$latest_backup"
            else
                error_exit "No backups found"
            fi
            ;;
        *)
            echo "Usage: $0 {interactive|list|to <backup_name>|latest}"
            echo "  interactive  - Interactive rollback selection (default)"
            echo "  list         - List available backups"
            echo "  to <name>    - Rollback to specific backup"
            echo "  latest       - Rollback to latest backup"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"