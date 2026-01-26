"""
Test Kr36 and Huxiu crawlers to see what content they find
"""
import asyncio
from src.crawler.kr36 import Kr36Crawler
from src.crawler.huxiu import HuxiuCrawler
from src.config import Config

async def test_crawlers():
    config = Config()
    
    # Test keyword from subscriptions
    keyword = "AI 资讯"
    
    print("=" * 80)
    print(f"Testing crawlers with keyword: {keyword}")
    print("=" * 80)
    
    # Test Kr36
    print("\n【36氪 (Kr36)】")
    print("-" * 80)
    kr36_crawler = Kr36Crawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=config.crawler.timeout
    )
    
    kr36_articles = kr36_crawler.crawl(keyword, max_results=20)
    print(f"Found {len(kr36_articles)} articles from 36氪:")
    for i, article in enumerate(kr36_articles, 1):
        print(f"\n{i}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   Content: {article.content[:150]}...")
        print(f"   Published: {article.published_at}")
    
    if not kr36_articles:
        print("⚠️ No articles matched the keyword")
    
    # Test Huxiu
    print("\n" + "=" * 80)
    print("【虎嗅网 (Huxiu)】")
    print("-" * 80)
    huxiu_crawler = HuxiuCrawler(
        user_agents=config.crawler.user_agents,
        request_interval=config.crawler.request_interval,
        timeout=config.crawler.timeout
    )
    
    huxiu_articles = huxiu_crawler.crawl(keyword, max_results=20)
    print(f"Found {len(huxiu_articles)} articles from 虎嗅:")
    for i, article in enumerate(huxiu_articles, 1):
        print(f"\n{i}. {article.title}")
        print(f"   URL: {article.url}")
        print(f"   Content: {article.content[:150]}...")
        print(f"   Published: {article.published_at}")
    
    if not huxiu_articles:
        print("⚠️ No articles matched the keyword")
    
    print("\n" + "=" * 80)
    print(f"Summary: {len(kr36_articles)} from 36氪, {len(huxiu_articles)} from 虎嗅")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_crawlers())
