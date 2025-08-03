#!/usr/bin/env python3
"""Test YouTube scraper locally without Firebase/Redis dependencies"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_scraper():
    """Test basic YouTube scraping functionality"""
    try:
        from youtube_scraper_production import YouTubeScraperProduction
        
        print("Testing YouTube scraper...")
        
        # Initialize scraper
        scraper = YouTubeScraperProduction(headless=False)  # Show browser for testing
        
        # Test keyword
        keyword = "Python programming"
        print(f"Searching for: {keyword}")
        
        # Scrape YouTube
        results = scraper.search_youtube(keyword)
        
        if results:
            print(f"\n✅ Found {len(results)} videos for '{keyword}'")
            
            # Show first 3 results
            for i, video in enumerate(results[:3], 1):
                print(f"\n{i}. {video.get('title', 'No title')}")
                print(f"   Channel: {video.get('channel', 'Unknown')}")
                print(f"   Views: {video.get('views', 0):,}")
                print(f"   URL: {video.get('url', 'No URL')}")
        else:
            print(f"\n❌ No results found for '{keyword}'")
            
        # Close browser
        scraper.close()
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_basic_scraper()