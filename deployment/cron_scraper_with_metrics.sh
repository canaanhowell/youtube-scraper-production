#!/bin/bash
# YouTube Scraper + Interval Metrics Cron Job

# Set up environment
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export HOME=/root

# Log start
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting YouTube scraper cron job" >> /opt/youtube_app/logs/cron.log

# Change to app directory
cd /opt/youtube_app

# Activate virtual environment and run scraper
source venv/bin/activate
python3 src/scripts/youtube_collection_manager.py >> /opt/youtube_app/logs/cron.log 2>&1

# Log scraper completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] YouTube scraper completed, running interval metrics" >> /opt/youtube_app/logs/cron.log

# Run interval metrics calculation
python3 src/scripts/collectors/run_analytics.py --task interval >> /opt/youtube_app/logs/cron.log 2>&1

# Log completion
echo "[$(date '+%Y-%m-%d %H:%M:%S')] YouTube scraper + interval metrics cron job completed" >> /opt/youtube_app/logs/cron.log