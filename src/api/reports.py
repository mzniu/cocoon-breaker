"""
Report management API endpoints
"""
import logging
from typing import List, Optional
from datetime import datetime, date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.db.database import Database
from src.db.repository import ReportRepository
from src.db.models import Report
from src.scheduler import get_scheduler

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/reports", tags=["reports"])


# Pydantic models
class ReportResponse(BaseModel):
    """Response model for report"""
    id: int
    keyword: str
    date: str
    file_path: str
    article_count: int
    generated_at: str
    
    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    """Response model for report list"""
    total: int
    items: List[ReportResponse]


class GenerateReportRequest(BaseModel):
    """Request model for generating report"""
    keyword: Optional[str] = None  # If None, generate for all subscriptions


# Dependency to get database
def get_db() -> Database:
    """Get database dependency"""
    from src.main import get_db as main_get_db
    return main_get_db()


@router.get("", response_model=ReportListResponse)
async def list_reports(
    keyword: Optional[str] = None,
    db: Database = Depends(get_db)
):
    """
    Get all reports, optionally filtered by keyword
    
    Args:
        keyword: Optional keyword filter
    
    Returns:
        List of reports
    """
    try:
        repo = ReportRepository(db)
        
        # Get all reports from database
        reports = await repo.get_all(limit=100)
        
        # Filter by keyword if provided
        if keyword:
            reports = [r for r in reports if r.keyword == keyword]
        
        items = [
            ReportResponse(
                id=report.id,
                keyword=report.keyword,
                date=report.date.isoformat() if isinstance(report.date, date) else report.date,
                file_path=report.file_path,
                article_count=report.article_count,
                generated_at=report.generated_at.isoformat() if report.generated_at else ""
            )
            for report in reports
        ]
        
        return ReportListResponse(
            total=len(items),
            items=items
        )
    
    except Exception as e:
        logger.error(f"Failed to list reports: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve reports"
        )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: Database = Depends(get_db)
):
    """
    Get report by ID
    
    Args:
        report_id: Report ID
    
    Returns:
        Report details
    """
    try:
        repo = ReportRepository(db)
        report = await repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        return ReportResponse(
            id=report.id,
            keyword=report.keyword,
            date=report.date.isoformat() if report.date else "",
            file_path=report.file_path,
            article_count=report.article_count,
            generated_at=report.generated_at.isoformat() if report.generated_at else ""
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report"
        )


@router.get("/{report_id}/download")
async def download_report(
    report_id: int,
    db: Database = Depends(get_db)
):
    """
    Download report HTML file
    
    Args:
        report_id: Report ID
    
    Returns:
        HTML file
    """
    try:
        repo = ReportRepository(db)
        report = await repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Check if file exists
        file_path = Path(report.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )
        
        # Return file
        return FileResponse(
            path=str(file_path),
            media_type="text/html",
            filename=file_path.name
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download report"
        )


@router.get("/{report_id}/view")
async def view_report(
    report_id: int,
    db: Database = Depends(get_db)
):
    """
    View report HTML inline (for iframe display)
    
    Args:
        report_id: Report ID
    
    Returns:
        HTML content for inline display
    """
    try:
        repo = ReportRepository(db)
        report = await repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Check if file exists
        file_path = Path(report.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )
        
        # Read and return HTML content
        from fastapi.responses import HTMLResponse
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to view report {report_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to view report"
        )


@router.get("/keyword/{keyword}/{date}")
async def get_report_by_keyword_date(
    keyword: str,
    date: str,
    db: Database = Depends(get_db)
):
    """
    Get report by keyword and date (for viewing in iframe)
    
    Args:
        keyword: Topic keyword
        date: Report date (YYYY-MM-DD)
    
    Returns:
        Report HTML file for inline display
    """
    try:
        # Parse date
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
        
        repo = ReportRepository(db)
        report = await repo.get_by_keyword_date(keyword, report_date)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report for {keyword} on {date} not found"
            )
        
        # Check if file exists
        file_path = Path(report.file_path)
        if not file_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Report file not found"
            )
        
        # Return file for inline display (not download)
        from fastapi.responses import HTMLResponse
        with open(file_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        return HTMLResponse(content=html_content)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get report for {keyword} on {date}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report"
        )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_report(request: GenerateReportRequest):
    """
    Trigger manual report generation
    
    Args:
        request: Generate request (keyword optional)
    
    Returns:
        Accepted status
    """
    try:
        scheduler = await get_scheduler()
        
        # Run task once
        await scheduler.run_once()
        
        logger.info(f"Report generation triggered for {request.keyword or 'all subscriptions'}")
        
        return {
            "status": "accepted",
            "message": "Report generation started"
        }
    
    except Exception as e:
        logger.error(f"Failed to trigger report generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger report generation"
        )


@router.post("/collect-articles", status_code=status.HTTP_202_ACCEPTED)
async def collect_articles():
    """
    Trigger manual article collection (crawl only, no report generation)
    
    Returns:
        Accepted status with collected article count
    """
    try:
        from src.scheduler.tasks import get_scheduler
        
        scheduler = await get_scheduler()
        
        # Run article collection only
        await scheduler.collect_articles_only()
        
        logger.info("Article collection triggered")
        
        return {
            "status": "accepted",
            "message": "Article collection started"
        }
    
    except Exception as e:
        logger.error(f"Failed to trigger article collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger article collection"
        )
