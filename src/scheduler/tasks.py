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
    ScheduleRepository,
    CrawlScheduleRepository
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
        self.crawl_schedule_repo = None
        
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
        self.crawl_schedule_repo = CrawlScheduleRepository(self.db)
        
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
        
        # Add 36Kr crawler if enabled in config
        if self.config.kr36.enabled:
            try:
                from src.crawler.kr36 import Kr36Crawler
                kr36_crawler = Kr36Crawler(
                    user_agents=self.config.crawler.user_agents,
                    request_interval=self.config.crawler.request_interval,
                    timeout=self.config.crawler.timeout
                )
                self.crawlers.append(kr36_crawler)
                logger.info("36Kr RSS crawler enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize 36Kr crawler: {e}")
        
        # Add Huxiu crawler if enabled in config
        if self.config.huxiu.enabled:
            try:
                from src.crawler.huxiu import HuxiuCrawler
                huxiu_crawler = HuxiuCrawler(
                    user_agents=self.config.crawler.user_agents,
                    request_interval=self.config.crawler.request_interval,
                    timeout=self.config.crawler.timeout
                )
                self.crawlers.append(huxiu_crawler)
                logger.info("Huxiu (虎嗅网) RSS crawler enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Huxiu crawler: {e}")
        
        # Add Toutiao crawler if enabled in config
        if self.config.toutiao.enabled:
            try:
                from src.crawler.toutiao import ToutiaoCrawler
                toutiao_crawler = ToutiaoCrawler(
                    user_agents=self.config.crawler.user_agents,
                    request_interval=self.config.crawler.request_interval,
                    timeout=self.config.crawler.timeout
                )
                self.crawlers.append(toutiao_crawler)
                logger.info("Toutiao (今日头条) search crawler enabled")
            except Exception as e:
                logger.warning(f"Failed to initialize Toutiao crawler: {e}")
        
        logger.info("DailyReportTask initialized")
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.db:
            await self.db.close()
        logger.info("DailyReportTask cleaned up")
    
    async def run(self, keyword: str = None):
        """Execute daily report generation
        
        Args:
            keyword: Optional specific keyword to generate report for.
                     If None, generates reports for all enabled subscriptions.
        """
        if self._running:
            logger.warning("Task already running, skipping")
            return
        
        self._running = True
        
        try:
            logger.info(f"Starting daily report generation (keyword={keyword})")
            
            # Get subscriptions to process
            if keyword:
                # Process specific keyword
                logger.info(f"Processing single keyword: {keyword}")
                try:
                    await self._process_subscription(keyword)
                except Exception as e:
                    logger.error(f"Failed to process subscription {keyword}: {e}")
            else:
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
        
        # Step 3: Get recent articles for report with scoring
        time_range = self.config.report.time_range_hours
        
        # Use mixed scoring for better article selection
        recent_articles = await self.article_repo.get_by_keyword_with_scoring(
            keyword,
            hours=time_range,
            quality_weight=self.config.report.quality_weight,
            freshness_weight=self.config.report.freshness_weight,
            time_decay_lambda=self.config.report.time_decay_lambda
        )
        
        if time_range > 0:
            logger.info(f"Found {len(recent_articles)} articles within {time_range} hours for {keyword} (scored)")
        else:
            logger.info(f"Found {len(recent_articles)} articles (no time limit) for {keyword} (scored)")
        
        if not recent_articles:
            logger.warning(f"No recent articles for {keyword}")
            return
        
        # Step 4: Generate report
        report_result = self.report_generator.generate_report(
            keyword,
            recent_articles
        )
        
        if report_result and report_result.get('html_content'):
            # Step 5: Save report record to database (no file output)
            import json
            
            report = Report(
                id=None,
                keyword=keyword,
                date=str(datetime.now().date()),
                file_path="",  # No longer saving to file
                article_count=report_result.get('article_count', len(recent_articles)),
                generated_at=datetime.now(),
                html_content=report_result.get('html_content'),
                summary=report_result.get('summary'),
                article_ids=json.dumps(report_result.get('article_ids', []))
            )
            
            report_id = await self.report_repo.create(report)
            logger.info(f"Report generated and saved to database (ID={report_id})")
        else:
            logger.error(f"Failed to generate report for {keyword}")

    async def collect_articles(self):
        """Collect articles for all enabled subscriptions (without generating reports)"""
        if self._running:
            logger.warning("Task already running, skipping article collection")
            return
        
        self._running = True
        
        try:
            logger.info("Starting scheduled article collection...")
            
            # Get enabled subscriptions
            subscriptions = await self.subscription_repo.get_enabled()
            
            if not subscriptions:
                logger.info("No enabled subscriptions for article collection")
                return
            
            logger.info(f"Collecting articles for {len(subscriptions)} subscriptions")
            
            # Process each subscription (crawl and save only)
            total_saved = 0
            for subscription in subscriptions:
                try:
                    keyword = subscription.keyword
                    logger.info(f"Collecting articles for: {keyword}")
                    
                    # Crawl articles
                    articles = await self._crawl_articles(keyword)
                    
                    if not articles:
                        logger.warning(f"No articles found for {keyword}")
                        continue
                    
                    # Save to database (with deduplication)
                    saved_count = await self._save_articles(articles)
                    total_saved += saved_count
                    logger.info(f"Saved {saved_count}/{len(articles)} articles for {keyword}")
                    
                except Exception as e:
                    logger.error(f"Failed to collect articles for {subscription.keyword}: {e}")
                    continue
            
            logger.info(f"Article collection completed. Total saved: {total_saved}")
            
        finally:
            self._running = False

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
                
                # Log detailed article list for debugging
                if articles:
                    logger.info(f"[{crawler.__class__.__name__}] Article list:")
                    for i, article in enumerate(articles, 1):
                        logger.info(f"  [{i}] {article.title[:80]}")
                        logger.info(f"      URL: {article.url}")
                        logger.info(f"      Source: {article.source} | Published: {article.published_at}")
                
            except Exception as e:
                logger.error(f"Crawler {crawler.__class__.__name__} failed: {e}")
                continue
        
        return all_articles
    
    async def _save_articles(self, articles: List[Article]) -> int:
        """Save articles to database with deduplication logging"""
        if not articles:
            return 0
        
        # Step 1: Batch check for duplicates
        logger.info(f"[DEDUP] Checking {len(articles)} articles for duplicates...")
        urls = [article.url for article in articles]
        existing_urls = await self.article_repo.check_urls_exist(urls)
        
        # Separate new and duplicate articles
        new_articles = []
        duplicate_count = 0
        
        for article in articles:
            if article.url in existing_urls:
                duplicate_count += 1
                logger.info(f"[DEDUP] ✗ DUPLICATE skipped: {article.title[:60]}")
                logger.debug(f"[DEDUP]   URL: {article.url}")
            else:
                new_articles.append(article)
        
        logger.info(f"[DEDUP] Found {len(new_articles)} new articles, {duplicate_count} duplicates")
        
        if not new_articles:
            logger.info(f"[DEDUP] Summary: 0 new, {duplicate_count} duplicates, {len(articles)} total")
            return 0
        
        # Step 2: Save and analyze only new articles
        saved_count = 0
        
        for i, article in enumerate(new_articles, 1):
            try:
                article_id = await self.article_repo.create(article)
                if article_id is not None:
                    saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save article {article.url}: {e}")
                continue
        
        logger.info(f"[DEDUP] Summary: {saved_count} new, {duplicate_count} duplicates, {len(articles)} total")
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
        
        # Get schedule config for report generation
        config = get_config()
        schedule_config = await self.task.schedule_repo.get_config()
        
        # Schedule report generation task
        if schedule_config and schedule_config.enabled:
            schedule_time = schedule_config.time
            logger.info(f"Scheduling daily report generation at {schedule_time}")
            
            schedule.every().day.at(schedule_time).do(
                lambda: asyncio.run(self.task.run())
            )
        else:
            logger.info("Report generation scheduler is disabled")
        
        # Get crawl schedule config for article collection
        crawl_config = await self.task.crawl_schedule_repo.get_config()
        
        # Schedule article collection tasks
        if crawl_config and crawl_config.enabled:
            logger.info(f"Scheduling article collection at {crawl_config.times}")
            
            for crawl_time in crawl_config.times:
                schedule.every().day.at(crawl_time).do(
                    lambda: asyncio.run(self.task.collect_articles())
                )
                logger.info(f"  - Article collection scheduled at {crawl_time}")
        else:
            logger.info("Article collection scheduler is disabled")
        
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
    
    async def run_once(self, keyword: str = None):
        """Run task once immediately (for manual trigger)
        
        Args:
            keyword: Optional specific keyword to generate report for.
                     If None, generates reports for all enabled subscriptions.
        """
        logger.info(f"Running task once (keyword={keyword})")
        
        # Initialize if not already initialized
        if self.task.db is None:
            await self.task.initialize()
        
        await self.task.run(keyword=keyword)
    
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
_scheduler_initialized = False


async def get_scheduler() -> TaskScheduler:
    """Get global scheduler instance"""
    global _scheduler_instance, _scheduler_initialized
    
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    
    # Ensure task is initialized
    if not _scheduler_initialized:
        await _scheduler_instance.task.initialize()
        _scheduler_initialized = True
    
    return _scheduler_instance
