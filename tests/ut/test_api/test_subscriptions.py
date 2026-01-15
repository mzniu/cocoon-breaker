"""
Unit tests for subscriptions API
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.main import app
from src.db.models import Subscription


@pytest.mark.asyncio
async def test_list_subscriptions_empty():
    """Test listing empty subscriptions"""
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = []
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/subscriptions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert data["items"] == []


@pytest.mark.asyncio
async def test_list_subscriptions_with_data():
    """Test listing subscriptions with data"""
    subscriptions = [
        Subscription(
            id=1,
            keyword="AI",
            created_at=datetime(2024, 1, 1, 10, 0, 0),
            enabled=True
        ),
        Subscription(
            id=2,
            keyword="Python",
            created_at=datetime(2024, 1, 2, 10, 0, 0),
            enabled=False
        )
    ]
    
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = subscriptions
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/subscriptions")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["keyword"] == "AI"


@pytest.mark.asyncio
async def test_create_subscription_success():
    """Test creating subscription successfully"""
    with patch('src.api.subscriptions.get_db') as mock_get_db, \
         patch('src.api.subscriptions.get_config') as mock_config:
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = []
        mock_repo.create.return_value = 1
        
        mock_get_db.return_value = mock_db
        
        mock_cfg = AsyncMock()
        mock_cfg.subscriptions.max_keywords = 5
        mock_config.return_value = mock_cfg
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={"keyword": "AI"}
                )
            
            assert response.status_code == 201
            data = response.json()
            assert data["id"] == 1
            assert data["keyword"] == "AI"
            assert data["enabled"] is True


@pytest.mark.asyncio
async def test_create_subscription_duplicate():
    """Test creating duplicate subscription"""
    existing = [
        Subscription(
            id=1,
            keyword="AI",
            created_at=datetime.now(),
            enabled=True
        )
    ]
    
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = existing
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={"keyword": "AI"}
                )
            
            assert response.status_code == 409
            assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_subscription_max_limit():
    """Test creating subscription when at max limit"""
    existing = [
        Subscription(id=i, keyword=f"Topic{i}", created_at=datetime.now(), enabled=True)
        for i in range(5)
    ]
    
    with patch('src.api.subscriptions.get_db') as mock_get_db, \
         patch('src.api.subscriptions.get_config') as mock_config:
        
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = existing
        
        mock_get_db.return_value = mock_db
        
        mock_cfg = AsyncMock()
        mock_cfg.subscriptions.max_keywords = 5
        mock_config.return_value = mock_cfg
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.post(
                    "/api/subscriptions",
                    json={"keyword": "NewTopic"}
                )
            
            assert response.status_code == 400
            assert "Maximum" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_subscription_success():
    """Test deleting subscription successfully"""
    existing = [
        Subscription(id=1, keyword="AI", created_at=datetime.now(), enabled=True)
    ]
    
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = existing
        mock_repo.delete.return_value = True
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete("/api/subscriptions/1")
            
            assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_subscription_not_found():
    """Test deleting non-existent subscription"""
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = []
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.delete("/api/subscriptions/999")
            
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_toggle_subscription_success():
    """Test toggling subscription enabled status"""
    existing = [
        Subscription(id=1, keyword="AI", created_at=datetime.now(), enabled=True)
    ]
    
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = existing
        mock_repo.update_enabled.return_value = True
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.patch(
                    "/api/subscriptions/1/enabled?enabled=false"
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["enabled"] is False


@pytest.mark.asyncio
async def test_toggle_subscription_not_found():
    """Test toggling non-existent subscription"""
    with patch('src.api.subscriptions.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_all.return_value = []
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.subscriptions.SubscriptionRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.patch(
                    "/api/subscriptions/999/enabled?enabled=false"
                )
            
            assert response.status_code == 404
