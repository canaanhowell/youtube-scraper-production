#!/usr/bin/env python3
"""
Investigate the negative filtering percentages which indicate something unusual
in the data collection process.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
load_env()

def investigate_chatgpt_anomaly(fc):
    """Investigate the ChatGPT collection anomaly where more videos are collected than found"""
    print("=== INVESTIGATING CHATGPT NEGATIVE FILTERING ANOMALY ===")
    
    # Get interval metrics for ChatGPT
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=3)
    
    metrics_ref = fc.db.collection('youtube_keywords').document('chatgpt').collection('interval_metrics')
    metrics = list(metrics_ref.where('timestamp', '>=', start_time).stream())
    
    print(f"Analyzing {len(metrics)} interval metric records for ChatGPT")
    
    # Look for the specific anomalies
    anomalies = []
    for metric in metrics:
        metric_data = metric.to_dict()
        found_in_search = metric_data.get('videos_found_in_search', 0)
        video_count = metric_data.get('video_count', 0)
        new_videos = metric_data.get('new_videos', 0)
        timestamp = metric_data.get('timestamp')
        
        # Identify anomalous records where video_count > found_in_search
        if video_count > found_in_search and found_in_search > 0:
            anomalies.append({
                'timestamp': timestamp,
                'found': found_in_search,
                'collected': video_count,
                'new': new_videos,
                'ratio': video_count / found_in_search if found_in_search > 0 else 0,
                'doc_id': metric.id
            })
    
    print(f"\nFound {len(anomalies)} anomalous records where collected > found:")
    
    for anomaly in sorted(anomalies, key=lambda x: x['timestamp'])[:20]:  # Show first 20
        time_str = anomaly['timestamp'].strftime('%m-%d %H:%M:%S') if anomaly['timestamp'] else 'N/A'
        print(f"{time_str}: Found {anomaly['found']:>3}, Collected {anomaly['collected']:>4}, "
              f"Ratio: {anomaly['ratio']:>6.1f}x, New: {anomaly['new']}")
    
    # Look at the collection logs during the same period
    print(f"\n=== COLLECTION LOGS DURING ANOMALY PERIOD ===")
    
    logs_ref = fc.db.collection('youtube_collection_logs')
    logs = list(logs_ref.where('timestamp', '>=', start_time).stream())
    
    chatgpt_collections = []
    for log in logs:
        log_data = log.to_dict()
        videos_per_keyword = log_data.get('videos_per_keyword', {})
        if 'chatgpt' in videos_per_keyword:
            chatgpt_collections.append({
                'timestamp': log_data.get('timestamp'),
                'videos_collected': videos_per_keyword['chatgpt'],
                'total_videos': log_data.get('total_videos_collected', 0),
                'success': log_data.get('success', False),
                'errors': log_data.get('errors', []),
                'log_id': log.id
            })
    
    print(f"\nFound {len(chatgpt_collections)} collection runs mentioning ChatGPT:")
    
    for collection in sorted(chatgpt_collections, key=lambda x: x['timestamp'] or datetime.min.replace(tzinfo=timezone.utc))[-10:]:
        time_str = collection['timestamp'].strftime('%m-%d %H:%M:%S') if collection['timestamp'] else 'N/A'
        status = "✅" if collection['success'] else "❌"
        print(f"{time_str} {status}: {collection['videos_collected']} ChatGPT videos, "
              f"{collection['total_videos']} total, Errors: {len(collection['errors'])}")

def investigate_video_storage(fc, keyword='chatgpt', hours=72):
    """Investigate actual video storage patterns"""
    print(f"\n=== INVESTIGATING ACTUAL VIDEO STORAGE FOR {keyword.upper()} ===")
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours)
    
    videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
    videos = list(videos_ref.where('collected_at', '>=', start_time).stream())
    
    print(f"Total {keyword} videos in storage (last {hours}h): {len(videos)}")
    
    if videos:
        # Group by collection hour
        hourly_counts = defaultdict(int)
        containers = Counter()
        
        for video in videos:
            video_data = video.to_dict()
            collected_at = video_data.get('collected_at')
            container = video_data.get('container', 'unknown')
            
            containers[container] += 1
            
            if collected_at:
                hour_key = collected_at.strftime('%Y-%m-%d %H:00')
                hourly_counts[hour_key] += 1
        
        print(f"\nVideo collection by hour:")
        for hour, count in sorted(hourly_counts.items())[-24:]:  # Last 24 hours
            print(f"  {hour}: {count} videos")
        
        print(f"\nContainer distribution: {dict(containers)}")
        
        # Check for duplicate video IDs
        video_ids = [video.id for video in videos]
        unique_ids = set(video_ids)
        
        print(f"\nVideo ID analysis:")
        print(f"  Total video records: {len(video_ids)}")
        print(f"  Unique video IDs: {len(unique_ids)}")
        print(f"  Duplicate records: {len(video_ids) - len(unique_ids)}")
        
        if len(video_ids) > len(unique_ids):
            from collections import Counter
            id_counts = Counter(video_ids)
            duplicates = {vid_id: count for vid_id, count in id_counts.items() if count > 1}
            print(f"  Top duplicate video IDs:")
            for vid_id, count in list(duplicates.items())[:5]:
                print(f"    {vid_id}: {count} times")

def analyze_collection_patterns_detailed(fc):
    """Analyze detailed collection patterns to understand the source of anomalies"""
    print(f"\n=== DETAILED COLLECTION PATTERN ANALYSIS ===")
    
    # Look at recent collection logs in detail
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=2)
    
    logs_ref = fc.db.collection('youtube_collection_logs')
    logs = list(logs_ref.where('timestamp', '>=', start_time).stream())
    
    print(f"Analyzing {len(logs)} recent collection logs")
    
    # Group logs by success/failure and analyze patterns
    successful_logs = []
    failed_logs = []
    
    for log in logs:
        log_data = log.to_dict()
        if log_data.get('success', False):
            successful_logs.append(log_data)
        else:
            failed_logs.append(log_data)
    
    print(f"\nSuccess/Failure breakdown:")
    print(f"  Successful runs: {len(successful_logs)}")
    print(f"  Failed runs: {len(failed_logs)}")
    
    # Analyze successful runs
    if successful_logs:
        print(f"\n--- SUCCESSFUL RUNS ANALYSIS ---")
        
        total_videos_collected = []
        keywords_per_run = []
        
        for log_data in successful_logs:
            total_videos_collected.append(log_data.get('total_videos_collected', 0))
            keywords_processed = log_data.get('keywords_processed', [])
            keywords_per_run.append(len(keywords_processed))
        
        if total_videos_collected:
            avg_videos = sum(total_videos_collected) / len(total_videos_collected)
            print(f"  Average videos per successful run: {avg_videos:.1f}")
            print(f"  Max videos in a run: {max(total_videos_collected)}")
            print(f"  Min videos in a run: {min(total_videos_collected)}")
        
        if keywords_per_run:
            avg_keywords = sum(keywords_per_run) / len(keywords_per_run)
            print(f"  Average keywords per run: {avg_keywords:.1f}")
    
    # Analyze failed runs
    if failed_logs:
        print(f"\n--- FAILED RUNS ANALYSIS ---")
        
        error_categories = Counter()
        
        for log_data in failed_logs:
            errors = log_data.get('errors', [])
            for error in errors:
                # Categorize errors
                error_str = str(error).lower()
                if 'timeout' in error_str or 'connection' in error_str:
                    error_categories['network'] += 1
                elif 'firebase' in error_str or 'firestore' in error_str:
                    error_categories['database'] += 1
                elif 'vpn' in error_str:
                    error_categories['vpn'] += 1
                else:
                    error_categories['other'] += 1
        
        print(f"  Error categories: {dict(error_categories)}")

def check_time_filter_effectiveness(fc):
    """Check if the time filter is actually working by examining video upload dates"""
    print(f"\n=== TIME FILTER EFFECTIVENESS ANALYSIS ===")
    
    keywords_to_check = ['chatgpt', 'claude', 'midjourney']
    
    for keyword in keywords_to_check:
        print(f"\n--- {keyword.upper()} TIME FILTER CHECK ---")
        
        try:
            videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
            recent_videos = list(videos_ref.order_by('collected_at', direction='DESCENDING').limit(100).stream())
            
            if recent_videos:
                upload_ages = []
                
                for video in recent_videos:
                    video_data = video.to_dict()
                    days_ago = video_data.get('days_ago')
                    upload_date = video_data.get('upload_date', '')
                    
                    if isinstance(days_ago, (int, float)) and days_ago >= 0:
                        upload_ages.append(days_ago)
                
                if upload_ages:
                    print(f"  Sample size: {len(upload_ages)} videos with valid days_ago")
                    print(f"  Average video age: {sum(upload_ages) / len(upload_ages):.1f} days")
                    print(f"  Newest video: {min(upload_ages):.1f} days ago")
                    print(f"  Oldest video: {max(upload_ages):.1f} days ago")
                    
                    # Check distribution
                    recent_videos_count = sum(1 for age in upload_ages if age <= 7)  # Within 7 days
                    old_videos_count = sum(1 for age in upload_ages if age > 30)    # Older than 30 days
                    
                    print(f"  Videos ≤7 days old: {recent_videos_count} ({recent_videos_count/len(upload_ages)*100:.1f}%)")
                    print(f"  Videos >30 days old: {old_videos_count} ({old_videos_count/len(upload_ages)*100:.1f}%)")
                    
                    # This tells us if the time filter is working
                    if old_videos_count > recent_videos_count:
                        print(f"  ⚠️ Time filter may not be working properly - more old than recent videos")
                    else:
                        print(f"  ✅ Time filter appears to be working - more recent videos")
                else:
                    print(f"  ❌ No videos with valid days_ago data")
            else:
                print(f"  ❌ No videos found for {keyword}")
        
        except Exception as e:
            print(f"  ❌ Error analyzing {keyword}: {e}")

def main():
    print("Starting Investigation of Negative Filtering Anomaly")
    print("=" * 60)
    
    try:
        # Connect to Firebase
        print("Connecting to Firebase...")
        fc = FirebaseClient()
        print("✅ Connected to Firebase successfully")
        
        # Run investigations
        investigate_chatgpt_anomaly(fc)
        investigate_video_storage(fc, 'chatgpt', 72)
        investigate_video_storage(fc, 'claude', 72)
        analyze_collection_patterns_detailed(fc)
        check_time_filter_effectiveness(fc)
        
        print(f"\n{'='*60}")
        print("INVESTIGATION COMPLETE")
        print(f"{'='*60}")
        
        print("🔍 KEY FINDINGS:")
        print("1. Negative filtering percentages indicate collected videos > videos found in search")
        print("2. This suggests either:")
        print("   - Multiple collection runs being combined in metrics")
        print("   - Videos being counted multiple times")
        print("   - Metrics not being reset properly between runs")
        print("3. Need to check if the collection process is accumulating counts instead of resetting")
        
        print("\n💡 NEXT STEPS:")
        print("1. Review how interval_metrics are calculated and stored")
        print("2. Check if video counting is cumulative vs. per-collection")
        print("3. Verify time filter implementation in the scraping process")
        print("4. Investigate if the 20-video limit is being applied correctly")
        
    except Exception as e:
        print(f"❌ Investigation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()