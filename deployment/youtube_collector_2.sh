#!/bin/bash
# YouTube Collector Instance 2
# Handles second third of keywords with youtube-vpn-2

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/collector_2.log"
mkdir -p "$PROJECT_ROOT/logs"

# Add timestamp to log
echo "========================================" >> "$LOG_FILE"
echo "Starting Collection Instance 2 at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Run collector instance 2
python src/scripts/youtube_collection_manager_simple.py \
    --instance 2 \
    --container-name youtube-vpn-2 \
    >> "$LOG_FILE" 2>&1

# Log completion
echo "Collection Instance 2 completed at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"