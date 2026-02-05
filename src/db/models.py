"""
Database models using dataclass
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """Article model"""
    id: Optional[int]
    title: str
    url: str
    content: str
    source: str  # "baidu" | "bing"
    keyword: str
    crawled_at: datetime
    published_at: Optional[datetime] = None
    full_content: Optional[str] = None
    fetch_status: str = 'pending'  # 'pending' | 'success' | 'failed' | 'no_content'
    fetched_at: Optional[datetime] = None
    fetch_error: Optional[str] = None
    # AI analysis fields
    actual_published_at: Optional[datetime] = None
    actual_source: Optional[str] = None
    importance_score: Optional[float] = None  # 0-100
    analysis_status: str = 'pending'  # 'pending' | 'success' | 'failed'
    analyzed_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.crawled_at, str):
            self.crawled_at = datetime.fromisoformat(self.crawled_at)
        if isinstance(self.published_at, str) and self.published_at:
            self.published_at = datetime.fromisoformat(self.published_at)
        if isinstance(self.fetched_at, str) and self.fetched_at:
            self.fetched_at = datetime.fromisoformat(self.fetched_at)
        if isinstance(self.actual_published_at, str) and self.actual_published_at:
            self.actual_published_at = datetime.fromisoformat(self.actual_published_at)
        if isinstance(self.analyzed_at, str) and self.analyzed_at:
            self.analyzed_at = datetime.fromisoformat(self.analyzed_at)


@dataclass
class Subscription:
    """Subscription model"""
    id: Optional[int]
    keyword: str
    created_at: datetime
    enabled: bool = True
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.created_at, str):
            self.created_at = datetime.fromisoformat(self.created_at)


@dataclass
class Report:
    """Report model"""
    id: Optional[int]
    keyword: str
    date: str  # YYYY-MM-DD format
    file_path: str
    article_count: int
    generated_at: datetime
    html_content: Optional[str] = None  # Full HTML content of the report
    summary: Optional[str] = None  # Report summary (今日必读)
    article_ids: Optional[str] = None  # JSON array of article IDs used in report
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.generated_at, str):
            self.generated_at = datetime.fromisoformat(self.generated_at)
    
    def get_article_id_list(self) -> list[int]:
        """Get article IDs as list"""
        if not self.article_ids:
            return []
        import json
        return json.loads(self.article_ids)


@dataclass
class ScheduleConfig:
    """Schedule configuration model for report generation"""
    id: Optional[int]
    time: str  # HH:MM format
    enabled: bool
    updated_at: datetime
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)


@dataclass
class CrawlScheduleConfig:
    """Crawl schedule configuration model for article collection"""
    id: Optional[int]
    enabled: bool
    times: list[str]  # List of HH:MM format times, e.g. ["06:00", "12:00", "18:00", "22:00"]
    updated_at: datetime
    
    def __post_init__(self):
        """Ensure datetime objects and parse times"""
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
        if isinstance(self.times, str):
            import json
            self.times = json.loads(self.times)
