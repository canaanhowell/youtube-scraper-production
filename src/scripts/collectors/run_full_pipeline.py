#!/usr/bin/env python3
"""
Run the complete YouTube data pipeline: scraping + analytics.

This script runs the full pipeline including:
1. YouTube video scraping (with VPN rotation)
2. Analytics processing (metrics, aggregation, snapshots)
"""

import sys
import os
import subprocess
import logging
import time
from datetime import datetime
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_scraping():
    """Run the YouTube scraping process."""
    logger.info("Starting YouTube scraping...")
    start_time = time.time()
    
    try:
        # Run the collection manager
        result = subprocess.run(
            [sys.executable, 'youtube_collection_manager.py'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            duration = time.time() - start_time
            logger.info(f"✓ Scraping completed successfully in {duration:.1f} seconds")
            return True
        else:
            logger.error(f"Scraping failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run scraping: {e}", exc_info=True)
        return False


def run_analytics():
    """Run the analytics pipeline."""
    logger.info("Starting analytics processing...")
    start_time = time.time()
    
    try:
        # Run the analytics pipeline
        result = subprocess.run(
            [sys.executable, 'run_analytics.py', '--task', 'all'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        if result.returncode == 0:
            duration = time.time() - start_time
            logger.info(f"✓ Analytics completed successfully in {duration:.1f} seconds")
            return True
        else:
            logger.error(f"Analytics failed with code {result.returncode}")
            logger.error(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to run analytics: {e}", exc_info=True)
        return False


def main():
    """Run the complete pipeline."""
    logger.info("="*60)
    logger.info(f"Starting full YouTube pipeline at {datetime.now()}")
    logger.info("="*60)
    
    # Ensure logs directory exists
    Path('logs').mkdir(exist_ok=True)
    
    pipeline_start = time.time()
    
    # Step 1: Run scraping
    scraping_success = run_scraping()
    
    if not scraping_success:
        logger.error("Scraping failed, skipping analytics")
        return 1
    
    # Optional: Add a delay between scraping and analytics
    logger.info("Waiting 30 seconds before running analytics...")
    time.sleep(30)
    
    # Step 2: Run analytics
    analytics_success = run_analytics()
    
    # Summary
    total_duration = time.time() - pipeline_start
    logger.info("="*60)
    logger.info("Pipeline Summary:")
    logger.info(f"- Scraping: {'✓ Success' if scraping_success else '✗ Failed'}")
    logger.info(f"- Analytics: {'✓ Success' if analytics_success else '✗ Failed'}")
    logger.info(f"- Total duration: {total_duration/60:.1f} minutes")
    logger.info("="*60)
    
    return 0 if (scraping_success and analytics_success) else 1


if __name__ == '__main__':
    sys.exit(main())