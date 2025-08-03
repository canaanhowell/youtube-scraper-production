# YouTube Scraper DevOps Workflow

Complete guide for managing the YouTube scraper application from local development through GitHub to VM deployment.

## Overview

This document describes the modern DevOps pipeline implemented for the YouTube scraper system, providing automated testing, deployment, and monitoring capabilities.

## Architecture

```
Local Development → GitHub Actions CI/CD → VM Deployment
        ↓                    ↓                ↓
   Pre-commit hooks    Automated testing   Systemd services
   Code quality       Security scanning    Health monitoring
   Local testing      Build verification   Backup/rollback
```

## Quick Start

### 1. Local Development Setup

```bash
# Clone repository
git clone https://github.com/canaanhowell/youtube-scraper-production.git
cd youtube-scraper-production

# Setup Python environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup pre-commit hooks
pre-commit install

# Configure environment
cp environments/.env.example .env
# Edit .env with your configuration
```

### 2. Development Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes and test locally
python src/scripts/collectors/run_analytics.py --help

# Commit with pre-commit hooks
git add .
git commit -m "feat: add new analytics feature"

# Push and create PR
git push origin feature/your-feature
```

### 3. Deployment

Deployment happens automatically when code is merged to `main` branch via GitHub Actions.

## Directory Structure

```
youtube-scraper-production/
├── .github/
│   └── workflows/           # GitHub Actions workflows
│       ├── ci.yml          # Continuous Integration
│       ├── deploy.yml      # Production Deployment
│       └── release.yml     # Release Management
├── deployment/
│   ├── scripts/            # Deployment automation
│   │   ├── deploy.sh       # Main deployment script
│   │   ├── health_check.sh # Health monitoring
│   │   ├── backup.sh       # Backup management
│   │   └── rollback.sh     # Rollback procedures
│   └── systemd/            # Service definitions
│       ├── youtube-scraper.service
│       ├── youtube-analytics.service
│       └── *.timer         # Scheduled services
├── environments/           # Environment configurations
│   ├── .env.example        # Configuration template
│   ├── development.env     # Development settings
│   └── production.env      # Production settings
├── src/                    # Application source code
│   ├── analytics/          # Analytics modules
│   ├── scripts/            # Executable scripts
│   ├── utils/              # Utility functions
│   └── config/             # Configuration files
└── tests/                  # Test suites
    ├── unit/               # Unit tests
    ├── integration/        # Integration tests
    └── performance/        # Performance tests
```

## CI/CD Pipeline

### Continuous Integration (.github/workflows/ci.yml)

Triggered on: Push to `main`/`develop`, Pull Requests

**Stages:**
1. **Code Quality & Security**
   - Black code formatting check
   - Import sorting (isort)
   - Linting (flake8)
   - Security scan (Bandit)
   - Dependency security check

2. **Testing**
   - Unit tests with coverage
   - Integration tests
   - Build verification

3. **Deployment Ready**
   - Creates deployment artifact
   - Prepares for production deployment

### Deployment Pipeline (.github/workflows/deploy.yml)

Triggered on: Push to `main` branch

**Stages:**
1. **Pre-deployment**
   - Version generation
   - CI verification

2. **Deploy to VM**
   - Package creation
   - Secure file transfer
   - Service management
   - Health checks

3. **Post-deployment**
   - Service verification
   - Log analysis
   - Performance validation

4. **Rollback** (on failure)
   - Automatic restoration
   - Service recovery

### Release Management (.github/workflows/release.yml)

Triggered on: Git tags (`v*`)

**Features:**
- Changelog generation
- Release package creation
- GitHub release creation
- Automated deployment trigger

## Environment Management

### Development Environment

```bash
# Use development configuration
cp environments/development.env .env

# Key settings for development:
# - Reduced keyword limits
# - Debug logging enabled
# - Local Redis/Firebase
# - Relaxed security settings
```

### Production Environment

```bash
# Production configuration managed via GitHub Secrets
# - Full keyword processing (50+)
# - Optimized performance settings
# - Enhanced security
# - Monitoring enabled
```

### Environment Variables

Configure these in GitHub Secrets for production:

```
VM_HOST=134.199.201.56
VM_USER=root
VM_SSH_KEY=<private-key-content>
FIREBASE_SERVICE_KEY=<service-account-json>
REDIS_URL=<upstash-redis-url>
REDIS_TOKEN=<upstash-token>
SURFSHARK_PRIVATE_KEY=<vpn-key>
SURFSHARK_ADDRESS=<vpn-address>
```

## Service Management

### Systemd Services

**Main Services:**
- `youtube-scraper.service` - Core scraping service
- `youtube-analytics.service` - Analytics processing (on-demand)
- `youtube-monitoring.service` - Health monitoring (on-demand)

**Timers:**
- `youtube-analytics.timer` - Analytics every 2 hours
- `youtube-monitoring.timer` - Health checks every 30 minutes

### Service Commands

```bash
# Check service status
sudo systemctl status youtube-scraper
sudo systemctl status youtube-analytics

# View logs
sudo journalctl -u youtube-scraper -f
sudo journalctl -u youtube-analytics --since "1 hour ago"

# Manual operations
sudo systemctl start youtube-scraper
sudo systemctl stop youtube-analytics
sudo systemctl restart youtube-monitoring
```

## Deployment Operations

### Manual Deployment

```bash
# SSH to production server
ssh -i /workspace/droplet1 root@134.199.201.56

# Navigate to deployment directory
cd /opt/youtube_app

# Run deployment script
./deployment/scripts/deploy.sh
```

### Health Checks

```bash
# Run comprehensive health check
./deployment/scripts/health_check.sh

# Check specific components
python3 src/scripts/collectors/run_analytics.py --help
systemctl is-active youtube-scraper
```

### Backup & Rollback

```bash
# Create manual backup
./deployment/scripts/backup.sh full

# List available backups
./deployment/scripts/backup.sh list

# Rollback to previous version
./deployment/scripts/rollback.sh interactive

# Quick rollback to latest backup
./deployment/scripts/rollback.sh latest
```

## Monitoring & Alerting

### Health Monitoring

- **Automated health checks** every 30 minutes
- **Service status monitoring** via systemd
- **Resource usage tracking** (CPU, memory, disk)
- **Application functionality tests**

### Log Management

**Log Locations:**
- `/opt/youtube_app/logs/app.log` - Application logs
- `/opt/youtube_app/logs/error.log` - Error logs
- `/opt/youtube_app/logs/analytics.log` - Analytics logs
- `/opt/youtube_app/logs/deployment.log` - Deployment logs

**Log Rotation:**
- Automatic rotation at 100MB
- 7 backup files retained
- Daily cleanup of old logs

### Performance Monitoring

```bash
# Monitor container resources
python3 monitor_containers.py

# View system performance
top -p $(pgrep -f youtube)
df -h /opt/youtube_app
```

## Security

### Access Control

- **SSH key-based authentication**
- **GitHub branch protection rules**
- **Required code reviews**
- **Automated security scanning**

### Secrets Management

- **GitHub Secrets** for CI/CD variables
- **Environment-based configuration**
- **No hardcoded credentials**
- **Regular credential rotation**

### Container Security

- **Resource limits** (4GB RAM, 2 CPU cores)
- **Security constraints** (no-new-privileges)
- **Network isolation** via VPN
- **Regular security updates**

## Troubleshooting

### Common Issues

**Deployment Failures:**
```bash
# Check deployment logs
tail -f /opt/youtube_app/logs/deployment.log

# Verify GitHub Actions
# Check workflow run in GitHub repository

# Manual rollback if needed
./deployment/scripts/rollback.sh latest
```

**Service Issues:**
```bash
# Check service status
sudo systemctl status youtube-scraper --no-pager -l

# Check application logs
tail -f /opt/youtube_app/logs/error.log

# Restart services
sudo systemctl restart youtube-scraper
```

**Health Check Failures:**
```bash
# Run detailed health check
./deployment/scripts/health_check.sh

# Check specific components
python3 -c "from src.utils.firebase_client_enhanced import FirebaseClient; print('✓ Firebase OK')"
```

### Emergency Procedures

**Complete System Failure:**
1. SSH to server: `ssh -i /workspace/droplet1 root@134.199.201.56`
2. Check system status: `systemctl status`
3. Review logs: `journalctl --since "1 hour ago"`
4. Rollback if needed: `./deployment/scripts/rollback.sh latest`
5. Contact development team if unresolved

**Data Loss Prevention:**
- Daily automated backups
- 30-day backup retention
- Git-based code versioning
- Firebase automatic backups

## Development Best Practices

### Code Quality

- **Pre-commit hooks** enforce code standards
- **Automated testing** prevents regressions
- **Security scanning** identifies vulnerabilities
- **Type checking** improves code reliability

### Git Workflow

```bash
# Feature development
git checkout -b feature/feature-name
# Development and testing
git add . && git commit -m "feat: description"
git push origin feature/feature-name
# Create PR, review, merge to main
# Automatic deployment to production
```

### Testing Strategy

- **Unit tests** for individual components
- **Integration tests** for external services
- **Performance tests** for scalability
- **End-to-end tests** for complete workflows

## Performance Optimization

### Resource Management

- **Container limits** prevent resource exhaustion
- **Memory monitoring** with automatic alerts
- **CPU usage optimization** for 50+ keywords
- **Disk space management** with cleanup automation

### Scaling Considerations

- **Horizontal scaling** via multiple VPN servers
- **Load balancing** across processing tasks
- **Database optimization** for large datasets
- **Caching strategies** for improved performance

## Maintenance

### Regular Tasks

**Weekly:**
- Review deployment logs
- Check backup integrity
- Update dependencies
- Monitor resource usage

**Monthly:**
- Security scan review
- Performance analysis
- Backup cleanup
- Documentation updates

**Quarterly:**
- Infrastructure review
- Security assessment
- Disaster recovery testing
- Capacity planning

This DevOps workflow provides a robust, automated, and maintainable approach to managing the YouTube scraper application at enterprise scale.

## 🎉 **DEPLOYMENT STATUS: COMPLETE (2025-08-03)**

The enhanced DevOps infrastructure has been **successfully deployed and is fully operational** on the production VM (134.199.201.56). All enterprise-grade features are active and monitoring the system:

### ✅ **Active Enterprise Services**
- **Security Scanning**: Weekly automated vulnerability assessments (126 findings tracked)
- **Performance Testing**: Monthly load testing and optimization analysis  
- **Health Monitoring**: 30-minute interval system health verification
- **Analytics Processing**: 2-hour interval data processing and insights generation

### 🛡️ **Enhanced Security Infrastructure**
- **Comprehensive Vulnerability Scanning**: Multi-tool scanning with detailed remediation reports
- **Real-time Threat Detection**: Automated identification of security issues
- **Multi-format Reporting**: JSON, HTML, CSV outputs for security analysis

### 📊 **Performance & Monitoring**
- **Load Testing Framework**: Concurrent user simulation and stress testing
- **Performance Profiling**: Memory, CPU, and execution time analysis
- **Real-time Metrics**: System resource monitoring with automated alerting
- **Comprehensive Dashboards**: HTML reports with real-time system status

### 🚀 **Production Ready**
The system now operates with enterprise-grade reliability, comprehensive monitoring, and automated security scanning. All enhanced DevOps tools are deployed and actively maintaining system health and security posture.