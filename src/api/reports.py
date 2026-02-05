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


class ReportDetailResponse(BaseModel):
    """Detailed response model for report with content"""
    id: int
    keyword: str
    date: str
    file_path: str
    article_count: int
    generated_at: str
    summary: Optional[str] = None
    article_ids: Optional[List[int]] = None
    has_content: bool = False  # Whether html_content is stored in DB
    
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


@router.get("/{report_id}", response_model=ReportDetailResponse)
async def get_report(
    report_id: int,
    db: Database = Depends(get_db)
):
    """
    Get report by ID with detailed information
    
    Args:
        report_id: Report ID
    
    Returns:
        Report details including summary and article IDs
    """
    try:
        import json
        repo = ReportRepository(db)
        report = await repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Parse article_ids from JSON
        article_ids = None
        if report.article_ids:
            try:
                article_ids = json.loads(report.article_ids)
            except:
                article_ids = []
        
        return ReportDetailResponse(
            id=report.id,
            keyword=report.keyword,
            date=report.date if isinstance(report.date, str) else report.date.isoformat(),
            file_path=report.file_path,
            article_count=report.article_count,
            generated_at=report.generated_at.isoformat() if report.generated_at else "",
            summary=report.summary,
            article_ids=article_ids,
            has_content=report.html_content is not None
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
    Download report HTML from database
    
    Args:
        report_id: Report ID
    
    Returns:
        HTML file for download
    """
    try:
        from fastapi.responses import Response
        
        repo = ReportRepository(db)
        report = await repo.get_by_id(report_id)
        
        if not report:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Report {report_id} not found"
            )
        
        # Get HTML content from database
        if not report.html_content:
            # Fall back to file if no content in database
            file_path = Path(report.file_path) if report.file_path else None
            if file_path and file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Report content not found"
                )
        else:
            html_content = report.html_content
        
        # Generate filename
        filename = f"{report.keyword}_{report.date}.html"
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
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
    Prioritizes database content, falls back to file
    
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
        
        from fastapi.responses import HTMLResponse
        
        # Get html_content from database
        if report.html_content:
            logger.info(f"Serving report {report_id} from database")
            return HTMLResponse(content=report.html_content)
        
        # Fall back to file for legacy reports
        if report.file_path:
            file_path = Path(report.file_path)
            if file_path.exists():
                logger.info(f"Serving report {report_id} from file: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                return HTMLResponse(content=html_content)
        
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report content not found"
        )
    
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


@router.post("/generate-only", status_code=status.HTTP_202_ACCEPTED)
async def generate_report_only(request: GenerateReportRequest):
    """
    Generate reports from existing articles only (no crawling).
    
    This endpoint uses background tasks and returns immediately.
    Use GET /api/tasks/{task_id} to check progress.
    
    Args:
        request: Generate request (keyword optional)
    
    Returns:
        Accepted status with task_id
    """
    try:
        from src.utils.task_manager import get_task_manager, TaskType
        from src.api.tasks import generate_report_only_task
        
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        # Submit as background task
        task_id = await task_manager.submit(
            TaskType.GENERATE_REPORT_ONLY,
            generate_report_only_task,
            keyword
        )
        
        logger.info(f"Generate report only task submitted: {task_id}, keyword={keyword}")
        
        return {
            "status": "accepted",
            "message": "仅生成日报任务已提交（基于现有文章）",
            "task_id": task_id,
            "check_status_url": f"/api/tasks/{task_id}"
        }
    
    except Exception as e:
        logger.error(f"Failed to trigger report only generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger report only generation"
        )


@router.post("/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_report(request: GenerateReportRequest):
    """
    Trigger manual report generation (background task).
    
    This endpoint now uses background tasks and returns immediately.
    Use GET /api/tasks/{task_id} to check progress.
    
    Args:
        request: Generate request (keyword optional)
    
    Returns:
        Accepted status with task_id
    """
    try:
        from src.utils.task_manager import get_task_manager, TaskType
        from src.api.tasks import full_pipeline_task
        
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        # Submit as background task
        task_id = await task_manager.submit(
            TaskType.FULL_PIPELINE,
            full_pipeline_task,
            keyword
        )
        
        logger.info(f"Report generation task submitted: {task_id}, keyword={keyword}")
        
        return {
            "status": "accepted",
            "message": "日报生成任务已提交（后台执行）",
            "task_id": task_id,
            "check_status_url": f"/api/tasks/{task_id}"
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
    Trigger manual article collection (crawl only, no report generation).
    
    This endpoint now uses background tasks and returns immediately.
    Use GET /api/tasks/{task_id} to check progress.
    
    Returns:
        Accepted status with task_id
    """
    try:
        from src.utils.task_manager import get_task_manager, TaskType
        from src.api.tasks import crawl_articles_task
        
        task_manager = get_task_manager()
        
        # Submit as background task
        task_id = await task_manager.submit(
            TaskType.CRAWL,
            crawl_articles_task,
            None  # All subscriptions
        )
        
        logger.info(f"Article collection task submitted: {task_id}")
        
        return {
            "status": "accepted",
            "message": "文章爬取任务已提交（后台执行）",
            "task_id": task_id,
            "check_status_url": f"/api/tasks/{task_id}"
        }
    
    except Exception as e:
        logger.error(f"Failed to trigger article collection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger article collection"
        )
