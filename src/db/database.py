"""
Database connection and initialization
"""
import aiosqlite
import sqlite3
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Database:
    """SQLite database manager"""
    
    def __init__(self, db_path: str = "./data/cocoon.db"):
        self.db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        
        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def connect(self):
        """Establish database connection"""
        self._conn = await aiosqlite.connect(self.db_path)
        self._conn.row_factory = aiosqlite.Row
        await self.initialize()
    
    async def close(self):
        """Close database connection"""
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    async def initialize(self):
        """Create tables if they don't exist"""
        await self._create_articles_table()
        await self._create_subscriptions_table()
        await self._create_reports_table()
        await self._create_schedule_table()
        await self._conn.commit()
    
    async def _create_articles_table(self):
        """Create articles table"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                content TEXT,
                source TEXT NOT NULL,
                keyword TEXT NOT NULL,
                crawled_at TEXT NOT NULL,
                published_at TEXT,
                UNIQUE(url)
            )
        """)
        
        # Create indices for better query performance
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_keyword 
            ON articles(keyword)
        """)
        
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_crawled_at 
            ON articles(crawled_at DESC)
        """)
    
    async def _create_subscriptions_table(self):
        """Create subscriptions table"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                UNIQUE(keyword)
            )
        """)
    
    async def _create_reports_table(self):
        """Create reports table"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                date TEXT NOT NULL,
                file_path TEXT NOT NULL,
                article_count INTEGER NOT NULL,
                generated_at TEXT NOT NULL,
                UNIQUE(keyword, date)
            )
        """)
        
        await self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_reports_date 
            ON reports(date DESC)
        """)
    
    async def _create_schedule_table(self):
        """Create schedule configuration table"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS schedule_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                time TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                updated_at TEXT NOT NULL
            )
        """)
        
        # Insert default schedule if not exists
        await self._conn.execute("""
            INSERT OR IGNORE INTO schedule_config (id, time, enabled, updated_at)
            VALUES (1, '08:00', 1, datetime('now'))
        """)
    
    @property
    def conn(self) -> aiosqlite.Connection:
        """Get database connection"""
        if self._conn is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._conn


# Synchronous version for initialization and testing
def init_database_sync(db_path: str = "./data/cocoon.db"):
    """Initialize database synchronously (for setup scripts)"""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            url TEXT UNIQUE NOT NULL,
            content TEXT,
            source TEXT NOT NULL,
            keyword TEXT NOT NULL,
            crawled_at TEXT NOT NULL,
            published_at TEXT,
            UNIQUE(url)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT UNIQUE NOT NULL,
            created_at TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            UNIQUE(keyword)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            keyword TEXT NOT NULL,
            date TEXT NOT NULL,
            file_path TEXT NOT NULL,
            article_count INTEGER NOT NULL,
            generated_at TEXT NOT NULL,
            UNIQUE(keyword, date)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schedule_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            time TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            updated_at TEXT NOT NULL
        )
    """)
    
    cursor.execute("""
        INSERT OR IGNORE INTO schedule_config (id, time, enabled, updated_at)
        VALUES (1, '08:00', 1, datetime('now'))
    """)
    
    conn.commit()
    conn.close()
    
    logger.info(f"Database initialized at {db_path}")
