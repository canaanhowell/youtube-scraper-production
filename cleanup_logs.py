#!/usr/bin/env python3
"""
Log Cleanup Script for YouTube Scraper
Removes empty and old timestamped log files
"""

import sys
from pathlib import Path

# Add project path to sys.path
sys.path.append(str(Path(__file__).parent))

from src.utils.logging_config_enhanced import cleanup_old_log_files

if __name__ == "__main__":
    print("Starting log cleanup...")
    cleanup_old_log_files(
        log_dir="/opt/youtube_scraper/logs",
        days_old=7
    )
    print("Log cleanup completed.")