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
            # 添加更多迁移...
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


async def run_migrations(db_path: str):
    """Standalone migration runner"""
    migration = DatabaseMigration(db_path)
    
    async with aiosqlite.connect(db_path) as conn:
        await migration.migrate(conn)
        print("✅ Migrations completed successfully")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migrations("./data/cocoon.db"))
