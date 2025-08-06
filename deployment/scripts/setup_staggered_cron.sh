#!/bin/bash
# Setup staggered cron jobs for YouTube multi-instance scraper
# Each instance runs on a different schedule to spread the load

echo "Setting up staggered cron jobs for YouTube scrapers..."

# Remove any existing YouTube scraper cron jobs
echo "Removing any existing YouTube scraper cron jobs..."
(crontab -l 2>/dev/null | grep -v "youtube_collector" | grep -v "cron_scraper" | grep -v "interval_metrics") | crontab -

# Add staggered cron jobs for each instance
echo "Adding staggered cron jobs..."

# Get current crontab
CURRENT_CRON=$(crontab -l 2>/dev/null || echo "")

# Add new staggered entries
# Instance 1: Runs at :00, :10, :20, :30, :40, :50
# Instance 2: Runs at :03, :13, :23, :33, :43, :53  
# Instance 3: Runs at :06, :16, :26, :36, :46, :56
# Interval metrics: Runs at :09, :19, :29, :39, :49, :59

NEW_CRON="$CURRENT_CRON
# YouTube Scraper - Staggered Multi-Instance Collection
# Instance 1 - Every 10 minutes at :00
0,10,20,30,40,50 * * * * /opt/youtube_app/deployment/youtube_collector_1.sh >> /opt/youtube_app/logs/cron_instance_1.log 2>&1

# Instance 2 - Every 10 minutes at :03 (3 minute offset)
3,13,23,33,43,53 * * * * /opt/youtube_app/deployment/youtube_collector_2.sh >> /opt/youtube_app/logs/cron_instance_2.log 2>&1

# Instance 3 - Every 10 minutes at :06 (6 minute offset)  
6,16,26,36,46,56 * * * * /opt/youtube_app/deployment/youtube_collector_3.sh >> /opt/youtube_app/logs/cron_instance_3.log 2>&1

# Interval Metrics - Every 10 minutes at :09 (after all instances complete)
9,19,29,39,49,59 * * * * cd /opt/youtube_app && source venv/bin/activate && python src/analytics/metrics/youtube_keywords_interval_metrics.py >> /opt/youtube_app/logs/interval_metrics_cron.log 2>&1"

# Install the new crontab
echo "$NEW_CRON" | crontab -

# Show current crontab
echo ""
echo "✅ Staggered cron jobs installed!"
echo ""
echo "Current crontab:"
crontab -l | grep -A 20 "YouTube Scraper"

# Make sure all scripts are executable
chmod +x /opt/youtube_app/deployment/youtube_collector_1.sh
chmod +x /opt/youtube_app/deployment/youtube_collector_2.sh
chmod +x /opt/youtube_app/deployment/youtube_collector_3.sh

# Create log files if they don't exist
mkdir -p /opt/youtube_app/logs
touch /opt/youtube_app/logs/cron_instance_1.log
touch /opt/youtube_app/logs/cron_instance_2.log
touch /opt/youtube_app/logs/cron_instance_3.log
touch /opt/youtube_app/logs/interval_metrics_cron.log
chmod 644 /opt/youtube_app/logs/*.log

echo ""
echo "📅 Schedule Summary:"
echo "  Every 10 minutes:"
echo "    - :00 - Instance 1 starts (youtube-vpn-1)"
echo "    - :03 - Instance 2 starts (youtube-vpn-2)"  
echo "    - :06 - Instance 3 starts (youtube-vpn-3)"
echo "    - :09 - Interval metrics calculation"
echo ""
echo "📁 Log Files:"
echo "  - Instance 1: /opt/youtube_app/logs/cron_instance_1.log"
echo "  - Instance 2: /opt/youtube_app/logs/cron_instance_2.log"
echo "  - Instance 3: /opt/youtube_app/logs/cron_instance_3.log"
echo "  - Metrics: /opt/youtube_app/logs/interval_metrics_cron.log"
echo ""
echo "This spreads the load across 9 minutes instead of running all at once."