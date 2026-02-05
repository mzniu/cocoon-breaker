"""
Background task manager for async task execution.
Supports task submission, status tracking, progress updates, and cancellation.

This is the lightweight in-memory implementation (Phase 1).
Can be upgraded to Celery+Redis (Phase 2) by implementing CeleryTaskManager.
"""
import asyncio
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine, Dict, List, Optional

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"       # Waiting to start
    RUNNING = "running"       # Currently executing
    COMPLETED = "completed"   # Finished successfully
    FAILED = "failed"         # Finished with error
    CANCELLED = "cancelled"   # Cancelled by user


class TaskType(str, Enum):
    """Task type identifiers"""
    CRAWL = "crawl"                    # Article crawling
    GENERATE_REPORT = "generate_report" # Report generation
    GENERATE_REPORT_ONLY = "generate_report_only" # Generate report from existing articles
    FULL_PIPELINE = "full_pipeline"     # Crawl + Generate


@dataclass
class TaskProgress:
    """Task progress information"""
    current: int = 0           # Current step
    total: int = 0             # Total steps
    percentage: float = 0.0    # Percentage (0-100)
    message: str = ""          # Current status message


@dataclass
class TaskInfo:
    """Complete task information"""
    task_id: str
    task_type: TaskType
    status: TaskStatus
    progress: TaskProgress
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "progress": {
                "current": self.progress.current,
                "total": self.progress.total,
                "percentage": self.progress.percentage,
                "message": self.progress.message
            },
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result,
            "error": self.error,
            "logs": self.logs[-50:]  # Last 50 log entries
        }


class TaskContext:
    """
    Context passed to task functions for progress reporting.
    Task functions should call update_progress() and add_log() to report status.
    """
    
    def __init__(self, task_info: TaskInfo):
        self._task_info = task_info
        self._cancelled = False
    
    @property
    def is_cancelled(self) -> bool:
        """Check if task has been cancelled"""
        return self._cancelled
    
    def cancel(self):
        """Mark task as cancelled"""
        self._cancelled = True
    
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update task progress"""
        self._task_info.progress.current = current
        self._task_info.progress.total = total
        self._task_info.progress.percentage = (current / total * 100) if total > 0 else 0
        self._task_info.progress.message = message
        logger.debug(f"Task {self._task_info.task_id}: {current}/{total} - {message}")
    
    def add_log(self, message: str):
        """Add log entry to task"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self._task_info.logs.append(log_entry)
        logger.info(f"Task {self._task_info.task_id}: {message}")


class BaseTaskManager(ABC):
    """
    Abstract base class for task managers.
    Implement this to switch between different backends (asyncio, Celery, etc.)
    """
    
    @abstractmethod
    async def submit(
        self,
        task_type: TaskType,
        func: Callable[[TaskContext], Coroutine],
        *args,
        **kwargs
    ) -> str:
        """
        Submit a task for background execution.
        
        Args:
            task_type: Type of task
            func: Async function to execute, must accept TaskContext as first arg
            *args, **kwargs: Additional arguments for func
            
        Returns:
            task_id: Unique identifier for the task
        """
        pass
    
    @abstractmethod
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task information by ID"""
        pass
    
    @abstractmethod
    async def get_all_tasks(self, limit: int = 50) -> List[TaskInfo]:
        """Get all tasks, newest first"""
        pass
    
    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        pass
    
    @abstractmethod
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove old completed tasks"""
        pass


class AsyncTaskManager(BaseTaskManager):
    """
    In-memory task manager using asyncio.
    
    Features:
    - Non-blocking task execution
    - Progress tracking
    - Task cancellation
    - Log collection
    
    Limitations:
    - Tasks lost on server restart
    - Single-server only
    """
    
    def __init__(self):
        self._tasks: Dict[str, TaskInfo] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._contexts: Dict[str, TaskContext] = {}
        self._max_tasks = 100  # Max tasks to keep in memory
    
    async def submit(
        self,
        task_type: TaskType,
        func: Callable[[TaskContext], Coroutine],
        *args,
        **kwargs
    ) -> str:
        """Submit task for background execution"""
        task_id = str(uuid.uuid4())[:8]  # Short UUID for readability
        
        # Create task info
        task_info = TaskInfo(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            progress=TaskProgress(),
            created_at=datetime.now()
        )
        
        # Create context for progress reporting
        context = TaskContext(task_info)
        
        # Store task
        self._tasks[task_id] = task_info
        self._contexts[task_id] = context
        
        # Start background execution
        asyncio_task = asyncio.create_task(
            self._execute_task(task_id, func, context, *args, **kwargs)
        )
        self._running_tasks[task_id] = asyncio_task
        
        logger.info(f"Task {task_id} ({task_type.value}) submitted")
        
        # Cleanup old tasks if too many
        if len(self._tasks) > self._max_tasks:
            await self.cleanup_old_tasks(max_age_hours=1)
        
        return task_id
    
    async def _execute_task(
        self,
        task_id: str,
        func: Callable[[TaskContext], Coroutine],
        context: TaskContext,
        *args,
        **kwargs
    ):
        """Execute task and update status"""
        task_info = self._tasks[task_id]
        
        try:
            # Mark as running
            task_info.status = TaskStatus.RUNNING
            task_info.started_at = datetime.now()
            context.add_log("任务开始执行")
            
            # Execute the function
            result = await func(context, *args, **kwargs)
            
            # Check if cancelled during execution
            if context.is_cancelled:
                task_info.status = TaskStatus.CANCELLED
                context.add_log("任务已取消")
            else:
                task_info.status = TaskStatus.COMPLETED
                task_info.result = result
                context.add_log("任务执行完成")
            
        except asyncio.CancelledError:
            task_info.status = TaskStatus.CANCELLED
            context.add_log("任务被取消")
            
        except Exception as e:
            task_info.status = TaskStatus.FAILED
            task_info.error = str(e)
            context.add_log(f"任务失败: {e}")
            logger.exception(f"Task {task_id} failed: {e}")
            
        finally:
            task_info.completed_at = datetime.now()
            
            # Cleanup running task reference
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
    
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """Get task by ID"""
        return self._tasks.get(task_id)
    
    async def get_all_tasks(self, limit: int = 50) -> List[TaskInfo]:
        """Get all tasks, newest first"""
        sorted_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return sorted_tasks[:limit]
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        if task_id not in self._tasks:
            return False
        
        task_info = self._tasks[task_id]
        
        # Only cancel if pending or running
        if task_info.status not in (TaskStatus.PENDING, TaskStatus.RUNNING):
            return False
        
        # Mark context as cancelled
        if task_id in self._contexts:
            self._contexts[task_id].cancel()
        
        # Cancel asyncio task
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
        
        task_info.status = TaskStatus.CANCELLED
        task_info.completed_at = datetime.now()
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    async def cleanup_old_tasks(self, max_age_hours: int = 24):
        """Remove old completed tasks"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task_info in self._tasks.items():
            # Only cleanup completed/failed/cancelled tasks
            if task_info.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                if task_info.completed_at:
                    age_hours = (now - task_info.completed_at).total_seconds() / 3600
                    if age_hours > max_age_hours:
                        to_remove.append(task_id)
        
        for task_id in to_remove:
            del self._tasks[task_id]
            if task_id in self._contexts:
                del self._contexts[task_id]
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old tasks")


# Global singleton instance
_task_manager: Optional[AsyncTaskManager] = None


def get_task_manager() -> AsyncTaskManager:
    """Get global task manager instance"""
    global _task_manager
    if _task_manager is None:
        _task_manager = AsyncTaskManager()
    return _task_manager
