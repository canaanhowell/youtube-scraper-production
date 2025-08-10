#!/usr/bin/env python3
"""
Monitor deployment and verify logging fixes are working
"""

import os
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def monitor_deployment():
    """Monitor deployment by checking for new logs with fixed fields"""
    print("🔍 MONITORING DEPLOYMENT - CHECKING FOR FIXED LOGS")
    print("="*60)
    
    # Load environment
    load_env()
    firebase = FirebaseClient()
    
    # Get current time to identify new logs
    deployment_time = datetime.now(timezone.utc)
    print(f"Deployment initiated at: {deployment_time.strftime('%H:%M:%S UTC')}")
    print(f"Waiting for new collection logs with fixed statistics...")
    print("-" * 60)
    
    check_count = 0
    max_checks = 20  # Check for up to 20 minutes
    
    while check_count < max_checks:
        check_count += 1
        current_time = datetime.now(timezone.utc)
        
        try:
            # Get recent logs
            logs_ref = firebase.db.collection('youtube_collection_logs')
            recent_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(5).get()
            
            print(f"\n⏰ Check #{check_count} at {current_time.strftime('%H:%M:%S')}:")
            
            found_fixed_log = False
            for i, log in enumerate(recent_logs, 1):
                log_data = log.to_dict()
                log_timestamp = log_data.get('timestamp')
                
                # Check if this is a post-deployment log
                if log_timestamp and log_timestamp > deployment_time:
                    print(f"  📝 NEW Log {i}: {log.id}")
                    
                    # Check for fixed fields
                    keywords_successful = log_data.get('keywords_successful')
                    keywords_failed = log_data.get('keywords_failed') 
                    success_rate = log_data.get('success_rate')
                    script_name = log_data.get('script_name')
                    total_videos = log_data.get('total_videos_collected', 0)
                    
                    print(f"    Script: {script_name}")
                    print(f"    Videos: {total_videos}")
                    print(f"    Keywords successful: {keywords_successful}")
                    print(f"    Keywords failed: {keywords_failed}")
                    print(f"    Success rate: {success_rate}%")
                    
                    # Check if this is a properly fixed log
                    if (keywords_successful is not None and 
                        script_name == 'youtube_collection_manager.py' and
                        success_rate is not None):
                        
                        if total_videos > 0 and keywords_successful > 0:
                            print(f"    🎉 FIXED LOG DETECTED!")
                            print(f"    ✅ Has videos: {total_videos}")
                            print(f"    ✅ Has successful keywords: {keywords_successful}")
                            print(f"    ✅ Has success rate: {success_rate}%")
                            print(f"    ✅ Has script name: {script_name}")
                            found_fixed_log = True
                        elif total_videos > 0 and keywords_successful == 0:
                            print(f"    ⚠️  PARTIALLY FIXED: Has videos but 0 successful keywords")
                        else:
                            print(f"    ℹ️  Empty run (no videos collected)")
                    else:
                        print(f"    ❌ Still using old logging format")
                        
                else:
                    # Old log from before deployment
                    print(f"  📜 Old Log {i}: {log.id}")
                    print(f"    Videos: {log_data.get('total_videos_collected', 0)}")
                    print(f"    Keywords successful: {log_data.get('keywords_successful', 'MISSING')}")
                    
            if found_fixed_log:
                print(f"\n🎊 DEPLOYMENT SUCCESS!")
                print(f"   The logging fixes are now active and working correctly.")
                print(f"   Collection statistics will now show real performance metrics.")
                break
                
            else:
                print(f"   ⏳ No fixed logs yet. Waiting 60 seconds...")
                if check_count < max_checks:
                    time.sleep(60)  # Wait 1 minute between checks
                
        except Exception as e:
            print(f"   ❌ Error checking logs: {e}")
            if check_count < max_checks:
                time.sleep(60)
    
    if check_count >= max_checks:
        print(f"\n⏰ TIMEOUT: No fixed logs detected after {max_checks} minutes")
        print(f"   This could mean:")
        print(f"   1. Deployment is still in progress")
        print(f"   2. Collection cycle hasn't run yet")
        print(f"   3. There may be an issue with the deployment")
        print(f"   ")
        print(f"   Check GitHub Actions: https://github.com/canaanhowell/youtube-scraper-production/actions")
        print(f"   SSH to VM: ssh -i /workspace/droplet1 root@134.199.201.56")
    
    print(f"\n" + "="*60)
    print("MONITORING COMPLETE")

if __name__ == "__main__":
    monitor_deployment()