#!/usr/bin/env python3
"""Debug video extraction to see what's happening"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.scripts.youtube_scraper_production import YouTubeScraperProduction

# Load environment
load_env()

# Create scraper instance
scraper = YouTubeScraperProduction()

# Let's manually check the extraction
print("Testing video extraction with 'chatgpt' keyword")
print("Current filter: sp=EgQIARAB (Last hour)")
print("=" * 80)

# Try different filter parameters
filters = {
    "EgQIARAB": "Last hour (current)",
    "EgQIAhAB": "Last hour + Sort by upload date",
    "CAISBAgCEAE": "Sort by upload date + Last hour"
}

for filter_param, description in filters.items():
    print(f"\nTesting filter: sp={filter_param} ({description})")
    print("-" * 40)
    
    # We'll need to run this on the VM since it needs VPN
    break  # Just show what we're testing

print("\nTo test different sort orders, we need to modify the search URL in youtube_scraper_production.py")
print("Current: sp=EgQIARAB")
print("For 'Sort by upload date': sp=CAISBAgCEAE or sp=EgQIAhAB")