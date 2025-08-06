#!/usr/bin/env python3
"""
Analyze video timestamps to identify videos older than 1 hour
"""

import sys
import re
from pathlib import Path
from datetime import datetime, timezone, timedelta
from collections import defaultdict

# Add project to path
sys.path.append(str(Path(__file__).parent))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

def parse_published_time(published_time):
    """Parse YouTube's published_time text and return approximate age in minutes"""
    
    if not published_time:
        return None
    
    published_time = published_time.lower().strip()
    
    # Handle "Streamed X ago" or "Premiered X ago"
    published_time = re.sub(r'^(streamed|premiered)\s+', '', published_time)
    
    # Extract number and unit
    patterns = [
        r'(\d+)\s*seconds?\s+ago',
        r'(\d+)\s*minutes?\s+ago', 
        r'(\d+)\s*hours?\s+ago',
        r'(\d+)\s*days?\s+ago',
        r'(\d+)\s*weeks?\s+ago',
        r'(\d+)\s*months?\s+ago',
        r'(\d+)\s*years?\s+ago'
    ]
    
    for i, pattern in enumerate(patterns):
        match = re.search(pattern, published_time)
        if match:
            number = int(match.group(1))
            
            # Convert to minutes
            if i == 0:  # seconds
                return number / 60
            elif i == 1:  # minutes
                return number
            elif i == 2:  # hours
                return number * 60
            elif i == 3:  # days
                return number * 24 * 60
            elif i == 4:  # weeks
                return number * 7 * 24 * 60
            elif i == 5:  # months
                return number * 30 * 24 * 60
            elif i == 6:  # years
                return number * 365 * 24 * 60
    
    # Handle special cases
    if 'just now' in published_time or 'now' in published_time:
        return 0
    
    # Unknown format
    return None

def analyze_keyword_videos(keyword, limit=500):
    """Analyze videos for a specific keyword"""
    
    print(f"\n🔍 Analyzing keyword: {keyword}")
    print("-" * 40)
    
    try:
        fc = FirebaseClient()
        videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
        
        # Get recent videos
        videos = []
        for doc in videos_ref.order_by('collected_at', direction='DESCENDING').limit(limit).stream():
            video_data = doc.to_dict()
            videos.append({
                'id': doc.id,
                'title': video_data.get('title', ''),
                'published_time': video_data.get('published_time', ''),
                'collected_at': video_data.get('collected_at', ''),
                'channel_name': video_data.get('channel_name', ''),
                'view_count': video_data.get('view_count', '')
            })
        
        if not videos:
            print("   ❌ No videos found")
            return None
        
        print(f"   ✅ Found {len(videos)} videos")
        
        # Analyze timestamps
        age_stats = {
            'fresh': 0,      # ≤ 60 minutes
            'borderline': 0, # 61-120 minutes  
            'old': 0,        # > 120 minutes
            'unknown': 0     # unparseable
        }
        
        old_videos = []
        
        for video in videos:
            published_time = video['published_time']
            age_minutes = parse_published_time(published_time)
            
            if age_minutes is None:
                age_stats['unknown'] += 1
            elif age_minutes <= 60:
                age_stats['fresh'] += 1
            elif age_minutes <= 120:
                age_stats['borderline'] += 1
            else:
                age_stats['old'] += 1
                old_videos.append((video, age_minutes))
        
        # Print statistics
        print(f"   📊 Age Distribution:")
        print(f"      Fresh (≤1h):     {age_stats['fresh']:3d} ({age_stats['fresh']/len(videos)*100:.1f}%)")
        print(f"      Borderline (1-2h): {age_stats['borderline']:3d} ({age_stats['borderline']/len(videos)*100:.1f}%)")
        print(f"      Old (>2h):        {age_stats['old']:3d} ({age_stats['old']/len(videos)*100:.1f}%)")
        print(f"      Unknown:          {age_stats['unknown']:3d} ({age_stats['unknown']/len(videos)*100:.1f}%)")
        
        # Show problematic videos
        if old_videos:
            print(f"\n   🚨 Videos older than 2 hours ({len(old_videos)}):")
            # Sort by age (oldest first)
            old_videos.sort(key=lambda x: x[1], reverse=True)
            
            for i, (video, age_minutes) in enumerate(old_videos[:5]):  # Show worst 5
                age_hours = age_minutes / 60
                title = video['title'][:50] + "..." if len(video['title']) > 50 else video['title']
                print(f"      {i+1}. {age_hours:.1f}h ago: {video['published_time']}")
                print(f"         {title}")
                print(f"         Collected: {video['collected_at']}")
                print()
        
        return {
            'keyword': keyword,
            'total_videos': len(videos),
            'stats': age_stats,
            'old_videos_count': len(old_videos),
            'old_videos': old_videos[:10]  # Keep top 10 for details
        }
        
    except Exception as e:
        print(f"   ❌ Error analyzing {keyword}: {e}")
        return None

def analyze_recent_collections():
    """Analyze recent collections to identify timestamp issues"""
    
    print("🕐 Video Timestamp Analysis")
    print("=" * 80)
    
    # Common keywords to analyze
    keywords = [
        'chatgpt', 'midjourney', 'stable_diffusion', 'claude_ai', 
        'openai', 'artificial_intelligence', 'machine_learning',
        'leonardo_ai', 'runway', 'dalle'
    ]
    
    overall_stats = {
        'total_videos': 0,
        'fresh': 0,
        'borderline': 0,
        'old': 0,
        'unknown': 0
    }
    
    keyword_results = []
    
    for keyword in keywords:
        result = analyze_keyword_videos(keyword, limit=200)
        if result:
            keyword_results.append(result)
            
            # Add to overall stats
            overall_stats['total_videos'] += result['total_videos']
            overall_stats['fresh'] += result['stats']['fresh']
            overall_stats['borderline'] += result['stats']['borderline'] 
            overall_stats['old'] += result['stats']['old']
            overall_stats['unknown'] += result['stats']['unknown']
    
    # Print overall summary
    print(f"\n📊 Overall Summary")
    print("=" * 40)
    print(f"Total videos analyzed: {overall_stats['total_videos']:,}")
    print(f"Fresh (≤1h):          {overall_stats['fresh']:,} ({overall_stats['fresh']/overall_stats['total_videos']*100:.1f}%)")
    print(f"Borderline (1-2h):    {overall_stats['borderline']:,} ({overall_stats['borderline']/overall_stats['total_videos']*100:.1f}%)")
    print(f"Old (>2h):            {overall_stats['old']:,} ({overall_stats['old']/overall_stats['total_videos']*100:.1f}%)")
    print(f"Unknown:              {overall_stats['unknown']:,} ({overall_stats['unknown']/overall_stats['total_videos']*100:.1f}%)")
    
    # Identify worst offenders
    problematic_keywords = [r for r in keyword_results if r['old_videos_count'] > 0]
    problematic_keywords.sort(key=lambda x: x['old_videos_count'], reverse=True)
    
    if problematic_keywords:
        print(f"\n🚨 Keywords with Most Old Videos:")
        for result in problematic_keywords[:5]:
            old_pct = result['old_videos_count'] / result['total_videos'] * 100
            print(f"   {result['keyword']:20s}: {result['old_videos_count']:3d} old videos ({old_pct:.1f}%)")
    
    # Recommendations based on analysis
    print(f"\n💡 Recommendations:")
    
    if overall_stats['old'] > overall_stats['total_videos'] * 0.1:  # >10% old videos
        print("   🚨 HIGH PRIORITY: >10% of videos are older than 2 hours")
        print("      - Implement client-side time filtering immediately")
        print("      - Consider using stricter YouTube filter parameters")
    elif overall_stats['old'] > 0:
        print("   ⚠️  MEDIUM PRIORITY: Some old videos detected")
        print("      - Monitor trends and consider client-side filtering")
    else:
        print("   ✅ LOW PRIORITY: No significantly old videos detected")
        print("      - Current filtering appears to be working well")
    
    if overall_stats['borderline'] > overall_stats['total_videos'] * 0.2:  # >20% borderline
        print("   📊 Consider tightening filter to exclude 1-2 hour videos")
    
    return keyword_results

def test_time_parsing():
    """Test the time parsing function with various inputs"""
    
    print("\n🧪 Testing Time Parsing Function")
    print("=" * 40)
    
    test_cases = [
        "5 minutes ago",
        "1 hour ago", 
        "2 hours ago",
        "30 seconds ago",
        "1 day ago",
        "3 weeks ago",
        "Streamed 45 minutes ago",
        "Premiered 2 hours ago",
        "just now",
        "unknown format",
        "",
        None
    ]
    
    for test_case in test_cases:
        result = parse_published_time(test_case)
        if result is not None:
            if result < 60:
                status = "✅ Fresh"
            elif result < 120:
                status = "⚠️  Borderline"
            else:
                status = "🚨 Old"
            print(f"   '{test_case}' -> {result:.1f} minutes ({status})")
        else:
            print(f"   '{test_case}' -> Unable to parse")

def main():
    """Main analysis function"""
    
    print("🎯 YouTube Video Timestamp Investigation")
    print("=" * 80)
    
    # Test time parsing
    test_time_parsing()
    
    # Analyze recent collections
    analyze_recent_collections()
    
    print("\n" + "=" * 80)
    print("Investigation Complete")

if __name__ == "__main__":
    main()