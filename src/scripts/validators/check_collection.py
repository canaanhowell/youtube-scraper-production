from src.utils.firebase_client import FirebaseClient
from datetime import datetime, timezone, timedelta

fc = FirebaseClient()

# Check dalle videos
print('=== Recent DALLE videos in Firebase ===')
videos_ref = fc.db.collection('youtube_videos').document('dalle').collection('videos')
recent_videos = videos_ref.order_by('collected_at', direction='DESCENDING').limit(5).get()

for video in recent_videos:
    data = video.to_dict()
    title = data.get('title', 'No title')[:60]
    views = data.get('view_count', 0)
    duration = data.get('duration', 'N/A')
    collected = data.get('collected_at', 'Unknown')
    print(f'- {title}...')
    print(f'  Views: {views}, Duration: {duration}')
    print(f'  Collected: {collected}')
    print()

# Check collection logs
print('\n=== Recent Collection Logs ===')
logs_ref = fc.db.collection('youtube_collection_logs')
one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

recent_logs = logs_ref.order_by('timestamp', direction='DESCENDING').limit(5).get()

for log in recent_logs:
    data = log.to_dict()
    print(f'Log ID: {log.id}')
    print(f'  Success: {data.get("success", False)}')
    print(f'  Keywords: {data.get("keywords_processed", [])}')
    print(f'  Total Videos: {data.get("total_videos_collected", 0)}')
    print(f'  Duration: {data.get("duration_seconds", 0):.1f}s')
    print()
