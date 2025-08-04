#!/bin/bash

# Fix daily metrics cron job for YouTube analytics
# This ensures the daily metrics runs at 2:00 AM every day

echo "Checking and fixing daily YouTube metrics cron job..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if cron job exists
echo -e "${YELLOW}Checking existing cron jobs...${NC}"
if crontab -l 2>/dev/null | grep -q "cron_daily_metrics.sh"; then
    echo -e "${GREEN}✓ Daily metrics cron job found${NC}"
    echo "Current cron entry:"
    crontab -l | grep "cron_daily_metrics.sh"
else
    echo -e "${RED}✗ Daily metrics cron job NOT found${NC}"
    echo -e "${YELLOW}Setting up daily metrics cron job...${NC}"
    
    # Create the cron script
    cat > /opt/youtube_app/cron_daily_metrics.sh << 'EOF'
#!/bin/bash
# Daily metrics calculation script

# Set up environment
export PATH="/usr/local/bin:/usr/bin:/bin"
cd /opt/youtube_app

# Activate virtual environment
source venv/bin/activate

# Log start time
echo "$(date): Starting daily metrics calculation" >> /opt/youtube_app/logs/daily_metrics.log

# Run the VM-specific daily metrics script
python3 src/analytics/metrics/youtube_daily_metrics_unified_vm.py >> /opt/youtube_app/logs/daily_metrics.log 2>&1

# Log completion
echo "$(date): Daily metrics calculation complete" >> /opt/youtube_app/logs/daily_metrics.log
echo "----------------------------------------" >> /opt/youtube_app/logs/daily_metrics.log
EOF

    # Make it executable
    chmod +x /opt/youtube_app/cron_daily_metrics.sh
    
    # Add to crontab
    # First, get existing crontab
    crontab -l > /tmp/current_cron 2>/dev/null || true
    
    # Add new cron job (runs at 2:00 AM every day)
    echo "0 2 * * * /opt/youtube_app/cron_daily_metrics.sh" >> /tmp/current_cron
    
    # Install new crontab
    crontab /tmp/current_cron
    rm /tmp/current_cron
    
    echo -e "${GREEN}✓ Daily metrics cron job installed successfully!${NC}"
fi

# Create log file if it doesn't exist
if [ ! -f /opt/youtube_app/logs/daily_metrics.log ]; then
    touch /opt/youtube_app/logs/daily_metrics.log
    chown $(whoami):$(whoami) /opt/youtube_app/logs/daily_metrics.log
    echo -e "${GREEN}✓ Created daily metrics log file${NC}"
fi

# Check if we should run it now (if it's after 2 AM and hasn't run today)
CURRENT_HOUR=$(date +%H)
LAST_RUN=$(grep "Starting daily metrics calculation" /opt/youtube_app/logs/daily_metrics.log 2>/dev/null | tail -1 | cut -d' ' -f1-3)
TODAY=$(date +"%a %b %d")

if [ "$CURRENT_HOUR" -ge "02" ] && [[ "$LAST_RUN" != *"$TODAY"* ]]; then
    echo -e "${YELLOW}It's past 2 AM and daily metrics hasn't run today. Running now...${NC}"
    /opt/youtube_app/cron_daily_metrics.sh
    echo -e "${GREEN}✓ Daily metrics calculation completed${NC}"
fi

# Show status
echo ""
echo -e "${GREEN}Current Setup:${NC}"
echo "- Cron job: Runs daily at 2:00 AM"
echo "- Script: /opt/youtube_app/cron_daily_metrics.sh"
echo "- Logs: /opt/youtube_app/logs/daily_metrics.log"
echo ""
echo -e "${YELLOW}Next scheduled run:${NC}"
# Calculate next 2 AM
if [ "$CURRENT_HOUR" -lt "02" ]; then
    echo "Today at 2:00 AM"
else
    echo "Tomorrow at 2:00 AM"
fi

# Show last few runs
echo ""
echo -e "${YELLOW}Recent runs:${NC}"
grep "Starting daily metrics calculation" /opt/youtube_app/logs/daily_metrics.log 2>/dev/null | tail -5 || echo "No previous runs found"

echo ""
echo -e "${GREEN}✓ Daily metrics cron job check complete!${NC}"