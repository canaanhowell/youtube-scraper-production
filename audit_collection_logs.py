#!/usr/bin/env python3
"""
Comprehensive audit of videos collected vs collection logs
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, Counter
import json

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def audit_collection_vs_logs():
    """Comprehensive audit of actual videos vs logged metrics"""
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Get today's date in UTC
    today = datetime.now(timezone.utc).date()
    yesterday = today - timedelta(days=1)
    
    print("="*100)
    print(f"COMPREHENSIVE COLLECTION AUDIT - {today}")
    print("="*100)
    
    # === PART 1: ANALYZE ACTUAL VIDEOS COLLECTED ===
    print("\n📊 PART 1: ACTUAL VIDEOS ANALYSIS")
    print("-" * 60)
    
    actual_videos_by_time = defaultdict(list)
    actual_videos_by_keyword = defaultdict(int)
    total_actual_videos = 0
    
    try:
        keywords = firebase.get_keywords()
        print(f"Analyzing {len(keywords)} keywords...")
        
        for i, keyword in enumerate(keywords, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(keywords)} keywords analyzed")
            
            try:
                videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
                # Get more videos to ensure we catch everything
                all_videos = videos_ref.limit(1000).get()
                
                keyword_videos_today = []
                for video in all_videos:
                    video_data = video.to_dict()
                    collected_at_str = video_data.get('collected_at', '')
                    
                    if collected_at_str:
                        try:
                            collected_at = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
                            if collected_at.date() == today:
                                keyword_videos_today.append({
                                    'keyword': keyword,
                                    'video_id': video_data.get('id', ''),
                                    'title': video_data.get('title', ''),
                                    'collected_at': collected_at,
                                    'source': video_data.get('source', '')
                                })
                                
                                # Group by 10-minute intervals for comparison with logs
                                minute_group = (collected_at.hour * 60 + collected_at.minute) // 10 * 10
                                time_key = collected_at.replace(minute=minute_group, second=0, microsecond=0)
                                actual_videos_by_time[time_key].append(video_data)
                
                if keyword_videos_today:
                    actual_videos_by_keyword[keyword] = len(keyword_videos_today)
                    total_actual_videos += len(keyword_videos_today)
                    
            except Exception as e:
                print(f"    Error checking {keyword}: {e}")
    
    except Exception as e:
        print(f"Error in video analysis: {e}")
        return
    
    print(f"\n✅ ACTUAL VIDEOS SUMMARY:")
    print(f"   Total videos found: {total_actual_videos}")
    print(f"   Keywords with videos: {len(actual_videos_by_keyword)}")
    print(f"   Time periods with videos: {len(actual_videos_by_time)}")
    
    # === PART 2: ANALYZE COLLECTION LOGS ===
    print("\n📋 PART 2: COLLECTION LOGS ANALYSIS")
    print("-" * 60)
    
    try:
        logs_ref = firebase.db.collection('youtube_collection_logs')
        all_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(500).get()
        
        logged_videos_by_time = defaultdict(int)
        logged_keywords_by_time = defaultdict(int)
        logged_success_rates = []
        total_logged_videos = 0
        today_logs = []
        
        for log in all_logs:
            log_data = log.to_dict()
            timestamp = log_data.get('timestamp')
            
            if timestamp and timestamp.date() == today:
                today_logs.append(log_data)
                
                # Group by 10-minute intervals
                minute_group = (timestamp.hour * 60 + timestamp.minute) // 10 * 10
                time_key = timestamp.replace(minute=minute_group, second=0, microsecond=0)
                
                videos_collected = log_data.get('total_videos_collected', 0)
                keywords_processed = log_data.get('keywords_successful', 0)
                success_rate = log_data.get('success_rate', 0)
                
                logged_videos_by_time[time_key] += videos_collected
                logged_keywords_by_time[time_key] += keywords_processed
                logged_success_rates.append(success_rate)
                total_logged_videos += videos_collected
        
        print(f"✅ LOGGED METRICS SUMMARY:")
        print(f"   Total collection runs: {len(today_logs)}")
        print(f"   Total logged videos: {total_logged_videos}")
        print(f"   Average success rate: {sum(logged_success_rates)/len(logged_success_rates) if logged_success_rates else 0:.1f}%")
        print(f"   Time periods with logs: {len(logged_videos_by_time)}")
        
    except Exception as e:
        print(f"Error analyzing logs: {e}")
        return
    
    # === PART 3: DETAILED COMPARISON ===
    print("\n🔍 PART 3: DETAILED COMPARISON ANALYSIS")
    print("-" * 60)
    
    # Compare time periods
    all_time_periods = set(actual_videos_by_time.keys()) | set(logged_videos_by_time.keys())
    discrepancies = []
    
    print("\nTime Period Analysis (10-minute intervals):")
    print("Time Period          | Actual Videos | Logged Videos | Difference")
    print("-" * 70)
    
    for time_period in sorted(all_time_periods):
        actual_count = len(actual_videos_by_time.get(time_period, []))
        logged_count = logged_videos_by_time.get(time_period, 0)
        difference = actual_count - logged_count
        
        if difference != 0:
            discrepancies.append({
                'time_period': time_period,
                'actual': actual_count,
                'logged': logged_count,
                'difference': difference
            })
        
        status = "✓" if difference == 0 else "✗"
        print(f"{time_period.strftime('%H:%M')}              | {actual_count:12d} | {logged_count:12d} | {difference:+10d} {status}")
    
    # === PART 4: ROOT CAUSE ANALYSIS ===
    print(f"\n🔬 PART 4: ROOT CAUSE ANALYSIS")
    print("-" * 60)
    
    print(f"\n📊 OVERALL DISCREPANCY:")
    print(f"   Actual videos collected: {total_actual_videos}")
    print(f"   Logged videos reported:  {total_logged_videos}")
    print(f"   Missing from logs:       {total_actual_videos - total_logged_videos}")
    print(f"   Accuracy rate:           {(total_logged_videos/total_actual_videos*100) if total_actual_videos > 0 else 0:.1f}%")
    
    if discrepancies:
        print(f"\n❌ DISCREPANCIES FOUND: {len(discrepancies)} time periods")
        
        # Find patterns
        over_reporting = [d for d in discrepancies if d['difference'] < 0]
        under_reporting = [d for d in discrepancies if d['difference'] > 0]
        
        print(f"   Under-reporting periods: {len(under_reporting)}")
        print(f"   Over-reporting periods:  {len(over_reporting)}")
        
        if under_reporting:
            total_missing = sum(d['difference'] for d in under_reporting)
            print(f"   Total missing videos in logs: {total_missing}")
        
        # Show worst discrepancies
        worst_discrepancies = sorted(discrepancies, key=lambda x: abs(x['difference']), reverse=True)[:5]
        print(f"\n🚨 WORST DISCREPANCIES:")
        for i, disc in enumerate(worst_discrepancies, 1):
            print(f"   {i}. {disc['time_period'].strftime('%H:%M')}: {disc['actual']} actual vs {disc['logged']} logged ({disc['difference']:+d})")
    
    # === PART 5: SAMPLE LOG INSPECTION ===
    print(f"\n🔍 PART 5: SAMPLE LOG INSPECTION")
    print("-" * 60)
    
    # Look at recent logs in detail
    if today_logs:
        print(f"\nRecent collection logs (detailed):")
        for i, log in enumerate(today_logs[:5], 1):
            print(f"\n  Log {i} - {log.get('timestamp', 'Unknown')}:")
            print(f"    Session ID: {log.get('session_id', 'Unknown')}")
            print(f"    Script: {log.get('script_name', 'Unknown')}")
            print(f"    Videos collected: {log.get('total_videos_collected', 0)}")
            print(f"    Keywords successful: {log.get('keywords_successful', 0)}")
            print(f"    Keywords failed: {log.get('keywords_failed', 0)}")
            print(f"    Success rate: {log.get('success_rate', 0)}%")
            print(f"    Duration: {log.get('duration_seconds', 0)}s")
            print(f"    Errors: {len(log.get('errors', []))}")
            print(f"    VPN container: {log.get('container', 'Unknown')}")
            
            # Check if keywords_processed list exists
            keywords_processed = log.get('keywords_processed', [])
            print(f"    Keywords processed list: {len(keywords_processed)} items")
            
            # Check videos_per_keyword data
            videos_per_keyword = log.get('videos_per_keyword', {})
            print(f"    Videos per keyword data: {len(videos_per_keyword)} keywords")
            if videos_per_keyword:
                total_from_breakdown = sum(videos_per_keyword.values())
                print(f"    Sum of per-keyword videos: {total_from_breakdown}")
    
    # === PART 6: RECOMMENDATIONS ===
    print(f"\n💡 PART 6: RECOMMENDATIONS")
    print("-" * 60)
    
    if total_actual_videos > total_logged_videos:
        print(f"✅ COLLECTION IS WORKING: {total_actual_videos} videos successfully stored")
        print(f"❌ LOGGING IS BROKEN: Only {total_logged_videos} videos reported in logs")
        print(f"\nPossible causes:")
        print(f"   1. Collection stats not being updated properly in scraper")
        print(f"   2. Log aggregation missing some collection runs")
        print(f"   3. Multiple instances writing conflicting stats")
        print(f"   4. Error in _finalize_collection method")
        
        print(f"\nNext steps:")
        print(f"   1. Check youtube_scraper_production.py logging logic")
        print(f"   2. Check youtube_collection_manager.py stats aggregation")
        print(f"   3. Verify firebase.log_collection_run() method")
        print(f"   4. Check for instance-specific logging issues")
    
    print("\n" + "="*100)
    print("AUDIT COMPLETE")
    print("="*100)

if __name__ == "__main__":
    audit_collection_vs_logs()