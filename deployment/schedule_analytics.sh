#!/bin/bash
# Cron job wrapper for YouTube analytics
# Add to crontab:
# 0 */2 * * * /opt/youtube_app/schedule_analytics.sh >> /opt/youtube_app/logs/cron_analytics.log 2>&1

set -e

# Change to script directory
cd "$(dirname "$0")"

# Activate virtual environment if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "========================================"
echo "Starting analytics at $(date)"
echo "========================================"

# Run analytics pipeline
python3 run_analytics.py --task all

echo "Analytics completed at $(date)"
echo ""