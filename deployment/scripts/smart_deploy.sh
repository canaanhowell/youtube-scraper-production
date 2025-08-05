#!/bin/bash

# Smart Auto-Deployment Script for YouTube Scraper
# Detects changes and deploys only what's needed

set -e  # Exit on any error

# Configuration
PROJECT_DIR="/opt/youtube_app"
BACKUP_DIR="/opt/youtube_app_backups"
LOG_FILE="/var/log/youtube_deploy.log"
VENV_PATH="$PROJECT_DIR/venv"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

# Create backup
create_backup() {
    log "Creating backup..."
    mkdir -p "$BACKUP_DIR"
    
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/backup_$TIMESTAMP.tar.gz"
    
    cd "$PROJECT_DIR"
    tar -czf "$BACKUP_FILE" \
        --exclude='venv' \
        --exclude='logs' \
        --exclude='__pycache__' \
        --exclude='.git' \
        .
    
    log "Backup created: $BACKUP_FILE"
    echo "$BACKUP_FILE" > "$BACKUP_DIR/latest_backup.txt"
}

# Detect what services exist and are running
detect_services() {
    log "Detecting installed services..."
    
    SERVICES=()
    
    # Check for existing services
    if systemctl list-unit-files | grep -q "youtube-scraper.service"; then
        SERVICES+=("youtube-scraper")
    fi
    
    if systemctl list-unit-files | grep -q "youtube-analytics.service"; then
        SERVICES+=("youtube-analytics")
    fi
    
    if systemctl list-unit-files | grep -q "youtube-monitoring.service"; then
        SERVICES+=("youtube-monitoring")
    fi
    
    log "Found services: ${SERVICES[*]}"
}

# Detect changes and determine what needs to be restarted
detect_changes() {
    log "Detecting changes..."
    
    # Get the last commit hash from previous deployment
    LAST_COMMIT_FILE="$PROJECT_DIR/.last_deploy_commit"
    if [ -f "$LAST_COMMIT_FILE" ]; then
        LAST_COMMIT=$(cat "$LAST_COMMIT_FILE")
        log "Last deployed commit: $LAST_COMMIT"
    else
        log "No previous deployment found, deploying all changes"
        LAST_COMMIT=""
    fi
    
    # Get current commit
    CURRENT_COMMIT=$(git rev-parse HEAD)
    log "Current commit: $CURRENT_COMMIT"
    
    # If no previous commit, assume everything changed
    if [ -z "$LAST_COMMIT" ]; then
        CHANGED_FILES="all"
    else
        # Get list of changed files
        CHANGED_FILES=$(git diff --name-only "$LAST_COMMIT" "$CURRENT_COMMIT" 2>/dev/null || echo "all")
    fi
    
    log "Changed files: $CHANGED_FILES"
    
    # Determine what needs to restart
    RESTART_SERVICES=()
    UPDATE_DEPS=false
    
    if [[ "$CHANGED_FILES" == "all" ]] || echo "$CHANGED_FILES" | grep -q "requirements.txt"; then
        UPDATE_DEPS=true
        log "Dependencies need updating"
    fi
    
    # Check for core scraper changes
    if [[ "$CHANGED_FILES" == "all" ]] || echo "$CHANGED_FILES" | grep -E "(youtube_scraper|youtube_collection)" > /dev/null; then
        RESTART_SERVICES+=("youtube-scraper")
        log "Core scraper files changed"
    fi
    
    # Check for analytics changes
    if [[ "$CHANGED_FILES" == "all" ]] || echo "$CHANGED_FILES" | grep -E "(analytics|src/analytics)" > /dev/null; then
        RESTART_SERVICES+=("youtube-analytics")
        log "Analytics files changed"
    fi
    
    # Check for monitoring changes
    if [[ "$CHANGED_FILES" == "all" ]] || echo "$CHANGED_FILES" | grep -E "(monitor|monitoring)" > /dev/null; then
        RESTART_SERVICES+=("youtube-monitoring")
        log "Monitoring files changed"
    fi
    
    # Check for systemd service files
    if [[ "$CHANGED_FILES" == "all" ]] || echo "$CHANGED_FILES" | grep -E "deployment/systemd" > /dev/null; then
        log "Systemd service files changed - will reinstall services"
        REINSTALL_SERVICES=true
    fi
}

# Update dependencies if needed
update_dependencies() {
    if [ "$UPDATE_DEPS" = true ]; then
        log "Updating dependencies..."
        
        cd "$PROJECT_DIR"
        source "$VENV_PATH/bin/activate"
        
        # Install/update requirements
        pip install -r requirements.txt --upgrade
        
        log "Dependencies updated successfully"
    else
        log "No dependency updates needed"
    fi
}

# Install new systemd services if they exist
install_services() {
    log "Checking for new systemd services..."
    
    SYSTEMD_DIR="$PROJECT_DIR/deployment/systemd"
    
    if [ -d "$SYSTEMD_DIR" ]; then
        # Copy any .service and .timer files
        for file in "$SYSTEMD_DIR"/*.service "$SYSTEMD_DIR"/*.timer; do
            if [ -f "$file" ]; then
                SERVICE_NAME=$(basename "$file")
                log "Installing service: $SERVICE_NAME"
                cp "$file" "/etc/systemd/system/"
            fi
        done
        
        # Reload systemd
        systemctl daemon-reload
        
        # Enable new services (but don't start them yet)
        for file in "$SYSTEMD_DIR"/*.service; do
            if [ -f "$file" ]; then
                SERVICE_NAME=$(basename "$file" .service)
                if ! systemctl is-enabled "$SERVICE_NAME" >/dev/null 2>&1; then
                    log "Enabling new service: $SERVICE_NAME"
                    systemctl enable "$SERVICE_NAME"
                fi
            fi
        done
        
        # Enable new timers
        for file in "$SYSTEMD_DIR"/*.timer; do
            if [ -f "$file" ]; then
                TIMER_NAME=$(basename "$file" .timer)
                if ! systemctl is-enabled "$TIMER_NAME.timer" >/dev/null 2>&1; then
                    log "Enabling new timer: $TIMER_NAME.timer"
                    systemctl enable "$TIMER_NAME.timer"
                fi
            fi
        done
    fi
}

# Restart affected services
restart_services() {
    log "Restarting affected services..."
    
    # Remove duplicates from restart list
    UNIQUE_SERVICES=($(echo "${RESTART_SERVICES[@]}" | tr ' ' '\n' | sort -u | tr '\n' ' '))
    
    for service in "${UNIQUE_SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "$service.service"; then
            log "Restarting $service..."
            
            # Stop service
            if systemctl is-active "$service" >/dev/null 2>&1; then
                systemctl stop "$service"
            fi
            
            # Start service
            systemctl start "$service"
            
            # Check if it started successfully
            if systemctl is-active "$service" >/dev/null 2>&1; then
                log "✓ $service restarted successfully"
            else
                log_error "✗ Failed to restart $service"
                return 1
            fi
        else
            log_warning "Service $service not found, skipping"
        fi
    done
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    # Check if core services are running
    CORE_SERVICES=("youtube-scraper")
    
    for service in "${CORE_SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "$service.service"; then
            if systemctl is-active "$service" >/dev/null 2>&1; then
                log "✓ $service is running"
            else
                log_error "✗ $service is not running"
                return 1
            fi
        fi
    done
    
    # Test a basic function if possible
    cd "$PROJECT_DIR"
    source "$VENV_PATH/bin/activate"
    
    # Quick test (if test script exists)
    if [ -f "test_deployment.py" ]; then
        log "Running deployment test..."
        if python3 test_deployment.py; then
            log "✓ Deployment test passed"
        else
            log_error "✗ Deployment test failed"
            return 1
        fi
    fi
    
    return 0
}

# Rollback function
rollback() {
    log_error "Deployment failed, rolling back..."
    
    if [ -f "$BACKUP_DIR/latest_backup.txt" ]; then
        LATEST_BACKUP=$(cat "$BACKUP_DIR/latest_backup.txt")
        
        if [ -f "$LATEST_BACKUP" ]; then
            log "Restoring from backup: $LATEST_BACKUP"
            
            cd "$PROJECT_DIR"
            tar -xzf "$LATEST_BACKUP"
            
            # Restart services
            for service in "${SERVICES[@]}"; do
                if systemctl list-unit-files | grep -q "$service.service"; then
                    systemctl restart "$service" || true
                fi
            done
            
            log "Rollback completed"
        else
            log_error "Backup file not found: $LATEST_BACKUP"
        fi
    else
        log_error "No backup information found"
    fi
}

# Main deployment function
main() {
    log "Starting smart deployment..."
    
    cd "$PROJECT_DIR"
    
    # Detect current services
    detect_services
    
    # Create backup
    create_backup
    
    # Detect changes
    detect_changes
    
    # Update code (git pull already done by GitHub Actions)
    log "Code already updated by GitHub Actions"
    
    # Update dependencies if needed
    update_dependencies
    
    # Install new services
    install_services
    
    # Restart affected services
    if ! restart_services; then
        rollback
        exit 1
    fi
    
    # Verify deployment
    if ! verify_deployment; then
        rollback
        exit 1
    fi
    
    # Save current commit for next deployment
    echo "$(git rev-parse HEAD)" > "$PROJECT_DIR/.last_deploy_commit"
    
    log "✅ Smart deployment completed successfully!"
    
    # Show status
    log "Service status:"
    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "$service.service"; then
            STATUS=$(systemctl is-active "$service" 2>/dev/null || echo "inactive")
            log "  $service: $STATUS"
        fi
    done
}

# Run main function with error handling
if main; then
    exit 0
else
    log_error "Deployment failed"
    exit 1
fi