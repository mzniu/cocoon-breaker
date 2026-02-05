"""
Schedule configuration API endpoints
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.db.database import Database
from src.db.repository import ScheduleRepository, CrawlScheduleRepository
from src.db.models import ScheduleConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


# Pydantic models
class ScheduleResponse(BaseModel):
    """Response model for schedule configuration"""
    id: int
    time: str = Field(..., description="Time in HH:MM format")
    enabled: bool
    updated_at: str
    
    class Config:
        from_attributes = True


class ScheduleUpdateRequest(BaseModel):
    """Request model for updating schedule"""
    time: str = Field(..., pattern=r'^([01]\d|2[0-3]):([0-5]\d)$', description="Time in HH:MM format")
    enabled: bool


class CrawlScheduleResponse(BaseModel):
    """Response model for crawl schedule configuration"""
    id: int
    enabled: bool
    times: list[str] = Field(..., description="List of times in HH:MM format")
    updated_at: str
    
    class Config:
        from_attributes = True


class CrawlScheduleUpdateRequest(BaseModel):
    """Request model for updating crawl schedule"""
    enabled: bool
    times: list[str] = Field(..., min_length=1, description="List of times in HH:MM format")


# Dependency to get database
def get_db() -> Database:
    """Get database dependency"""
    from src.main import get_db as main_get_db
    return main_get_db()


@router.get("", response_model=ScheduleResponse)
async def get_schedule(db: Database = Depends(get_db)):
    """
    Get current schedule configuration
    
    Returns:
        Schedule configuration
    """
    try:
        repo = ScheduleRepository(db)
        schedule = await repo.get_config()
        
        if not schedule:
            # Return default schedule if not found
            return ScheduleResponse(
                id=1,
                time="08:00",
                enabled=True,
                updated_at=datetime.now().isoformat()
            )
        
        return ScheduleResponse(
            id=schedule.id,
            time=schedule.time,
            enabled=schedule.enabled,
            updated_at=schedule.updated_at.isoformat() if schedule.updated_at else ""
        )
    
    except Exception as e:
        logger.error(f"Failed to get schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve schedule configuration"
        )


@router.put("", response_model=ScheduleResponse)
async def update_schedule(
    request: ScheduleUpdateRequest,
    db: Database = Depends(get_db)
):
    """
    Update schedule configuration
    
    Args:
        request: Schedule update data
    
    Returns:
        Updated schedule configuration
    """
    try:
        repo = ScheduleRepository(db)
        
        # Update schedule using update_config
        success = await repo.update_config(request.time, request.enabled)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update schedule configuration"
            )
        
        logger.info(f"Schedule updated: {request.time}, enabled={request.enabled}")
        
        # Get updated config to return
        schedule = await repo.get_config()
        
        # If scheduler is running, we need to restart it with new schedule
        # This would be handled by the scheduler watching for config changes
        # For now, just return the updated config
        
        return ScheduleResponse(
            id=schedule.id,
            time=schedule.time,
            enabled=schedule.enabled,
            updated_at=schedule.updated_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update schedule configuration"
        )


# ==================== Crawl Schedule APIs ====================

@router.get("/crawl", response_model=CrawlScheduleResponse)
async def get_crawl_schedule(db: Database = Depends(get_db)):
    """
    Get crawl schedule configuration for article collection
    
    Returns:
        Crawl schedule configuration with times list
    """
    try:
        repo = CrawlScheduleRepository(db)
        config = await repo.get_config()
        
        if not config:
            # Return default schedule if not found
            return CrawlScheduleResponse(
                id=1,
                enabled=True,
                times=["06:00", "12:00", "18:00", "22:00"],
                updated_at=datetime.now().isoformat()
            )
        
        return CrawlScheduleResponse(
            id=config.id,
            enabled=config.enabled,
            times=config.times,
            updated_at=config.updated_at.isoformat() if config.updated_at else ""
        )
    
    except Exception as e:
        logger.error(f"Failed to get crawl schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve crawl schedule configuration"
        )


@router.put("/crawl", response_model=CrawlScheduleResponse)
async def update_crawl_schedule(
    request: CrawlScheduleUpdateRequest,
    db: Database = Depends(get_db)
):
    """
    Update crawl schedule configuration
    
    Args:
        request: Crawl schedule update data with times list
    
    Returns:
        Updated crawl schedule configuration
    """
    try:
        # Validate time format
        import re
        time_pattern = r'^([01]\d|2[0-3]):([0-5]\d)$'
        for t in request.times:
            if not re.match(time_pattern, t):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid time format: {t}. Expected HH:MM format."
                )
        
        repo = CrawlScheduleRepository(db)
        
        # Update crawl schedule
        success = await repo.update_config(request.enabled, request.times)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update crawl schedule configuration"
            )
        
        logger.info(f"Crawl schedule updated: enabled={request.enabled}, times={request.times}")
        
        # Get updated config to return
        config = await repo.get_config()
        
        return CrawlScheduleResponse(
            id=config.id,
            enabled=config.enabled,
            times=config.times,
            updated_at=config.updated_at.isoformat()
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update crawl schedule: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update crawl schedule configuration"
        )
