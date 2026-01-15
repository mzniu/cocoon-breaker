"""
Baidu news crawler
"""
import logging
from datetime import datetime
from typing import List
from urllib.parse import quote

from bs4 import BeautifulSoup

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class BaiduCrawler(BaseCrawler):
    """Crawler for Baidu News"""
    
    BASE_URL = "https://www.baidu.com/s"
    
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl Baidu news for given keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            
        Returns:
            List of Article objects (empty list on failure)
        """
        articles = []
        
        try:
            # Get homepage first for cookies
            logger.info(f"Crawling Baidu for keyword: {keyword}")
            self._make_request("https://www.baidu.com/")
            
            # Baidu search parameters
            params = {
                'wd': keyword,
                'pn': 0,  # Page number (0 = first page)
                'ie': 'utf-8',
                'rn': str(max_results)  # Results per page
            }
            
            response = self._make_request(self.BASE_URL, params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for security verification
            if "安全验证" in response.text or "verify.baidu.com" in response.text:
                logger.warning("Baidu triggered security check, results may be limited")
            
            # Find search results with improved selectors
            results = soup.select('.result.c-container')
            if not results:
                results = soup.select('div[class*="result"]')
            
            logger.info(f"Baidu returned {len(results)} search results")
            
            # Debug: log first result HTML if available
            if results and len(results) > 0:
                logger.debug(f"First result structure: {results[0].prettify()[:500]}")
            
            for idx, result in enumerate(results[:max_results]):
                try:
                    article = self._parse_result(result, keyword)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse Baidu result {idx}: {e}")
                    continue
                
                # Add delay between parsing (avoid rate limiting)
                if idx < len(results) - 1:
                    self._random_delay()
            
            logger.info(f"Crawled {len(articles)} articles from Baidu for keyword: {keyword}")
            
        except Exception as e:
            logger.error(f"Baidu crawler failed for keyword '{keyword}': {e}")
            # Return empty list on failure (don't throw exception)
        
        return articles
    
    def _parse_result(self, result_div, keyword: str) -> Article | None:
        """
        Parse single Baidu search result
        
        Args:
            result_div: BeautifulSoup result div element
            keyword: Search keyword
            
        Returns:
            Article object or None if parsing fails
        """
        try:
            # Extract title and URL - improved selectors
            title_elem = result_div.select_one('h3 a') or result_div.select_one('h3')
            if not title_elem:
                return None
            
            link_elem = result_div.select_one('h3 a') or result_div.select_one('a')
            if not link_elem:
                return None
            
            title = self._extract_text(title_elem)
            url = link_elem.get('href', '')
            
            # Handle relative URLs
            if url.startswith('/'):
                url = "https://www.baidu.com" + url
            
            if not title or not url:
                return None
            
            # Extract content snippet with improved selectors
            content_elem = result_div.select_one('.c-abstract') or \
                          result_div.select_one('div[class*="content-"]') or \
                          result_div.select_one('.op-se-it-content')
            
            if content_elem:
                content = self._extract_text(content_elem)
            else:
                # Fallback: extract text from entire result and remove title
                full_text = self._extract_text(result_div)
                content = full_text.replace(title, '', 1).strip()
                if len(content) > 200:
                    content = content[:200] + "..."
            
            # Use title as content if nothing else found
            if not content or content == "...":
                content = title
            
            # Create Article object
            article = Article(
                id=None,
                title=title,
                url=url,
                content=content,
                source='baidu',
                keyword=keyword,
                crawled_at=datetime.now(),
                published_at=None  # Baidu doesn't always provide publish date
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Failed to parse Baidu result: {e}")
            return None
