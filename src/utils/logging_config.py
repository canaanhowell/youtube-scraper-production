import logging
import os
from datetime import datetime
from pathlib import Path

def setup_logging():
    """Set up logging configuration for YouTube scraper"""
    
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    
    # Generate log filenames with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Configure main logger
    logger = logging.getLogger('youtube_scraper')
    logger.setLevel(logging.DEBUG)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler for all logs
    file_handler = logging.FileHandler(log_dir / f'youtube_scraper_{timestamp}.log')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Error file handler
    error_handler = logging.FileHandler(log_dir / 'error.log')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)
    
    # Network logger for HTTP requests
    network_logger = logging.getLogger('youtube_scraper.network')
    network_handler = logging.FileHandler(log_dir / 'network.log')
    network_handler.setLevel(logging.DEBUG)
    network_handler.setFormatter(file_format)
    network_logger.addHandler(network_handler)
    
    return logger, network_logger