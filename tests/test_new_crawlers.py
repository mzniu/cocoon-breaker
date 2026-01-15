"""
Test 36Kr and The Paper crawlers
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.crawler.kr36 import Kr36Crawler
from src.crawler.huxiu import HuxiuCrawler


async def test_kr36():
    """Test 36Kr crawler"""
    print("\n=== Testing 36Kr Crawler ===")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ]
    
    crawler = Kr36Crawler(
        user_agents=user_agents,
        request_interval=[1, 2],
        timeout=10
    )
    
    # Test with keyword
    keyword = "人工智能"
    print(f"Searching for: {keyword}")
    
    articles = crawler.crawl(keyword, max_results=5)
    
    print(f"\nFound {len(articles)} articles:")
    for idx, article in enumerate(articles, 1):
        print(f"\n{idx}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   Source: {article.source}")
        print(f"   Published: {article.published_at}")
        print(f"   Content: {article.content[:100]}...")


async def test_huxiu():
    """Test Huxiu (虎嗅网) crawler"""
    print("\n\n=== Testing Huxiu (虎嗅网) Crawler ===")
    
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    ]
    
    crawler = HuxiuCrawler(
        user_agents=user_agents,
        request_interval=[1, 2],
        timeout=10
    )
    
    # Test with keyword
    keyword = "科技"
    print(f"Searching for: {keyword}")
    
    articles = crawler.crawl(keyword, max_results=5)
    
    print(f"\nFound {len(articles)} articles:")
    for idx, article in enumerate(articles, 1):
        print(f"\n{idx}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   Source: {article.source}")
        print(f"   Published: {article.published_at}")
        print(f"   Content: {article.content[:100]}...")


async def main():
    """Run all tests"""
    try:
        await test_kr36()
        await test_huxiu()
        print("\n\n✅ All tests completed!")
    except Exception as e:
        print(f"\n\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
