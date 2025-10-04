#!/usr/bin/env python3
"""
Test script for Web Crawler Agent
"""
import asyncio
from agents.web_crawler.agent import WebCrawlerAgent

async def test_web_crawler():
    """Test the web crawler agent"""
    config = {}
    crawler = WebCrawlerAgent(config)

    # Test URLs
    urls = ["https://www.google.com", "https://www.wikipedia.org"]

    print("Testing Web Crawler Agent...")
    print(f"URLs to crawl: {urls}")

    try:
        results = await crawler.execute({"urls": urls})
        print("✅ Crawler test successful!")
        print(f"Results: {results}")

        # Print detailed results
        for result in results["results"]:
            print(f"\n--- Results for {result['url']} ---")
            print(f"Title: {result['data']['title']}")
            print(f"Text length: {len(result['data']['text'])} characters")
            print(f"Text preview: {result['data']['text'][:200]}...")

    except Exception as e:
        print(f"❌ Crawler test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_web_crawler())
