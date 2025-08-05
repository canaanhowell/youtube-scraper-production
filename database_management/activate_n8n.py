#!/usr/bin/env python3
"""
Activate n8n keyword in youtube_keywords collection.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment variables
from src.utils.env_loader import load_env
load_env()

from src.utils.firebase_client import FirebaseClient
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def activate_n8n():
    """Activate n8n keyword in youtube_keywords."""
    
    firebase_client = FirebaseClient()
    
    print("\n" + "="*80)
    print("ACTIVATING N8N KEYWORD")
    print("="*80)
    
    # Get the n8n document
    doc_ref = firebase_client.db.collection('youtube_keywords').document('n8n')
    doc = doc_ref.get()
    
    if not doc.exists:
        print("❌ n8n keyword not found in youtube_keywords!")
        return
    
    doc_data = doc.to_dict()
    current_status = doc_data.get('active', False)
    
    print(f"Current status: {'ACTIVE' if current_status else 'inactive'}")
    
    if current_status:
        print("✅ n8n is already active!")
    else:
        # Update to active
        try:
            doc_ref.update({
                'active': True,
                'updated_at': datetime.now()
            })
            print("✅ Successfully activated n8n")
        except Exception as e:
            print(f"❌ Failed to activate n8n: {e}")
            return
    
    # Verify all automation keywords
    print("\n" + "="*80)
    print("VERIFYING ALL AUTOMATION KEYWORDS")
    print("="*80)
    
    automation_keywords = ['make.com', 'zapier', 'n8n']
    
    for keyword in automation_keywords:
        doc = firebase_client.db.collection('youtube_keywords').document(keyword).get()
        if doc.exists:
            data = doc.to_dict()
            active = data.get('active', False)
            status = "ACTIVE" if active else "inactive"
            print(f"  - {keyword}: {status}")
        else:
            print(f"  - {keyword}: NOT FOUND")
    
    # Show summary of all active keywords
    print("\n" + "="*80)
    print("SUMMARY OF ALL YOUTUBE KEYWORDS")
    print("="*80)
    
    all_docs = firebase_client.db.collection('youtube_keywords').stream()
    active_count = 0
    total_count = 0
    
    by_category = {}
    
    for doc in all_docs:
        data = doc.to_dict()
        keyword = data.get('keyword', doc.id)
        category = data.get('category', 'unknown')
        active = data.get('active', False)
        
        total_count += 1
        if active:
            active_count += 1
        
        if category not in by_category:
            by_category[category] = {'active': 0, 'total': 0}
        
        by_category[category]['total'] += 1
        if active:
            by_category[category]['active'] += 1
    
    print(f"\nTotal keywords: {total_count}")
    print(f"Active keywords: {active_count}")
    print(f"Inactive keywords: {total_count - active_count}")
    
    print("\nBy category:")
    for category in sorted(by_category.keys()):
        stats = by_category[category]
        print(f"  - {category}: {stats['active']}/{stats['total']} active")
    
    print("\n✅ All automation keywords are now active and will be collected in the next YouTube scraper run!")

if __name__ == "__main__":
    activate_n8n()