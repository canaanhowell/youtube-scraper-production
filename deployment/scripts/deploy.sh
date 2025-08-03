#!/bin/bash

# YouTube Scraper Production Deployment Script
# This script handles the automated deployment process

set -e  # Exit on any error

# Configuration
DEPLOYMENT_PATH="/opt/youtube_scraper"
BACKUP_DIR="$DEPLOYMENT_PATH/backups"
LOG_FILE="$DEPLOYMENT_PATH/logs/deployment.log"
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

# Create necessary directories
setup_directories() {
    log INFO "Setting up directory structure..."
    
    mkdir -p "$DEPLOYMENT_PATH"/{src,logs,backups,tmp}
    mkdir -p "$DEPLOYMENT_PATH/src"/{analytics,scripts,utils,config}
    
    # Ensure proper ownership
    chown -R $USER:$USER "$DEPLOYMENT_PATH"
    
    log INFO "Directory structure created"
}

# Create backup of current deployment
create_backup() {
    log INFO "Creating backup of current deployment..."
    
    local backup_name="backup-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    mkdir -p "$backup_path"
    
    if [ -d "$DEPLOYMENT_PATH/src" ]; then
        tar -czf "$backup_path/youtube-scraper-backup.tar.gz" \
            -C "$DEPLOYMENT_PATH" \
            --exclude='logs/*' \
            --exclude='venv/*' \
            --exclude='backups/*' \
            --exclude='tmp/*' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            .
        
        log INFO "Backup created: $backup_path/youtube-scraper-backup.tar.gz"
        echo "$backup_path" > "$DEPLOYMENT_PATH/tmp/last_backup"
    else
        log WARN "No existing deployment found, skipping backup"
    fi
}

# Stop services
stop_services() {
    log INFO "Stopping services..."
    
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
    log INFO "Starting services..."
    
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
            error_exit "$service failed to start"
        fi
    done
    
    log INFO "All services started"
}

# Update application code
update_code() {
    log INFO "Updating application code..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Pull latest code from git
    if [ -d ".git" ]; then
        log INFO "Updating from git repository..."
        git fetch origin
        git reset --hard origin/main
    else
        log WARN "Not a git repository, code should be updated via deployment package"
    fi
    
    log INFO "Code update completed"
}

# Update Python dependencies
update_dependencies() {
    log INFO "Updating Python dependencies..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Activate virtual environment
    if [ ! -d "venv" ]; then
        log INFO "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install/update requirements
    if [ -f "requirements.txt" ]; then
        log INFO "Installing requirements..."
        pip install -r requirements.txt
    else
        error_exit "requirements.txt not found"
    fi
    
    # Install analytics dependencies
    pip install numpy>=1.24.0 aiofiles>=23.0.0 colorama>=0.4.6
    
    # Install enhanced DevOps tool dependencies
    log INFO "Installing enhanced DevOps tools..."
    pip install psutil>=5.9.0 memory-profiler>=0.61.0
    pip install bandit>=1.7.5 safety>=2.3.0 pip-audit>=2.6.0
    pip install locust>=2.17.0 line-profiler>=4.1.0
    pip install requests>=2.31.0 pyyaml>=6.0.0
    
    log INFO "Dependencies updated successfully"
}

# Setup enhanced DevOps tools
setup_enhanced_tools() {
    log INFO "Setting up enhanced monitoring and security tools..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Create monitoring directories
    mkdir -p monitoring/reports security/reports tools/{profiling_reports,load_test_reports}
    
    # Configure monitoring alerts
    if [ -f "monitoring/alert_config.json" ]; then
        log INFO "Configuring monitoring alerts..."
        
        # Set up monitoring service
        if [ -f "monitoring/alerting.py" ]; then
            chmod +x monitoring/alerting.py
            log INFO "Monitoring service configured"
        fi
    fi
    
    # Initialize security scanning
    if [ -f "security/scanner.py" ]; then
        log INFO "Initializing security scanner..."
        chmod +x security/scanner.py
        
        # Run initial security scan
        python3 security/scanner.py --project-root . --output-dir security/reports || log WARN "Initial security scan failed"
    fi
    
    # Set up performance profiling
    if [ -f "tools/profiling.py" ]; then
        chmod +x tools/profiling.py
        log INFO "Performance profiling tools configured"
    fi
    
    # Set up load testing
    if [ -f "tools/load_testing.py" ]; then
        chmod +x tools/load_testing.py
        log INFO "Load testing framework configured"
    fi
    
    # Initialize database migration system
    if [ -f "tools/database_migration.py" ]; then
        chmod +x tools/database_migration.py
        log INFO "Database migration tools configured"
    fi
    
    # Set proper ownership
    chown -R $USER:$USER "$DEPLOYMENT_PATH"/{monitoring,security,tools}
    
    log INFO "Enhanced DevOps tools setup completed"
}

# Update environment configuration
update_environment() {
    log INFO "Updating environment configuration..."
    
    cd "$DEPLOYMENT_PATH"
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        log INFO "Creating .env file..."
        cp environments/.env.production .env 2>/dev/null || {
            log WARN ".env.production template not found, creating basic .env"
            cat > .env << EOF
ENVIRONMENT=production
LOG_LEVEL=INFO
GOOGLE_SERVICE_KEY_PATH=/opt/credentials/firebase.json
# Add other environment variables as needed
EOF
        }
    fi
    
    log INFO "Environment configuration updated"
}

# Run health checks
health_check() {
    log INFO "Running health checks..."
    
    cd "$DEPLOYMENT_PATH"
    source venv/bin/activate
    
    # Check if services are running
    for service in "${SERVICES[@]}"; do
        if ! systemctl is-active --quiet "$service"; then
            error_exit "Health check failed: $service is not running"
        fi
    done
    
    # Test Python imports
    python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from src.analytics.metrics.keywords_interval_metrics import *
    from src.analytics.aggregators.category_metrics_aggregator import *
    from src.utils.firebase_client_enhanced import FirebaseClient
    print('✓ Core modules import successfully')
except Exception as e:
    print(f'✗ Import error: {e}')
    exit(1)
" || error_exit "Health check failed: Python imports"
    
    # Test analytics entry point
    python3 src/scripts/collectors/run_analytics.py --help > /dev/null || error_exit "Health check failed: Analytics entry point"
    
    # Test enhanced DevOps tools
    if [ -f "monitoring/alerting.py" ]; then
        python3 monitoring/alerting.py --help > /dev/null 2>&1 || log WARN "Monitoring system not responding"
    fi
    
    if [ -f "security/scanner.py" ]; then
        python3 security/scanner.py --help > /dev/null 2>&1 || log WARN "Security scanner not responding"
    fi
    
    if [ -f "tools/profiling.py" ]; then
        python3 -c "from tools.profiling import PerformanceProfiler; print('✓ Profiling tools available')" || log WARN "Profiling tools not available"
    fi
    
    if [ -f "tools/load_testing.py" ]; then
        python3 tools/load_testing.py --help > /dev/null 2>&1 || log WARN "Load testing framework not responding"
    fi
    
    if [ -f "tools/database_migration.py" ]; then
        python3 tools/database_migration.py --help > /dev/null 2>&1 || log WARN "Database migration tools not responding"
    fi
    
    # Check log files
    if [ ! -f "logs/app.log" ]; then
        touch logs/app.log
    fi
    
    log INFO "All health checks passed"
}

# Cleanup old backups
cleanup_backups() {
    log INFO "Cleaning up old backups..."
    
    # Keep only last 7 days of backups
    find "$BACKUP_DIR" -name "backup-*" -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    
    log INFO "Backup cleanup completed"
}

# Rollback to previous version
rollback() {
    log INFO "Rolling back to previous version..."
    
    if [ -f "$DEPLOYMENT_PATH/tmp/last_backup" ]; then
        local backup_path=$(cat "$DEPLOYMENT_PATH/tmp/last_backup")
        local backup_file="$backup_path/youtube-scraper-backup.tar.gz"
        
        if [ -f "$backup_file" ]; then
            log INFO "Restoring from backup: $backup_file"
            
            # Stop services
            stop_services
            
            # Restore backup
            cd "$DEPLOYMENT_PATH"
            tar -xzf "$backup_file"
            
            # Start services
            start_services
            
            log INFO "Rollback completed successfully"
        else
            error_exit "Backup file not found: $backup_file"
        fi
    else
        error_exit "No backup information found"
    fi
}

# Main deployment function
deploy() {
    log INFO "Starting deployment process..."
    
    # Check permissions
    check_permissions
    
    # Setup directories
    setup_directories
    
    # Create backup
    create_backup
    
    # Stop services
    stop_services
    
    # Update code
    update_code
    
    # Update dependencies
    update_dependencies
    
    # Update environment
    update_environment
    
    # Setup enhanced DevOps tools
    setup_enhanced_tools
    
    # Start services
    start_services
    
    # Run health checks
    health_check
    
    # Cleanup old backups
    cleanup_backups
    
    log INFO "Deployment completed successfully!"
}

# Main script execution
main() {
    case "${1:-deploy}" in
        deploy)
            deploy
            ;;
        rollback)
            rollback
            ;;
        health-check)
            health_check
            ;;
        stop)
            stop_services
            ;;
        start)
            start_services
            ;;
        *)
            echo "Usage: $0 {deploy|rollback|health-check|stop|start}"
            echo "  deploy      - Run full deployment process (default)"
            echo "  rollback    - Rollback to previous version"
            echo "  health-check - Run health checks only"
            echo "  stop        - Stop all services"
            echo "  start       - Start all services"
            exit 1
            ;;
    esac
}

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Run main function
main "$@"