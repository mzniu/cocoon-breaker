"""
Subscription management API endpoints
"""
import logging
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from src.db.database import Database
from src.db.repository import SubscriptionRepository
from src.db.models import Subscription

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscriptions", tags=["subscriptions"])


# Pydantic models
class SubscriptionCreate(BaseModel):
    """Request model for creating subscription"""
    keyword: str = Field(..., min_length=1, max_length=50, description="Search keyword")


class SubscriptionResponse(BaseModel):
    """Response model for subscription"""
    id: int
    keyword: str
    created_at: str
    enabled: bool
    
    class Config:
        from_attributes = True


class SubscriptionListResponse(BaseModel):
    """Response model for subscription list"""
    total: int
    items: List[SubscriptionResponse]


# Dependency to get database
def get_db() -> Database:
    """Get database dependency"""
    from src.main import get_db as main_get_db
    return main_get_db()


@router.get("", response_model=SubscriptionListResponse)
async def list_subscriptions(db: Database = Depends(get_db)):
    """
    Get all subscriptions
    
    Returns:
        List of all subscriptions
    """
    try:
        repo = SubscriptionRepository(db)
        subscriptions = await repo.get_all()
        
        items = [
            SubscriptionResponse(
                id=sub.id,
                keyword=sub.keyword,
                created_at=sub.created_at.isoformat() if sub.created_at else "",
                enabled=sub.enabled
            )
            for sub in subscriptions
        ]
        
        return SubscriptionListResponse(
            total=len(items),
            items=items
        )
    
    except Exception as e:
        logger.error(f"Failed to list subscriptions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve subscriptions"
        )


@router.post("", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_subscription(
    subscription: SubscriptionCreate,
    db: Database = Depends(get_db)
):
    """
    Create new subscription
    
    Args:
        subscription: Subscription data
    
    Returns:
        Created subscription
    """
    try:
        repo = SubscriptionRepository(db)
        
        # Check if keyword already exists
        existing = await repo.get_all()
        if any(s.keyword == subscription.keyword for s in existing):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Subscription for '{subscription.keyword}' already exists"
            )
        
        # Check subscription limit (max 5 from config)
        from src.config import get_config
        config = get_config()
        max_subscriptions = config.subscriptions.max_keywords
        
        if len(existing) >= max_subscriptions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum {max_subscriptions} subscriptions allowed"
            )
        
        # Create subscription (pass keyword string, not object)
        sub_id = await repo.create(subscription.keyword)
        
        if sub_id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create subscription"
            )
        
        logger.info(f"Created subscription: {subscription.keyword} (id={sub_id})")
        
        return SubscriptionResponse(
            id=sub_id,
            keyword=subscription.keyword,
            created_at=datetime.now().isoformat(),
            enabled=True
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create subscription"
        )


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subscription(
    subscription_id: int,
    db: Database = Depends(get_db)
):
    """
    Delete subscription
    
    Args:
        subscription_id: Subscription ID
    """
    try:
        repo = SubscriptionRepository(db)
        
        # Check if subscription exists
        subscriptions = await repo.get_all()
        subscription = next((s for s in subscriptions if s.id == subscription_id), None)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription {subscription_id} not found"
            )
        
        # Delete subscription
        success = await repo.delete(subscription_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete subscription"
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete subscription"
        )


@router.patch("/{subscription_id}/enabled", response_model=SubscriptionResponse)
async def toggle_subscription(
    subscription_id: int,
    enabled: bool,
    db: Database = Depends(get_db)
):
    """
    Enable or disable subscription
    
    Args:
        subscription_id: Subscription ID
        enabled: Enable status
    
    Returns:
        Updated subscription
    """
    try:
        repo = SubscriptionRepository(db)
        
        # Check if subscription exists
        subscriptions = await repo.get_all()
        subscription = next((s for s in subscriptions if s.id == subscription_id), None)
        
        if not subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription {subscription_id} not found"
            )
        
        # Update enabled status
        success = await repo.update_enabled(subscription_id, enabled)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update subscription"
            )
        
        # Return updated subscription
        subscription.enabled = enabled
        
        return SubscriptionResponse(
            id=subscription.id,
            keyword=subscription.keyword,
            created_at=subscription.created_at.isoformat() if subscription.created_at else "",
            enabled=subscription.enabled
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to toggle subscription {subscription_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update subscription"
        )
