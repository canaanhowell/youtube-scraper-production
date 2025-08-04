#!/usr/bin/env python3
"""
Test script for YouTube pagination functionality
Tests both with and without pagination enabled
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.env_loader import load_env
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/workspace/youtube_app/logs/pagination_test.log')
    ]
)
logger = logging.getLogger(__name__)

def test_pagination():
    """Test pagination functionality"""
    
    # Load environment
    load_env()
    
    # Test keywords
    test_keywords = ["claude", "chatgpt"]
    
    logger.info("=== YouTube Pagination Test ===")
    
    for keyword in test_keywords:
        logger.info(f"\n--- Testing keyword: {keyword} ---")
        
        # Test without pagination
        logger.info("1. Testing WITHOUT pagination (traditional method)")
        os.environ['YOUTUBE_ENABLE_PAGINATION'] = 'false'
        scraper_no_pagination = YouTubeScraperProduction()
        
        start_time = time.time()
        result_no_pagination = scraper_no_pagination.scrape_keyword(keyword, max_videos=50)
        no_pagination_duration = time.time() - start_time
        
        no_pagination_count = result_no_pagination.get('saved_to_firebase', 0)
        logger.info(f"   Without pagination: {no_pagination_count} videos in {no_pagination_duration:.1f}s")
        
        # Test with pagination
        logger.info("2. Testing WITH pagination (scroll method)")
        os.environ['YOUTUBE_ENABLE_PAGINATION'] = 'true'
        os.environ['YOUTUBE_MAX_SCROLL_ATTEMPTS'] = '5'  # Limit for testing
        scraper_with_pagination = YouTubeScraperProduction()
        
        start_time = time.time()
        result_with_pagination = scraper_with_pagination.scrape_keyword(keyword, max_videos=50)
        pagination_duration = time.time() - start_time
        
        pagination_count = result_with_pagination.get('saved_to_firebase', 0)
        logger.info(f"   With pagination: {pagination_count} videos in {pagination_duration:.1f}s")
        
        # Compare results
        improvement = pagination_count - no_pagination_count
        percentage_improvement = (improvement / max(no_pagination_count, 1)) * 100
        
        logger.info(f"   Improvement: +{improvement} videos ({percentage_improvement:.1f}%)")
        
        # Wait between keywords
        if keyword != test_keywords[-1]:
            logger.info("   Waiting 30s before next test...")
            time.sleep(30)
    
    logger.info("\n=== Test Complete ===")

if __name__ == "__main__":
    test_pagination()