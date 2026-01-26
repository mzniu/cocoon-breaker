"""
Toutiao (今日头条) search crawler using Selenium
"""
import logging
import time
from datetime import datetime
from typing import List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from src.crawler.base import BaseCrawler
from src.db.models import Article

logger = logging.getLogger(__name__)


class ToutiaoCrawler(BaseCrawler):
    """Crawler for Toutiao search results using Selenium"""
    
    SEARCH_URL = "https://so.toutiao.com/search"
    
    def __init__(self, user_agents: List[str], request_interval: List[int], timeout: int = 30):
        """
        Initialize Toutiao crawler with Selenium
        
        Args:
            user_agents: List of user agent strings
            request_interval: [min, max] seconds for random delay
            timeout: Page load timeout in seconds
        """
        super().__init__(user_agents, request_interval, timeout)
        self.driver = None
    
    def _init_driver(self):
        """Initialize Chrome WebDriver with options"""
        if self.driver:
            return
        
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')  # Use new headless mode
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(f'user-agent={self._get_random_user_agent()}')
            
            # More anti-detection measures
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.page_load_strategy = 'normal'
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(self.timeout)
            self.driver.implicitly_wait(5)
            
            # Enhanced stealth: Remove webdriver flag and mask automation
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
                    window.chrome = {runtime: {}};
                '''
            })
            
            logger.info("[Toutiao] Chrome WebDriver initialized with stealth mode")
        except Exception as e:
            logger.error(f"[Toutiao] Failed to initialize WebDriver: {e}")
            raise
    
    def _close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                logger.info("[Toutiao] Chrome WebDriver closed")
            except Exception as e:
                logger.warning(f"[Toutiao] Error closing WebDriver: {e}")
    
    def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
        """
        Crawl Toutiao search results with explicit waits
        
        Args:
            keyword: Search keyword
            max_results: Maximum number of results
            
        Returns:
            List of Article objects (empty list on failure)
        """
        articles = []
        
        try:
            logger.info(f"[Toutiao] Crawling for keyword: {keyword}")
            
            # Initialize driver
            self._init_driver()
            
            # Build search URL with pagination
            import urllib.parse
            encoded_keyword = urllib.parse.quote(keyword)
            
            # Try multiple pages (conservative: 2-3 pages max)
            max_pages = min(3, (max_results + 9) // 10)  # Each page ~10 results
            
            for page_num in range(max_pages):
                logger.info(f"[Toutiao] Fetching page {page_num + 1}/{max_pages}")
                
                # Construct URL with page number
                search_url = f"https://www.toutiao.com/search/?keyword={encoded_keyword}&pd=synthesis&source=search_tab&dvpf=pc&aid=4916&page_num={page_num}"
                logger.info(f"[Toutiao] Opening: {search_url}")
                
                # Load page
                self.driver.get(search_url)
                current_url = self.driver.current_url
                logger.info(f"[Toutiao] Page loaded - URL: {current_url}")
                
                # Check if redirected to error page
                if current_url.startswith('data:') or not current_url.startswith('http'):
                    logger.warning(f"[Toutiao] Invalid URL loaded on page {page_num + 1}, skipping")
                    continue
                
                # Wait for search results to load - try multiple possible containers
                wait = WebDriverWait(self.driver, 30)
                result_container = None
                
                # Try different possible result container selectors
                possible_selectors = [
                    (By.CLASS_NAME, "s-result-list"),
                    (By.CSS_SELECTOR, "[class*='result']"),
                    (By.CSS_SELECTOR, "[class*='search']"),
                    (By.TAG_NAME, "main"),
                    (By.ID, "search-result"),
                ]
                
                for by, selector in possible_selectors:
                    try:
                        logger.info(f"[Toutiao] Waiting for element: {by}='{selector}'")
                        result_container = wait.until(
                            EC.presence_of_element_located((by, selector))
                        )
                        logger.info(f"[Toutiao] Found container using: {by}='{selector}'")
                        break
                    except TimeoutException:
                        logger.debug(f"[Toutiao] Timeout for selector: {by}='{selector}'")
                        continue
                
                if not result_container:
                    logger.warning("[Toutiao] No result container found, trying to parse page directly")
                
                # Additional wait for content to render
                time.sleep(5)
                
                # Check if verification page appeared (more precise detection)
                def has_captcha():
                    """Check if CAPTCHA/verification is present"""
                    try:
                        # Check for common verification elements
                        captcha_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                            "[class*='captcha'], [class*='verify'], [id*='captcha'], [id*='verify']")
                        if captcha_elements:
                            return True
                        
                        # Check page title
                        title = self.driver.title.lower()
                        if '验证' in title or 'verify' in title:
                            return True
                        
                        # Check for verification text in prominent areas
                        body = self.driver.find_element(By.TAG_NAME, "body")
                        visible_text = body.text[:500]  # Only check first 500 chars
                        if '滑动验证' in visible_text or '点击验证' in visible_text or '拖动滑块' in visible_text:
                            return True
                        
                        return False
                    except:
                        return False
                
                if has_captcha():
                    logger.warning(f"[Toutiao] Verification/CAPTCHA detected on page {page_num + 1}, skipping")
                    continue
                
                # Try to find article links with multiple strategies
                link_elements = []
                
                # Strategy 1: Find links containing article/group in href
                try:
                    links_with_article = self.driver.find_elements(
                        By.CSS_SELECTOR, 
                        "a[href*='/article/'], a[href*='/group/'], a[href*='/news/']"
                    )
                    if links_with_article:
                        logger.info(f"[Toutiao] Found {len(links_with_article)} article/group/news links")
                        link_elements.extend(links_with_article)
                except Exception as e:
                    logger.debug(f"[Toutiao] Article links strategy failed: {e}")
                
                # Strategy 2: Find all links and filter by text
                if not link_elements:
                    try:
                        all_links = self.driver.find_elements(By.TAG_NAME, "a")
                        logger.info(f"[Toutiao] Found {len(all_links)} total links")
                        
                        # Filter links with meaningful text
                        for link in all_links:
                            try:
                                text = link.text.strip()
                                href = link.get_attribute('href') or ''
                                
                                # Must have text and href
                                if not text or not href or len(text) < 10:
                                    continue
                                
                                # Exclude navigation/footer links
                                if any(x in href for x in ['login', 'download', 'about', 'help']):
                                    continue
                                
                                # Check if keyword appears in text (case insensitive)
                                if keyword.lower() in text.lower():
                                    link_elements.append(link)
                                    
                            except Exception as e:
                                continue
                        
                        logger.info(f"[Toutiao] Filtered to {len(link_elements)} relevant links")
                    except Exception as e:
                        logger.error(f"[Toutiao] Link filtering failed: {e}")
                page_articles = []
                for idx, link in enumerate(link_elements):
                    try:
                        article = self._parse_link(link, keyword)
                        if article:
                            page_articles.append(article)
                            logger.debug(f"[Toutiao] Parsed article {idx+1}: {article.title[:50]}")
                    except Exception as e:
                        logger.debug(f"[Toutiao] Failed to parse link {idx+1}: {e}")
                        continue
                
                logger.info(f"[Toutiao] Page {page_num + 1} found {len(page_articles)} articles")
                articles.extend(page_articles)
                
                # Check if we have enough articles
                if len(articles) >= max_results:
                    logger.info(f"[Toutiao] Reached target of {max_results} articles")
                    break
                
                # Small delay between pages to avoid rate limiting
                if page_num < max_pages - 1:
                    time.sleep(2)
            
            logger.info(f"[Toutiao] Successfully crawled {len(articles)} articles for '{keyword}'")
            return articles[:max_results]  # Return only requested amount
            
        except TimeoutException as e:
            logger.error(f"[Toutiao] Timeout waiting for content: {e}")
            logger.info("[Toutiao] Page may require longer load time or different selectors")
            return []
        except Exception as e:
            logger.error(f"[Toutiao] Crawl failed: {e}")
            import traceback
            logger.debug(traceback.format_exc())
            return []
        
        finally:
            self._close_driver()
    
    def _parse_link(self, link, keyword: str) -> Article | None:
        """Parse a link element to Article"""
        try:
            # Get href and text
            url = link.get_attribute('href')
            title = link.text.strip()
            
            # Validate URL
            if not url or not url.startswith('http'):
                return None
            
            # Validate title
            if not title or len(title) < 5:
                return None
            
            # Check if keyword is in title (case insensitive)
            if keyword.lower() not in title.lower():
                return None
            
            # Limit title and content length
            if len(title) > 200:
                title = title[:200]
            
            # Use title as content for now
            content = title
            if len(content) > 500:
                content = content[:500]
            
            article = Article(
                id=None,
                title=title,
                url=url,
                content=content,
                source='toutiao',
                keyword=keyword,
                crawled_at=datetime.now(),
                published_at=None
            )
            
            return article
            
        except Exception as e:
            logger.debug(f"[Toutiao] Error parsing link: {e}")
            return None
