"""
Articles API endpoints
"""
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from src.db.database import Database
from src.db.repository import ArticleRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


# Pydantic models
class ArticleResponse(BaseModel):
    """Response model for article"""
    id: int
    title: str
    url: str
    content: str
    source: str
    keyword: str
    crawled_at: str
    published_at: str | None
    
    class Config:
        from_attributes = True


class ArticleListResponse(BaseModel):
    """Response model for article list"""
    total: int
    items: list[ArticleResponse]


# Dependency to get database
def get_db() -> Database:
    """Get database dependency"""
    from src.main import get_db as main_get_db
    return main_get_db()


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    keyword: str | None = Query(None, description="Filter by keyword"),
    source: str | None = Query(None, description="Filter by source (baidu/bing)"),
    hours: int | None = Query(None, description="Only show articles from last N hours"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    db: Database = Depends(get_db)
):
    """
    Get all articles with optional filters
    
    Query Parameters:
        - keyword: Filter by subscription keyword
        - source: Filter by crawler source (baidu/bing)
        - hours: Only show articles from last N hours
        - limit: Maximum number of results (1-500)
    
    Returns:
        List of articles
    """
    try:
        repo = ArticleRepository(db)
        
        # Get articles based on filters
        if keyword and hours:
            articles = await repo.get_recent_by_keyword(keyword, hours, limit)
        elif keyword:
            articles = await repo.get_by_keyword(keyword, limit)
        else:
            # Get all recent articles
            articles = await repo.get_all(limit)
        
        # Apply source filter if specified
        if source:
            articles = [a for a in articles if a.source == source]
        
        # Convert to response model
        items = [
            ArticleResponse(
                id=article.id,
                title=article.title,
                url=article.url,
                content=article.content,
                source=article.source,
                keyword=article.keyword,
                crawled_at=article.crawled_at.isoformat() if article.crawled_at else "",
                published_at=article.published_at.isoformat() if article.published_at else None
            )
            for article in articles
        ]
        
        logger.info(f"Retrieved {len(items)} articles (keyword={keyword}, source={source}, hours={hours})")
        
        return ArticleListResponse(
            total=len(items),
            items=items
        )
    
    except Exception as e:
        logger.error(f"Failed to list articles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve articles"
        )


@router.get("/{article_id}", response_model=ArticleResponse)
async def get_article(
    article_id: int,
    db: Database = Depends(get_db)
):
    """
    Get article by ID
    
    Args:
        article_id: Article ID
    
    Returns:
        Article details
    """
    try:
        repo = ArticleRepository(db)
        article = await repo.get_by_id(article_id)
        
        if not article:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Article {article_id} not found"
            )
        
        return ArticleResponse(
            id=article.id,
            title=article.title,
            url=article.url,
            content=article.content,
            source=article.source,
            keyword=article.keyword,
            crawled_at=article.crawled_at.isoformat() if article.crawled_at else "",
            published_at=article.published_at.isoformat() if article.published_at else None
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get article {article_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve article"
        )


@router.delete("/cleanup")
async def cleanup_old_articles(
    days: int = Query(30, ge=1, le=365, description="Delete articles older than N days"),
    db: Database = Depends(get_db)
):
    """
    Cleanup old articles
    
    Query Parameters:
        - days: Delete articles older than this many days (default 30)
    
    Returns:
        Number of deleted articles
    """
    try:
        repo = ArticleRepository(db)
        deleted_count = await repo.delete_old_articles(days)
        
        logger.info(f"Deleted {deleted_count} articles older than {days} days")
        
        return {
            "status": "success",
            "deleted_count": deleted_count,
            "message": f"Deleted {deleted_count} articles older than {days} days"
        }
    
    except Exception as e:
        logger.error(f"Failed to cleanup articles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cleanup articles"
        )
