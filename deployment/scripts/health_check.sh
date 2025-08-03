#!/bin/bash

# YouTube Scraper Health Check Script
# Comprehensive health monitoring for the YouTube scraper system

set -e

# Configuration
DEPLOYMENT_PATH="/opt/youtube_app"
LOG_FILE="$DEPLOYMENT_PATH/logs/health_check.log"
SERVICES=("youtube-scraper" "youtube-analytics")
CRITICAL_PROCESSES=("python3")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Health check results
HEALTH_STATUS=0
CHECKS_PASSED=0
CHECKS_FAILED=0

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

# Check result tracking
check_result() {
    local check_name="$1"
    local result="$2"
    local message="$3"
    
    if [ "$result" -eq 0 ]; then
        log INFO "✅ $check_name: $message"
        ((CHECKS_PASSED++))
    else
        log ERROR "❌ $check_name: $message"
        ((CHECKS_FAILED++))
        HEALTH_STATUS=1
    fi
}

# Check system resources
check_system_resources() {
    log INFO "Checking system resources..."
    
    # Check disk space
    local disk_usage=$(df "$DEPLOYMENT_PATH" | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 90 ]; then
        check_result "Disk Space" 0 "Usage: ${disk_usage}% (OK)"
    else
        check_result "Disk Space" 1 "Usage: ${disk_usage}% (Critical)"
    fi
    
    # Check memory usage
    local mem_usage=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
    if [ "$mem_usage" -lt 90 ]; then
        check_result "Memory Usage" 0 "Usage: ${mem_usage}% (OK)"
    else
        check_result "Memory Usage" 1 "Usage: ${mem_usage}% (High)"
    fi
    
    # Check CPU load
    local cpu_load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    local cpu_cores=$(nproc)
    local cpu_threshold=$(echo "$cpu_cores * 2" | bc -l)
    
    if (( $(echo "$cpu_load < $cpu_threshold" | bc -l) )); then
        check_result "CPU Load" 0 "Load: $cpu_load (OK, threshold: $cpu_threshold)"
    else
        check_result "CPU Load" 1 "Load: $cpu_load (High, threshold: $cpu_threshold)"
    fi
}

# Check services status
check_services() {
    log INFO "Checking services status..."
    
    for service in "${SERVICES[@]}"; do
        if systemctl is-active --quiet "$service"; then
            # Check if service is enabled
            if systemctl is-enabled --quiet "$service"; then
                check_result "Service $service" 0 "Active and enabled"
            else
                check_result "Service $service" 1 "Active but not enabled"
            fi
            
            # Check service logs for recent errors
            local error_count=$(journalctl -u "$service" --since "10 minutes ago" | grep -i "error\|exception\|failed" | wc -l)
            if [ "$error_count" -eq 0 ]; then
                check_result "Service $service Logs" 0 "No recent errors"
            else
                check_result "Service $service Logs" 1 "$error_count errors in last 10 minutes"
            fi
        else
            check_result "Service $service" 1 "Inactive"
        fi
    done
}

# Check application health
check_application() {
    log INFO "Checking application health..."
    
    cd "$DEPLOYMENT_PATH" || {
        check_result "Application Directory" 1 "Cannot access $DEPLOYMENT_PATH"
        return
    }
    
    # Check if virtual environment exists
    if [ -d "venv" ]; then
        check_result "Virtual Environment" 0 "Present"
    else
        check_result "Virtual Environment" 1 "Missing"
        return
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Check Python imports
    python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from src.analytics.metrics.keywords_interval_metrics import *
    print('✓ Interval metrics import OK')
except Exception as e:
    print(f'✗ Interval metrics import failed: {e}')
    exit(1)
" && check_result "Interval Metrics Import" 0 "Success" || check_result "Interval Metrics Import" 1 "Failed"
    
    python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from src.analytics.aggregators.category_metrics_aggregator import *
    print('✓ Category aggregator import OK')
except Exception as e:
    print(f'✗ Category aggregator import failed: {e}')
    exit(1)
" && check_result "Category Aggregator Import" 0 "Success" || check_result "Category Aggregator Import" 1 "Failed"
    
    python3 -c "
import sys, os
sys.path.insert(0, '.')
try:
    from src.utils.firebase_client_enhanced import FirebaseClient
    print('✓ Firebase client import OK')
except Exception as e:
    print(f'✗ Firebase client import failed: {e}')
    exit(1)
" && check_result "Firebase Client Import" 0 "Success" || check_result "Firebase Client Import" 1 "Failed"
    
    # Test analytics entry point
    python3 src/scripts/collectors/run_analytics.py --help > /dev/null 2>&1 && \
        check_result "Analytics Entry Point" 0 "Accessible" || \
        check_result "Analytics Entry Point" 1 "Not accessible"
}

# Check external dependencies
check_external_dependencies() {
    log INFO "Checking external dependencies..."
    
    cd "$DEPLOYMENT_PATH" || return
    source venv/bin/activate
    
    # Check Firebase connectivity (if credentials are available)
    if [ -f ".env" ] && grep -q "GOOGLE_SERVICE_KEY_PATH" .env; then
        python3 -c "
import sys, os
sys.path.insert(0, '.')
from src.utils.env_loader import load_env
load_env()
try:
    from src.utils.firebase_client_enhanced import FirebaseClient
    client = FirebaseClient()
    print('✓ Firebase connection test passed')
except Exception as e:
    print(f'✗ Firebase connection failed: {e}')
    exit(1)
" && check_result "Firebase Connectivity" 0 "Connected" || check_result "Firebase Connectivity" 1 "Connection failed"
    else
        check_result "Firebase Connectivity" 1 "No credentials configured"
    fi
    
    # Check Redis connectivity (if configured)
    if [ -f ".env" ] && grep -q "UPSTASH_REDIS" .env; then
        python3 -c "
import sys, os
sys.path.insert(0, '.')
from src.utils.env_loader import load_env
load_env()
try:
    from src.utils.redis_client_enhanced import RedisClient
    client = RedisClient()
    # Test basic operation
    client.set('health_check', 'test', ex=10)
    result = client.get('health_check')
    if result == 'test':
        print('✓ Redis connection test passed')
    else:
        raise Exception('Test value mismatch')
except Exception as e:
    print(f'✗ Redis connection failed: {e}')
    exit(1)
" && check_result "Redis Connectivity" 0 "Connected" || check_result "Redis Connectivity" 1 "Connection failed"
    else
        check_result "Redis Connectivity" 1 "No Redis configuration found"
    fi
}

# Check Docker containers (VPN)
check_docker_containers() {
    log INFO "Checking Docker containers..."
    
    if command -v docker &> /dev/null; then
        # Check if Docker is running
        if docker info &> /dev/null; then
            check_result "Docker Service" 0 "Running"
            
            # Check for Gluetun container
            if docker ps --format "table {{.Names}}" | grep -q "gluetun"; then
                check_result "Gluetun VPN Container" 0 "Running"
                
                # Check VPN connection
                local vpn_ip=$(docker exec gluetun wget -qO- http://ipinfo.io/ip 2>/dev/null || echo "unknown")
                if [ "$vpn_ip" != "unknown" ]; then
                    check_result "VPN IP" 0 "Active (IP: $vpn_ip)"
                else
                    check_result "VPN IP" 1 "Cannot retrieve VPN IP"
                fi
            else
                check_result "Gluetun VPN Container" 1 "Not running"
            fi
        else
            check_result "Docker Service" 1 "Not running or inaccessible"
        fi
    else
        check_result "Docker Installation" 1 "Docker not installed"
    fi
}

# Check log files
check_log_files() {
    log INFO "Checking log files..."
    
    local log_dir="$DEPLOYMENT_PATH/logs"
    
    if [ -d "$log_dir" ]; then
        check_result "Log Directory" 0 "Present"
        
        # Check for critical log files
        for logfile in "app.log" "error.log" "network.log"; do
            if [ -f "$log_dir/$logfile" ]; then
                local file_age=$(find "$log_dir/$logfile" -mtime +1 | wc -l)
                if [ "$file_age" -eq 0 ]; then
                    check_result "Log File $logfile" 0 "Recent activity"
                else
                    check_result "Log File $logfile" 1 "No recent activity (>24h)"
                fi
            else
                check_result "Log File $logfile" 1 "Missing"
            fi
        done
        
        # Check log file sizes
        local large_logs=$(find "$log_dir" -name "*.log" -size +100M | wc -l)
        if [ "$large_logs" -eq 0 ]; then
            check_result "Log File Sizes" 0 "All logs <100MB"
        else
            check_result "Log File Sizes" 1 "$large_logs log files >100MB"
        fi
    else
        check_result "Log Directory" 1 "Missing"
    fi
}

# Check configuration files
check_configuration() {
    log INFO "Checking configuration files..."
    
    cd "$DEPLOYMENT_PATH" || return
    
    # Check .env file
    if [ -f ".env" ]; then
        check_result "Environment File" 0 "Present"
        
        # Check for required environment variables
        local required_vars=("ENVIRONMENT" "GOOGLE_SERVICE_KEY_PATH")
        for var in "${required_vars[@]}"; do
            if grep -q "$var" .env; then
                check_result "Environment Variable $var" 0 "Configured"
            else
                check_result "Environment Variable $var" 1 "Missing"
            fi
        done
    else
        check_result "Environment File" 1 "Missing .env file"
    fi
    
    # Check category mapping configuration
    if [ -f "src/config/category_mapping.json" ]; then
        python3 -c "
import json
try:
    with open('src/config/category_mapping.json') as f:
        data = json.load(f)
        if 'ph_to_youtube_reddit_mapping' in data:
            count = len(data['ph_to_youtube_reddit_mapping'])
            print(f'✓ Category mapping valid: {count} mappings')
        else:
            raise ValueError('Missing ph_to_youtube_reddit_mapping key')
except Exception as e:
    print(f'✗ Category mapping invalid: {e}')
    exit(1)
" && check_result "Category Mapping" 0 "Valid configuration" || check_result "Category Mapping" 1 "Invalid configuration"
    else
        check_result "Category Mapping" 1 "Missing configuration file"
    fi
}

# Generate health report
generate_report() {
    local total_checks=$((CHECKS_PASSED + CHECKS_FAILED))
    local success_rate=$(echo "scale=1; $CHECKS_PASSED * 100 / $total_checks" | bc -l)
    
    echo ""
    echo "========================================"
    echo "          HEALTH CHECK REPORT"
    echo "========================================"
    echo "Timestamp: $(date)"
    echo "Total Checks: $total_checks"
    echo -e "Passed: ${GREEN}$CHECKS_PASSED${NC}"
    echo -e "Failed: ${RED}$CHECKS_FAILED${NC}"
    echo "Success Rate: $success_rate%"
    echo ""
    
    if [ "$HEALTH_STATUS" -eq 0 ]; then
        echo -e "${GREEN}✅ SYSTEM HEALTHY${NC}"
    else
        echo -e "${RED}❌ SYSTEM ISSUES DETECTED${NC}"
    fi
    
    echo "========================================"
    
    # Log summary
    log INFO "Health check completed: $CHECKS_PASSED passed, $CHECKS_FAILED failed (Success rate: $success_rate%)"
}

# Main health check function
main() {
    log INFO "Starting comprehensive health check..."
    
    # Create log directory if it doesn't exist
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # Run all health checks
    check_system_resources
    check_services
    check_application
    check_external_dependencies
    check_docker_containers
    check_log_files
    check_configuration
    
    # Generate report
    generate_report
    
    # Exit with appropriate status
    exit $HEALTH_STATUS
}

# Run health check
main "$@"