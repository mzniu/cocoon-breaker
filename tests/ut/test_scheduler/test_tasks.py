"""
Unit tests for scheduler tasks
"""
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.scheduler.tasks import DailyReportTask, TaskScheduler
from src.db.models import Article, Subscription, ScheduleConfig


class TestDailyReportTask:
    """Test DailyReportTask"""
    
    @pytest.mark.asyncio
    async def test_initialize(self):
        """Test task initialization"""
        task = DailyReportTask()
        
        with patch('src.scheduler.tasks.Database') as mock_db_class, \
             patch('src.scheduler.tasks.DeepseekClient') as mock_client_class, \
             patch('src.scheduler.tasks.ReportGenerator') as mock_gen_class:
            
            mock_db = AsyncMock()
            mock_db_class.return_value = mock_db
            
            await task.initialize()
            
            assert task.db is not None
            assert task.deepseek_client is not None
            assert task.report_generator is not None
            assert len(task.crawlers) == 2
            
            await task.cleanup()
    
    @pytest.mark.asyncio
    async def test_run_no_subscriptions(self):
        """Test run with no enabled subscriptions"""
        task = DailyReportTask()
        task.subscription_repo = AsyncMock()
        task.subscription_repo.get_enabled.return_value = []
        
        await task.run()
        
        # Should return early
        assert not task._running
    
    @pytest.mark.asyncio
    async def test_run_with_subscriptions(self):
        """Test run with enabled subscriptions"""
        task = DailyReportTask()
        task.subscription_repo = AsyncMock()
        task.subscription_repo.get_enabled.return_value = [
            Subscription(id=1, keyword="AI", created_at=datetime.now(), enabled=True)
        ]
        
        task._process_subscription = AsyncMock()
        
        await task.run()
        
        task._process_subscription.assert_called_once_with("AI")
    
    @pytest.mark.asyncio
    async def test_process_subscription_success(self):
        """Test processing subscription successfully"""
        task = DailyReportTask()
        
        # Mock repositories
        task.article_repo = AsyncMock()
        task.report_repo = AsyncMock()
        
        # Mock articles
        articles = [
            Article(
                id=1,
                title="Test",
                url="https://example.com/1",
                content="Content",
                source="baidu",
                keyword="AI",
                crawled_at=datetime.now()
            )
        ]
        
        task._crawl_articles = AsyncMock(return_value=articles)
        task._save_articles = AsyncMock(return_value=1)
        task.article_repo.get_recent_by_keyword.return_value = articles
        
        # Mock report generator
        task.report_generator = Mock()
        task.report_generator.generate_report.return_value = "reports/AI_2024-01-01.html"
        
        await task._process_subscription("AI")
        
        task.report_repo.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_subscription_no_articles(self):
        """Test processing subscription with no articles"""
        task = DailyReportTask()
        
        task._crawl_articles = AsyncMock(return_value=[])
        task._save_articles = AsyncMock()
        
        await task._process_subscription("AI")
        
        # Should return early
        task._save_articles.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_crawl_articles_multiple_sources(self):
        """Test crawling from multiple sources"""
        task = DailyReportTask()
        task.config = Mock()
        task.config.crawler.max_results_per_source = 5
        
        # Mock crawlers
        mock_crawler1 = Mock()
        mock_crawler1.crawl.return_value = [
            Article(id=1, title="A1", url="https://a.com/1", content="C1",
                   source="baidu", keyword="AI", crawled_at=datetime.now())
        ]
        
        mock_crawler2 = Mock()
        mock_crawler2.crawl.return_value = [
            Article(id=2, title="A2", url="https://b.com/2", content="C2",
                   source="bing", keyword="AI", crawled_at=datetime.now())
        ]
        
        task.crawlers = [mock_crawler1, mock_crawler2]
        
        articles = await task._crawl_articles("AI")
        
        assert len(articles) == 2
    
    @pytest.mark.asyncio
    async def test_crawl_articles_crawler_failure(self):
        """Test handling crawler failure"""
        task = DailyReportTask()
        task.config = Mock()
        task.config.crawler.max_results_per_source = 5
        
        # First crawler fails, second succeeds
        mock_crawler1 = Mock()
        mock_crawler1.crawl.side_effect = Exception("Crawl error")
        
        mock_crawler2 = Mock()
        mock_crawler2.crawl.return_value = [
            Article(id=1, title="A1", url="https://a.com/1", content="C1",
                   source="bing", keyword="AI", crawled_at=datetime.now())
        ]
        
        task.crawlers = [mock_crawler1, mock_crawler2]
        
        articles = await task._crawl_articles("AI")
        
        # Should still get articles from second crawler
        assert len(articles) == 1
    
    @pytest.mark.asyncio
    async def test_save_articles(self):
        """Test saving articles to database"""
        task = DailyReportTask()
        task.article_repo = AsyncMock()
        task.article_repo.create.side_effect = [1, None, 2]  # Second is duplicate
        
        articles = [
            Article(id=None, title="A1", url="https://a.com/1", content="C1",
                   source="baidu", keyword="AI", crawled_at=datetime.now()),
            Article(id=None, title="A2", url="https://a.com/2", content="C2",
                   source="baidu", keyword="AI", crawled_at=datetime.now()),
            Article(id=None, title="A3", url="https://a.com/3", content="C3",
                   source="bing", keyword="AI", crawled_at=datetime.now()),
        ]
        
        saved_count = await task._save_articles(articles)
        
        assert saved_count == 2  # Two saved, one duplicate


class TestTaskScheduler:
    """Test TaskScheduler"""
    
    @pytest.mark.asyncio
    async def test_start_scheduler_disabled(self):
        """Test starting scheduler when disabled"""
        scheduler = TaskScheduler()
        scheduler.task = AsyncMock()
        scheduler.task.initialize = AsyncMock()
        scheduler.task.schedule_repo = AsyncMock()
        scheduler.task.schedule_repo.get.return_value = ScheduleConfig(
            id=1,
            time="08:00",
            enabled=False,
            updated_at=datetime.now()
        )
        
        await scheduler.start()
        
        # Should not start thread
        assert scheduler.scheduler_thread is None
        
        await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_start_scheduler_enabled(self):
        """Test starting scheduler when enabled"""
        scheduler = TaskScheduler()
        scheduler.task = AsyncMock()
        scheduler.task.initialize = AsyncMock()
        scheduler.task.schedule_repo = AsyncMock()
        scheduler.task.schedule_repo.get.return_value = ScheduleConfig(
            id=1,
            time="08:00",
            enabled=True,
            updated_at=datetime.now()
        )
        
        with patch('src.scheduler.tasks.schedule'):
            await scheduler.start()
            
            # Should start thread
            assert scheduler.scheduler_thread is not None
            assert scheduler.scheduler_thread.daemon is True
            
            await scheduler.stop()
    
    @pytest.mark.asyncio
    async def test_run_once(self):
        """Test manual task execution"""
        scheduler = TaskScheduler()
        scheduler.task = AsyncMock()
        scheduler.task.run = AsyncMock()
        
        await scheduler.run_once()
        
        scheduler.task.run.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_stop_scheduler(self):
        """Test stopping scheduler"""
        scheduler = TaskScheduler()
        scheduler.task = AsyncMock()
        scheduler.task.cleanup = AsyncMock()
        scheduler.scheduler_thread = Mock()
        scheduler.scheduler_thread.join = Mock()
        
        with patch('src.scheduler.tasks.schedule.clear') as mock_clear:
            await scheduler.stop()
            
            scheduler.task.cleanup.assert_called_once()
            mock_clear.assert_called_once()
            assert scheduler._stop_event.is_set()
