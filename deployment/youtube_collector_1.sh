#!/bin/bash
# YouTube Collector Instance 1
# Handles first third of keywords with youtube-vpn-1

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Log file
LOG_FILE="$PROJECT_ROOT/logs/collector_1.log"
mkdir -p "$PROJECT_ROOT/logs"

# Add timestamp to log
echo "========================================" >> "$LOG_FILE"
echo "Starting Collection Instance 1 at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Activate virtual environment
source venv/bin/activate

# Run collector instance 1
python src/scripts/youtube_collection_manager_simple.py \
    --instance 1 \
    --container-name youtube-vpn-1 \
    >> "$LOG_FILE" 2>&1

# Log completion
echo "Collection Instance 1 completed at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"