"""
Google Search Crawler (using Custom Search API)
"""
import logging
import requests
from typing import List
from datetime import datetime

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class GoogleCrawler(BaseCrawler):
    """Google search crawler using Custom Search API"""
    
    def __init__(self, user_agents: List[str], request_interval: tuple = (1, 2), timeout: int = 10):
        """Initialize Google crawler"""
        super().__init__(user_agents, request_interval, timeout)
        self.api_url = "https://www.googleapis.com/customsearch/v1"
        self.api_key = None
        self.search_engine_id = None
    
    def set_api_credentials(self, api_key: str, search_engine_id: str):
        """Set Google API credentials"""
        self.api_key = api_key
        self.search_engine_id = search_engine_id
    
    def crawl(self, keyword: str, max_results: int = 10) -> List[Article]:
        """
        Crawl Google search results using Custom Search API
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return (max 10 per request)
        
        Returns:
            List of Article objects
        """
        try:
            # Check API credentials
            if not self.api_key or not self.search_engine_id:
                logger.error("Google API credentials not configured")
                return []
            
            logger.info(f"Starting Google API search for keyword: {keyword}")
            
            # Google Custom Search API limits to 10 results per request
            num_results = min(max_results, 10)
            
            # Build API request
            params = {
                'key': self.api_key,
                'cx': self.search_engine_id,
                'q': keyword,
                'num': num_results,
                'lr': 'lang_zh-CN',  # Language restriction
            }
            
            # Make API request
            response = requests.get(
                self.api_url,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check for API errors
            if 'error' in data:
                error_msg = data['error'].get('message', 'Unknown error')
                error_code = data['error'].get('code', 'N/A')
                logger.error(f"Google API error [{error_code}]: {error_msg}")
                
                if error_code == 429:
                    logger.error("Google API rate limit exceeded (100 requests/day for free tier)")
                
                return []
            
            # Extract search results
            items = data.get('items', [])
            
            if not items:
                logger.warning(f"No results found from Google API for keyword: {keyword}")
                return []
            
            logger.info(f"Found {len(items)} items in Google API response")
            
            articles = []
            
            for item in items:
                try:
                    title = item.get('title', '')
                    url = item.get('link', '')
                    snippet = item.get('snippet', '')
                    
                    if not title or not url:
                        continue
                    
                    # Filter out Google's internal links
                    if any(x in url for x in ['google.com/search', 'accounts.google', 'support.google']):
                        continue
                    
                    # Create Article object
                    article = Article(
                        id=None,
                        title=title.strip(),
                        url=url,
                        content=snippet.strip() if snippet else "无摘要",
                        source="google",
                        keyword=keyword,
                        crawled_at=datetime.now(),
                        published_at=None
                    )
                    
                    articles.append(article)
                    logger.debug(f"Extracted article: {title[:50]}...")
                    
                except Exception as e:
                    logger.error(f"Error parsing Google API result item: {e}")
                    continue
            
            logger.info(f"Successfully crawled {len(articles)} articles from Google API for keyword: {keyword}")
            
            # Log first result for debugging
            if articles:
                first = articles[0]
                logger.debug(f"First result: {first.title}")
                logger.debug(f"First result URL: {first.url}")
            
            return articles
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                logger.error("Google API rate limit exceeded")
            else:
                logger.error(f"HTTP error from Google API: {e}")
            return []
        except requests.exceptions.Timeout:
            logger.error(f"Timeout calling Google API for keyword: {keyword}")
            return []
        except Exception as e:
            logger.error(f"Error crawling Google API for keyword {keyword}: {e}")
            return []
