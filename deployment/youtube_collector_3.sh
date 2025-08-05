#!/bin/bash
# YouTube Collector Instance 3
# Handles last third of keywords with youtube-vpn-3

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/collector_3.log"
mkdir -p "$PROJECT_ROOT/logs"

# Add timestamp to log
echo "========================================" >> "$LOG_FILE"
echo "Starting Collection Instance 3 at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Run collector instance 3
python src/scripts/youtube_collection_manager_simple.py \
    --instance 3 \
    --container-name youtube-vpn-3 \
    >> "$LOG_FILE" 2>&1

# Log completion
echo "Collection Instance 3 completed at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"