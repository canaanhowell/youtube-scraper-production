#!/usr/bin/env python3
"""
Monitor youtube_collection_logs for hash document IDs and alert when found.
This helps identify which process is creating documents with auto-generated IDs.
"""

import sys
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()


def is_hash_id(doc_id):
    """
    Check if a document ID looks like a hash (auto-generated ID).
    Hash IDs are typically 20 characters of mixed alphanumeric.
    Our meaningful IDs contain underscores and follow patterns like:
    - interval_metrics_2025-08-05_15-30-45_UTC
    - daily_metrics_2025-08-05_02-00-00_UTC
    - scraper_2025-08-05_15-15-00_UTC
    """
    # If it contains underscore or dash, it's likely a meaningful ID
    if '_' in doc_id or '-' in doc_id:
        return False
    
    # Check if it looks like a hash: 16-28 chars, alphanumeric only
    if re.match(r'^[a-zA-Z0-9]{16,28}$', doc_id):
        return True
    
    return False


def monitor_collection_logs(check_interval=60):
    """
    Monitor youtube_collection_logs for new hash document IDs.
    
    Args:
        check_interval: Seconds between checks
    """
    print("Connecting to Firebase...")
    fc = FirebaseClient()
    
    # Track known documents
    known_docs = set()
    
    # Initial scan
    print("\nPerforming initial scan...")
    logs_ref = fc.db.collection('youtube_collection_logs')
    initial_docs = list(logs_ref.stream())
    
    hash_count = 0
    for doc in initial_docs:
        known_docs.add(doc.id)
        if is_hash_id(doc.id):
            hash_count += 1
            data = doc.to_dict()
            print(f"⚠️  Found existing hash ID: {doc.id}")
            print(f"   Created: {data.get('timestamp', 'unknown')}")
            print(f"   Session: {data.get('session_id', 'unknown')}")
            print(f"   Script: {data.get('script_name', data.get('event_type', 'unknown'))}")
    
    print(f"\nInitial scan complete. Found {hash_count} hash IDs out of {len(initial_docs)} total documents.")
    print(f"\nStarting monitoring (checking every {check_interval} seconds)...")
    print("Press Ctrl+C to stop.\n")
    
    try:
        while True:
            time.sleep(check_interval)
            
            # Check for new documents
            current_docs = list(logs_ref.stream())
            
            for doc in current_docs:
                if doc.id not in known_docs:
                    known_docs.add(doc.id)
                    
                    if is_hash_id(doc.id):
                        # Alert! New hash ID found
                        data = doc.to_dict()
                        print(f"\n🚨 ALERT: New hash ID detected!")
                        print(f"   Document ID: {doc.id}")
                        print(f"   Created: {datetime.now()}")
                        print(f"   Timestamp: {data.get('timestamp', 'unknown')}")
                        print(f"   Session ID: {data.get('session_id', 'unknown')}")
                        print(f"   Script Name: {data.get('script_name', 'unknown')}")
                        print(f"   Event Type: {data.get('event_type', 'unknown')}")
                        print(f"   Run Type: {data.get('run_type', 'unknown')}")
                        print(f"   Keywords: {data.get('keywords_processed', [])}")
                        
                        # Try to identify the source
                        if 'keyword_results' in data:
                            print("   Source: Likely from collection_logger.py")
                        elif 'run_type' in data and 'interval' in str(data.get('run_type')):
                            print("   Source: Likely from interval metrics script")
                        elif 'run_type' in data and 'daily' in str(data.get('run_type')):
                            print("   Source: Likely from daily metrics script")
                        else:
                            print("   Source: Unknown - check data structure")
                        
                        print("\n   Full document data:")
                        for key, value in sorted(data.items()):
                            if key not in ['keyword_results', 'summary']:  # Skip large nested data
                                print(f"     {key}: {value}")
                        print("\n")
                    else:
                        print(f"✅ New document with proper ID: {doc.id}")
            
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")
        return


def main():
    """Run the monitor with configurable check interval."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Monitor youtube_collection_logs for hash document IDs'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Check interval in seconds (default: 60)'
    )
    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit (don\'t monitor continuously)'
    )
    
    args = parser.parse_args()
    
    if args.once:
        # Just do one check
        print("Performing one-time check...")
        fc = FirebaseClient()
        logs_ref = fc.db.collection('youtube_collection_logs')
        docs = list(logs_ref.stream())
        
        hash_docs = []
        for doc in docs:
            if is_hash_id(doc.id):
                hash_docs.append(doc)
        
        if hash_docs:
            print(f"\nFound {len(hash_docs)} documents with hash IDs:")
            for doc in hash_docs:
                data = doc.to_dict()
                print(f"\n  ID: {doc.id}")
                print(f"  Timestamp: {data.get('timestamp', 'unknown')}")
                print(f"  Session: {data.get('session_id', 'unknown')}")
                print(f"  Script: {data.get('script_name', data.get('event_type', 'unknown'))}")
        else:
            print("\n✅ No hash IDs found! All documents use proper timestamp IDs.")
    else:
        # Run continuous monitoring
        monitor_collection_logs(args.interval)


if __name__ == "__main__":
    main()