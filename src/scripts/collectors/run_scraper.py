#\!/usr/bin/env python3
import sys
import argparse
import logging
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.scripts.youtube_scraper_production import YouTubeScraperProduction

def main():
    parser = argparse.ArgumentParser(description='Run YouTube scraper for a keyword')
    parser.add_argument('--keyword', required=True, help='Keyword to search')
    parser.add_argument('--max-videos', type=int, default=1000, help='Maximum videos to collect')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Create scraper and run
    scraper = YouTubeScraperProduction()
    result = scraper.scrape_keyword(args.keyword, args.max_videos)
    
    # Return success/failure based on saved count
    if result.get('success', False):
        print(f"Successfully saved {result['saved_to_firebase']} videos for '{args.keyword}'")
        sys.exit(0)
    else:
        print(f"Failed to save videos for '{args.keyword}': {result.get('error', 'Unknown error')}")
        sys.exit(1)

if __name__ == "__main__":
    main()
