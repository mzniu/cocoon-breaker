"""
Huxiu (虎嗅网) crawler using RSS
"""
import logging
from datetime import datetime
from typing import List
import xml.etree.ElementTree as ET

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class HuxiuCrawler(BaseCrawler):
    """Crawler for Huxiu RSS feed (虎嗅网商业科技深度报道)"""
    
    # 使用虎嗅网RSS（稳定可靠）
    RSS_URL = "https://www.huxiu.com/rss/0.xml"
    
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl Huxiu RSS feed and filter by keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            
        Returns:
            List of Article objects (empty list on failure)
        """
        articles = []
        
        try:
            logger.info(f"Crawling Huxiu RSS for keyword: {keyword}")
            
            response = self._make_request(self.RSS_URL)
            response.encoding = 'utf-8'
            
            # Parse RSS XML
            root = ET.fromstring(response.content)
            
            # Find all items in the feed
            items = root.findall('.//item')
            logger.info(f"Huxiu RSS returned {len(items)} total items")
            
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
                    logger.warning(f"Failed to parse Huxiu item: {e}")
                    continue
            
            logger.info(f"Crawled {len(articles)} articles from Huxiu for keyword: {keyword}")
            return articles
            
        except Exception as e:
            logger.error(f"Failed to crawl Huxiu RSS: {e}")
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
                    # Try RFC 2822 format first
                    from email.utils import parsedate_to_datetime
                    published_at = parsedate_to_datetime(pub_date_str)
                except:
                    try:
                        # Fallback: manual parsing
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
                source='huxiu',  # 更改source标识为虎嗅
                keyword=keyword,
                crawled_at=datetime.now(),
                published_at=published_at
            )
            
            logger.debug(f"Parsed Huxiu article: {title[:50]}")
            return article
            
        except Exception as e:
            logger.warning(f"Error parsing Huxiu item: {e}")
            return None
