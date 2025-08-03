#\!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.firebase_client import FirebaseClient

def get_comprehensive_stats():
    try:
        fc = FirebaseClient()
        
        # Get active keywords - debug the format first
        keywords = fc.get_keywords()
        print(f"=== FIREBASE STATISTICS ===\n")
        print(f"📊 Active Keywords: {len(keywords)}")
        
        # Debug: Check the structure of keywords
        print(f"Debug - Keywords type: {type(keywords)}")
        if keywords:
            print(f"Debug - First keyword type: {type(keywords[0])}")
            print(f"Debug - First keyword: {keywords[0]}")
        
        # Extract keyword names based on the actual structure
        keyword_names = []
        if isinstance(keywords, list) and keywords:
            if isinstance(keywords[0], str):
                keyword_names = keywords
            elif isinstance(keywords[0], dict):
                keyword_names = [k.get('keyword', k.get('name', str(k))) for k in keywords]
            
        print(f"Keywords: {sorted(keyword_names)}\n")
        
        # Get video counts per keyword
        total_videos = 0
        keyword_stats = {}
        
        for keyword in keyword_names:
            try:
                videos_ref = fc.db.collection('youtube_videos').document(keyword).collection('videos')
                # Count documents more efficiently
                videos_stream = videos_ref.stream()
                count = len(list(videos_stream))
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
            interval_keywords = []
            for keyword in keyword_names:
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
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    get_comprehensive_stats()
