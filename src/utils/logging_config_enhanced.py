#!/usr/bin/env python3
"""
Enhanced Logging Configuration for YouTube Scraper
Implements proper log rotation and consistent file naming
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple

def get_default_log_dir():
    """Get the appropriate log directory based on environment"""
    # Check if running on production VM
    if Path("/opt/youtube_scraper").exists():
        return "/opt/youtube_scraper/logs"
    # Use local directory for development
    else:
        return str(Path.cwd() / "logs")

def setup_logging(
    log_level: str = "INFO",
    log_dir: str = None,
    max_bytes: int = 100 * 1024 * 1024,  # 100MB
    backup_count: int = 7,  # Keep 7 rotated files
    console_output: bool = True
) -> Tuple[logging.Logger, logging.Logger]:
    """
    Set up enhanced logging configuration with rotation
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_dir: Directory for log files (None to use default)
        max_bytes: Maximum size per log file before rotation
        backup_count: Number of rotated files to keep
        console_output: Whether to output to console
    
    Returns:
        Tuple of (main_logger, network_logger)
    """
    
    # Use default log directory if not specified
    if log_dir is None:
        log_dir = get_default_log_dir()
    
    # Create logs directory if it doesn't exist
    log_dir = Path(log_dir)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Convert log level string to logging constant
    log_level_const = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Configure root logger to prevent interference
    logging.getLogger().handlers.clear()
    
    # Main application logger
    main_logger = logging.getLogger('youtube_scraper')
    main_logger.setLevel(log_level_const)
    main_logger.handlers.clear()  # Clear any existing handlers
    
    # Console handler (optional)
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level_const)
        console_handler.setFormatter(simple_formatter)
        main_logger.addHandler(console_handler)
    
    # Main log file with rotation
    main_file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'scraper.log',
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    main_file_handler.setLevel(log_level_const)
    main_file_handler.setFormatter(detailed_formatter)
    main_logger.addHandler(main_file_handler)
    
    # Error-only log file with rotation
    error_file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'error.log',
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(detailed_formatter)
    main_logger.addHandler(error_file_handler)
    
    # Network logger for HTTP/API requests
    network_logger = logging.getLogger('network')
    network_logger.setLevel(log_level_const)
    network_logger.handlers.clear()  # Clear any existing handlers
    network_logger.propagate = False  # Don't propagate to root logger
    
    # Network log file with rotation
    network_file_handler = logging.handlers.RotatingFileHandler(
        log_dir / 'network.log',
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    network_file_handler.setLevel(log_level_const)
    network_file_handler.setFormatter(detailed_formatter)
    network_logger.addHandler(network_file_handler)
    
    # Also send network logs to console if enabled
    if console_output:
        network_console_handler = logging.StreamHandler(sys.stdout)
        network_console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        network_console_handler.setFormatter(simple_formatter)
        network_logger.addHandler(network_console_handler)
    
    # Log the logging configuration
    main_logger.info(f"Enhanced logging configured - Level: {log_level}, Dir: {log_dir}")
    main_logger.info(f"Log rotation: {max_bytes//1024//1024}MB max, {backup_count} backups")
    
    return main_logger, network_logger


def setup_basic_logging() -> logging.Logger:
    """
    Set up basic logging for simple scripts
    Uses the enhanced logging but with simpler configuration
    """
    main_logger, _ = setup_logging(
        log_level="INFO",
        log_dir=None,  # Use default based on environment
        console_output=True,
        max_bytes=50 * 1024 * 1024,  # 50MB
        backup_count=3
    )
    return main_logger


def cleanup_old_log_files(log_dir: str = None, days_old: int = 7):
    """
    Clean up old timestamped log files and empty log files
    
    Args:
        log_dir: Directory containing log files (None to use default)
        days_old: Remove files older than this many days
    """
    import time
    
    if log_dir is None:
        log_dir = get_default_log_dir()
    
    log_dir = Path(log_dir)
    if not log_dir.exists():
        return
    
    current_time = time.time()
    cutoff_time = current_time - (days_old * 24 * 60 * 60)
    
    removed_count = 0
    
    for log_file in log_dir.glob("*.log"):
        try:
            # Remove empty files
            if log_file.stat().st_size == 0:
                log_file.unlink()
                removed_count += 1
                continue
            
            # Remove old timestamped files (youtube_scraper_YYYYMMDD_HHMMSS.log pattern)
            if log_file.name.startswith("youtube_scraper_") and len(log_file.name) > 30:
                if log_file.stat().st_mtime < cutoff_time:
                    log_file.unlink()
                    removed_count += 1
                    
        except Exception as e:
            print(f"Error removing {log_file}: {e}")
    
    if removed_count > 0:
        print(f"Cleaned up {removed_count} old/empty log files")


if __name__ == "__main__":
    # Test the enhanced logging configuration
    print("Testing enhanced logging configuration...")
    
    # Test basic setup
    logger, network_logger = setup_logging(log_level="DEBUG", log_dir=None, console_output=True)
    
    # Test logging at different levels
    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    
    # Test network logger
    network_logger.info("Network request to example.com")
    network_logger.warning("Network timeout detected")
    
    print("✅ Enhanced logging test completed")
    print(f"📁 Check {get_default_log_dir()} for log files")
    
    # Test cleanup
    print("\nTesting log cleanup...")
    cleanup_old_log_files()
    print("✅ Log cleanup test completed")