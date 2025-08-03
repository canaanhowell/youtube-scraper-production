#!/usr/bin/env python3
"""Test YouTube scraping with Playwright directly"""

import asyncio
from playwright.async_api import async_playwright
import json

async def test_youtube_scraping():
    """Test basic YouTube scraping without dependencies"""
    async with async_playwright() as p:
        # Launch browser (visible for testing)
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # Search keyword
            keyword = "Python programming"
            print(f"Searching YouTube for: {keyword}")
            
            # Go to YouTube
            await page.goto("https://www.youtube.com")
            await page.wait_for_timeout(2000)
            
            # Search for keyword
            search_box = await page.wait_for_selector('input[id="search"]', timeout=5000)
            await search_box.fill(keyword)
            await search_box.press("Enter")
            
            # Wait for results
            await page.wait_for_selector('ytd-video-renderer', timeout=10000)
            await page.wait_for_timeout(2000)
            
            # Get video results
            videos = await page.query_selector_all('ytd-video-renderer')
            
            print(f"\n✅ Found {len(videos)} videos")
            
            results = []
            for i, video in enumerate(videos[:5]):  # Get first 5 videos
                try:
                    # Get video data
                    title_elem = await video.query_selector('h3 a#video-title')
                    title = await title_elem.get_attribute('title') if title_elem else "No title"
                    
                    url_elem = await video.query_selector('h3 a#video-title')
                    url = await url_elem.get_attribute('href') if url_elem else ""
                    if url and not url.startswith('http'):
                        url = f"https://www.youtube.com{url}"
                    
                    channel_elem = await video.query_selector('ytd-channel-name a')
                    channel = await channel_elem.inner_text() if channel_elem else "Unknown"
                    
                    views_elem = await video.query_selector('span.inline-metadata-item:first-child')
                    views_text = await views_elem.inner_text() if views_elem else "0 views"
                    
                    video_data = {
                        'title': title,
                        'url': url,
                        'channel': channel,
                        'views_text': views_text
                    }
                    
                    results.append(video_data)
                    
                    print(f"\n{i+1}. {title}")
                    print(f"   Channel: {channel}")
                    print(f"   Views: {views_text}")
                    print(f"   URL: {url}")
                    
                except Exception as e:
                    print(f"Error parsing video {i+1}: {e}")
            
            # Save results
            with open('test_results.json', 'w') as f:
                json.dump(results, f, indent=2)
            print(f"\n💾 Results saved to test_results.json")
            
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            await browser.close()

if __name__ == "__main__":
    print("🧪 Testing YouTube scraper with Playwright...")
    asyncio.run(test_youtube_scraping())