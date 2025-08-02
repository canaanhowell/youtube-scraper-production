#\!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.firebase_client import FirebaseClient
from collections import defaultdict

def get_comprehensive_stats():
    try:
        fc = FirebaseClient()
        
        # Get active keywords
        keywords = fc.get_keywords()
        print(f"=== FIREBASE STATISTICS ===\n")
        print(f"📊 Active Keywords: {len(keywords)}")
        print(f"Keywords: {sorted([k['keyword'] for k in keywords])}\n")
        
        # Get video counts per keyword
        total_videos = 0
        keyword_stats = {}
        
        for keyword_doc in keywords:
            keyword = keyword_doc['keyword']
            try:
                videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
                videos = list(videos_ref.limit(1000).stream())  # Limit for performance
                count = len(videos)
                keyword_stats[keyword] = count
                total_videos += count
                print(f"  📹 {keyword}: {count} videos")
            except Exception as e:
                print(f"  ❌ {keyword}: Error counting - {e}")
                keyword_stats[keyword] = 0
        
        print(f"\n🎥 Total Videos: {total_videos}\n")
        
        # Get recent collection logs
        try:
            logs_ref = fc.db.collection('youtube_collection_logs')
            recent_logs = list(logs_ref.order_by('timestamp', direction='DESCENDING').limit(5).stream())
            
            print(f"📝 Recent Collection Runs ({len(recent_logs)}):")
            for log in recent_logs:
                data = log.to_dict()
                timestamp = data.get('timestamp', 'Unknown')
                total_saved = data.get('total_videos_saved', 0)
                keywords_processed = data.get('keywords_processed', 0)
                print(f"  🕐 {timestamp}: {total_saved} videos from {keywords_processed} keywords")
        except Exception as e:
            print(f"❌ Error getting collection logs: {e}")
        
        # Check for interval metrics collection
        print(f"\n🔄 Checking Interval Metrics Collection...")
        try:
            # Check if any keywords have interval_metrics subcollection
            interval_keywords = []
            for keyword_doc in keywords:
                keyword = keyword_doc['keyword']
                try:
                    interval_ref = fc.db.collection('youtube_keywords').document(keyword).collection('interval_metrics')
                    interval_docs = list(interval_ref.limit(1).stream())
                    if interval_docs:
                        interval_keywords.append(keyword)
                except:
                    pass
            
            if interval_keywords:
                print(f"  ✅ Interval metrics found for {len(interval_keywords)} keywords: {interval_keywords}")
                
                # Get latest interval metric
                try:
                    latest_keyword = interval_keywords[0]
                    latest_ref = fc.db.collection('youtube_keywords').document(latest_keyword).collection('interval_metrics')
                    latest_docs = list(latest_ref.order_by('timestamp', direction='DESCENDING').limit(1).stream())
                    if latest_docs:
                        latest_data = latest_docs[0].to_dict()
                        latest_time = latest_data.get('timestamp', 'Unknown')
                        print(f"  🕐 Latest interval metric: {latest_time} ({latest_keyword})")
                except Exception as e:
                    print(f"  ⚠️ Error getting latest interval metric: {e}")
            else:
                print(f"  ❌ No interval metrics found")
        except Exception as e:
            print(f"❌ Error checking interval metrics: {e}")
            
    except Exception as e:
        print(f"❌ Error getting Firebase stats: {e}")

if __name__ == '__main__':
    get_comprehensive_stats()
