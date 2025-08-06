#!/usr/bin/env python3
"""
Research alternative YouTube filter parameters
"""

import base64
import urllib.parse

def research_youtube_filters():
    """Research different YouTube filter combinations"""
    
    print("🔬 YouTube Filter Parameter Research")
    print("=" * 80)
    
    print("\n📚 Known YouTube Search Filters:")
    
    # Time-based filters
    time_filters = {
        "Last hour": "EgQIARAB",
        "Today": "EgQIAhAB", 
        "This week": "EgQIAxAB",
        "This month": "EgQIBBAB",
        "This year": "EgQIBRAB"
    }
    
    print("\n🕐 Time Filters:")
    for name, filter_code in time_filters.items():
        decoded = decode_filter(filter_code)
        print(f"   {name:15s}: sp={filter_code} -> {decoded}")
    
    # Sort order filters  
    sort_filters = {
        "Relevance": "CAASAhAB",
        "Upload date": "CAISAhAB", 
        "View count": "CAMSAhAB",
        "Rating": "CAESAhAB"
    }
    
    print("\n📊 Sort Filters:")
    for name, filter_code in sort_filters.items():
        decoded = decode_filter(filter_code)
        print(f"   {name:15s}: sp={filter_code} -> {decoded}")
    
    # Combined filters (time + sort)
    combined_filters = {
        "Last hour + Upload date": "CAISBAgBEAE%3D",
        "Last hour + Upload date (double-encoded)": "CAISBAgBEAE%253D",
        "Today + Upload date": "CAISBAgCEAE%3D",
        "Last hour + View count": "CAMSBAgBEAE%3D",
        "Last hour + Relevance": "CAASBAgBEAE%3D"
    }
    
    print("\n🔄 Combined Filters:")
    for name, filter_code in combined_filters.items():
        # Handle URL encoding
        decoded_url = urllib.parse.unquote(filter_code)
        if '%' in decoded_url:
            decoded_url = urllib.parse.unquote(decoded_url)
        
        param = decoded_url.split('=')[1] if '=' in decoded_url else filter_code
        decoded = decode_filter(param)
        print(f"   {name:35s}: sp={filter_code}")
        print(f"   {' ' * 37}-> {decoded}")
    
    # Duration filters
    duration_filters = {
        "Under 4 minutes": "EgQQARgB",
        "4-20 minutes": "EgQQARgC", 
        "Over 20 minutes": "EgQQARgD"
    }
    
    print("\n⏱️  Duration Filters:")
    for name, filter_code in duration_filters.items():
        decoded = decode_filter(filter_code)
        print(f"   {name:20s}: sp={filter_code} -> {decoded}")

def decode_filter(filter_code):
    """Decode a YouTube filter parameter"""
    try:
        # Add padding if needed
        missing_padding = len(filter_code) % 4
        if missing_padding:
            filter_code += '=' * (4 - missing_padding)
        
        decoded_bytes = base64.b64decode(filter_code)
        return f"bytes({decoded_bytes.hex()})"
    except:
        return "decode_error"

def suggest_alternative_filters():
    """Suggest alternative filter strategies"""
    
    print("\n💡 Alternative Filter Strategies")
    print("=" * 50)
    
    print("1. 🎯 Stricter Time Window:")
    print("   - Problem: 'Last hour' might be ~70-90 minutes")
    print("   - Solution: No stricter time filter available")
    print("   - Verdict: Client-side filtering is the only option")
    
    print("\n2. 🔄 Different Sort Orders:")
    print("   - Current: Upload date + Last hour")
    print("   - Alternative: Relevance + Last hour")
    print("   - Concern: May get less recent but more popular videos")
    print("   - Verdict: Upload date sort is optimal for recent content")
    
    print("\n3. 📊 Multiple Requests:")
    print("   - Strategy: Make multiple requests with different filters")
    print("   - Example: 'Last hour' + 'Today' with deduplication")
    print("   - Concern: Increased API calls and complexity")
    print("   - Verdict: Not recommended for production")
    
    print("\n4. 🕐 Time-based Scheduling:")
    print("   - Strategy: Adjust collection frequency")
    print("   - Example: Run every 30 minutes instead of 60")
    print("   - Benefit: Catch more truly recent content")
    print("   - Verdict: Good complement to client-side filtering")
    
    print("\n5. 🎪 API Alternatives:")
    print("   - YouTube Data API v3 has publishedAfter parameter")
    print("   - More precise time filtering")
    print("   - Concern: API quotas and costs")
    print("   - Verdict: Consider for future if scraping becomes unreliable")

def final_recommendations():
    """Provide final recommendations"""
    
    print("\n🎯 Final Recommendations")
    print("=" * 50)
    
    print("✅ KEEP current filter: sp=CAISBAgBEAE%253D")
    print("   - Correctly formatted and working")
    print("   - Gets most recent content sorted by upload date")
    print("   - Issue is with YouTube's fuzzy time boundaries")
    
    print("\n✅ IMPLEMENT client-side time filtering:")
    print("   - Parse 'published_time' text from each video")
    print("   - Filter out videos older than 60 minutes")
    print("   - Configurable threshold via environment variables")
    print("   - Log filtered videos for monitoring")
    
    print("\n✅ MONITOR filtering effectiveness:")
    print("   - Track percentage of videos filtered client-side")
    print("   - Alert if >10% of videos are filtered (indicates YouTube issues)")
    print("   - Adjust thresholds based on observed patterns")
    
    print("\n✅ OPTIONAL optimizations:")
    print("   - Increase collection frequency (every 30-45 minutes)")
    print("   - Add timezone awareness to time parsing")
    print("   - Consider YouTube Data API for critical keywords")
    
    print("\n❌ DO NOT change YouTube filter parameters:")
    print("   - Current filter is optimal for our use case")
    print("   - No stricter time filters available")
    print("   - Alternative sorts would reduce content freshness")

def main():
    """Main research function"""
    
    research_youtube_filters()
    suggest_alternative_filters()
    final_recommendations()

if __name__ == "__main__":
    main()