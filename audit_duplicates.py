#!/usr/bin/env python3
"""
Comprehensive duplicate audit for today's video collection
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, Counter

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

def audit_duplicates():
    """Comprehensive duplicate audit of today's videos"""
    # Load environment
    load_env()
    
    # Initialize Firebase
    firebase = FirebaseClient()
    
    # Get today's date in UTC
    today = datetime.now(timezone.utc).date()
    
    print("="*100)
    print(f"DUPLICATE AUDIT - {today}")
    print("="*100)
    
    # Track all videos and duplicates
    all_video_ids = []
    video_id_to_keywords = defaultdict(list)
    keyword_video_counts = {}
    duplicate_details = []
    
    try:
        keywords = firebase.get_keywords()
        print(f"Auditing {len(keywords)} keywords for duplicate videos...")
        print("="*100)
        
        # Collect all videos from today
        for i, keyword in enumerate(keywords, 1):
            print(f"Checking {i:2d}/{len(keywords)}: {keyword:30s}", end=" ")
            
            try:
                videos_ref = firebase.db.collection('youtube_videos').document(keyword).collection('videos')
                all_videos = videos_ref.limit(1000).get()
                
                keyword_videos_today = []
                for video in all_videos:
                    video_data = video.to_dict()
                    collected_at_str = video_data.get('collected_at', '')
                    
                    if collected_at_str:
                        try:
                            collected_at = datetime.fromisoformat(collected_at_str.replace('Z', '+00:00'))
                            if collected_at.date() == today:
                                video_id = video_data.get('id', '')
                                if video_id:
                                    all_video_ids.append(video_id)
                                    video_id_to_keywords[video_id].append({
                                        'keyword': keyword,
                                        'title': video_data.get('title', ''),
                                        'collected_at': collected_at,
                                        'source': video_data.get('source', '')
                                    })
                                    keyword_videos_today.append(video_data)
                        except:
                            pass
                
                keyword_video_counts[keyword] = len(keyword_videos_today)
                print(f"✓ {len(keyword_videos_today):3d} videos")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                keyword_video_counts[keyword] = 0
        
        # Analyze duplicates
        print(f"\n" + "="*100)
        print("DUPLICATE ANALYSIS")
        print("="*100)
        
        total_videos = len(all_video_ids)
        unique_videos = len(set(all_video_ids))
        duplicate_videos = total_videos - unique_videos
        
        print(f"📊 OVERALL STATISTICS:")
        print(f"   Total video entries:     {total_videos}")
        print(f"   Unique video IDs:        {unique_videos}")
        print(f"   Duplicate entries:       {duplicate_videos}")
        print(f"   Duplication rate:        {(duplicate_videos/total_videos*100) if total_videos > 0 else 0:.2f}%")
        
        # Find specific duplicates
        video_id_counts = Counter(all_video_ids)
        duplicates = {vid: count for vid, count in video_id_counts.items() if count > 1}
        
        if duplicates:
            print(f"\n🚨 DUPLICATE VIDEOS FOUND: {len(duplicates)} video IDs appear multiple times")
            print(f"   Total duplicate instances: {sum(duplicates.values()) - len(duplicates)}")
            
            # Show worst duplicates
            worst_duplicates = sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:10]
            
            print(f"\n📋 TOP DUPLICATES:")
            for i, (video_id, count) in enumerate(worst_duplicates, 1):
                print(f"\n   {i:2d}. Video ID: {video_id} ({count} times)")
                
                # Show which keywords have this video
                keywords_with_video = video_id_to_keywords[video_id]
                print(f"       Keywords: ", end="")
                keyword_names = [kw['keyword'] for kw in keywords_with_video]
                print(f"{', '.join(keyword_names)}")
                
                # Show title
                if keywords_with_video:
                    title = keywords_with_video[0]['title'][:80]
                    print(f"       Title: {title}{'...' if len(keywords_with_video[0]['title']) > 80 else ''}")
                
                # Show collection times to see if it's a timing issue
                times = [kw['collected_at'].strftime('%H:%M:%S') for kw in keywords_with_video]
                print(f"       Times: {', '.join(times)}")
            
            # Analyze duplicate patterns
            print(f"\n🔍 DUPLICATE PATTERNS:")
            
            # Pattern 1: Same video across multiple keywords
            cross_keyword_duplicates = []
            same_keyword_duplicates = []
            
            for video_id, instances in video_id_to_keywords.items():
                if len(instances) > 1:
                    keywords_involved = set(inst['keyword'] for inst in instances)
                    if len(keywords_involved) > 1:
                        cross_keyword_duplicates.append((video_id, keywords_involved))
                    else:
                        same_keyword_duplicates.append((video_id, list(keywords_involved)[0], len(instances)))
            
            print(f"   Cross-keyword duplicates: {len(cross_keyword_duplicates)} videos appear in multiple keywords")
            print(f"   Same-keyword duplicates:  {len(same_keyword_duplicates)} videos duplicated within same keyword")
            
            # Show some cross-keyword examples
            if cross_keyword_duplicates:
                print(f"\n   📌 CROSS-KEYWORD DUPLICATE EXAMPLES:")
                for i, (video_id, keywords_set) in enumerate(cross_keyword_duplicates[:5], 1):
                    print(f"      {i}. {video_id}: {', '.join(sorted(keywords_set))}")
            
            # Show same-keyword examples
            if same_keyword_duplicates:
                print(f"\n   📌 SAME-KEYWORD DUPLICATE EXAMPLES:")
                for i, (video_id, keyword, count) in enumerate(same_keyword_duplicates[:5], 1):
                    print(f"      {i}. {video_id} in '{keyword}' ({count} times)")
        
        else:
            print(f"\n✅ NO DUPLICATES FOUND - All video IDs are unique!")
        
        # Analyze by keyword
        print(f"\n" + "="*100)
        print("KEYWORD ANALYSIS")
        print("="*100)
        
        keywords_with_videos = [(kw, count) for kw, count in keyword_video_counts.items() if count > 0]
        keywords_with_videos.sort(key=lambda x: x[1], reverse=True)
        
        print(f"📊 KEYWORDS WITH VIDEOS TODAY: {len(keywords_with_videos)}")
        print(f"   Keywords with no videos: {len(keywords) - len(keywords_with_videos)}")
        
        print(f"\n🏆 TOP PERFORMING KEYWORDS:")
        for i, (keyword, count) in enumerate(keywords_with_videos[:15], 1):
            print(f"   {i:2d}. {keyword:30s}: {count:3d} videos")
        
        # Check for keywords with suspiciously high counts (potential duplicate issue)
        high_count_keywords = [(kw, count) for kw, count in keywords_with_videos if count > 50]
        if high_count_keywords:
            print(f"\n⚠️  HIGH COUNT KEYWORDS (>50 videos - check for duplicates):")
            for keyword, count in high_count_keywords:
                print(f"   {keyword:30s}: {count:3d} videos")
        
        # Time distribution analysis
        print(f"\n" + "="*100)
        print("TIME DISTRIBUTION ANALYSIS")
        print("="*100)
        
        hourly_distribution = defaultdict(int)
        minute_distribution = defaultdict(int)
        
        for video_id, instances in video_id_to_keywords.items():
            for instance in instances:
                collected_at = instance['collected_at']
                hourly_distribution[collected_at.hour] += 1
                # Group by 10-minute intervals
                minute_group = (collected_at.hour * 60 + collected_at.minute) // 10
                minute_distribution[minute_group] += 1
        
        print(f"📊 HOURLY DISTRIBUTION:")
        for hour in sorted(hourly_distribution.keys()):
            print(f"   {hour:02d}:00-{hour:02d}:59: {hourly_distribution[hour]:4d} videos")
        
        # Look for suspicious spikes that might indicate duplicate collection runs
        avg_per_10min = total_videos / len(minute_distribution) if minute_distribution else 0
        high_periods = [(period, count) for period, count in minute_distribution.items() 
                       if count > avg_per_10min * 2 and count > 10]
        
        if high_periods:
            print(f"\n⚠️  HIGH ACTIVITY PERIODS (>2x average, might indicate duplicate runs):")
            for period, count in sorted(high_periods)[:10]:
                hour = period // 6
                minute = (period % 6) * 10
                print(f"   {hour:02d}:{minute:02d}: {count} videos (avg: {avg_per_10min:.1f})")
        
    except Exception as e:
        print(f"Error in duplicate audit: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print(f"\n" + "="*100)
    print("AUDIT COMPLETE")
    print("="*100)
    
    # Summary
    if duplicate_videos > 0:
        print(f"❌ DUPLICATES DETECTED: {duplicate_videos} duplicate video entries")
        print(f"   This indicates the Redis deduplication is not working properly")
        print(f"   or multiple instances are collecting the same videos")
    else:
        print(f"✅ NO DUPLICATES: All {unique_videos} videos are unique")
        print(f"   Redis deduplication appears to be working correctly")

if __name__ == "__main__":
    audit_duplicates()