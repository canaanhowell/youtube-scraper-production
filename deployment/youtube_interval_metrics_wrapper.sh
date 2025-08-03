#\!/bin/bash
# YouTube interval metrics collection wrapper script
# Runs after hourly YouTube collection to calculate metrics

LOG_FILE="/opt/youtube_app/logs/interval_metrics.log"
LOCK_FILE="/opt/youtube_app/interval_metrics.lock"
SCRIPT_DIR="/opt/youtube_app"

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log messages
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Check if lock file exists (prevents concurrent runs)
if [ -f "$LOCK_FILE" ]; then
    log "ERROR: Interval metrics collection already running (lock file exists)"
    exit 1
fi

# Create lock file
echo $$ > "$LOCK_FILE"

# Cleanup function
cleanup() {
    rm -f "$LOCK_FILE"
}
trap cleanup EXIT

log "Starting YouTube interval metrics collection"

# Change to script directory
cd "$SCRIPT_DIR" || exit 1

# Activate virtual environment
source venv/bin/activate

# Run the interval metrics script
python3 youtube_keywords_interval_metrics.py >> "$LOG_FILE" 2>&1

if [ $? -eq 0 ]; then
    log "Interval metrics collection completed successfully"
else
    log "ERROR: Interval metrics collection failed"
fi

log "Interval metrics wrapper script finished"
log "----------------------------------------"
