#!/usr/bin/env python3
"""
Check sizes of collections to merge
"""

import sys
from pathlib import Path

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def main():
    fc = FirebaseClient()
    
    collections_to_check = [
        ('"chatgpt"', 'chatgpt'),
        ('Runway', 'runway'),
        ('leonardo ai', 'leonardo_ai'),
        ('stable diffusion', 'stable_diffusion')
    ]
    
    print("Checking collection sizes...\n")
    
    for from_id, to_id in collections_to_check:
        print(f"{from_id} → {to_id}")
        
        # Check source
        from_ref = fc.db.collection('youtube_videos').document(from_id)
        if from_ref.get().exists:
            from_count = len(list(from_ref.collection('videos').limit(1000).stream()))
            print(f"  Source: {from_count} videos")
        else:
            print(f"  Source: Does not exist")
        
        # Check target
        to_ref = fc.db.collection('youtube_videos').document(to_id)
        if to_ref.get().exists:
            to_count = len(list(to_ref.collection('videos').limit(1000).stream()))
            print(f"  Target: {to_count} videos")
        else:
            print(f"  Target: Does not exist")
        
        print()

if __name__ == "__main__":
    main()