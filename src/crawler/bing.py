"""
Bing search crawler
"""
import logging
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class BingCrawler(BaseCrawler):
    """Crawler for Bing Search"""
    
    BASE_URL = "https://cn.bing.com/search"
    
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl Bing search results for given keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            
        Returns:
            List of Article objects (empty list on failure)
        """
        articles = []
        
        try:
            # Get homepage first for cookies
            logger.info(f"Crawling Bing for keyword: {keyword}")
            self._make_request("https://cn.bing.com/")
            
            # Bing search parameters
            params = {
                'q': keyword,
                'count': str(max_results),
                'mkt': 'zh-CN',
                'setlang': 'zh-hans',
                'form': 'QBRE'
            }
            
            response = self._make_request(self.BASE_URL, params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check for "no results" page
            if "在此处找不到任何结果" in response.text or "No results found" in response.text:
                logger.warning("Bing returned 'No results found' page")
            
            # Find search results with improved selectors
            results = soup.select('ol#b_results > li.b_algo')
            if not results:
                results = soup.select('li.b_algo')
            if not results:
                results = soup.select('.b_algo')
            
            logger.info(f"Bing returned {len(results)} search results")
            
            # Debug: log first result HTML if available
            if results and len(results) > 0:
                logger.debug(f"First result structure: {results[0].prettify()[:500]}")
            
            for idx, result in enumerate(results[:max_results]):
                # Skip ads and other non-content items
                if result.select_one('.b_ad') or "b_ans" in result.get('class', []):
                    continue
                    
                try:
                    article = self._parse_result(result, keyword)
                    if article:
                        articles.append(article)
                except Exception as e:
                    logger.warning(f"Failed to parse Bing result {idx}: {e}")
                    continue
                
                # Add delay between parsing
                if idx < len(results) - 1:
                    self._random_delay()
            
            logger.info(f"Crawled {len(articles)} articles from Bing for keyword: {keyword}")
            
        except Exception as e:
            logger.error(f"Bing crawler failed for keyword '{keyword}': {e}")
            # Return empty list on failure (don't throw exception)
        
        return articles
    
    def _parse_result(self, result_li, keyword: str) -> Article | None:
        """
        Parse single Bing search result
        
        Args:
            result_li: BeautifulSoup result li element
            keyword: Search keyword
            
        Returns:
            Article object or None if parsing fails
        """
        try:
            # Extract title and URL
            title_elem = result_li.select_one('h2 a') or result_li.select_one('h2')
            if not title_elem:
                return None
            
            link_elem = result_li.select_one('a')
            if not link_elem:
                return None
            
            title = self._extract_text(title_elem)
            url = link_elem.get('href', '')
            
            # Filter out Bing internal links
            if not url.startswith('http') or "bing.com/ck/ms" in url or "microsoft.com" in url:
                return None
            
            # Title too short, likely not a valid result
            if not title or len(title) < 2:
                return None
            
            # Extract content snippet with improved selectors
            snippet_elem = result_li.select_one('.b_caption p') or \
                          result_li.select_one('.b_algoSnippet') or \
                          result_li.select_one('.b_content p') or \
                          result_li.select_one('.b_caption')
            
            content = self._extract_text(snippet_elem) if snippet_elem else title
            
            # Create Article object
            article = Article(
                id=None,
                title=title,
                url=url,
                content=content,
                source='bing',
                keyword=keyword,
                crawled_at=datetime.now(),
                published_at=None
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"Failed to parse Bing result: {e}")
            return None

