#!/bin/bash
# Setup production cron job for YouTube scraper

# Create cron script
cat > /opt/youtube_app/cron_scraper.sh << 'EOF'
#!/bin/bash
# YouTube Scraper Cron Job with Interval Metrics

# Set up environment
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting YouTube scraper cron job" >> /opt/youtube_app/logs/cron.log

# Change to app directory
cd /opt/youtube_app

# Activate virtual environment and run scraper
source venv/bin/activate
python src/scripts/youtube_collection_manager.py >> /opt/youtube_app/logs/cron.log 2>&1

# Run interval metrics immediately after scraper
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting interval metrics calculation" >> /opt/youtube_app/logs/cron.log
python src/analytics/metrics/youtube_keywords_interval_metrics.py >> /opt/youtube_app/logs/cron.log 2>&1

# Log completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] YouTube scraper and interval metrics completed" >> /opt/youtube_app/logs/cron.log
EOF

# Make script executable
chmod +x /opt/youtube_app/cron_scraper.sh

# Add to crontab (runs every 10 minutes)
(crontab -l 2>/dev/null | grep -v "cron_scraper.sh"; echo "*/10 * * * * /opt/youtube_app/cron_scraper.sh") | crontab -

# Show current crontab
echo "Cron job installed. Current crontab:"
crontab -l

# Create log file if it doesn't exist
touch /opt/youtube_app/logs/cron.log
chmod 644 /opt/youtube_app/logs/cron.log

echo "YouTube scraper will run every 10 minutes"
echo "Logs: /opt/youtube_app/logs/cron.log"