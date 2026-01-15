"""
Schedule configuration API endpoints
"""
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.db.database import Database
from src.db.repository import ScheduleRepository
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
