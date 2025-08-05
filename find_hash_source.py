#!/usr/bin/env python3
"""Find source of new hash document and delete it"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.env_loader import load_env
from src.utils.firebase_client import FirebaseClient

# Load environment
load_env()

# Initialize Firebase
firebase = FirebaseClient()

print("Finding source of hash document: JcrpFGq6q2jSFK0WLGpQ")
print("=" * 60)

# Get the specific hash document
collection_ref = firebase.db.collection('youtube_collection_logs')
doc = collection_ref.document('JcrpFGq6q2jSFK0WLGpQ').get()

if doc.exists:
    doc_data = doc.to_dict()
    print("Hash document found:")
    print(f"  ID: JcrpFGq6q2jSFK0WLGpQ")
    print(f"  Data keys: {list(doc_data.keys())}")
    print(f"  Timestamp: {doc_data.get('timestamp', 'Unknown')}")
    print(f"  Script: {doc_data.get('script_name', 'Unknown')}")
    print(f"  Type: {doc_data.get('type', 'Unknown')}")
    print(f"  Run type: {doc_data.get('run_type', 'Unknown')}")
    
    # Show full document for debugging
    print("\nFull document data:")
    for key, value in doc_data.items():
        print(f"  {key}: {value}")
    
    # Delete the hash document
    print(f"\nDeleting hash document...")
    collection_ref.document('JcrpFGq6q2jSFK0WLGpQ').delete()
    print("✅ Hash document deleted")
    
else:
    print("Hash document not found - may have been deleted already")

print("\nChecking for other recent hash documents...")

# Get all documents and check for recent hashes
docs = collection_ref.stream()
import re
hash_pattern = re.compile(r'^[a-zA-Z0-9]{15,25}$')

recent_hashes = []
for doc in docs:
    if hash_pattern.match(doc.id):
        doc_data = doc.to_dict()
        recent_hashes.append({
            'id': doc.id,
            'timestamp': doc_data.get('timestamp', 'Unknown'),
            'type': doc_data.get('type', 'Unknown'),
            'script': doc_data.get('script_name', 'Unknown')
        })

if recent_hashes:
    print(f"\nFound {len(recent_hashes)} hash documents:")
    for hash_doc in sorted(recent_hashes, key=lambda x: str(x['timestamp']), reverse=True)[:5]:
        print(f"  - {hash_doc['id']} ({hash_doc['type']}, {hash_doc['timestamp']})")
else:
    print("No other hash documents found")