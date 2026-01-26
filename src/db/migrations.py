"""
Database migration system
"""
import aiosqlite
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class DatabaseMigration:
    """Handle database schema migrations"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    async def get_version(self, conn: aiosqlite.Connection) -> int:
        """Get current database version"""
        try:
            cursor = await conn.execute(
                "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
            )
            row = await cursor.fetchone()
            return row[0] if row else 0
        except:
            # Table doesn't exist, version 0
            return 0
    
    async def set_version(self, conn: aiosqlite.Connection, version: int):
        """Set database version"""
        await conn.execute(
            "INSERT INTO schema_version (version, applied_at) VALUES (?, datetime('now'))",
            (version,)
        )
    
    async def migrate(self, conn: aiosqlite.Connection):
        """Run all pending migrations"""
        # Create migration tracking table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
        """)
        
        current_version = await self.get_version(conn)
        logger.info(f"Current database version: {current_version}")
        
        # Define migrations
        migrations = [
            (1, self._migration_001_initial),
            (2, self._migration_002_add_score_cache),
            (3, self._migration_003_add_full_content_fields),
            (4, self._migration_004_add_analysis_fields),
        ]
        
        # Apply pending migrations
        for version, migration_func in migrations:
            if version > current_version:
                logger.info(f"Applying migration {version}...")
                await migration_func(conn)
                await self.set_version(conn, version)
                logger.info(f"Migration {version} completed")
        
        await conn.commit()
    
    async def _migration_001_initial(self, conn: aiosqlite.Connection):
        """Initial schema (baseline)"""
        # 这个迁移是占位符，表示现有结构
        pass
    
    async def _migration_002_add_score_cache(self, conn: aiosqlite.Connection):
        """Add cached score column to articles table (optional)"""
        # 仅作示例，实际可能不需要
        await conn.execute("""
            ALTER TABLE articles 
            ADD COLUMN cached_score REAL DEFAULT NULL
        """)
        
        # Create index for score-based queries
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_score 
            ON articles(cached_score DESC) 
            WHERE cached_score IS NOT NULL
        """)
    
    async def _migration_003_add_full_content_fields(self, conn: aiosqlite.Connection):
        """Add full content fetching related fields"""
        # Add full_content field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN full_content TEXT
            """)
        except Exception as e:
            logger.warning(f"Column full_content may already exist: {e}")
        
        # Add fetch_status field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN fetch_status TEXT DEFAULT 'pending'
            """)
        except Exception as e:
            logger.warning(f"Column fetch_status may already exist: {e}")
        
        # Add fetched_at field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN fetched_at TEXT
            """)
        except Exception as e:
            logger.warning(f"Column fetched_at may already exist: {e}")
        
        # Add fetch_error field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN fetch_error TEXT
            """)
        except Exception as e:
            logger.warning(f"Column fetch_error may already exist: {e}")
        
        # Create index for fetch_status
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_fetch_status 
            ON articles(fetch_status)
        """)
        
        logger.info("Added full_content related fields to articles table")
    
    async def _migration_004_add_analysis_fields(self, conn: aiosqlite.Connection):
        """Add AI analysis related fields"""
        # Add actual_published_at field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN actual_published_at TEXT
            """)
        except Exception as e:
            logger.warning(f"Column actual_published_at may already exist: {e}")
        
        # Add actual_source field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN actual_source TEXT
            """)
        except Exception as e:
            logger.warning(f"Column actual_source may already exist: {e}")
        
        # Add importance_score field (0-100)
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN importance_score REAL
            """)
        except Exception as e:
            logger.warning(f"Column importance_score may already exist: {e}")
        
        # Add analysis_status field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN analysis_status TEXT DEFAULT 'pending'
            """)
        except Exception as e:
            logger.warning(f"Column analysis_status may already exist: {e}")
        
        # Add analyzed_at field
        try:
            await conn.execute("""
                ALTER TABLE articles 
                ADD COLUMN analyzed_at TEXT
            """)
        except Exception as e:
            logger.warning(f"Column analyzed_at may already exist: {e}")
        
        # Create index for analysis_status
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_analysis_status 
            ON articles(analysis_status)
        """)
        
        # Create index for importance_score
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_articles_importance_score 
            ON articles(importance_score DESC)
        """)
        
        logger.info("Added AI analysis related fields to articles table")


async def run_migrations(db_path: str):
    """Standalone migration runner"""
    migration = DatabaseMigration(db_path)
    
    async with aiosqlite.connect(db_path) as conn:
        await migration.migrate(conn)
        print("✅ Migrations completed successfully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migrations("./data/cocoon.db"))
