#!/bin/bash
# Daily metrics calculation script

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
cd /opt/youtube_app

# Activate virtual environment
source venv/bin/activate

# Run daily metrics for yesterday
echo "$(date): Starting daily metrics calculation" >> /opt/youtube_app/logs/daily_metrics.log
python3 src/analytics/metrics/youtube_daily_metrics_unified_vm.py >> /opt/youtube_app/logs/daily_metrics.log 2>&1
echo "$(date): Daily metrics calculation complete" >> /opt/youtube_app/logs/daily_metrics.log
echo "----------------------------------------" >> /opt/youtube_app/logs/daily_metrics.log