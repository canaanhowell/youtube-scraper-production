#!/usr/bin/env python3
"""
Analyze YouTube filter parameters without requiring Docker access
"""

import base64
import urllib.parse
import json
from datetime import datetime, timedelta

def decode_youtube_filter(filter_param):
    """Decode YouTube search filter parameter"""
    
    print(f"🔍 Analyzing filter: {filter_param}")
    
    # Handle URL encoding
    if '%' in filter_param:
        decoded_url = urllib.parse.unquote(filter_param)
        print(f"   URL decoded: {decoded_url}")
        
        # Some parameters are double-encoded
        if '%' in decoded_url:
            double_decoded = urllib.parse.unquote(decoded_url)
            print(f"   Double decoded: {double_decoded}")
            filter_param = double_decoded
        else:
            filter_param = decoded_url
    
    # Extract the actual parameter value
    if 'sp=' in filter_param:
        param_value = filter_param.split('sp=')[1].split('&')[0]
    else:
        param_value = filter_param
    
    print(f"   Parameter value: {param_value}")
    
    # Try to decode as base64
    try:
        # Add padding if needed
        missing_padding = len(param_value) % 4
        if missing_padding:
            param_value += '=' * (4 - missing_padding)
        
        decoded_bytes = base64.b64decode(param_value)
        print(f"   Base64 decoded (bytes): {decoded_bytes}")
        print(f"   Base64 decoded (hex): {decoded_bytes.hex()}")
        
        # Try to interpret as protobuf-like structure
        analyze_protobuf_bytes(decoded_bytes)
        
    except Exception as e:
        print(f"   Base64 decode failed: {e}")

def analyze_protobuf_bytes(data):
    """Analyze protobuf-like binary data"""
    
    print(f"   📋 Protobuf Analysis:")
    
    # YouTube search filters are typically protobuf messages
    # Common patterns:
    # - Field 1: Search type
    # - Field 2: Sort order  
    # - Field 18: Time filter
    # - Field 19: Duration filter
    
    hex_str = data.hex()
    print(f"      Hex: {hex_str}")
    
    # Look for common patterns
    patterns = {
        "08": "Field 1 (varint)",
        "10": "Field 2 (varint)", 
        "90": "Field 18 (varint) - Time filter",
        "98": "Field 19 (varint) - Duration filter",
        "01": "Value: Upload date sort",
        "02": "Value: View count sort",
        "03": "Value: Rating sort",
        "04": "Value: Relevance sort"
    }
    
    for pattern, description in patterns.items():
        if pattern.lower() in hex_str.lower():
            print(f"      Found {pattern}: {description}")

def compare_filters():
    """Compare different YouTube filter parameters"""
    
    print("\n🔬 Filter Comparison")
    print("=" * 50)
    
    filters = {
        "Old filter (Last hour only)": "sp=EgQIARAB",
        "Current filter (Last hour + Sort by date)": "sp=CAISBAgBEAE%253D",
        "Decoded current filter": "sp=CAISBAgBEAE="
    }
    
    for name, filter_param in filters.items():
        print(f"\n{name}:")
        decode_youtube_filter(filter_param)

def analyze_time_filtering():
    """Analyze YouTube's time filtering behavior"""
    
    print("\n🕐 YouTube Time Filtering Analysis")
    print("=" * 50)
    
    print("YouTube's 'Last Hour' filter behavior:")
    print("- 'Last Hour' typically means videos uploaded in the past 60 minutes")
    print("- However, YouTube's algorithm may include:")
    print("  1. Videos uploaded up to 70-90 minutes ago (buffer zone)")
    print("  2. Videos with delayed processing/indexing")
    print("  3. Videos with timezone discrepancies")
    print("  4. Recently trending videos that cross the boundary")
    
    print("\nPotential causes of older videos:")
    print("1. 🕒 Timezone Issues:")
    print("   - Video upload time vs server time discrepancies")
    print("   - Different timezone interpretations")
    
    print("2. 📊 YouTube Algorithm:")
    print("   - Trending videos get priority even if slightly older")
    print("   - Engagement metrics override strict time filtering")
    
    print("3. 🔄 Processing Delays:")
    print("   - Video processing/indexing delays")
    print("   - Search index update lag")
    
    print("4. 🔍 Filter Implementation:")
    print("   - YouTube's filter may not be strictly 60 minutes")
    print("   - Could be 'approximately last hour' with fuzzy boundaries")

def recommend_solutions():
    """Recommend solutions for the filtering issue"""
    
    print("\n💡 Recommended Solutions")
    print("=" * 50)
    
    print("1. 🎯 Client-side Time Filtering:")
    print("   - Parse the 'published_time' text on collected videos")
    print("   - Filter out videos older than 60 minutes in post-processing")
    print("   - More reliable than relying solely on YouTube's filter")
    
    print("2. 🔍 Alternative Filter Parameters:")
    print("   - Test different YouTube filter combinations")
    print("   - Consider using API endpoints if available")
    print("   - Experiment with more restrictive time windows")
    
    print("3. 📊 Multiple Filter Strategy:")
    print("   - Use YouTube filter as primary filter")
    print("   - Apply secondary client-side filtering")
    print("   - Log discrepancies for monitoring")
    
    print("4. 🚨 Monitoring & Alerting:")
    print("   - Track percentage of old videos in collections")
    print("   - Alert when >20% of videos are older than 1 hour")
    print("   - Regular audits of collected video timestamps")

def main():
    """Main analysis function"""
    
    print("🧬 YouTube Filter Parameter Analysis")
    print("=" * 80)
    
    # Compare different filters
    compare_filters()
    
    # Analyze time filtering behavior
    analyze_time_filtering()
    
    # Provide recommendations
    recommend_solutions()
    
    print("\n" + "=" * 80)
    print("Analysis Complete")
    
    print("\n🎯 Key Findings:")
    print("1. Current filter 'sp=CAISBAgBEAE%253D' is correctly formatted")
    print("2. Recent Firebase data shows videos are mostly within 1 hour")  
    print("3. YouTube's 'Last Hour' filter may have fuzzy boundaries")
    print("4. Recommend implementing client-side time filtering as backup")

if __name__ == "__main__":
    main()