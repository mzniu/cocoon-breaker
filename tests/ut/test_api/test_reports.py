"""
Unit tests for reports API
"""
import pytest
import tempfile
import os
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, date
from pathlib import Path

from src.main import app
from src.db.models import Report


@pytest.mark.asyncio
async def test_list_reports():
    """Test listing reports"""
    with patch('src.api.reports.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_get_db.return_value = mock_db
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/reports")
        
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data


@pytest.mark.asyncio
async def test_get_report_by_id():
    """Test getting report by ID"""
    report = Report(
        id=1,
        keyword="AI",
        date=date(2024, 1, 1),
        file_path="reports/AI_2024-01-01.html",
        article_count=5,
        generated_at=datetime(2024, 1, 1, 10, 0, 0)
    )
    
    with patch('src.api.reports.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = report
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.reports.ReportRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/reports/1")
            
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["keyword"] == "AI"
            assert data["article_count"] == 5


@pytest.mark.asyncio
async def test_get_report_not_found():
    """Test getting non-existent report"""
    with patch('src.api.reports.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = None
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.reports.ReportRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/reports/999")
            
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_download_report():
    """Test downloading report file"""
    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body>Test Report</body></html>")
        temp_file = f.name
    
    try:
        report = Report(
            id=1,
            keyword="AI",
            date=date(2024, 1, 1),
            file_path=temp_file,
            article_count=5,
            generated_at=datetime.now()
        )
        
        with patch('src.api.reports.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.get_by_id.return_value = report
            
            mock_get_db.return_value = mock_db
            
            with patch('src.api.reports.ReportRepository', return_value=mock_repo):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/reports/1/download")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/html; charset=utf-8"
    
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


@pytest.mark.asyncio
async def test_download_report_file_not_found():
    """Test downloading report with missing file"""
    report = Report(
        id=1,
        keyword="AI",
        date=date(2024, 1, 1),
        file_path="nonexistent.html",
        article_count=5,
        generated_at=datetime.now()
    )
    
    with patch('src.api.reports.get_db') as mock_get_db:
        mock_db = AsyncMock()
        mock_repo = AsyncMock()
        mock_repo.get_by_id.return_value = report
        
        mock_get_db.return_value = mock_db
        
        with patch('src.api.reports.ReportRepository', return_value=mock_repo):
            async with AsyncClient(app=app, base_url="http://test") as client:
                response = await client.get("/api/reports/1/download")
            
            assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_report_by_keyword_date():
    """Test getting report by keyword and date"""
    # Create temp HTML file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
        f.write("<html><body>Test Report</body></html>")
        temp_file = f.name
    
    try:
        report = Report(
            id=1,
            keyword="AI",
            date=date(2024, 1, 1),
            file_path=temp_file,
            article_count=5,
            generated_at=datetime.now()
        )
        
        with patch('src.api.reports.get_db') as mock_get_db:
            mock_db = AsyncMock()
            mock_repo = AsyncMock()
            mock_repo.get_by_keyword_date.return_value = report
            
            mock_get_db.return_value = mock_db
            
            with patch('src.api.reports.ReportRepository', return_value=mock_repo):
                async with AsyncClient(app=app, base_url="http://test") as client:
                    response = await client.get("/api/reports/keyword/AI/2024-01-01")
                
                assert response.status_code == 200
                assert response.headers["content-type"] == "text/html; charset=utf-8"
    
    finally:
        if os.path.exists(temp_file):
            os.unlink(temp_file)


@pytest.mark.asyncio
async def test_get_report_by_keyword_date_invalid_format():
    """Test getting report with invalid date format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/reports/keyword/AI/invalid-date")
    
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_generate_report():
    """Test triggering manual report generation"""
    with patch('src.api.reports.get_scheduler') as mock_get_scheduler:
        mock_scheduler = AsyncMock()
        mock_scheduler.run_once = AsyncMock()
        mock_get_scheduler.return_value = mock_scheduler
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/reports/generate",
                json={"keyword": "AI"}
            )
        
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "accepted"
        mock_scheduler.run_once.assert_called_once()


@pytest.mark.asyncio
async def test_generate_report_all_subscriptions():
    """Test generating reports for all subscriptions"""
    with patch('src.api.reports.get_scheduler') as mock_get_scheduler:
        mock_scheduler = AsyncMock()
        mock_scheduler.run_once = AsyncMock()
        mock_get_scheduler.return_value = mock_scheduler
        
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/reports/generate",
                json={}
            )
        
        assert response.status_code == 202
