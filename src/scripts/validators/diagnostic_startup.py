#\!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/opt/youtube_app')

print(f"Python executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Working directory: {os.getcwd()}")
print(f"sys.path[0:3]: {sys.path[0:3]}")

try:
    from src.utils.firebase_client import FirebaseClient
    print("FirebaseClient imported from src.utils.firebase_client")
    print(f"FirebaseClient module: {FirebaseClient.__module__}")
    print(f"Has get_keywords: {hasattr(FirebaseClient, 'get_keywords')}")
    print(f"Has log_collection_run: {hasattr(FirebaseClient, 'log_collection_run')}")
except Exception as e:
    print(f"Error importing FirebaseClient: {e}")

# Test instantiation with env vars
os.environ['GOOGLE_SERVICE_KEY_PATH'] = '/opt/youtube_app/ai-tracker-466821-892ecf5150a3.json'
try:
    fc = FirebaseClient()
    print("FirebaseClient instantiated successfully")
except Exception as e:
    print(f"Error instantiating FirebaseClient: {e}")
