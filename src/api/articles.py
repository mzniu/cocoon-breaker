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
    score: float | None = None  # 时效性评分
    
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
    Get all articles with optional filters and scoring
    
    Query Parameters:
        - keyword: Filter by subscription keyword
        - source: Filter by crawler source (baidu/bing)
        - hours: Only show articles from last N hours
        - limit: Maximum number of results (1-500)
    
    Returns:
        List of articles with freshness scores
    """
    import math
    
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
        
        # Calculate scores for each article
        now = datetime.now()
        items = []
        
        for article in articles:
            # Calculate hours since crawled
            time_diff = now - article.crawled_at
            hours_old = time_diff.total_seconds() / 3600
            
            # === 质量评分（多维度）===
            content_length = len(article.content)
            
            # 1. 内容长度评分（钟形曲线，200-2000字最优）
            if content_length < 200:
                length_score = content_length / 200 * 0.6  # 太短扣分
            elif content_length <= 2000:
                length_score = 0.6 + (content_length - 200) / 1800 * 0.4  # 200-2000渐增到1.0
            else:
                # 超过2000字开始衰减
                length_score = max(0.7, 1.0 - (content_length - 2000) / 5000 * 0.3)
            
            # 2. 标题质量评分
            title_length = len(article.title)
            if 10 <= title_length <= 50:
                title_score = 1.0
            elif title_length < 10:
                title_score = 0.6
            else:
                title_score = max(0.7, 1.0 - (title_length - 50) / 50 * 0.3)  # 标题党扣分
            
            # 3. 来源权威性评分（分级）
            source_weights = {
                'kr36': 1.3,      # 专业科技媒体
                'huxiu': 1.3,     # 专业商业媒体
                'tavily': 1.2,    # AI搜索，信息质量较高
                'google': 1.15,   # 国际搜索引擎
                'yahoo': 1.1,     # 综合门户
                'baidu': 1.0      # 基础搜索
            }
            source_weight = source_weights.get(article.source, 1.0)
            
            # 综合质量评分 = (长度评分40% + 标题评分20%) * 来源权重 + 来源基础分40%
            quality_score = (length_score * 0.4 + title_score * 0.2) * source_weight + (source_weight - 1.0) * 0.4
            quality_score = min(1.0, quality_score)
            
            # === 时效性评分（指数衰减）===
            # 根据内容长度调整时效性权重：短文更看重时效性，长文更看重质量
            if content_length < 500:
                time_decay_lambda = 0.15  # 短新闻，衰减快
                freshness_weight = 0.4    # 时效性权重高
            elif content_length < 1500:
                time_decay_lambda = 0.1   # 中等文章
                freshness_weight = 0.3    # 时效性权重中等
            else:
                time_decay_lambda = 0.05  # 长文/深度文章，衰减慢
                freshness_weight = 0.2    # 时效性权重低
            
            freshness_score = math.exp(-time_decay_lambda * hours_old)
            
            # === 最终评分 ===
            quality_weight = 1.0 - freshness_weight
            final_score = quality_weight * quality_score + freshness_weight * freshness_score
            
            items.append(
                ArticleResponse(
                    id=article.id,
                    title=article.title,
                    url=article.url,
                    content=article.content,
                    source=article.source,
                    keyword=article.keyword,
                    crawled_at=article.crawled_at.isoformat() if article.crawled_at else "",
                    published_at=article.published_at.isoformat() if article.published_at else None,
                    score=round(final_score, 4)  # 保留4位小数
                )
            )
        
        logger.info(f"Retrieved {len(items)} articles with scores (keyword={keyword}, source={source}, hours={hours})")
        
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
