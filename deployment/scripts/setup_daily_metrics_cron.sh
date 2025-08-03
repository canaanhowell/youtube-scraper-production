#!/bin/bash

# Setup daily metrics cron job for YouTube analytics
# Runs daily at 2:00 AM to process previous day's data

echo "Setting up daily YouTube metrics cron job..."

# Create the cron script
cat > /opt/youtube_app/cron_daily_metrics.sh << 'EOF'
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
EOF

# Make it executable
chmod +x /opt/youtube_app/cron_daily_metrics.sh

# Add to crontab (runs at 2:00 AM every day)
# First, get existing crontab
crontab -l > /tmp/current_cron 2>/dev/null || true

# Check if daily metrics job already exists
if grep -q "cron_daily_metrics.sh" /tmp/current_cron; then
    echo "Daily metrics cron job already exists, updating..."
    # Remove old entry
    grep -v "cron_daily_metrics.sh" /tmp/current_cron > /tmp/new_cron || true
else
    cp /tmp/current_cron /tmp/new_cron 2>/dev/null || touch /tmp/new_cron
fi

# Add new cron job
echo "0 2 * * * /opt/youtube_app/cron_daily_metrics.sh" >> /tmp/new_cron

# Install new crontab
crontab /tmp/new_cron
rm /tmp/current_cron /tmp/new_cron

echo "Daily metrics cron job installed successfully!"
echo "Will run daily at 2:00 AM"
echo "Logs will be written to: /opt/youtube_app/logs/daily_metrics.log"

# Create log file if it doesn't exist
touch /opt/youtube_app/logs/daily_metrics.log
chown $(whoami):$(whoami) /opt/youtube_app/logs/daily_metrics.log

# Show current cron jobs
echo ""
echo "Current cron jobs:"
crontab -l