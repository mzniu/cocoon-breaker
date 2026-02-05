"""
Task management API endpoints.
Provides endpoints for submitting, querying, and cancelling background tasks.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from src.utils.task_manager import (
    get_task_manager,
    TaskType,
    TaskStatus,
    TaskContext,
    TaskInfo
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# ============ Pydantic Models ============

class TaskSubmitRequest(BaseModel):
    """Request model for submitting a task"""
    keyword: Optional[str] = Field(None, description="Specific keyword to process (optional)")


class TaskSubmitResponse(BaseModel):
    """Response model for task submission"""
    task_id: str
    task_type: str
    status: str
    message: str


class TaskProgressResponse(BaseModel):
    """Task progress information"""
    current: int
    total: int
    percentage: float
    message: str


class TaskDetailResponse(BaseModel):
    """Detailed task information"""
    task_id: str
    task_type: str
    status: str
    progress: TaskProgressResponse
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    result: Optional[dict]
    error: Optional[str]
    logs: List[str]


class TaskListResponse(BaseModel):
    """Response model for task list"""
    total: int
    tasks: List[TaskDetailResponse]


class TaskCancelResponse(BaseModel):
    """Response model for task cancellation"""
    task_id: str
    cancelled: bool
    message: str


# ============ Task Functions ============

async def crawl_articles_task(ctx: TaskContext, keyword: Optional[str] = None):
    """
    Background task for crawling articles.
    
    Args:
        ctx: TaskContext for progress reporting
        keyword: Optional specific keyword (None = all subscriptions)
    """
    from src.scheduler.tasks import get_scheduler
    
    scheduler = await get_scheduler()
    task = scheduler.task
    
    # Get subscriptions
    if keyword:
        subscriptions = [type('Sub', (), {'keyword': keyword})()]
        ctx.add_log(f"爬取关键词: {keyword}")
    else:
        subscriptions = await task.subscription_repo.get_enabled()
        ctx.add_log(f"获取到 {len(subscriptions)} 个订阅")
    
    if not subscriptions:
        ctx.add_log("没有找到订阅，任务结束")
        return {"articles_count": 0, "keywords": []}
    
    total_steps = len(subscriptions) * len(task.crawlers)
    current_step = 0
    total_articles = 0
    processed_keywords = []
    
    ctx.update_progress(0, total_steps, "开始爬取...")
    
    for sub in subscriptions:
        kw = sub.keyword
        processed_keywords.append(kw)
        ctx.add_log(f"处理关键词: {kw}")
        
        for crawler in task.crawlers:
            if ctx.is_cancelled:
                ctx.add_log("任务被取消")
                return {"articles_count": total_articles, "keywords": processed_keywords, "cancelled": True}
            
            crawler_name = crawler.__class__.__name__
            current_step += 1
            ctx.update_progress(current_step, total_steps, f"[{kw}] 使用 {crawler_name} 爬取中...")
            
            try:
                articles = crawler.crawl(kw, max_results=20)
                
                # Save articles
                saved_count = 0
                for article in articles:
                    try:
                        article_id = await task.article_repo.create(article)
                        if article_id:
                            saved_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to save article: {e}")
                
                total_articles += saved_count
                ctx.add_log(f"[{kw}] {crawler_name}: 获取 {len(articles)} 篇, 保存 {saved_count} 篇")
                
            except Exception as e:
                ctx.add_log(f"[{kw}] {crawler_name} 爬取失败: {e}")
                logger.error(f"Crawler {crawler_name} failed for {kw}: {e}")
    
    ctx.update_progress(total_steps, total_steps, "爬取完成")
    ctx.add_log(f"总计保存 {total_articles} 篇文章")
    
    return {
        "articles_count": total_articles,
        "keywords": processed_keywords
    }


async def generate_report_task(ctx: TaskContext, keyword: Optional[str] = None):
    """
    Background task for generating reports.
    
    Args:
        ctx: TaskContext for progress reporting
        keyword: Optional specific keyword (None = all subscriptions)
    """
    from src.scheduler.tasks import get_scheduler
    
    scheduler = await get_scheduler()
    
    ctx.add_log("开始生成日报...")
    ctx.update_progress(0, 1, "生成日报中...")
    
    try:
        # Use existing run_once which handles everything
        await scheduler.run_once(keyword=keyword)
        
        ctx.update_progress(1, 1, "日报生成完成")
        ctx.add_log("日报生成成功")
        
        return {"status": "success", "keyword": keyword}
        
    except Exception as e:
        ctx.add_log(f"日报生成失败: {e}")
        raise


async def generate_report_only_task(ctx: TaskContext, keyword: Optional[str] = None):
    """
    Background task for generating reports from existing articles (no crawling).
    
    Args:
        ctx: TaskContext for progress reporting
        keyword: Optional specific keyword (None = all subscriptions)
    """
    from src.main import get_db
    from src.db.repository import SubscriptionRepository, ArticleRepository, ReportRepository
    from src.report.generator import ReportGenerator
    from src.ai.deepseek import DeepseekClient
    from datetime import datetime
    
    ctx.add_log("开始基于现有文章生成日报...")
    
    try:
        # Get database and repositories
        db = get_db()
        sub_repo = SubscriptionRepository(db)
        article_repo = ArticleRepository(db)
        report_repo = ReportRepository(db)
        
        # Get subscriptions
        subscriptions = await sub_repo.get_all()
        if keyword:
            subscriptions = [s for s in subscriptions if s.keyword == keyword]
        
        if not subscriptions:
            ctx.add_log("未找到订阅关键词")
            return {"status": "failed", "message": "未找到订阅关键词"}
        
        total_steps = len(subscriptions)
        current_step = 0
        
        ctx.update_progress(0, total_steps, "准备生成日报...")
        
        # Initialize AI client and report generator
        from src.config import get_config
        config = get_config()
        deepseek_client = DeepseekClient(
            api_key=config.llm.api_key,
            model=config.llm.model,
            base_url=config.llm.base_url,
            timeout=config.llm.timeout
        )
        report_generator = ReportGenerator(deepseek_client)
        
        generated_reports = []
        
        for subscription in subscriptions:
            if ctx.is_cancelled:
                ctx.add_log("任务被取消")
                return {"status": "cancelled"}
            
            current_step += 1
            kw = subscription.keyword
            ctx.update_progress(current_step, total_steps, f"为关键词 '{kw}' 生成日报...")
            ctx.add_log(f"处理关键词: {kw}")
            
            # Get articles from last 24 hours
            articles = await article_repo.get_by_keyword_with_scoring(
                keyword=kw,
                hours=24,  # Last 24 hours
                limit=50
            )
            
            if not articles:
                ctx.add_log(f"关键词 '{kw}' 没有找到最近24小时的文章")
                continue
            
            ctx.add_log(f"找到 {len(articles)} 篇相关文章，开始生成日报...")
            
            # Generate report
            try:
                report_data = report_generator.generate_report(
                    keyword=kw,
                    articles=articles,  # 直接传递Article对象列表
                    date=datetime.now()
                )
                
                if report_data and report_data['html_content']:
                    # Create Report object
                    from src.db.models import Report
                    import json
                    
                    report = Report(
                        id=None,
                        keyword=kw,
                        date=datetime.now().date().isoformat(),
                        file_path="",  # No file, content in DB
                        article_count=report_data['article_count'],
                        generated_at=datetime.now(),
                        html_content=report_data['html_content'],
                        summary=report_data['summary'],
                        article_ids=json.dumps(report_data['article_ids']) if report_data['article_ids'] else None
                    )
                    
                    # Save report to database
                    report_id = await report_repo.create(report)
                    
                    generated_reports.append({
                        "keyword": kw,
                        "report_id": report_id,
                        "article_count": report_data['article_count']
                    })
                    
                    ctx.add_log(f"关键词 '{kw}' 日报生成成功 (ID: {report_id})")
                else:
                    ctx.add_log(f"关键词 '{kw}' 日报生成失败：无有效内容")
                    
            except Exception as e:
                ctx.add_log(f"关键词 '{kw}' 日报生成失败: {e}")
                logger.error(f"Report generation failed for {kw}: {e}")
        
        ctx.update_progress(total_steps, total_steps, "日报生成完成")
        ctx.add_log(f"成功生成 {len(generated_reports)} 份日报")
        
        return {
            "status": "success", 
            "reports_generated": len(generated_reports),
            "reports": generated_reports
        }
        
    except Exception as e:
        ctx.add_log(f"日报生成失败: {e}")
        logger.error(f"Generate report only task failed: {e}")
        raise


async def full_pipeline_task(ctx: TaskContext, keyword: Optional[str] = None):
    """
    Background task for full pipeline: crawl + generate report.
    
    Args:
        ctx: TaskContext for progress reporting
        keyword: Optional specific keyword (None = all subscriptions)
    """
    ctx.add_log("开始完整流程: 爬取 + 生成日报")
    
    # Phase 1: Crawl
    ctx.update_progress(0, 2, "阶段1: 爬取文章...")
    crawl_result = await crawl_articles_task(ctx, keyword)
    
    if ctx.is_cancelled:
        return {"phase": "crawl", "cancelled": True}
    
    # Phase 2: Generate report
    ctx.update_progress(1, 2, "阶段2: 生成日报...")
    report_result = await generate_report_task(ctx, keyword)
    
    ctx.update_progress(2, 2, "完整流程执行完成")
    
    return {
        "crawl": crawl_result,
        "report": report_result
    }


# ============ API Endpoints ============

@router.post("/crawl", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_crawl_task(request: TaskSubmitRequest = None):
    """
    Submit a background task to crawl articles.
    
    Returns immediately with task_id. Use GET /api/tasks/{task_id} to check status.
    """
    try:
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        task_id = await task_manager.submit(
            TaskType.CRAWL,
            crawl_articles_task,
            keyword
        )
        
        logger.info(f"Crawl task submitted: {task_id}, keyword={keyword}")
        
        return TaskSubmitResponse(
            task_id=task_id,
            task_type=TaskType.CRAWL.value,
            status="pending",
            message=f"爬取任务已提交，关键词: {keyword or '全部订阅'}"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit crawl task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {e}"
        )


@router.post("/generate-only", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_generate_only_task(request: TaskSubmitRequest = None):
    """
    Submit a background task to generate reports from existing articles only (no crawling).
    
    Returns immediately with task_id. Use GET /api/tasks/{task_id} to check status.
    """
    try:
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        task_id = await task_manager.submit(
            TaskType.GENERATE_REPORT_ONLY,
            generate_report_only_task,
            keyword
        )
        
        logger.info(f"Generate report only task submitted: {task_id}, keyword={keyword}")
        
        return TaskSubmitResponse(
            task_id=task_id,
            task_type=TaskType.GENERATE_REPORT_ONLY.value,
            status="pending",
            message=f"仅生成日报任务已提交，关键词: {keyword or '全部订阅'}"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit generate only task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {e}"
        )


@router.post("/generate", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_generate_task(request: TaskSubmitRequest = None):
    """
    Submit a background task to generate report.
    
    Returns immediately with task_id. Use GET /api/tasks/{task_id} to check status.
    """
    try:
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        task_id = await task_manager.submit(
            TaskType.GENERATE_REPORT,
            generate_report_task,
            keyword
        )
        
        logger.info(f"Generate task submitted: {task_id}, keyword={keyword}")
        
        return TaskSubmitResponse(
            task_id=task_id,
            task_type=TaskType.GENERATE_REPORT.value,
            status="pending",
            message=f"日报生成任务已提交，关键词: {keyword or '全部订阅'}"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit generate task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {e}"
        )


@router.post("/full-pipeline", response_model=TaskSubmitResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_full_pipeline_task(request: TaskSubmitRequest = None):
    """
    Submit a background task for full pipeline (crawl + generate).
    
    Returns immediately with task_id. Use GET /api/tasks/{task_id} to check status.
    """
    try:
        task_manager = get_task_manager()
        keyword = request.keyword if request else None
        
        task_id = await task_manager.submit(
            TaskType.FULL_PIPELINE,
            full_pipeline_task,
            keyword
        )
        
        logger.info(f"Full pipeline task submitted: {task_id}, keyword={keyword}")
        
        return TaskSubmitResponse(
            task_id=task_id,
            task_type=TaskType.FULL_PIPELINE.value,
            status="pending",
            message=f"完整流程任务已提交，关键词: {keyword or '全部订阅'}"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit full pipeline task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"提交任务失败: {e}"
        )


@router.get("", response_model=TaskListResponse)
async def list_tasks(limit: int = Query(50, ge=1, le=100)):
    """
    List all tasks, newest first.
    """
    try:
        task_manager = get_task_manager()
        tasks = await task_manager.get_all_tasks(limit=limit)
        
        return TaskListResponse(
            total=len(tasks),
            tasks=[
                TaskDetailResponse(
                    task_id=t.task_id,
                    task_type=t.task_type.value,
                    status=t.status.value,
                    progress=TaskProgressResponse(
                        current=t.progress.current,
                        total=t.progress.total,
                        percentage=t.progress.percentage,
                        message=t.progress.message
                    ),
                    created_at=t.created_at.isoformat(),
                    started_at=t.started_at.isoformat() if t.started_at else None,
                    completed_at=t.completed_at.isoformat() if t.completed_at else None,
                    result=t.result,
                    error=t.error,
                    logs=t.logs[-20:]  # Last 20 logs for list view
                )
                for t in tasks
            ]
        )
        
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务列表失败: {e}"
        )


@router.get("/{task_id}", response_model=TaskDetailResponse)
async def get_task(task_id: str):
    """
    Get detailed information about a specific task.
    """
    try:
        task_manager = get_task_manager()
        task = await task_manager.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}"
            )
        
        return TaskDetailResponse(
            task_id=task.task_id,
            task_type=task.task_type.value,
            status=task.status.value,
            progress=TaskProgressResponse(
                current=task.progress.current,
                total=task.progress.total,
                percentage=task.progress.percentage,
                message=task.progress.message
            ),
            created_at=task.created_at.isoformat(),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            result=task.result,
            error=task.error,
            logs=task.logs  # Full logs for detail view
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取任务详情失败: {e}"
        )


@router.delete("/{task_id}", response_model=TaskCancelResponse)
async def cancel_task(task_id: str):
    """
    Cancel a running or pending task.
    """
    try:
        task_manager = get_task_manager()
        
        task = await task_manager.get_task(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"任务不存在: {task_id}"
            )
        
        cancelled = await task_manager.cancel_task(task_id)
        
        return TaskCancelResponse(
            task_id=task_id,
            cancelled=cancelled,
            message="任务已取消" if cancelled else "任务无法取消（可能已完成或已取消）"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"取消任务失败: {e}"
        )
