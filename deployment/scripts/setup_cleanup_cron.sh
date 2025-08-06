#!/bin/bash
# Setup weekly cleanup cron job for old YouTube collection logs

echo "Setting up weekly cleanup cron job for YouTube collection logs..."

# Add cleanup job to crontab
# Runs every Sunday at 3 AM UTC
CLEANUP_CRON="0 3 * * 0 cd /opt/youtube_app && source venv/bin/activate && python cleanup_old_logs_auto.py >> /opt/youtube_app/logs/cleanup_cron.log 2>&1"

# Check if cleanup job already exists
if crontab -l 2>/dev/null | grep -q "cleanup_old_logs_auto.py"; then
    echo "Cleanup cron job already exists. Updating..."
    # Remove old cleanup job
    (crontab -l 2>/dev/null | grep -v "cleanup_old_logs_auto.py") | crontab -
fi

# Add new cleanup job
(crontab -l 2>/dev/null; echo ""; echo "# Weekly cleanup of old YouTube collection logs (>5 days)"; echo "$CLEANUP_CRON") | crontab -

# Create log file
touch /opt/youtube_app/logs/cleanup_cron.log
chmod 644 /opt/youtube_app/logs/cleanup_cron.log

# Make cleanup scripts executable
chmod +x /opt/youtube_app/cleanup_old_collection_logs.py
chmod +x /opt/youtube_app/cleanup_old_logs_auto.py

echo ""
echo "✅ Cleanup cron job configured!"
echo ""
echo "Schedule: Every Sunday at 3:00 AM UTC"
echo "Log file: /opt/youtube_app/logs/cleanup_cron.log"
echo ""
echo "The cleanup will:"
echo "  - Remove youtube_collection_logs older than 5 days"
echo "  - Log cleanup statistics to youtube_maintenance_logs"
echo "  - Help maintain database performance"
echo ""
echo "To run cleanup manually:"
echo "  cd /opt/youtube_app"
echo "  python cleanup_old_collection_logs.py    # Interactive version"
echo "  python cleanup_old_logs_auto.py          # Automated version"

# Show current crontab
echo ""
echo "Current crontab:"
crontab -l | tail -20