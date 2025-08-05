#!/usr/bin/env python3
"""Test multi-instance collection with just one instance"""
import sys
sys.path.insert(0, '/opt/youtube_app')

from src.utils.firebase_client_enhanced import FirebaseClient

# Test getting keywords with data
fb = FirebaseClient()
print("Testing get_keywords_with_data()...")

keywords = fb.get_keywords_with_data()
print(f"\nTotal keywords: {len(keywords)}")

if keywords:
    print(f"\nFirst keyword structure:")
    first = keywords[0]
    print(f"Type: {type(first)}")
    print(f"Keyword: {first.get('keyword', 'N/A')}")
    print(f"Category: {first.get('category', 'N/A')}")
    print(f"Active: {first.get('active', 'N/A')}")
    
    # Test distribution
    print(f"\nDistribution for 3 instances:")
    for i in range(1, 4):
        start = (i-1) * (len(keywords) // 3)
        end = start + (len(keywords) // 3) if i < 3 else len(keywords)
        instance_keywords = keywords[start:end]
        print(f"Instance {i}: Keywords {start+1}-{end} ({len(instance_keywords)} keywords)")
        for kw in instance_keywords:
            print(f"  - {kw.get('keyword', 'N/A')}")
else:
    print("No keywords found!")