#!/usr/bin/env python3
"""Test script to verify we can see video timestamps"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

# Load environment
load_env()

# Create scraper
scraper = YouTubeScraperProduction()

# Test with a keyword
keyword = 'ai news'
print(f"Testing YouTube scraper with keyword: '{keyword}'")
print("Looking for published timestamps...\n")

# Get the search URL
search_url = f'https://www.youtube.com/results?search_query={keyword.replace(" ", "+")}&sp=EgQIARAB'
print(f"Search URL: {search_url}")
print("(sp=EgQIARAB = Last hour filter)\n")

# Fetch the page
html_content = scraper._fetch_youtube_page(search_url)

if html_content:
    # Extract videos
    videos, filtered_count = scraper._extract_videos_from_initial_data(html_content, keyword)
    
    print(f"Found {len(videos)} videos")
    print(f"Filtered out {filtered_count} videos\n")
    
    # Show first 5 videos with timestamps
    print("First 5 videos with timestamps:")
    print("-" * 80)
    
    for i, video in enumerate(videos[:5]):
        print(f"\n{i+1}. {video['title']}")
        print(f"   Published: {video.get('published_time', 'No timestamp')}")
        print(f"   Views: {video.get('view_count', 'No views')}")
        print(f"   Channel: {video.get('channel_name', 'Unknown')}")
        print(f"   URL: {video['url']}")
else:
    print("Failed to fetch page content")