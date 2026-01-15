"""
Unit tests for Deepseek AI integration
"""
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.ai.deepseek import DeepseekClient, ArticleFilter
from src.db.models import Article


class TestDeepseekClient:
    """Test DeepseekClient"""
    
    def setup_method(self):
        """Setup test client"""
        self.client = DeepseekClient(
            api_key="test-key",
            model="deepseek-reasoner",
            timeout=10,
            max_retries=2
        )
    
    @patch('src.ai.deepseek.requests.post')
    def test_chat_completion_success(self, mock_post):
        """Test successful API call"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [
                {
                    'message': {
                        'content': 'Test response'
                    }
                }
            ]
        }
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Hello"}]
        result = self.client.chat_completion(messages)
        
        assert result == 'Test response'
        assert mock_post.call_count == 1
    
    @patch('src.ai.deepseek.requests.post')
    def test_chat_completion_timeout_retry(self, mock_post):
        """Test retry on timeout"""
        import requests
        
        # First call times out, second succeeds
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Success'}}]
        }
        
        mock_post.side_effect = [
            requests.exceptions.Timeout("Timeout"),
            mock_response
        ]
        
        messages = [{"role": "user", "content": "Test"}]
        result = self.client.chat_completion(messages)
        
        assert result == 'Success'
        assert mock_post.call_count == 2
    
    @patch('src.ai.deepseek.requests.post')
    def test_chat_completion_all_retries_fail(self, mock_post):
        """Test all retries fail"""
        import requests
        
        mock_post.side_effect = requests.exceptions.Timeout("Timeout")
        
        messages = [{"role": "user", "content": "Test"}]
        result = self.client.chat_completion(messages)
        
        assert result is None
        assert mock_post.call_count == 2  # max_retries=2
    
    @patch('src.ai.deepseek.requests.post')
    def test_chat_completion_empty_response(self, mock_post):
        """Test empty response handling"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'choices': []}
        mock_post.return_value = mock_response
        
        messages = [{"role": "user", "content": "Test"}]
        result = self.client.chat_completion(messages)
        
        assert result is None


class TestArticleFilter:
    """Test ArticleFilter"""
    
    def setup_method(self):
        """Setup test filter"""
        mock_client = Mock(spec=DeepseekClient)
        self.filter = ArticleFilter(mock_client)
        
        # Create test articles
        self.articles = [
            Article(
                id=1,
                title="AI突破性进展",
                url="https://example.com/1",
                content="人工智能领域取得重大突破...",
                source="baidu",
                keyword="AI",
                crawled_at=datetime.now()
            ),
            Article(
                id=2,
                title="普通AI新闻",
                url="https://example.com/2",
                content="AI行业日常动态...",
                source="bing",
                keyword="AI",
                crawled_at=datetime.now()
            )
        ]
    
    def test_filter_empty_articles(self):
        """Test filtering empty article list"""
        result = self.filter.filter_and_rank([], "AI")
        
        assert result == []
    
    def test_filter_with_valid_response(self):
        """Test filtering with valid AI response"""
        # Mock AI response
        json_response = """[
            {"index": 0, "priority": "high", "reason": "重大突破"},
            {"index": 1, "priority": "medium", "reason": "行业动态"}
        ]"""
        
        self.filter.client.chat_completion.return_value = json_response
        
        result = self.filter.filter_and_rank(self.articles, "AI", target_count=2)
        
        assert len(result) == 2
        assert result[0]['priority'] == 'high'
        assert result[0]['article'].title == "AI突破性进展"
    
    def test_filter_ai_failure_fallback(self):
        """Test fallback when AI fails"""
        self.filter.client.chat_completion.return_value = None
        
        result = self.filter.filter_and_rank(self.articles, "AI", target_count=2)
        
        # Should use fallback method
        assert len(result) == 2
        assert all(item['priority'] == 'medium' for item in result)
    
    def test_filter_invalid_json_response(self):
        """Test handling of invalid JSON response"""
        self.filter.client.chat_completion.return_value = "Invalid response"
        
        result = self.filter.filter_and_rank(self.articles, "AI", target_count=2)
        
        # Should fall back to simple filtering
        assert len(result) == 2
    
    def test_generate_summary_success(self):
        """Test summary generation"""
        filtered = [
            {
                'article': self.articles[0],
                'priority': 'high',
                'reason': 'Important'
            }
        ]
        
        self.filter.client.chat_completion.return_value = "今日AI领域取得重大突破。"
        
        summary = self.filter.generate_summary("AI", filtered)
        
        assert "AI" in summary
        assert len(summary) > 0
    
    def test_generate_summary_empty_articles(self):
        """Test summary with no articles"""
        summary = self.filter.generate_summary("AI", [])
        
        assert "暂无" in summary or "无" in summary
    
    def test_generate_summary_ai_failure(self):
        """Test summary generation when AI fails"""
        filtered = [
            {
                'article': self.articles[0],
                'priority': 'high',
                'reason': 'Important'
            }
        ]
        
        self.filter.client.chat_completion.return_value = None
        
        summary = self.filter.generate_summary("AI", filtered)
        
        # Should return fallback summary
        assert "AI" in summary
        assert len(summary) > 0
    
    def test_parse_filter_response_valid(self):
        """Test parsing valid filter response"""
        response = '[{"index": 0, "priority": "high", "reason": "Test"}]'
        
        result = self.filter._parse_filter_response(response, self.articles)
        
        assert len(result) == 1
        assert result[0]['priority'] == 'high'
    
    def test_parse_filter_response_out_of_bounds(self):
        """Test parsing response with out-of-bounds index"""
        response = '[{"index": 99, "priority": "high", "reason": "Test"}]'
        
        result = self.filter._parse_filter_response(response, self.articles)
        
        assert len(result) == 0
    
    def test_fallback_filter(self):
        """Test fallback filtering method"""
        result = self.filter._fallback_filter(self.articles, target_count=1)
        
        assert len(result) == 1
        assert result[0]['article'] == self.articles[0]
        assert result[0]['priority'] == 'medium'
