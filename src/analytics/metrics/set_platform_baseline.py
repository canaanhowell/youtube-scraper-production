#!/usr/bin/env python3
"""
Set hardcoded platform baseline for YouTube in platform_metrics collection.
Simple script to manually set the baseline value directly in Firestore.
"""

import os
import sys
from datetime import datetime, timezone

# Add parent directories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

# Import environment loader and Firebase client
from src.utils.env_loader import load_env
load_env()

from src.utils.firebase_client import FirebaseClient

def set_youtube_baseline(baseline_value: float = 150.0):
    """Set hardcoded baseline for YouTube platform."""
    
    fb_client = FirebaseClient()
    
    # Simple platform baseline document
    platform_doc = {
        'platform': 'youtube',
        'daily_baseline': baseline_value,
        'last_updated': datetime.now(timezone.utc),
        'method': 'hardcoded',
        'notes': 'Manually set baseline based on platform observation'
    }
    
    # Update platform_metrics document
    doc_ref = fb_client.db.collection('platform_metrics').document('youtube')
    doc_ref.set(platform_doc)
    
    print(f"✅ Set YouTube platform baseline to {baseline_value} videos/day")
    print(f"   Document: platform_metrics/youtube")
    print(f"   Updated: {platform_doc['last_updated']}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Set hardcoded YouTube platform baseline')
    parser.add_argument('--baseline', type=float, default=150.0,
                        help='Baseline value in videos/day (default: 150.0)')
    
    args = parser.parse_args()
    set_youtube_baseline(args.baseline)