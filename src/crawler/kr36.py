"""
36Kr (36氪) news crawler
"""
import logging
from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class Kr36Crawler(BaseCrawler):
    """Crawler for 36Kr RSS feed"""
    
    RSS_URL = "https://36kr.com/feed"
    
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl 36Kr RSS feed and filter by keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            
        Returns:
            List of Article objects (empty list on failure)
        """
        articles = []
        
        try:
            logger.info(f"Crawling 36Kr RSS for keyword: {keyword}")
            
            response = self._make_request(self.RSS_URL)
            response.encoding = 'utf-8'
            
            # Parse RSS XML
            root = ET.fromstring(response.content)
            
            # Find all items in the feed
            items = root.findall('.//item')
            logger.info(f"36Kr RSS returned {len(items)} total items")
            
            matched_count = 0
            for item in items:
                if matched_count >= max_results:
                    break
                
                try:
                    article = self._parse_item(item, keyword)
                    if article:
                        articles.append(article)
                        matched_count += 1
                except Exception as e:
                    logger.warning(f"Failed to parse 36Kr item: {e}")
                    continue
            
            logger.info(f"Crawled {len(articles)} articles from 36Kr for keyword: {keyword}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to crawl 36Kr RSS: {e}")
            return []
    
    def _parse_item(self, item: ET.Element, keyword: str) -> Article | None:
        """Parse RSS item to Article"""
        try:
            title = item.findtext('title', '').strip()
            link = item.findtext('link', '').strip()
            description = item.findtext('description', '').strip()
            pub_date_str = item.findtext('pubDate', '')
            
            # Filter by keyword (case insensitive search in title and description)
            keyword_lower = keyword.lower()
            if keyword_lower not in title.lower() and keyword_lower not in description.lower():
                return None
            
            # Parse publication date (RSS date format: Wed, 15 Jan 2026 10:00:00 +0800)
            published_at = None
            if pub_date_str:
                try:
                    # Remove timezone info for simpler parsing
                    date_part = pub_date_str.rsplit(' ', 1)[0]
                    published_at = datetime.strptime(date_part, '%a, %d %b %Y %H:%M:%S')
                except:
                    logger.debug(f"Failed to parse date: {pub_date_str}")
            
            # Extract content from description (remove HTML tags)
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(description, 'html.parser')
            content = soup.get_text().strip()
            
            # Limit content length
            if len(content) > 1000:
                content = content[:1000] + "..."
            
            article = Article(
                id=None,
                title=title,
                url=link,
                content=content if content else title,
                source='36kr',
                keyword=keyword,
                crawled_at=datetime.now(),
                published_at=published_at
            )
            
            logger.debug(f"Parsed 36Kr article: {title[:50]}")
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing 36Kr item: {e}")
            return None
