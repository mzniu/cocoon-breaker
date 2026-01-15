"""
Database repository for CRUD operations
"""
from datetime import datetime
from typing import List, Optional
import logging

from src.db.database import Database
from src.db.models import Article, Subscription, Report, ScheduleConfig as ScheduleConfigModel

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for Article operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, article: Article) -> Optional[int]:
        """
        Create new article (INSERT OR IGNORE for deduplication)
        Returns article ID if inserted, None if duplicate
        """
        try:
            cursor = await self.db.conn.execute("""
                INSERT OR IGNORE INTO articles 
                (title, url, content, source, keyword, crawled_at, published_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article.title,
                article.url,
                article.content,
                article.source,
                article.keyword,
                article.crawled_at.isoformat(),
                article.published_at.isoformat() if article.published_at else None
            ))
            
            await self.db.conn.commit()
            
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None
            
        except Exception as e:
            logger.error(f"Error creating article: {e}")
            raise
    
    async def get_by_keyword(self, keyword: str, limit: int = 100) -> List[Article]:
        """Get articles by keyword"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM articles 
            WHERE keyword = ?
            ORDER BY crawled_at DESC
            LIMIT ?
        """, (keyword, limit))
        
        rows = await cursor.fetchall()
        return [self._row_to_article(row) for row in rows]
    
    async def get_recent_by_keyword(self, keyword: str, hours: int = 24, limit: int = 100) -> List[Article]:
        """Get recent articles by keyword within specified hours"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM articles 
            WHERE keyword = ?
            AND crawled_at >= datetime('now', ? || ' hours')
            ORDER BY crawled_at DESC
            LIMIT ?
        """, (keyword, f'-{hours}', limit))
        
        rows = await cursor.fetchall()
        return [self._row_to_article(row) for row in rows]
    
    async def get_all(self, limit: int = 100) -> List[Article]:
        """Get all articles"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM articles 
            ORDER BY crawled_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        return [self._row_to_article(row) for row in rows]
    
    async def get_by_id(self, article_id: int) -> Optional[Article]:
        """Get article by ID"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM articles WHERE id = ?
        """, (article_id,))
        
        row = await cursor.fetchone()
        return self._row_to_article(row) if row else None
    
    async def delete_old_articles(self, days: int = 30) -> int:
        """Delete articles older than specified days"""
        cursor = await self.db.conn.execute("""
            DELETE FROM articles 
            WHERE crawled_at < datetime('now', ? || ' days')
        """, (f'-{days}',))
        
        await self.db.conn.commit()
        return cursor.rowcount
    
    def _row_to_article(self, row) -> Article:
        """Convert database row to Article model"""
        return Article(
            id=row['id'],
            title=row['title'],
            url=row['url'],
            content=row['content'],
            source=row['source'],
            keyword=row['keyword'],
            crawled_at=datetime.fromisoformat(row['crawled_at']),
            published_at=datetime.fromisoformat(row['published_at']) if row['published_at'] else None
        )


class SubscriptionRepository:
    """Repository for Subscription operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, keyword: str) -> Optional[int]:
        """Create new subscription"""
        try:
            cursor = await self.db.conn.execute("""
                INSERT OR IGNORE INTO subscriptions (keyword, created_at, enabled)
                VALUES (?, ?, 1)
            """, (keyword, datetime.now().isoformat()))
            
            await self.db.conn.commit()
            
            if cursor.rowcount > 0:
                return cursor.lastrowid
            return None
            
        except Exception as e:
            logger.error(f"Error creating subscription: {e}")
            raise
    
    async def get_all(self) -> List[Subscription]:
        """Get all subscriptions"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM subscriptions ORDER BY created_at DESC
        """)
        
        rows = await cursor.fetchall()
        return [self._row_to_subscription(row) for row in rows]
    
    async def get_enabled(self) -> List[Subscription]:
        """Get enabled subscriptions"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM subscriptions 
            WHERE enabled = 1
            ORDER BY created_at DESC
        """)
        
        rows = await cursor.fetchall()
        return [self._row_to_subscription(row) for row in rows]
    
    async def delete(self, subscription_id: int) -> bool:
        """Delete subscription by ID"""
        cursor = await self.db.conn.execute("""
            DELETE FROM subscriptions WHERE id = ?
        """, (subscription_id,))
        
        await self.db.conn.commit()
        return cursor.rowcount > 0
    
    async def update_enabled(self, subscription_id: int, enabled: bool) -> bool:
        """Update subscription enabled status"""
        cursor = await self.db.conn.execute("""
            UPDATE subscriptions SET enabled = ? WHERE id = ?
        """, (1 if enabled else 0, subscription_id))
        
        await self.db.conn.commit()
        return cursor.rowcount > 0
    
    def _row_to_subscription(self, row) -> Subscription:
        """Convert database row to Subscription model"""
        return Subscription(
            id=row['id'],
            keyword=row['keyword'],
            created_at=datetime.fromisoformat(row['created_at']),
            enabled=bool(row['enabled'])
        )


class ReportRepository:
    """Repository for Report operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def create(self, report: Report) -> int:
        """Create new report"""
        cursor = await self.db.conn.execute("""
            INSERT OR REPLACE INTO reports 
            (keyword, date, file_path, article_count, generated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            report.keyword,
            report.date,
            report.file_path,
            report.article_count,
            report.generated_at.isoformat()
        ))
        
        await self.db.conn.commit()
        return cursor.lastrowid
    
    async def get_all(self, limit: int = 50) -> List[Report]:
        """Get all reports"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM reports 
            ORDER BY date DESC, generated_at DESC
            LIMIT ?
        """, (limit,))
        
        rows = await cursor.fetchall()
        return [self._row_to_report(row) for row in rows]
    
    async def get_by_id(self, report_id: int) -> Optional[Report]:
        """Get report by ID"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM reports WHERE id = ?
        """, (report_id,))
        
        row = await cursor.fetchone()
        return self._row_to_report(row) if row else None
    
    async def get_by_keyword_date(self, keyword: str, date: str) -> Optional[Report]:
        """Get latest report by keyword and date"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM reports 
            WHERE keyword = ? AND date = ?
            ORDER BY generated_at DESC
            LIMIT 1
        """, (keyword, date))
        
        row = await cursor.fetchone()
        return self._row_to_report(row) if row else None
    
    def _row_to_report(self, row) -> Report:
        """Convert database row to Report model"""
        return Report(
            id=row['id'],
            keyword=row['keyword'],
            date=row['date'],
            file_path=row['file_path'],
            article_count=row['article_count'],
            generated_at=datetime.fromisoformat(row['generated_at'])
        )


class ScheduleRepository:
    """Repository for Schedule configuration operations"""
    
    def __init__(self, db: Database):
        self.db = db
    
    async def get_config(self) -> ScheduleConfigModel:
        """Get schedule configuration"""
        cursor = await self.db.conn.execute("""
            SELECT * FROM schedule_config WHERE id = 1
        """)
        
        row = await cursor.fetchone()
        if not row:
            # Create default if not exists
            await self._create_default()
            return await self.get_config()
        
        return ScheduleConfigModel(
            id=row['id'],
            time=row['time'],
            enabled=bool(row['enabled']),
            updated_at=datetime.fromisoformat(row['updated_at'])
        )
    
    async def update_config(self, time: str, enabled: bool) -> bool:
        """Update schedule configuration"""
        cursor = await self.db.conn.execute("""
            UPDATE schedule_config 
            SET time = ?, enabled = ?, updated_at = ?
            WHERE id = 1
        """, (time, 1 if enabled else 0, datetime.now().isoformat()))
        
        await self.db.conn.commit()
        return cursor.rowcount > 0
    
    async def _create_default(self):
        """Create default schedule configuration"""
        await self.db.conn.execute("""
            INSERT OR IGNORE INTO schedule_config (id, time, enabled, updated_at)
            VALUES (1, '08:00', 1, ?)
        """, (datetime.now().isoformat(),))
        
        await self.db.conn.commit()
