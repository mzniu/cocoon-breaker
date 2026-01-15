"""
Tavily API crawler
"""
import logging
import os
from datetime import datetime
from typing import List

from tavily import TavilyClient

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class TavilyCrawler(BaseCrawler):
    """Crawler using Tavily API for advanced search"""
    
    def __init__(self, user_agents: List[str], request_interval: List[int], timeout: int = 10,
                 api_key: str = None, search_depth: str = "advanced", max_results: int = 20):
        """Initialize Tavily crawler"""
        super().__init__(user_agents, request_interval, timeout)
        
        # Get API key from parameter or environment variable
        if not api_key:
            api_key = os.getenv('TAVILY_API_KEY')
        
        if not api_key:
            raise ValueError("Tavily API key not provided")
        
        self.client = TavilyClient(api_key)
        self.search_depth = search_depth
        self.default_max_results = max_results
        logger.info(f"Tavily crawler initialized (search_depth={search_depth}, max_results={max_results})")
    
    def crawl(self, keyword: str, max_results: int = None) -> List[Article]:
        """
        Crawl articles using Tavily API
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return (uses default if None)
            
        Returns:
            List of Article objects
        """
        if max_results is None:
            max_results = self.default_max_results
        
        logger.info(f"Crawling Tavily for keyword: {keyword}, max_results: {max_results}")
        
        articles = []
        
        try:
            # Perform search with configured depth
            response = self.client.search(
                query=keyword,
                search_depth=self.search_depth,
                max_results=max_results
            )
            
            # Parse results
            results = response.get('results', [])
            logger.info(f"Tavily returned {len(results)} results for '{keyword}'")
            
            for result in results:
                try:
                    # Extract article information
                    title = result.get('title', '')
                    url = result.get('url', '')
                    content = result.get('content', '')
                    
                    # Skip if missing required fields
                    if not title or not url:
                        logger.warning(f"Skipping result with missing title or URL")
                        continue
                    
                    # Create Article object
                    article = Article(
                        id=None,
                        title=title,
                        url=url,
                        content=content or '',
                        source='tavily',
                        keyword=keyword,
                        crawled_at=datetime.now()
                    )
                    
                    articles.append(article)
                    
                except Exception as e:
                    logger.error(f"Failed to parse Tavily result: {e}")
                    continue
            
            logger.info(f"Successfully crawled {len(articles)} articles from Tavily for '{keyword}'")
            
        except Exception as e:
            logger.error(f"Tavily crawling failed for '{keyword}': {e}")
            # Return empty list on error, don't interrupt the flow
            return []
        
        return articles
