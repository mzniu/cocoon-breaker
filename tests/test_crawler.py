"""
Quick crawler test script
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.crawler.baidu import BaiduCrawler
from src.crawler.yahoo import YahooCrawler
from src.crawler.google import GoogleCrawler
from src.config import get_config

def test_crawlers():
    """Test all crawlers"""
    keyword = "AI 资讯"
    
    print(f"\n{'='*60}")
    print(f"Testing crawlers with keyword: {keyword}")
    print(f"{'='*60}\n")
    
    # Load config
    config = get_config()
    
    # Test Baidu
    print("Testing Baidu Crawler...")
    baidu = BaiduCrawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=config.crawler.timeout
    )
    baidu_articles = baidu.crawl(keyword, max_results=5)
    print(f"✓ Baidu returned {len(baidu_articles)} articles")
    
    if baidu_articles:
        print(f"\nFirst article:")
        print(f"  Title: {baidu_articles[0].title}")
        print(f"  URL: {baidu_articles[0].url[:100]}...")
        print(f"  Content: {baidu_articles[0].content[:100]}...")
    else:
        print("⚠ No articles found from Baidu")
    
    print(f"\n{'-'*60}\n")
    
    # Test Yahoo
    print("Testing Yahoo Crawler...")
    yahoo = YahooCrawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=config.crawler.timeout
    )
    yahoo_articles = yahoo.crawl(keyword, max_results=5)
    print(f"✓ Yahoo returned {len(yahoo_articles)} articles")
    
    if yahoo_articles:
        print(f"\nFirst article:")
        print(f"  Title: {yahoo_articles[0].title}")
        print(f"  URL: {yahoo_articles[0].url[:100]}...")
        print(f"  Content: {yahoo_articles[0].content[:100]}...")
    else:
        print("⚠ No articles found from Yahoo")
    
    print(f"\n{'-'*60}\n")
    
    # Test Google (if configured)
    print("Testing Google Crawler (API)...")
    google = GoogleCrawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=config.crawler.timeout
    )
    
    # Check if Google API is configured
    if config.google.enabled and config.google.api_key and config.google.search_engine_id:
        google.set_api_credentials(
            config.google.api_key,
            config.google.search_engine_id
        )
        google_articles = google.crawl(keyword, max_results=5)
        print(f"✓ Google returned {len(google_articles)} articles")
        
        if google_articles:
            print(f"\nFirst article:")
            print(f"  Title: {google_articles[0].title}")
            print(f"  URL: {google_articles[0].url[:100]}...")
            print(f"  Content: {google_articles[0].content[:100]}...")
        else:
            print("⚠ No articles found from Google")
    else:
        print("⚠ Google API not configured (set GOOGLE_API_KEY and GOOGLE_SEARCH_ENGINE_ID)")
        print("  Enable in config.yaml: google.enabled = true")
        google_articles = []
    
    print(f"\n{'='*60}")
    print(f"Total articles: {len(baidu_articles) + len(yahoo_articles) + len(google_articles)}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    test_crawlers()
