"""
Unit tests for database repository
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta

from src.db.database import Database
from src.db.models import Article, Subscription, Report
from src.db.repository import (
    ArticleRepository,
    SubscriptionRepository,
    ReportRepository,
    ScheduleRepository
)


@pytest.fixture
async def test_db():
    """Create a temporary test database"""
    temp_fd, temp_path = tempfile.mkstemp(suffix='.db')
    os.close(temp_fd)
    
    db = Database(temp_path)
    await db.connect()
    
    yield db
    
    await db.close()
    os.unlink(temp_path)


@pytest.mark.asyncio
class TestArticleRepository:
    """Test ArticleRepository"""
    
    async def test_create_article(self, test_db):
        """Test creating an article"""
        repo = ArticleRepository(test_db)
        
        article = Article(
            id=None,
            title="Test Article",
            url="https://example.com/article1",
            content="Test content",
            source="baidu",
            keyword="AI",
            crawled_at=datetime.now()
        )
        
        article_id = await repo.create(article)
        assert article_id is not None
        assert article_id > 0
    
    async def test_create_duplicate_article(self, test_db):
        """Test creating duplicate article (should be ignored)"""
        repo = ArticleRepository(test_db)
        
        article = Article(
            id=None,
            title="Test Article",
            url="https://example.com/article2",
            content="Test content",
            source="baidu",
            keyword="AI",
            crawled_at=datetime.now()
        )
        
        # First insert
        first_id = await repo.create(article)
        assert first_id is not None
        
        # Duplicate insert (same URL)
        second_id = await repo.create(article)
        assert second_id is None  # Should return None for duplicate
    
    async def test_get_by_keyword(self, test_db):
        """Test getting articles by keyword"""
        repo = ArticleRepository(test_db)
        
        # Create test articles
        for i in range(3):
            article = Article(
                id=None,
                title=f"AI Article {i}",
                url=f"https://example.com/ai{i}",
                content="AI content",
                source="baidu",
                keyword="AI",
                crawled_at=datetime.now()
            )
            await repo.create(article)
        
        # Create article with different keyword
        other_article = Article(
            id=None,
            title="Python Article",
            url="https://example.com/python",
            content="Python content",
            source="bing",
            keyword="Python",
            crawled_at=datetime.now()
        )
        await repo.create(other_article)
        
        # Get AI articles
        ai_articles = await repo.get_by_keyword("AI")
        assert len(ai_articles) == 3
        assert all(a.keyword == "AI" for a in ai_articles)
    
    async def test_get_recent_by_keyword(self, test_db):
        """Test getting recent articles"""
        repo = ArticleRepository(test_db)
        
        # Create old article
        old_article = Article(
            id=None,
            title="Old Article",
            url="https://example.com/old",
            content="Old content",
            source="baidu",
            keyword="AI",
            crawled_at=datetime.now() - timedelta(hours=25)
        )
        await repo.create(old_article)
        
        # Create recent article
        recent_article = Article(
            id=None,
            title="Recent Article",
            url="https://example.com/recent",
            content="Recent content",
            source="baidu",
            keyword="AI",
            crawled_at=datetime.now()
        )
        await repo.create(recent_article)
        
        # Get articles from last 24 hours
        recent_articles = await repo.get_recent_by_keyword("AI", hours=24)
        assert len(recent_articles) == 1
        assert recent_articles[0].title == "Recent Article"


@pytest.mark.asyncio
class TestSubscriptionRepository:
    """Test SubscriptionRepository"""
    
    async def test_create_subscription(self, test_db):
        """Test creating a subscription"""
        repo = SubscriptionRepository(test_db)
        
        sub_id = await repo.create("AI")
        assert sub_id is not None
        assert sub_id > 0
    
    async def test_create_duplicate_subscription(self, test_db):
        """Test creating duplicate subscription"""
        repo = SubscriptionRepository(test_db)
        
        first_id = await repo.create("AI")
        assert first_id is not None
        
        second_id = await repo.create("AI")
        assert second_id is None  # Duplicate should return None
    
    async def test_get_all_subscriptions(self, test_db):
        """Test getting all subscriptions"""
        repo = SubscriptionRepository(test_db)
        
        await repo.create("AI")
        await repo.create("Machine Learning")
        await repo.create("Python")
        
        subscriptions = await repo.get_all()
        assert len(subscriptions) == 3
    
    async def test_get_enabled_subscriptions(self, test_db):
        """Test getting enabled subscriptions"""
        repo = SubscriptionRepository(test_db)
        
        sub_id1 = await repo.create("AI")
        sub_id2 = await repo.create("Python")
        
        # Disable one subscription
        await repo.update_enabled(sub_id2, False)
        
        enabled_subs = await repo.get_enabled()
        assert len(enabled_subs) == 1
        assert enabled_subs[0].keyword == "AI"
    
    async def test_delete_subscription(self, test_db):
        """Test deleting a subscription"""
        repo = SubscriptionRepository(test_db)
        
        sub_id = await repo.create("AI")
        
        # Delete
        deleted = await repo.delete(sub_id)
        assert deleted is True
        
        # Verify deleted
        subscriptions = await repo.get_all()
        assert len(subscriptions) == 0


@pytest.mark.asyncio
class TestReportRepository:
    """Test ReportRepository"""
    
    async def test_create_report(self, test_db):
        """Test creating a report"""
        repo = ReportRepository(test_db)
        
        report = Report(
            id=None,
            keyword="AI",
            date="2026-01-13",
            file_path="./reports/ai_2026-01-13.html",
            article_count=5,
            generated_at=datetime.now()
        )
        
        report_id = await repo.create(report)
        assert report_id is not None
        assert report_id > 0
    
    async def test_get_report_by_id(self, test_db):
        """Test getting report by ID"""
        repo = ReportRepository(test_db)
        
        report = Report(
            id=None,
            keyword="AI",
            date="2026-01-13",
            file_path="./reports/ai_2026-01-13.html",
            article_count=5,
            generated_at=datetime.now()
        )
        
        report_id = await repo.create(report)
        
        # Get by ID
        retrieved = await repo.get_by_id(report_id)
        assert retrieved is not None
        assert retrieved.keyword == "AI"
        assert retrieved.date == "2026-01-13"
    
    async def test_get_report_by_keyword_date(self, test_db):
        """Test getting report by keyword and date"""
        repo = ReportRepository(test_db)
        
        report = Report(
            id=None,
            keyword="AI",
            date="2026-01-13",
            file_path="./reports/ai_2026-01-13.html",
            article_count=5,
            generated_at=datetime.now()
        )
        
        await repo.create(report)
        
        # Get by keyword and date
        retrieved = await repo.get_by_keyword_date("AI", "2026-01-13")
        assert retrieved is not None
        assert retrieved.keyword == "AI"


@pytest.mark.asyncio
class TestScheduleRepository:
    """Test ScheduleRepository"""
    
    async def test_get_default_config(self, test_db):
        """Test getting default schedule configuration"""
        repo = ScheduleRepository(test_db)
        
        config = await repo.get_config()
        assert config is not None
        assert config.time == "08:00"
        assert config.enabled is True
    
    async def test_update_config(self, test_db):
        """Test updating schedule configuration"""
        repo = ScheduleRepository(test_db)
        
        # Update
        updated = await repo.update_config("09:30", False)
        assert updated is True
        
        # Verify
        config = await repo.get_config()
        assert config.time == "09:30"
        assert config.enabled is False
