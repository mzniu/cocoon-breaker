"""
Base crawler class
"""
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
import logging

import requests
from bs4 import BeautifulSoup

from src.db.models import Article

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Abstract base class for crawlers"""
    
    def __init__(self, user_agents: List[str], request_interval: List[int], timeout: int = 10):
        """
        Initialize crawler
        
        Args:
            user_agents: List of user agent strings for rotation
            request_interval: [min, max] seconds for random delay between requests
            timeout: Request timeout in seconds
        """
        self.user_agents = user_agents
        self.request_interval = request_interval
        self.timeout = timeout
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent"""
        return random.choice(self.user_agents)
    
    def _random_delay(self):
        """Add random delay between requests"""
        delay = random.uniform(self.request_interval[0], self.request_interval[1])
        time.sleep(delay)
    
    def _make_request(self, url: str, params: dict = None, timeout: int = None) -> requests.Response:
        """
        Make HTTP request with random user agent
        
        Args:
            url: Request URL
            params: Query parameters
            timeout: Optional timeout override (uses self.timeout if None)
            
        Returns:
            Response object
            
        Raises:
            requests.exceptions.RequestException: On request failure
        """
        headers = {
            'User-Agent': self._get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers=headers,
                timeout=timeout if timeout is not None else self.timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed for {url}: {e}")
            raise
    
    @abstractmethod
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl articles for given keyword
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results to return
            
        Returns:
            List of Article objects
        """
        pass
    
    def _extract_text(self, soup_element) -> str:
        """
        Extract clean text from BeautifulSoup element
        
        Args:
            soup_element: BeautifulSoup element
            
        Returns:
            Cleaned text string
        """
        if soup_element is None:
            return ""
        
        text = soup_element.get_text(strip=True)
        # Clean up extra whitespace
        text = ' '.join(text.split())
        return text
