#!/usr/bin/env python3
"""
Check which collection manager is currently running by analyzing recent logs
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def check_current_manager():
    """Check recent logs to see which collection manager is running"""
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    print("CHECKING CURRENT COLLECTION MANAGER")
    print("="*60)
    
    try:
        # Get recent collection logs
        logs_ref = firebase.db.collection('youtube_collection_logs')
        recent_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(10).get()
        
        script_names = []
        session_patterns = []
        
        print("Recent Collection Runs:")
        print("-" * 60)
        
        for i, log in enumerate(recent_logs, 1):
            log_data = log.to_dict()
            timestamp = log_data.get('timestamp', 'Unknown')
            script_name = log_data.get('script_name', 'Unknown')
            session_id = log_data.get('session_id', 'Unknown')
            videos = log_data.get('total_videos_collected', 0)
            keywords_successful = log_data.get('keywords_successful', 0)
            instance_id = log_data.get('instance_id', 'Unknown')
            container = log_data.get('container', 'Unknown')
            
            script_names.append(script_name)
            session_patterns.append(session_id)
            
            print(f"{i:2d}. {timestamp}")
            print(f"    Script: {script_name}")
            print(f"    Session: {session_id}")
            print(f"    Instance: {instance_id}")
            print(f"    Container: {container}")
            print(f"    Videos: {videos}, Keywords: {keywords_successful}")
            print()
        
        # Analyze patterns
        print("ANALYSIS:")
        print("-" * 60)
        
        from collections import Counter
        script_counts = Counter(script_names)
        
        print("Script usage:")
        for script, count in script_counts.most_common():
            print(f"  {script}: {count} times")
        
        # Check session ID patterns
        unique_sessions = set(session_patterns)
        print(f"\nUnique sessions: {len(unique_sessions)}")
        
        # Check for instance-based sessions
        instance_sessions = [s for s in session_patterns if 'instance' in s.lower()]
        if instance_sessions:
            print(f"Instance-based sessions: {len(instance_sessions)}")
            print("  Suggests youtube_collection_manager_simple.py is running")
        
        timestamp_sessions = [s for s in session_patterns if s.startswith('session_') and s != 'Unknown']
        if timestamp_sessions:
            print(f"Timestamp-based sessions: {len(timestamp_sessions)}")
            print("  Suggests youtube_collection_manager.py is running")
            
    except Exception as e:
        print(f"Error checking logs: {e}")
        return

if __name__ == "__main__":
    check_current_manager()