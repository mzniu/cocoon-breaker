"""
Unit tests for report generator
"""
import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime

from src.report.generator import ReportGenerator
from src.ai.deepseek import DeepseekClient
from src.db.models import Article


class TestReportGenerator:
    """Test ReportGenerator"""
    
    def setup_method(self):
        """Setup test generator"""
        # Create mock client
        self.mock_client = Mock(spec=DeepseekClient)
        
        # Create temp directories
        self.temp_dir = tempfile.mkdtemp()
        self.template_path = os.path.join(self.temp_dir, 'template.html')
        self.output_dir = os.path.join(self.temp_dir, 'reports')
        
        # Create mock template
        self.template_content = """<!DOCTYPE html>
<html>
<head><title>Daily Report</title></head>
<body>
    <h1>{{keywords}} - {{date}}</h1>
    <div class="summary">{{summary}}</div>
    <div class="info-list">
        <!-- Articles here -->
    </div>
    <footer>@小牛聊AI</footer>
</body>
</html>"""
        
        with open(self.template_path, 'w', encoding='utf-8') as f:
            f.write(self.template_content)
        
        # Create test articles
        self.articles = [
            Article(
                id=1,
                title="AI重大突破",
                url="https://example.com/1",
                content="人工智能领域取得重大突破，新模型性能提升显著。",
                source="baidu",
                keyword="AI",
                crawled_at=datetime.now()
            ),
            Article(
                id=2,
                title="AI行业动态",
                url="https://example.com/2",
                content="AI行业持续发展，多家公司发布新产品。",
                source="bing",
                keyword="AI",
                crawled_at=datetime.now()
            )
        ]
    
    def teardown_method(self):
        """Cleanup temp files"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_load_template_success(self):
        """Test loading template successfully"""
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        assert generator.template is not None
        assert "{{keywords}}" in generator.template
    
    def test_load_template_not_found(self):
        """Test loading non-existent template"""
        with pytest.raises(FileNotFoundError):
            ReportGenerator(
                self.mock_client,
                template_path="nonexistent.html",
                output_dir=self.output_dir
            )
    
    @patch('src.report.generator.ArticleFilter')
    def test_generate_report_success(self, mock_filter_class):
        """Test successful report generation"""
        # Setup mock filter
        mock_filter = Mock()
        mock_filter.filter_and_rank.return_value = [
            {'article': self.articles[0], 'priority': 'high', 'reason': 'Important'}
        ]
        mock_filter.generate_summary.return_value = "今日AI领域重要进展。"
        mock_filter_class.return_value = mock_filter
        
        # Mock AI HTML generation
        self.mock_client.chat_completion.return_value = """<!DOCTYPE html>
<html><body><h1>AI Report</h1></body></html>"""
        
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        filepath = generator.generate_report("AI", self.articles)
        
        assert filepath is not None
        assert os.path.exists(filepath)
        assert "AI_" in filepath
    
    @patch('src.report.generator.ArticleFilter')
    def test_generate_report_empty_articles(self, mock_filter_class):
        """Test report generation with empty articles"""
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        filepath = generator.generate_report("AI", [])
        
        assert filepath is not None
        assert os.path.exists(filepath)
        
        # Check content
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            assert "暂无" in content
    
    @patch('src.report.generator.ArticleFilter')
    def test_generate_report_ai_failure_fallback(self, mock_filter_class):
        """Test fallback when AI generation fails"""
        mock_filter = Mock()
        mock_filter.filter_and_rank.return_value = [
            {'article': self.articles[0], 'priority': 'high', 'reason': 'Test'}
        ]
        mock_filter.generate_summary.return_value = "Test summary"
        mock_filter_class.return_value = mock_filter
        
        # AI fails
        self.mock_client.chat_completion.return_value = None
        
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        filepath = generator.generate_report("AI", self.articles)
        
        assert filepath is not None
        assert os.path.exists(filepath)
    
    def test_extract_html_with_doctype(self):
        """Test extracting HTML with DOCTYPE"""
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        response = "Some text before\n<!DOCTYPE html><html><body>Test</body></html>\nText after"
        html = generator._extract_html(response)
        
        assert html.startswith('<!DOCTYPE html>')
        assert html.endswith('</html>')
    
    def test_extract_html_without_doctype(self):
        """Test extracting HTML without DOCTYPE"""
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        response = "<html><body>Test</body></html>"
        html = generator._extract_html(response)
        
        assert html.startswith('<html>')
    
    def test_fallback_html_generation(self):
        """Test fallback HTML generation"""
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        articles_list = [
            {
                'number': 1,
                'title': 'Test Article',
                'url': 'https://example.com',
                'content': 'Test content',
                'priority': 'high',
                'emoji': '🔴'
            }
        ]
        
        html = generator._fallback_html_generation(
            "AI",
            "2024-01-01",
            "Test summary",
            articles_list
        )
        
        assert "AI" in html
        assert "2024-01-01" in html
        assert "Test summary" in html
        assert "Test Article" in html
    
    @patch('src.report.generator.ArticleFilter')
    def test_generate_report_with_custom_date(self, mock_filter_class):
        """Test report generation with custom date"""
        mock_filter = Mock()
        mock_filter.filter_and_rank.return_value = [
            {'article': self.articles[0], 'priority': 'high', 'reason': 'Test'}
        ]
        mock_filter.generate_summary.return_value = "Summary"
        mock_filter_class.return_value = mock_filter
        
        self.mock_client.chat_completion.return_value = "<!DOCTYPE html><html></html>"
        
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=self.output_dir
        )
        
        custom_date = datetime(2024, 6, 15)
        filepath = generator.generate_report("AI", self.articles, date=custom_date)
        
        assert filepath is not None
        assert "2024-06-15" in filepath
    
    def test_output_directory_creation(self):
        """Test output directory is created if not exists"""
        output_path = os.path.join(self.temp_dir, 'new_reports')
        
        generator = ReportGenerator(
            self.mock_client,
            template_path=self.template_path,
            output_dir=output_path
        )
        
        assert os.path.exists(output_path)
