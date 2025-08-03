#!/bin/bash
# YouTube Scraper Wrapper with Lock File Protection

LOCKFILE="/var/run/youtube_scraper.lock"
LOGFILE="/opt/youtube_app/logs/wrapper.log"

# Function to log messages
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOGFILE"
}

# Check if lock file exists
if [ -f "$LOCKFILE" ]; then
    # Check if the PID in the lock file is still running
    if [ -r "$LOCKFILE" ]; then
        OLD_PID=$(cat "$LOCKFILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            log "ERROR: Another instance is already running (PID: $OLD_PID)"
            exit 1
        else
            log "WARNING: Stale lock file found, removing it"
            rm -f "$LOCKFILE"
        fi
    fi
fi

# Create lock file with current PID
echo $$ > "$LOCKFILE"
log "Starting YouTube scraper (PID: $$)"

# Ensure lock file is removed on exit
trap 'rm -f "$LOCKFILE"; log "Scraper finished, lock file removed"' EXIT

# Change to project directory
cd /opt/youtube_app || exit 1

# Activate virtual environment
source venv/bin/activate

# Export environment variables
export GOOGLE_SERVICE_KEY_PATH="/opt/youtube_app/ai-tracker-466821-892ecf5150a3.json"
export UPSTASH_REDIS_REST_URL="https://gusc1-capital-mole-32245.upstash.io"
export UPSTASH_REDIS_REST_TOKEN="AX31ASQgMGJjZjA4YzEtYzZkMC00ZmE2LWE0ZDgtYTMzZmEzZThkMmE2NjJlODU4Y2I5ZjMxNDc2NGFkYzM0NDhlODdiOTBiMjA="

# Ensure VPN container is running
if ! docker ps | grep -q youtube-vpn; then
    log "Starting VPN container"
    docker compose up -d
    sleep 15
fi

# Run the scraper
log "Running VPN keyword rotator"
python3 youtube_collection_manager.py

# Log completion
log "Scraper run completed"