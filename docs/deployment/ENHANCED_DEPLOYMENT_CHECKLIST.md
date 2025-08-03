# Enhanced YouTube Scraper Deployment Checklist

## Pre-Deployment Preparation

### 1. Development Environment Verification
- [ ] All enhanced tools tested locally
- [ ] Security scanning passes in CI/CD
- [ ] Performance profiling completed
- [ ] Load testing executed successfully
- [ ] Database migration scripts validated
- [ ] Pre-commit hooks installed and passing

### 2. GitHub Repository Preparation
- [ ] Enhanced CI/CD workflows committed
- [ ] All new systemd services in repository
- [ ] Updated requirements.txt with DevOps dependencies
- [ ] Security scanner configurations validated
- [ ] Monitoring alert configurations reviewed

### 3. VM Environment Preparation
- [ ] VM resources adequate (4 vCPU, 8GB RAM minimum)
- [ ] Backup of current deployment created
- [ ] Network connectivity verified
- [ ] SSH access confirmed
- [ ] Disk space sufficient (>10GB free)

## Deployment Process

### Phase 1: Enhanced Infrastructure Setup

#### A. Install Enhanced Dependencies
```bash
# Verify deployment script includes new dependencies
grep -A 10 "Install enhanced DevOps tools" deployment/scripts/deploy.sh

# Dependencies to verify:
# - psutil>=5.9.0 (system monitoring)
# - bandit>=1.7.5 (security scanning)
# - safety>=2.3.0 (dependency scanning)
# - pip-audit>=2.6.0 (alternative security)
# - memory-profiler>=0.61.0 (performance)
# - line-profiler>=4.1.0 (profiling)
# - locust>=2.17.0 (load testing)
# - pyyaml>=6.0.0 (config)
```

#### B. Directory Structure Creation
```bash
# Verify directories are created:
ls -la monitoring/reports/
ls -la security/reports/
ls -la tools/profiling_reports/
ls -la tools/load_test_reports/
```

#### C. Tool Permissions and Configuration
```bash
# Verify executable permissions:
ls -la monitoring/alerting.py
ls -la security/scanner.py
ls -la tools/profiling.py
ls -la tools/load_testing.py
ls -la tools/database_migration.py
```

### Phase 2: Systemd Services Configuration

#### A. Install New Services
```bash
# Copy systemd files to system directory
sudo cp deployment/systemd/youtube-security-scan.service /etc/systemd/system/
sudo cp deployment/systemd/youtube-security-scan.timer /etc/systemd/system/
sudo cp deployment/systemd/youtube-performance-check.service /etc/systemd/system/
sudo cp deployment/systemd/youtube-performance-check.timer /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload
```

#### B. Enable and Start New Services
```bash
# Enable new timers
sudo systemctl enable youtube-security-scan.timer
sudo systemctl enable youtube-performance-check.timer

# Start timers
sudo systemctl start youtube-security-scan.timer
sudo systemctl start youtube-performance-check.timer

# Verify enhanced monitoring service
sudo systemctl restart youtube-monitoring.service
```

#### C. Service Status Verification
```bash
# Check all services
sudo systemctl status youtube-scraper.service
sudo systemctl status youtube-analytics.service
sudo systemctl status youtube-monitoring.service
sudo systemctl status youtube-security-scan.timer
sudo systemctl status youtube-performance-check.timer
```

### Phase 3: Enhanced Tool Validation

#### A. Monitoring and Alerting System
```bash
# Test monitoring system
cd /opt/youtube_scraper
source venv/bin/activate

# Verify monitoring configuration
python3 -c "
import json
with open('monitoring/alert_config.json') as f:
    config = json.load(f)
    print(f'✓ Alert config loaded: {len(config.get(\"thresholds\", {}))} thresholds')
"

# Test alerting system (quick test)
python3 monitoring/alerting.py --help

# Check monitoring reports directory
ls -la monitoring/reports/
```

#### B. Security Scanning System
```bash
# Run initial security scan
python3 security/scanner.py --project-root . --output-dir security/reports

# Verify security reports generated
ls -la security/reports/

# Check for critical vulnerabilities
python3 -c "
import json, glob
reports = glob.glob('security/reports/security_report_*.json')
if reports:
    with open(reports[-1]) as f:
        data = json.load(f)
        print(f'Security scan: {data.get(\"critical_count\", 0)} critical, {data.get(\"high_count\", 0)} high issues')
else:
    print('No security reports found')
"
```

#### C. Performance Profiling Tools
```bash
# Test performance profiling
python3 tools/profiling.py

# Verify profiling reports
ls -la tools/profiling_reports/

# Test load testing framework
python3 tools/load_testing.py --test-type keywords --workers 3

# Check load test reports
ls -la tools/load_test_reports/
```

#### D. Database Migration System
```bash
# Initialize migration system
python3 tools/database_migration.py status

# Verify migration tracking
python3 -c "
from tools.database_migration import MigrationRunner
from pathlib import Path
import os

try:
    # This would use actual credentials in production
    print('✓ Database migration tools available')
    print('Note: Requires Firebase credentials for full testing')
except Exception as e:
    print(f'Migration tools check: {e}')
"
```

### Phase 4: Integration Testing

#### A. GitHub Actions Integration
```bash
# Verify enhanced CI/CD workflows
cat .github/workflows/ci.yml | grep -A 5 "Comprehensive security scan"
cat .github/workflows/ci.yml | grep -A 5 "Performance profiling"

# Check workflow includes all new tools
grep -c "security/scanner.py\|tools/profiling.py\|tools/load_testing.py" .github/workflows/ci.yml
```

#### B. End-to-End Testing
```bash
# Test complete analytics pipeline with monitoring
python3 src/scripts/collectors/run_analytics.py --task daily

# Monitor system resources during test
python3 -c "
import psutil
import time
print(f'CPU: {psutil.cpu_percent()}%, Memory: {psutil.virtual_memory().percent}%')
"

# Verify all logs are being written
ls -la logs/
tail -10 logs/app.log
```

### Phase 5: Production Validation

#### A. Service Monitoring Verification
```bash
# Check all services are running
systemctl is-active youtube-scraper
systemctl is-active youtube-analytics  
systemctl is-active youtube-monitoring
systemctl list-timers | grep youtube

# View recent service logs
sudo journalctl -u youtube-scraper --since "10 minutes ago"
sudo journalctl -u youtube-monitoring --since "10 minutes ago"
```

#### B. Alert System Testing
```bash
# Test alert system (if configured)
# Note: Only test with non-critical alerts to avoid false alarms

# Check monitoring dashboard
if [ -f "monitoring/reports/latest.html" ]; then
    echo "✓ Monitoring dashboard available"
    ls -la monitoring/reports/latest.html
else
    echo "✗ Monitoring dashboard not generated yet"
fi
```

#### C. Performance Baseline
```bash
# Establish performance baseline
python3 tools/load_testing.py --test-type full > performance_baseline.log

# Monitor for 24 hours and check:
# - No memory leaks
# - CPU usage within normal range
# - All services stable
# - No critical security alerts
```

## Post-Deployment Verification

### 1. 24-Hour Monitoring Period
- [ ] All services running continuously
- [ ] No critical errors in logs
- [ ] Performance within expected ranges
- [ ] Security scans completed successfully
- [ ] Monitoring alerts configured and working

### 2. Weekly Verification Tasks
- [ ] Security scan reports reviewed
- [ ] Performance metrics analyzed
- [ ] System resource usage checked
- [ ] Backup systems verified
- [ ] Alert system tested

### 3. Monthly Verification Tasks
- [ ] Load testing performed
- [ ] Database migration status checked
- [ ] Security configuration reviewed
- [ ] Performance optimization opportunities identified
- [ ] Documentation updated

## Rollback Procedures

### If Enhanced Tools Fail
```bash
# Disable new services temporarily
sudo systemctl stop youtube-security-scan.timer
sudo systemctl stop youtube-performance-check.timer

# Revert monitoring service if needed
sudo systemctl stop youtube-monitoring.service
# Edit service file to remove enhanced monitoring
sudo systemctl start youtube-monitoring.service

# Core scraper should continue working normally
sudo systemctl status youtube-scraper.service
```

### If Core System Affected
```bash
# Use existing rollback procedures
./deployment/scripts/rollback.sh latest

# Verify core functionality restored
./deployment/scripts/health_check.sh
```

## Success Criteria

✅ **Deployment Successful When:**
- [ ] All original services running normally
- [ ] Enhanced monitoring active and generating reports
- [ ] Security scanning scheduled and functioning
- [ ] Performance profiling tools operational
- [ ] Load testing framework working
- [ ] Database migration system initialized
- [ ] CI/CD pipeline includes all new checks
- [ ] No critical security vulnerabilities found
- [ ] System performance within acceptable range
- [ ] All health checks passing

## Emergency Contacts

- **System Administrator**: [Your contact]
- **Development Team**: [Team contact]
- **GitHub Repository**: https://github.com/canaanhowell/youtube-scraper-production
- **Documentation**: `/opt/youtube_scraper/docs/deployment/`

## Notes

- Keep this checklist updated with any changes to the deployment process
- Document any issues encountered and their solutions
- Regular review and update of security configurations
- Performance benchmarks should be updated quarterly