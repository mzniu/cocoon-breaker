"""
Unit tests for main application and health check
"""
import pytest
from httpx import AsyncClient

from src.main import app


@pytest.mark.asyncio
class TestHealthAPI:
    """Test health check API"""
    
    async def test_health_check(self):
        """Test health check endpoint returns ok"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "cocoon-breaker"
        assert "version" in data
    
    async def test_root_endpoint(self):
        """Test root endpoint"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert data["docs"] == "/docs"
    
    async def test_cors_headers(self):
        """Test CORS headers are present"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.options("/api/health")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
class TestApplicationLifecycle:
    """Test application lifecycle"""
    
    async def test_app_startup(self):
        """Test application can start successfully"""
        # App is already started in fixture, just verify it works
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/health")
        
        assert response.status_code == 200
