"""
FastAPI main application
"""
import sys
import asyncio
import logging
import logging.handlers
from pathlib import Path
from contextlib import asynccontextmanager

# Set Windows event loop policy for Playwright subprocess support
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Add project root to path for direct execution
if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_config
from src.db import Database
from src.api.subscriptions import router as subscriptions_router
from src.api.reports import router as reports_router
from src.api.schedule import router as schedule_router
from src.api.articles import router as articles_router

# Initialize logger
logger = logging.getLogger(__name__)


def setup_logging(config):
    """Setup logging configuration"""
    # Create logs directory
    log_file = Path(config.logging.file)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Create formatter
    formatter = logging.Formatter(config.logging.format)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        config.logging.file,
        maxBytes=config.logging.max_bytes,
        backupCount=config.logging.backup_count,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(config.logging.level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Setup log buffer for real-time log streaming
    from src.utils import setup_log_buffer
    setup_log_buffer()
    
    logger.info("Logging configured")


# Global database instance
db: Database = None
scheduler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    global db, scheduler
    
    # Startup
    config = get_config()
    setup_logging(config)
    
    logger.info("Starting Cocoon Breaker application...")
    
    # Initialize database
    db = Database(config.database.path)
    await db.connect()
    logger.info(f"Database connected: {config.database.path}")
    
    # Create output directories
    Path(config.output.directory).mkdir(parents=True, exist_ok=True)
    
    # Start scheduler (only if not in debug mode to avoid issues with hot reload)
    if not config.server.debug:
        from src.scheduler.tasks import get_scheduler
        scheduler = await get_scheduler()
        await scheduler.start()
        logger.info("Scheduler initialized")
    else:
        logger.info("Debug mode: Scheduler not started (use API to trigger reports)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Cocoon Breaker application...")
    
    # Stop scheduler first
    if scheduler:
        try:
            await scheduler.stop()
            logger.info("Scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping scheduler: {e}")
    
    # Close database
    if db:
        await db.close()
        logger.info("Database closed")


# Create FastAPI app
app = FastAPI(
    title="Cocoon Breaker API",
    description="AI-powered daily report generator",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Block direct access to /static/index.html (redirect to root)
@app.get("/static/index.html", tags=["System"])
async def block_static_index():
    """Redirect /static/index.html to root"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/", status_code=301)

# Block direct access to /static/articles.html (redirect to /articles.html)
@app.get("/static/articles.html", tags=["System"])
async def block_static_articles():
    """Redirect /static/articles.html to /articles.html"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/articles.html", status_code=301)

# Mount static files
app.mount("/static", StaticFiles(directory="src/static"), name="static")

# Register API routers
app.include_router(subscriptions_router)
app.include_router(reports_router)
app.include_router(schedule_router)
app.include_router(articles_router)


# Health check endpoint
@app.get("/api/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "cocoon-breaker",
        "version": "1.0.0"
    }


@app.get("/api/logs", tags=["System"])
async def get_logs(count: int = 50):
    """Get recent logs from buffer"""
    from src.utils import get_log_buffer
    buffer = get_log_buffer()
    return {
        "logs": buffer.get_logs(count)
    }


@app.get("/", tags=["System"])
async def root():
    """Root endpoint - serve index.html"""
    from fastapi.responses import FileResponse
    return FileResponse("src/static/index.html")


@app.get("/index.html", tags=["System"])
async def index():
    """Index page - serve index.html"""
    from fastapi.responses import FileResponse
    return FileResponse("src/static/index.html")


@app.get("/articles.html", tags=["System"])
async def articles():
    """Articles page - serve articles.html"""
    from fastapi.responses import FileResponse
    return FileResponse("src/static/articles.html")


def get_db() -> Database:
    """Get database instance for dependency injection"""
    if db is None:
        raise RuntimeError("Database not initialized")
    return db


if __name__ == "__main__":
    import uvicorn
    
    config = get_config()
    
    uvicorn.run(
        "src.main:app",
        host=config.server.host,
        port=config.server.port,
        reload=config.server.debug,
        log_level="info"
    )
