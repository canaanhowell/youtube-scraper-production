#!/bin/bash
# Setup production cron job for YouTube multi-instance scraper with staggered timing

echo "Setting up staggered multi-instance YouTube scraper cron job..."

# Remove any existing YouTube scraper cron jobs
echo "Removing any existing YouTube scraper cron jobs..."
(crontab -l 2>/dev/null | grep -v "cron_scraper.sh" | grep -v "cron_scraper_multi.sh" | grep -v "youtube_collector") | crontab -

# Add the new multi-instance cron job (runs every 10 minutes)
echo "Adding staggered multi-instance cron job (every 10 minutes)..."
(crontab -l 2>/dev/null; echo "*/10 * * * * /opt/youtube_app/deployment/cron_scraper_multi.sh") | crontab -

# Show current crontab
echo "Cron job installed. Current crontab:"
crontab -l

# Make sure the multi script is executable
chmod +x /opt/youtube_app/deployment/cron_scraper_multi.sh
chmod +x /opt/youtube_app/deployment/youtube_collector_1.sh
chmod +x /opt/youtube_app/deployment/youtube_collector_2.sh
chmod +x /opt/youtube_app/deployment/youtube_collector_3.sh

# Create log directory if it doesn't exist
mkdir -p /opt/youtube_app/logs
touch /opt/youtube_app/logs/cron_multi.log
chmod 644 /opt/youtube_app/logs/cron_multi.log

echo ""
echo "✅ Staggered multi-instance YouTube scraper cron job configured!"
echo ""
echo "Schedule: Every 10 minutes"
echo "Staggered timing:"
echo "  - Instance 1: Starts immediately"
echo "  - Instance 2: Starts 2 minutes later"  
echo "  - Instance 3: Starts 4 minutes later"
echo ""
echo "Logs:"
echo "  - Multi-instance log: /opt/youtube_app/logs/cron_multi.log"
echo "  - Individual logs: /opt/youtube_app/logs/collector_*.log"
echo ""
echo "This approach reduces server load by spreading out the three instances over 4 minutes"
echo "instead of starting all simultaneously."