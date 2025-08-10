#!/usr/bin/env python3
"""
Quick check of the most recent log to see if new fields are present
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def quick_check():
    """Quick check of recent log structure"""
    load_env()
    firebase = FirebaseClient()
    
    print("🔍 QUICK LOG STRUCTURE CHECK")
    print("="*50)
    
    # Get most recent log
    logs_ref = firebase.db.collection('youtube_collection_logs')
    recent_log = logs_ref.order_by('timestamp', direction='DESCENDING').limit(1).get()
    
    if recent_log:
        log_data = list(recent_log)[0].to_dict()
        log_id = list(recent_log)[0].id
        
        print(f"Most Recent Log: {log_id}")
        print(f"Timestamp: {log_data.get('timestamp')}")
        print("-" * 50)
        
        # Check for new fields
        new_fields = [
            'keywords_successful', 'keywords_failed', 'success_rate', 
            'script_name', 'instance_id', 'vm_hostname'
        ]
        
        print("Field Status:")
        for field in new_fields:
            value = log_data.get(field)
            if value is not None:
                print(f"  ✅ {field}: {value}")
            else:
                print(f"  ❌ {field}: MISSING")
        
        # Show key stats
        print(f"\nKey Stats:")
        print(f"  Videos collected: {log_data.get('total_videos_collected', 0)}")
        print(f"  Session ID: {log_data.get('session_id', 'Unknown')}")
        
        # Determine if this is a fixed log
        has_new_fields = any(log_data.get(field) is not None for field in new_fields)
        if has_new_fields:
            print(f"\n🎉 DEPLOYMENT SUCCESS - New fields detected!")
        else:
            print(f"\n⏳ Still using old format - deployment may be in progress")
    else:
        print("No logs found")

if __name__ == "__main__":
    quick_check()