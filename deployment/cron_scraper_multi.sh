#!/bin/bash
# YouTube Multi-Instance Collection Wrapper
# Runs 3 collection instances in parallel, then interval metrics
# NOTE: This script is deprecated - use individual cron entries instead

set -e

# Script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Main log file
LOG_FILE="$PROJECT_ROOT/logs/cron_multi.log"
mkdir -p "$PROJECT_ROOT/logs"

# Add timestamp to log
echo "========================================" >> "$LOG_FILE"
echo "Starting Multi-Instance Collection at $(date)" >> "$LOG_FILE"
echo "========================================" >> "$LOG_FILE"

# Change to project directory
cd "$PROJECT_ROOT"

# Start all 3 collectors in parallel
echo "Launching 3 collection instances in parallel..." >> "$LOG_FILE"

# Launch collectors in background
"$SCRIPT_DIR/youtube_collector_1.sh" &
PID1=$!
echo "Instance 1 started with PID $PID1" >> "$LOG_FILE"

"$SCRIPT_DIR/youtube_collector_2.sh" &
PID2=$!
echo "Instance 2 started with PID $PID2" >> "$LOG_FILE"

"$SCRIPT_DIR/youtube_collector_3.sh" &
PID3=$!
echo "Instance 3 started with PID $PID3" >> "$LOG_FILE"

# Wait for all collectors to finish
echo "All instances started. Waiting for completion..." >> "$LOG_FILE"
wait $PID1
STATUS1=$?
wait $PID2
STATUS2=$?
wait $PID3
STATUS3=$?

echo "Collection instances completed with statuses: $STATUS1, $STATUS2, $STATUS3" >> "$LOG_FILE"

# Run interval metrics after collection
echo "Running interval metrics calculation..." >> "$LOG_FILE"
source venv/bin/activate
python src/analytics/metrics/youtube_keywords_interval_metrics.py >> "$LOG_FILE" 2>&1

echo "Multi-instance collection completed at $(date)" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"