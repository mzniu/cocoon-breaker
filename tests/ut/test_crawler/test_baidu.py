"""
Unit tests for crawler modules
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.crawler.baidu import BaiduCrawler
from src.crawler.bing import BingCrawler
from src.db.models import Article


class TestBaiduCrawler:
    """Test BaiduCrawler"""
    
    def setup_method(self):
        """Setup test crawler"""
        self.crawler = BaiduCrawler(
            user_agents=["Test User Agent"],
            request_interval=[0, 0],  # No delay for testing
            timeout=5
        )
    
    @patch('src.crawler.base.requests.get')
    def test_crawl_success(self, mock_get):
        """Test successful crawl"""
        # Mock HTML response
        mock_html = """
        <html>
            <div class="result">
                <h3><a href="https://example.com/1">Test Article 1</a></h3>
                <div class="c-abstract">Test content 1</div>
            </div>
            <div class="result">
                <h3><a href="https://example.com/2">Test Article 2</a></h3>
                <div class="c-abstract">Test content 2</div>
            </div>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        articles = self.crawler.crawl("test keyword", max_results=10)
        
        assert len(articles) == 2
        assert articles[0].title == "Test Article 1"
        assert articles[0].url == "https://example.com/1"
        assert articles[0].source == "baidu"
        assert articles[0].keyword == "test keyword"
    
    @patch('src.crawler.base.requests.get')
    def test_crawl_network_error(self, mock_get):
        """Test crawl handles network errors gracefully"""
        mock_get.side_effect = Exception("Network error")
        
        # Should return empty list, not raise exception
        articles = self.crawler.crawl("test keyword")
        
        assert articles == []
    
    @patch('src.crawler.base.requests.get')
    def test_crawl_empty_results(self, mock_get):
        """Test crawl with no results"""
        mock_html = "<html><body>No results</body></html>"
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        articles = self.crawler.crawl("test keyword")
        
        assert articles == []
    
    def test_parse_result_missing_elements(self):
        """Test parsing result with missing elements"""
        from bs4 import BeautifulSoup
        
        # Result without required elements
        html = "<div class='result'><p>No title or link</p></div>"
        soup = BeautifulSoup(html, 'html.parser')
        result_div = soup.find('div')
        
        article = self.crawler._parse_result(result_div, "test")
        
        assert article is None


class TestBingCrawler:
    """Test BingCrawler"""
    
    def setup_method(self):
        """Setup test crawler"""
        self.crawler = BingCrawler(
            user_agents=["Test User Agent"],
            request_interval=[0, 0],
            timeout=5
        )
    
    @patch('src.crawler.base.requests.get')
    def test_crawl_success(self, mock_get):
        """Test successful crawl"""
        mock_html = """
        <html>
            <li class="b_algo">
                <h2><a href="https://example.com/1">Bing Article 1</a></h2>
                <p>Bing content 1</p>
            </li>
            <li class="b_algo">
                <h2><a href="https://example.com/2">Bing Article 2</a></h2>
                <p>Bing content 2</p>
            </li>
        </html>
        """
        
        mock_response = Mock()
        mock_response.text = mock_html
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        articles = self.crawler.crawl("test keyword", max_results=10)
        
        assert len(articles) == 2
        assert articles[0].title == "Bing Article 1"
        assert articles[0].source == "bing"
    
    @patch('src.crawler.base.requests.get')
    def test_crawl_network_error(self, mock_get):
        """Test crawl handles network errors"""
        mock_get.side_effect = Exception("Network error")
        
        articles = self.crawler.crawl("test keyword")
        
        assert articles == []


class TestBaseCrawler:
    """Test BaseCrawler base class"""
    
    def test_random_user_agent(self):
        """Test user agent rotation"""
        user_agents = ["Agent1", "Agent2", "Agent3"]
        crawler = BaiduCrawler(user_agents, [1, 2], 5)
        
        agent = crawler._get_random_user_agent()
        
        assert agent in user_agents
    
    def test_extract_text(self):
        """Test text extraction"""
        from bs4 import BeautifulSoup
        
        crawler = BaiduCrawler(["UA"], [0, 0], 5)
        
        html = "<div>  Text  with   extra   spaces  </div>"
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        
        text = crawler._extract_text(div)
        
        assert text == "Text with extra spaces"
    
    def test_extract_text_none(self):
        """Test text extraction with None element"""
        crawler = BaiduCrawler(["UA"], [0, 0], 5)
        
        text = crawler._extract_text(None)
        
        assert text == ""
