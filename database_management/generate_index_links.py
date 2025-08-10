#!/usr/bin/env python3
"""
Generate Firestore index creation links by running queries that require indexes.
When these queries fail, they provide direct links to create the required indexes.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.utils.firebase_client_enhanced import FirebaseClient

def generate_index_links():
    """Run queries that require indexes to generate creation links"""
    # Load environment
    load_env()
    
    # Initialize Firebase client
    firebase = FirebaseClient()
    
    print("🔧 Running queries to generate index creation links...")
    print("📝 When each query fails, it will provide a direct link to create the required index\n")
    
    queries = [
        {
            "name": "YouTube Keywords - Sort by keyword (descending)",
            "collection": "youtube_keywords",
            "query": lambda: firebase.db.collection('youtube_keywords').order_by('keyword', direction='DESCENDING').limit(1).get()
        },
        {
            "name": "YouTube Keywords - Sort by last_collected (descending)", 
            "collection": "youtube_keywords",
            "query": lambda: firebase.db.collection('youtube_keywords').order_by('last_collected', direction='DESCENDING').limit(1).get()
        },
        {
            "name": "YouTube Collection Logs - Sort by timestamp (descending)",
            "collection": "youtube_collection_logs", 
            "query": lambda: firebase.db.collection('youtube_collection_logs').order_by('timestamp', direction='DESCENDING').limit(1).get()
        },
        {
            "name": "YouTube Keywords - Active + Sort by keyword",
            "collection": "youtube_keywords",
            "query": lambda: firebase.db.collection('youtube_keywords').where('active', '==', True).order_by('keyword', direction='DESCENDING').limit(1).get()
        }
    ]
    
    for query_info in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query_info['name']}")
        print(f"Collection: {query_info['collection']}")
        
        try:
            # Try to execute the query
            result = query_info['query']()
            docs = list(result)
            print(f"✅ Index already exists! Found {len(docs)} documents")
            
        except Exception as e:
            error_msg = str(e)
            
            # Look for the index creation URL in the error message
            if "https://console.firebase.google.com" in error_msg:
                # Extract the URL from the error message
                import re
                url_match = re.search(r'(https://console\.firebase\.google\.com/[^\s]+)', error_msg)
                
                if url_match:
                    index_url = url_match.group(1)
                    print(f"❌ Index required!")
                    print(f"\n🔗 Click this link to create the index:")
                    print(f"   {index_url}")
                    print(f"\n📝 Or copy and paste into your browser")
                else:
                    print(f"❌ Error: {error_msg}")
            else:
                print(f"ℹ️  Query executed but no index link generated")
                print(f"   Error: {error_msg}")
    
    print(f"\n{'='*60}")
    print("\n✅ Process completed!")
    print("\n📋 Next steps:")
    print("1. Click each link above to create the required indexes")
    print("2. Wait 2-5 minutes for indexes to build")
    print("3. Sorting will then be enabled in the Firebase Console")
    print("\n💡 Tip: Once created, indexes are permanent and don't need to be recreated")

if __name__ == "__main__":
    generate_index_links()