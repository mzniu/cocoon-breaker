"""
Scheduler for automated daily report generation
"""
import asyncio
import logging
import os
import threading
import time
from datetime import datetime
from typing import List

import schedule

from src.config import get_config
from src.crawler import BaiduCrawler, YahooCrawler, GoogleCrawler, TavilyCrawler
from src.db.database import Database
from src.db.repository import (
    ArticleRepository,
    SubscriptionRepository,
    ReportRepository,
    ScheduleRepository
)
from src.db.models import Article, Report
from src.ai.deepseek import DeepseekClient
from src.report.generator import ReportGenerator

logger = logging.getLogger(__name__)


class DailyReportTask:
    """Daily report generation task"""
    
    def __init__(self):
        """Initialize task"""
        self.config = get_config()
        self.db = None
        self.deepseek_client = None
        self.report_generator = None
        self.crawlers = []
        
        # Repositories
        self.article_repo = None
        self.subscription_repo = None
        self.report_repo = None
        self.schedule_repo = None
        
        # Task running flag
        self._running = False
    
    async def initialize(self):
        """Initialize database and services"""
        # Database
        self.db = Database(self.config.database.path)
        await self.db.connect()
        
        # Repositories
        self.article_repo = ArticleRepository(self.db)
        self.subscription_repo = SubscriptionRepository(self.db)
        self.report_repo = ReportRepository(self.db)
        self.schedule_repo = ScheduleRepository(self.db)
        
        # Deepseek client
        self.deepseek_client = DeepseekClient(
            api_key=self.config.llm.api_key,
            model=self.config.llm.model,
            base_url=self.config.llm.base_url,
            timeout=self.config.llm.timeout
        )
        
        # Report generator
        self.report_generator = ReportGenerator(
            deepseek_client=self.deepseek_client,
            output_dir=self.config.output.directory
        )
        
        # Crawlers with config
        self.crawlers = [
            BaiduCrawler(
                user_agents=self.config.crawler.user_agents,
                request_interval=self.config.crawler.request_interval,
                timeout=self.config.crawler.timeout
            ),
            YahooCrawler(
                user_agents=self.config.crawler.user_agents,
                request_interval=self.config.crawler.request_interval,
                timeout=self.config.crawler.timeout
            ),
        ]
        
        # Add Google crawler if API is configured
        if self.config.google.enabled and self.config.google.api_key and self.config.google.search_engine_id:
            google_crawler = GoogleCrawler(
                user_agents=self.config.crawler.user_agents,
                request_interval=self.config.crawler.request_interval,
                timeout=self.config.crawler.timeout
            )
            google_crawler.set_api_credentials(
                self.config.google.api_key,
                self.config.google.search_engine_id
            )
            self.crawlers.append(google_crawler)
        
        # Add Tavily crawler if enabled in config
        if self.config.tavily.enabled and self.config.tavily.api_key:
            try:
                tavily_crawler = TavilyCrawler(
                    user_agents=self.config.crawler.user_agents,
                    request_interval=self.config.crawler.request_interval,
                    timeout=self.config.crawler.timeout,
                    api_key=self.config.tavily.api_key,
                    search_depth=self.config.tavily.search_depth,
                    max_results=self.config.tavily.max_results
                )
                self.crawlers.append(tavily_crawler)
                logger.info(f"Tavily crawler enabled (depth={self.config.tavily.search_depth})")
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily crawler: {e}")
        else:
            logger.info("Tavily crawler disabled (not enabled in config or API key not set)")
        
        logger.info("DailyReportTask initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db:
            await self.db.close()
        logger.info("DailyReportTask cleaned up")
    
    async def run(self):
        """Execute daily report generation"""
        if self._running:
            logger.warning("Task already running, skipping")
            return
        
        self._running = True
        
        try:
            logger.info("Starting daily report generation")
            
            # Get enabled subscriptions
            subscriptions = await self.subscription_repo.get_enabled()
            
            if not subscriptions:
                logger.info("No enabled subscriptions, skipping")
                return
            
            logger.info(f"Found {len(subscriptions)} enabled subscriptions")
            
            # Process each subscription
            for subscription in subscriptions:
                try:
                    await self._process_subscription(subscription.keyword)
                except Exception as e:
                    logger.error(f"Failed to process subscription {subscription.keyword}: {e}")
                    continue
            
            logger.info("Daily report generation completed")
            
        finally:
            self._running = False
    
    async def _process_subscription(self, keyword: str):
        """Process single subscription"""
        logger.info(f"Processing subscription: {keyword}")
        
        # Step 1: Crawl articles
        articles = await self._crawl_articles(keyword)
        
        if not articles:
            logger.warning(f"No articles found for {keyword}")
            return
        
        # Step 2: Save to database (with deduplication)
        saved_count = await self._save_articles(articles)
        logger.info(f"Saved {saved_count}/{len(articles)} articles for {keyword}")
        
        # Step 3: Get recent articles for report
        recent_articles = await self.article_repo.get_recent_by_keyword(
            keyword,
            hours=24
        )
        
        if not recent_articles:
            logger.warning(f"No recent articles for {keyword}")
            return
        
        # Step 4: Generate report
        report_path = self.report_generator.generate_report(
            keyword,
            recent_articles
        )
        
        if report_path:
            # Step 5: Save report record
            report = Report(
                id=None,
                keyword=keyword,
                date=datetime.now().date(),
                file_path=report_path,
                article_count=len(recent_articles),
                generated_at=datetime.now()
            )
            
            await self.report_repo.create(report)
            logger.info(f"Report generated: {report_path}")
        else:
            logger.error(f"Failed to generate report for {keyword}")
    
    async def _crawl_articles(self, keyword: str) -> List[Article]:
        """Crawl articles from all sources"""
        all_articles = []
        
        for crawler in self.crawlers:
            try:
                logger.info(f"Crawling {keyword} from {crawler.__class__.__name__}")
                
                # Run crawler in executor (blocking I/O)
                loop = asyncio.get_event_loop()
                articles = await loop.run_in_executor(
                    None,
                    crawler.crawl,
                    keyword,
                    self.config.crawler.max_results_per_keyword
                )
                
                all_articles.extend(articles)
                logger.info(f"Crawled {len(articles)} articles from {crawler.__class__.__name__}")
                
            except Exception as e:
                logger.error(f"Crawler {crawler.__class__.__name__} failed: {e}")
                continue
        
        return all_articles
    
    async def _save_articles(self, articles: List[Article]) -> int:
        """Save articles to database"""
        saved_count = 0
        
        for article in articles:
            try:
                article_id = await self.article_repo.create(article)
                if article_id is not None:
                    saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save article {article.url}: {e}")
                continue
        
        return saved_count


class TaskScheduler:
    """Task scheduler using schedule library"""
    
    def __init__(self):
        """Initialize scheduler"""
        self.task = DailyReportTask()
        self.scheduler_thread = None
        self._stop_event = threading.Event()
    
    async def start(self):
        """Start scheduler"""
        # Initialize task
        await self.task.initialize()
        
        # Get schedule config
        config = get_config()
        schedule_config = await self.task.schedule_repo.get()
        
        if not schedule_config or not schedule_config.enabled:
            logger.info("Scheduler is disabled")
            return
        
        # Schedule task
        schedule_time = schedule_config.time
        logger.info(f"Scheduling daily report at {schedule_time}")
        
        schedule.every().day.at(schedule_time).do(
            lambda: asyncio.run(self.task.run())
        )
        
        # Start scheduler thread (non-daemon for proper cleanup)
        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler,
            name="SchedulerThread"
        )
        self.scheduler_thread.start()
        
        logger.info("Scheduler started")
    
    async def stop(self):
        """Stop scheduler"""
        logger.info("Stopping scheduler")
        
        # Signal stop
        self._stop_event.set()
        
        # Clear all scheduled jobs first
        schedule.clear()
        
        # Wait for thread to finish (with shorter timeout)
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.debug("Waiting for scheduler thread to stop...")
            self.scheduler_thread.join(timeout=2)
            
            if self.scheduler_thread.is_alive():
                logger.warning("Scheduler thread did not stop in time, forcing shutdown")
        
        # Cleanup task (with timeout protection)
        try:
            import asyncio
            await asyncio.wait_for(self.task.cleanup(), timeout=2)
        except asyncio.TimeoutError:
            logger.warning("Task cleanup timed out")
        except Exception as e:
            logger.error(f"Error during task cleanup: {e}")
        
        logger.info("Scheduler stopped")
    
    def _run_scheduler(self):
        """Run scheduler loop in thread"""
        logger.info("Scheduler loop started")
        
        while not self._stop_event.is_set():
            schedule.run_pending()
            time.sleep(1)
        
        logger.info("Scheduler loop stopped")
    
    async def run_once(self):
        """Run task once immediately (for manual trigger)"""
        logger.info("Running task once")
        
        # Initialize if not already initialized
        if self.task.db is None:
            await self.task.initialize()
        
        await self.task.run()
    
    async def collect_articles_only(self):
        """Collect articles only without generating reports (for manual trigger)"""
        logger.info("Collecting articles only (no report generation)")
        
        # Initialize if not already initialized
        if self.task.db is None:
            await self.task.initialize()
        
        # Get enabled subscriptions
        subscriptions = await self.task.subscription_repo.get_enabled()
        
        if not subscriptions:
            logger.info("No enabled subscriptions for article collection")
            return
        
        logger.info(f"Collecting articles for {len(subscriptions)} subscriptions")
        
        # Process each subscription (crawl and save only)
        for subscription in subscriptions:
            try:
                keyword = subscription.keyword
                logger.info(f"Collecting articles for: {keyword}")
                
                # Crawl articles
                articles = await self.task._crawl_articles(keyword)
                
                if not articles:
                    logger.warning(f"No articles found for {keyword}")
                    continue
                
                # Save to database (with deduplication)
                saved_count = await self.task._save_articles(articles)
                logger.info(f"Saved {saved_count}/{len(articles)} articles for {keyword}")
                
            except Exception as e:
                logger.error(f"Failed to collect articles for {subscription.keyword}: {e}")
                continue
        
        logger.info("Article collection completed")


# Global scheduler instance
_scheduler_instance = None


async def get_scheduler() -> TaskScheduler:
    """Get global scheduler instance"""
    global _scheduler_instance
    
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    
    return _scheduler_instance
