#!/usr/bin/env python3
"""Simple test of youtube_app"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

# Load environment
load_env()

# Create scraper
scraper = YouTubeScraperProduction()

# Test a single keyword
print("Testing YouTube App with keyword: 'claude'")
result = scraper.scrape_keyword('claude', max_videos=10)

print(f"\nResults:")
print(f"  Total found: {result.get('total_found', 0)}")
print(f"  New videos: {result.get('new_videos', 0)}")
print(f"  Duplicates: {result.get('duplicates', 0)}")
print(f"  Saved: {result.get('saved_to_firebase', 0)}")
print(f"  Success: {result.get('success', False)}")

if 'error' in result:
    print(f"  Error: {result['error']}")