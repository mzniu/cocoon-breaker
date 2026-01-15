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
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.crawled_at, str):
            self.crawled_at = datetime.fromisoformat(self.crawled_at)
        if isinstance(self.published_at, str):
            self.published_at = datetime.fromisoformat(self.published_at)


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
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.generated_at, str):
            self.generated_at = datetime.fromisoformat(self.generated_at)


@dataclass
class ScheduleConfig:
    """Schedule configuration model"""
    id: Optional[int]
    time: str  # HH:MM format
    enabled: bool
    updated_at: datetime
    
    def __post_init__(self):
        """Ensure datetime objects"""
        if isinstance(self.updated_at, str):
            self.updated_at = datetime.fromisoformat(self.updated_at)
