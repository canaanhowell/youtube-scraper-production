#!/bin/bash

# Manual script to run daily metrics immediately
# Useful for testing or catching up on missed runs

echo "Manual YouTube Daily Metrics Runner"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if we're on the VM
if [ ! -d "/opt/youtube_app" ]; then
    echo -e "${RED}Error: This script must be run on the production VM${NC}"
    echo "Directory /opt/youtube_app not found"
    exit 1
fi

# Navigate to project directory
cd /opt/youtube_app

# Check for virtual environment
if [ ! -d "venv" ]; then
    echo -e "${RED}Error: Virtual environment not found${NC}"
    exit 1
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if the daily metrics script exists
if [ ! -f "src/analytics/metrics/youtube_daily_metrics_unified_vm.py" ]; then
    echo -e "${RED}Error: Daily metrics script not found${NC}"
    echo "Expected at: src/analytics/metrics/youtube_daily_metrics_unified_vm.py"
    exit 1
fi

# Run the daily metrics
echo -e "${YELLOW}Running daily metrics calculation...${NC}"
echo ""

# Create logs directory if it doesn't exist
mkdir -p logs

# Run with proper logging
python3 src/analytics/metrics/youtube_daily_metrics_unified_vm.py 2>&1 | tee -a logs/daily_metrics_manual.log

# Check exit status
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Daily metrics calculation completed successfully!${NC}"
    
    # Also append to the main daily metrics log
    echo "$(date): Manual run completed successfully" >> logs/daily_metrics.log
else
    echo ""
    echo -e "${RED}✗ Daily metrics calculation failed${NC}"
    echo "Check logs/daily_metrics_manual.log for details"
    exit 1
fi

# Show summary
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "- Log file: /opt/youtube_app/logs/daily_metrics_manual.log"
echo "- Main log: /opt/youtube_app/logs/daily_metrics.log"
echo ""

# Optionally check Firebase for recent updates
echo -e "${YELLOW}To verify the updates in Firebase:${NC}"
echo "1. Check youtube_keywords collection for updated daily_metrics"
echo "2. Check youtube_categories collection for updated daily snapshots"