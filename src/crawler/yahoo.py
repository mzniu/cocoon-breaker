"""
Yahoo Search Crawler
"""
import logging
import re
import urllib.parse
from typing import List
from datetime import datetime

from bs4 import BeautifulSoup

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class YahooCrawler(BaseCrawler):
    """Yahoo search crawler"""
    
    def __init__(self, user_agents: List[str], request_interval: tuple = (1, 3), timeout: int = 10):
        """Initialize Yahoo crawler"""
        super().__init__(user_agents, request_interval, timeout)
        self.search_url = "https://search.yahoo.com/search"
    
    def crawl(self, keyword: str, max_results: int = 10) -> List[Article]:
        """
        Crawl Yahoo search results
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return
        
        Returns:
            List of Article objects
        """
        try:
            logger.info(f"Starting Yahoo search for keyword: {keyword}")
            
            # Visit homepage first to get cookies
            try:
                self._make_request("https://search.yahoo.com/")
                self._random_sleep()
            except Exception as e:
                logger.warning(f"Failed to visit Yahoo homepage: {e}")
            
            # Build search URL
            params = {
                'p': keyword,
                'n': max_results,
            }
            url = f"{self.search_url}?{urllib.parse.urlencode(params)}"
            
            # Make request
            response = self._make_request(url)
            if not response:
                logger.warning(f"No response from Yahoo for keyword: {keyword}")
                return []
            
            # Parse results
            soup = BeautifulSoup(response.text, 'html.parser')
            articles = []
            
            # Find search result items
            items = soup.select('div.algo-sr')
            logger.info(f"Found {len(items)} items in Yahoo search results")
            
            if len(items) == 0:
                logger.warning("No search results found, checking page content...")
                logger.debug(f"Page title: {soup.title.string if soup.title else 'No title'}")
            
            for item in items:
                if len(articles) >= max_results:
                    break
                
                try:
                    # Extract title
                    h3 = item.find('h3')
                    if not h3:
                        continue
                    
                    title = h3.get_text().strip()
                    if not title:
                        continue
                    
                    # Extract URL
                    result_url = None
                    for a in item.find_all('a', href=True):
                        href = a.get('href', '')
                        
                        # Yahoo redirect link
                        if 'r.search.yahoo.com' in href:
                            match = re.search(r'/RU=([^/]+)/', href)
                            if match:
                                result_url = urllib.parse.unquote(match.group(1))
                                break
                        # Direct external link
                        elif href.startswith('http') and 'yahoo.com' not in href:
                            result_url = href
                            break
                    
                    if not result_url:
                        continue
                    
                    # Extract snippet/content
                    snippet = ""
                    for selector in ['span.fc-falcon', 'p.fz-ms', 'p', 'span.d-b']:
                        snippet_elem = item.select_one(selector)
                        if snippet_elem:
                            text = snippet_elem.get_text().strip()
                            if len(text) > 20:
                                snippet = text
                                break
                    
                    if not snippet:
                        snippet = "无摘要"
                    
                    # Create Article object
                    article = Article(
                        id=None,
                        title=title,
                        url=result_url,
                        content=snippet,
                        source="yahoo",
                        keyword=keyword,
                        crawled_at=datetime.now(),
                        published_at=None
                    )
                    
                    articles.append(article)
                    logger.debug(f"Extracted article: {title[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error parsing Yahoo search item: {e}")
                    continue
            
            logger.info(f"Successfully crawled {len(articles)} articles from Yahoo for keyword: {keyword}")
            
            # Log first result for debugging
            if articles:
                first = articles[0]
                logger.debug(f"First result: {first.title}")
                logger.debug(f"First result URL: {first.url}")
            
            return articles
            
        except Exception as e:
            logger.error(f"Error crawling Yahoo for keyword {keyword}: {e}")
            return []
