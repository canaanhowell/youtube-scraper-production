#!/usr/bin/env python3
"""
Analyze YouTube collection patterns to understand why some keywords collect fewer than 20 videos.
This script investigates collection logs, video counts, and filtering effects.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict, Counter
import json
import re

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = '/workspace/youtube_app/ai-tracker-466821-892ecf5150a3.json'
load_env()

def analyze_collection_logs(fc, days_back=5):
    """Analyze collection logs from the last N days"""
    print(f"=== ANALYZING COLLECTION LOGS (Last {days_back} days) ===")
    
    # Calculate time range
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=days_back)
    
    print(f"Time range: {start_time.strftime('%Y-%m-%d %H:%M UTC')} to {end_time.strftime('%Y-%m-%d %H:%M UTC')}")
    
    # Get collection logs
    logs_ref = fc.db.collection('youtube_collection_logs')
    logs = list(logs_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream())
    
    print(f"\nFound {len(logs)} collection runs")
    
    # Analyze logs
    keyword_stats = defaultdict(list)
    total_runs = 0
    successful_runs = 0
    
    for log in logs:
        log_data = log.to_dict()
        total_runs += 1
        
        if log_data.get('success', False):
            successful_runs += 1
        
        # Get videos per keyword data
        videos_per_keyword = log_data.get('videos_per_keyword', {})
        timestamp = log_data.get('timestamp')
        
        # Store data for each keyword
        for keyword, count in videos_per_keyword.items():
            keyword_stats[keyword].append({
                'count': count,
                'timestamp': timestamp,
                'log_id': log.id,
                'success': log_data.get('success', False),
                'total_videos': log_data.get('total_videos_collected', 0)
            })
    
    print(f"Successful runs: {successful_runs}/{total_runs} ({successful_runs/total_runs*100:.1f}%)")
    
    return keyword_stats

def analyze_keyword_patterns(keyword_stats):
    """Analyze patterns in keyword collection data"""
    print(f"\n=== KEYWORD COLLECTION PATTERNS ===")
    
    keyword_summary = {}
    
    for keyword, runs in keyword_stats.items():
        if not runs:
            continue
            
        counts = [run['count'] for run in runs if run['success']]
        if not counts:
            continue
            
        keyword_summary[keyword] = {
            'total_runs': len(runs),
            'successful_runs': len(counts),
            'avg_videos': sum(counts) / len(counts),
            'min_videos': min(counts),
            'max_videos': max(counts),
            'videos_20_count': sum(1 for c in counts if c == 20),
            'videos_less_than_20': sum(1 for c in counts if c < 20),
            'videos_more_than_20': sum(1 for c in counts if c > 20),
            'last_run': max(run['timestamp'] for run in runs),
            'counts_distribution': Counter(counts)
        }
    
    # Sort by average videos collected
    sorted_keywords = sorted(keyword_summary.items(), key=lambda x: x[1]['avg_videos'], reverse=True)
    
    print(f"\nKeyword Collection Summary ({len(sorted_keywords)} keywords):")
    print("=" * 80)
    print(f"{'Keyword':<15} {'Runs':<5} {'Avg':<6} {'Min':<4} {'Max':<4} {'=20':<4} {'<20':<4} {'>20':<4} {'Last Run'}")
    print("=" * 80)
    
    high_performing = []
    low_performing = []
    inconsistent = []
    
    for keyword, stats in sorted_keywords:
        last_run_str = stats['last_run'].strftime('%m-%d %H:%M') if stats['last_run'] else 'N/A'
        
        print(f"{keyword:<15} {stats['successful_runs']:<5} {stats['avg_videos']:<6.1f} "
              f"{stats['min_videos']:<4} {stats['max_videos']:<4} {stats['videos_20_count']:<4} "
              f"{stats['videos_less_than_20']:<4} {stats['videos_more_than_20']:<4} {last_run_str}")
        
        # Categorize keywords
        if stats['avg_videos'] >= 19:
            high_performing.append(keyword)
        elif stats['avg_videos'] < 15:
            low_performing.append(keyword)
        elif stats['videos_less_than_20'] > stats['videos_20_count']:
            inconsistent.append(keyword)
    
    print(f"\n=== KEYWORD CATEGORIES ===")
    print(f"High performing (avg ≥19): {', '.join(high_performing)}")
    print(f"Low performing (avg <15): {', '.join(low_performing)}")  
    print(f"Inconsistent: {', '.join(inconsistent)}")
    
    return keyword_summary, high_performing, low_performing, inconsistent

def analyze_recent_collections(fc, keywords_of_interest, hours_back=24):
    """Analyze recent video collections for specific keywords"""
    print(f"\n=== RECENT VIDEO COLLECTIONS (Last {hours_back} hours) ===")
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    for keyword in keywords_of_interest[:5]:  # Limit to top 5 for detailed analysis
        print(f"\n--- {keyword.upper()} ---")
        
        try:
            videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
            videos = list(videos_ref.where('collected_at', '>=', start_time).where('collected_at', '<=', end_time).stream())
            
            print(f"Total videos collected in last {hours_back}h: {len(videos)}")
            
            if videos:
                # Group by collection batch (within 30 minutes of each other)
                video_groups = defaultdict(list)
                
                for video in videos:
                    video_data = video.to_dict()
                    collected_at = video_data.get('collected_at')
                    
                    if collected_at:
                        # Round to nearest 30 minutes for grouping
                        minute = collected_at.minute
                        rounded_minute = (minute // 30) * 30
                        group_key = collected_at.replace(minute=rounded_minute, second=0, microsecond=0)
                        
                        video_groups[group_key].append({
                            'id': video.id,
                            'title': video_data.get('title', ''),
                            'collected_at': collected_at,
                            'view_count': video_data.get('view_count', 0),
                            'days_ago': video_data.get('days_ago', 0),
                            'upload_date': video_data.get('upload_date', ''),
                            'container': video_data.get('container', 'unknown')
                        })
                
                print(f"Collection batches: {len(video_groups)}")
                
                for group_time, group_videos in sorted(video_groups.items()):
                    group_time_str = group_time.strftime('%m-%d %H:%M UTC')
                    print(f"  {group_time_str}: {len(group_videos)} videos")
                    
                    # Analyze this batch
                    if group_videos:
                        containers = Counter(v['container'] for v in group_videos)
                        avg_days_ago = sum(v['days_ago'] for v in group_videos if isinstance(v['days_ago'], (int, float))) / len(group_videos)
                        
                        print(f"    Containers: {dict(containers)}")
                        print(f"    Avg days ago: {avg_days_ago:.1f}")
                        
                        # Show sample titles
                        sample_titles = [v['title'][:50] for v in group_videos[:3]]
                        print(f"    Sample titles: {'; '.join(sample_titles)}")
                        
        except Exception as e:
            print(f"Error analyzing {keyword}: {e}")

def analyze_interval_metrics(fc, keywords_of_interest, hours_back=48):
    """Analyze interval metrics to understand search results vs collected videos"""
    print(f"\n=== INTERVAL METRICS ANALYSIS (Last {hours_back} hours) ===")
    
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=hours_back)
    
    for keyword in keywords_of_interest[:5]:
        print(f"\n--- {keyword.upper()} METRICS ---")
        
        try:
            metrics_ref = fc.db.collection('youtube_keywords').document(keyword).collection('interval_metrics')
            metrics = list(metrics_ref.where('timestamp', '>=', start_time).where('timestamp', '<=', end_time).stream())
            
            print(f"Interval metric records: {len(metrics)}")
            
            if metrics:
                total_found = 0
                total_collected = 0
                total_new = 0
                
                print(f"{'Time':<12} {'Found':<6} {'Collected':<10} {'New':<5} {'Filter %':<9}")
                print("-" * 50)
                
                for metric in sorted(metrics, key=lambda x: x.to_dict().get('timestamp', datetime.min.replace(tzinfo=timezone.utc))):
                    metric_data = metric.to_dict()
                    timestamp = metric_data.get('timestamp')
                    
                    found_in_search = metric_data.get('videos_found_in_search', 0)
                    video_count = metric_data.get('video_count', 0)
                    new_videos = metric_data.get('new_videos', 0)
                    
                    total_found += found_in_search
                    total_collected += video_count
                    total_new += new_videos
                    
                    # Calculate filter percentage
                    filter_pct = 0
                    if found_in_search > 0:
                        filter_pct = ((found_in_search - video_count) / found_in_search) * 100
                    
                    time_str = timestamp.strftime('%m-%d %H:%M') if timestamp else 'N/A'
                    print(f"{time_str:<12} {found_in_search:<6} {video_count:<10} {new_videos:<5} {filter_pct:<8.1f}%")
                
                print("-" * 50)
                print(f"{'TOTALS':<12} {total_found:<6} {total_collected:<10} {total_new:<5}")
                
                if total_found > 0:
                    overall_filter_pct = ((total_found - total_collected) / total_found) * 100
                    print(f"Overall filtering: {overall_filter_pct:.1f}% of videos filtered out")
                
        except Exception as e:
            print(f"Error analyzing metrics for {keyword}: {e}")

def check_title_filtering_impact(fc, keyword, sample_size=50):
    """Check impact of title filtering on a specific keyword"""
    print(f"\n=== TITLE FILTERING ANALYSIS: {keyword.upper()} ===")
    
    try:
        # Get recent videos
        videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
        recent_videos = list(videos_ref.order_by('collected_at', direction='DESCENDING').limit(sample_size).stream())
        
        print(f"Analyzing {len(recent_videos)} recent videos for title patterns")
        
        if recent_videos:
            # Analyze titles for common patterns that might be filtered
            titles = []
            containers = Counter()
            
            for video in recent_videos:
                video_data = video.to_dict()
                title = video_data.get('title', '')
                container = video_data.get('container', 'unknown')
                
                titles.append(title.lower())
                containers[container] += 1
            
            # Common filter patterns (based on typical YouTube title filtering)
            filter_patterns = {
                'shorts': sum(1 for title in titles if 'short' in title),
                'tutorial_basic': sum(1 for title in titles if any(word in title for word in ['tutorial', 'how to', 'guide'])),
                'clickbait': sum(1 for title in titles if any(word in title for word in ['amazing', 'shocking', 'you won\'t believe'])),
                'non_english': sum(1 for title in titles if not all(ord(c) < 128 for c in title)),
                'numbers_heavy': sum(1 for title in titles if len([c for c in title if c.isdigit()]) > 5)
            }
            
            print(f"Title pattern analysis:")
            for pattern, count in filter_patterns.items():
                pct = (count / len(titles)) * 100
                print(f"  {pattern}: {count}/{len(titles)} ({pct:.1f}%)")
            
            print(f"\nContainer distribution: {dict(containers)}")
            
    except Exception as e:
        print(f"Error analyzing title filtering for {keyword}: {e}")

def main():
    print("Starting YouTube Collection Pattern Analysis")
    print("=" * 60)
    
    try:
        # Connect to Firebase
        print("Connecting to Firebase...")
        fc = FirebaseClient()
        print("✅ Connected to Firebase successfully")
        
        # 1. Analyze collection logs
        keyword_stats = analyze_collection_logs(fc, days_back=7)
        
        # 2. Analyze keyword patterns
        keyword_summary, high_performing, low_performing, inconsistent = analyze_keyword_patterns(keyword_stats)
        
        # 3. Focus on interesting keywords for deeper analysis
        keywords_of_interest = []
        
        # Add some high-performing keywords
        if high_performing:
            keywords_of_interest.extend(high_performing[:2])
        
        # Add some low-performing keywords
        if low_performing:
            keywords_of_interest.extend(low_performing[:2])
        
        # Add ChatGPT and Claude if they exist
        for keyword in ['chatgpt', 'claude']:
            if keyword in keyword_summary:
                keywords_of_interest.append(keyword)
        
        # Remove duplicates while preserving order
        keywords_of_interest = list(dict.fromkeys(keywords_of_interest))
        
        print(f"\nFocusing detailed analysis on: {', '.join(keywords_of_interest)}")
        
        # 4. Analyze recent collections in detail
        analyze_recent_collections(fc, keywords_of_interest, hours_back=48)
        
        # 5. Analyze interval metrics
        analyze_interval_metrics(fc, keywords_of_interest, hours_back=72)
        
        # 6. Check title filtering impact on a few keywords
        for keyword in keywords_of_interest[:3]:
            check_title_filtering_impact(fc, keyword)
        
        # 7. Generate summary and recommendations
        print(f"\n{'='*60}")
        print("ANALYSIS SUMMARY AND FINDINGS")
        print(f"{'='*60}")
        
        total_keywords = len(keyword_summary)
        high_performing_pct = len(high_performing) / total_keywords * 100 if total_keywords > 0 else 0
        low_performing_pct = len(low_performing) / total_keywords * 100 if total_keywords > 0 else 0
        
        print(f"📊 Total keywords analyzed: {total_keywords}")
        print(f"📈 High performing (≥19 avg videos): {len(high_performing)} ({high_performing_pct:.1f}%)")
        print(f"📉 Low performing (<15 avg videos): {len(low_performing)} ({low_performing_pct:.1f}%)")
        print(f"📊 Inconsistent keywords: {len(inconsistent)}")
        
        print(f"\n🔍 KEY FINDINGS:")
        
        if low_performing:
            print(f"1. Low-performing keywords: {', '.join(low_performing[:5])}")
            print("   → These may have limited YouTube content or face heavy filtering")
        
        if inconsistent:
            print(f"2. Inconsistent keywords: {', '.join(inconsistent[:3])}")
            print("   → These show high variation in collection counts")
        
        print(f"\n💡 RECOMMENDATIONS:")
        print("1. Investigate if low-performing keywords have sufficient YouTube content")
        print("2. Review title filtering rules - may be too aggressive for some keywords")
        print("3. Check if time filters are working properly vs. content availability")
        print("4. Monitor container distribution - some may be getting fewer results")
        print("5. Consider keyword-specific collection strategies")
        
        print(f"\n✅ Analysis complete!")
        
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()