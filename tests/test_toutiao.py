"""
Test Toutiao crawler
"""
from src.crawler.toutiao import ToutiaoCrawler
from src.config import Config

def test_toutiao():
    config = Config()
    
    crawler = ToutiaoCrawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=30
    )
    
    keyword = "人工智能"
    print(f"Testing Toutiao crawler with keyword: {keyword}")
    
    articles = crawler.crawl(keyword, max_results=20)  # Config default
    
    print(f"\nFound {len(articles)} articles:")
    for i, article in enumerate(articles, 1):
        print(f"\n{i}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   Content: {article.content[:100]}...")
        print(f"   Source: {article.source}")

if __name__ == "__main__":
    test_toutiao()
