#!/usr/bin/env python3
"""
Create Firestore indexes for sorting collections.
This will enable sorting in the Firebase Console.
"""

import os
import sys
from google.cloud import firestore_admin_v1
from google.oauth2 import service_account

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env

def create_indexes():
    """Create Firestore indexes for sorting"""
    # Load environment
    load_env()
    
    # Get credentials
    service_key_path = os.getenv('GOOGLE_SERVICE_KEY_PATH', '/workspace/youtube_app/ai-tracker-466821-bc88c21c2489.json')
    project_id = os.getenv('FIRESTORE_PROJECT_ID', 'ai-tracker-466821')
    
    if not os.path.exists(service_key_path):
        print(f"❌ Service key not found at: {service_key_path}")
        return
    
    print(f"🔧 Using service key: {service_key_path}")
    print(f"🔧 Project ID: {project_id}")
    
    # Initialize Firestore Admin client
    credentials = service_account.Credentials.from_service_account_file(service_key_path)
    client = firestore_admin_v1.FirestoreAdminClient(credentials=credentials)
    
    # Define parent path
    parent = f"projects/{project_id}/databases/(default)/collectionGroups"
    
    # Define indexes to create
    indexes = [
        {
            "name": "youtube_keywords_keyword_desc",
            "collection_group": "youtube_keywords",
            "fields": [
                {
                    "field_path": "keyword",
                    "order": firestore_admin_v1.Index.IndexField.Order.DESCENDING
                }
            ],
            "query_scope": firestore_admin_v1.Index.QueryScope.COLLECTION
        },
        {
            "name": "youtube_collection_logs_timestamp_desc",
            "collection_group": "youtube_collection_logs",
            "fields": [
                {
                    "field_path": "timestamp",
                    "order": firestore_admin_v1.Index.IndexField.Order.DESCENDING
                }
            ],
            "query_scope": firestore_admin_v1.Index.QueryScope.COLLECTION
        },
        {
            "name": "youtube_keywords_last_collected_desc",
            "collection_group": "youtube_keywords",
            "fields": [
                {
                    "field_path": "last_collected",
                    "order": firestore_admin_v1.Index.IndexField.Order.DESCENDING
                }
            ],
            "query_scope": firestore_admin_v1.Index.QueryScope.COLLECTION
        }
    ]
    
    # Create indexes
    for index_config in indexes:
        try:
            index = firestore_admin_v1.Index(
                query_scope=index_config["query_scope"],
                fields=[
                    firestore_admin_v1.Index.IndexField(
                        field_path=field["field_path"],
                        order=field["order"]
                    ) for field in index_config["fields"]
                ]
            )
            
            parent_path = f"projects/{project_id}/databases/(default)/collectionGroups/{index_config['collection_group']}"
            
            print(f"\n📊 Creating index for {index_config['collection_group']}...")
            print(f"   Fields: {', '.join([f['field_path'] + ' (DESC)' for f in index_config['fields']])}")
            
            operation = client.create_index(
                request={
                    "parent": parent_path,
                    "index": index
                }
            )
            
            print(f"✅ Index creation initiated: {operation.name}")
            print("   Note: Index creation takes a few minutes to complete")
            
        except Exception as e:
            if "already exists" in str(e):
                print(f"ℹ️  Index already exists for {index_config['collection_group']}")
            else:
                print(f"❌ Error creating index: {e}")
    
    print("\n✨ Index creation process completed!")
    print("🔍 Check the Firebase Console in a few minutes to see if sorting is enabled")
    print("📝 You can also check index status at:")
    print(f"   https://console.firebase.google.com/project/{project_id}/firestore/indexes")

if __name__ == "__main__":
    create_indexes()