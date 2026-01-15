"""
Unit tests for schedule API
"""
import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.main import app
from src.db.models import ScheduleConfig


@pytest.mark.asyncio
async def test_get_schedule():
    """Test getting schedule configuration"""
    schedule = ScheduleConfig(
        id=1,
        time="08:00",
        enabled=True,
        updated_at=datetime(2024, 1, 1, 10, 0, 0)
    )
    
    with patch('src.api.schedule.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = schedule
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.schedule.ScheduleRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/schedule")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["time"] == "08:00"
            assert data["enabled"] is True


@pytest.mark.asyncio
async def test_get_schedule_default():
    """Test getting default schedule when none exists"""
    with patch('src.api.schedule.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get.return_value = None
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.schedule.ScheduleRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/schedule")
            
            assert response.status_code == 200
            data = response.json()
            assert data["time"] == "08:00"
            assert data["enabled"] is True


@pytest.mark.asyncio
async def test_update_schedule():
    """Test updating schedule configuration"""
    with patch('src.api.schedule.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update.return_value = True
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.schedule.ScheduleRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.put(
                    "/api/schedule",
                    json={"time": "09:30", "enabled": False}
                )
            
            assert response.status_code == 200
            data = response.json()
            assert data["time"] == "09:30"
            assert data["enabled"] is False


@pytest.mark.asyncio
async def test_update_schedule_invalid_time_format():
    """Test updating schedule with invalid time format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/schedule",
            json={"time": "25:00", "enabled": True}  # Invalid hour
        )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_update_schedule_invalid_time_string():
    """Test updating schedule with invalid time string"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.put(
            "/api/schedule",
            json={"time": "invalid", "enabled": True}
        )
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_update_schedule_update_fails():
    """Test updating schedule when database update fails"""
    with patch('src.api.schedule.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.update.return_value = False
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.schedule.ScheduleRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.put(
                    "/api/schedule",
                    json={"time": "09:00", "enabled": True}
                )
            
            assert response.status_code == 500


@pytest.mark.asyncio
async def test_update_schedule_valid_times():
    """Test updating schedule with various valid times"""
    valid_times = ["00:00", "12:00", "23:59", "08:30"]
    
    for time in valid_times:
        with patch('src.api.schedule.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.update.return_value = True
            
            mock_get_db.return_value = mock_db
            
            with patch('src.api.schedule.ScheduleRepository', return_value=mock_repo):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.put(
                        "/api/schedule",
                        json={"time": time, "enabled": True}
                    )
                
                assert response.status_code == 200, f"Failed for time: {time}"
                data = response.json()
                assert data["time"] == time
