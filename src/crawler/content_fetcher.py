"""
Full content fetcher for articles using Selenium
"""
import logging
import time
from typing import Dict
from bs4 import BeautifulSoup
import html2text
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

logger = logging.getLogger(__name__)


class ContentFetcher:
    """Fetch full content from article URLs using Selenium"""
    
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self._driver_service = None
    
    def _get_driver(self):
        """Create and configure Chrome WebDriver"""
        logger.info(f"[DEBUG] Setting up Chrome options...")
        
        options = Options()
        options.add_argument('--headless=new')  # New headless mode
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        logger.info(f"[DEBUG] Installing/updating ChromeDriver...")
        
        # Use webdriver-manager to automatically manage ChromeDriver
        service = Service(ChromeDriverManager().install())
        
        logger.info(f"[DEBUG] Creating Chrome driver instance...")
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(self.timeout)
        
        logger.info(f"[DEBUG] Chrome driver created successfully")
        return driver
    
    def fetch_content(self, url: str) -> Dict[str, any]:
        """
        Fetch full content from URL using Selenium
        
        Args:
            url: Article URL
            
        Returns:
            Dict with keys:
                - status: 'success' | 'failed' | 'no_content'
                - content: Full text content (if success)
                - title: Extracted title (if available)
                - error: Error message (if failed)
        """
        driver = None
        try:
            logger.info(f"[DEBUG] Starting fetch for URL: {url}")
            
            # Create driver
            driver = self._get_driver()
            
            # Navigate to URL
            logger.info(f"[DEBUG] Navigating to URL: {url}")
            driver.get(url)
            logger.info(f"[DEBUG] Page loaded successfully")
            
            # Wait a bit for dynamic content
            logger.info(f"[DEBUG] Waiting 2s for dynamic content...")
            time.sleep(2)
            logger.info(f"[DEBUG] Wait complete")
            
            # Get title
            logger.info(f"[DEBUG] Getting page title...")
            title = driver.title
            logger.info(f"[DEBUG] Title: {title}")
            
            # Get page source
            logger.info(f"[DEBUG] Getting page source...")
            page_source = driver.page_source
            logger.info(f"[DEBUG] Page source length: {len(page_source)} chars")
            
            # Parse with BeautifulSoup
            logger.info(f"[DEBUG] Parsing HTML with BeautifulSoup...")
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Try multiple selectors for content
            content_html = None
            selectors = [
                'article',
                '[role="main"]',
                '.article-content',
                '.post-content',
                '.entry-content',
                '.content',
                'main',
                '#content'
            ]
            
            logger.info(f"[DEBUG] Trying {len(selectors)} content selectors...")
            for selector in selectors:
                try:
                    logger.info(f"[DEBUG] Trying selector: {selector}")
                    element = soup.select_one(selector)
                    if element:
                        content_html = str(element)
                        logger.info(f"[DEBUG] ✓ Found content using selector: {selector} ({len(content_html)} chars)")
                        break
                    else:
                        logger.info(f"[DEBUG] ✗ Selector {selector} returned None")
                except Exception as e:
                    logger.warning(f"[DEBUG] ✗ Selector {selector} failed: {e}")
                    continue
            
            # Fallback to body
            if not content_html:
                logger.info(f"[DEBUG] No selector worked, using body")
                body = soup.find('body')
                if body:
                    content_html = str(body)
                else:
                    content_html = page_source
                logger.info(f"[DEBUG] Fallback HTML length: {len(content_html)} chars")
            
            # Parse the content HTML
            content_soup = BeautifulSoup(content_html, 'html.parser')
            
            # Remove unwanted elements
            logger.info(f"[DEBUG] Removing unwanted elements...")
            removed_count = 0
            for tag in content_soup(['script', 'style', 'iframe', 'noscript', 'nav', 'header', 'footer', 'aside', 'form']):
                tag.decompose()
                removed_count += 1
            logger.info(f"[DEBUG] Removed {removed_count} unwanted tags")
            
            # Convert HTML to Markdown
            logger.info(f"[DEBUG] Converting HTML to Markdown...")
            h2t = html2text.HTML2Text()
            h2t.ignore_links = False
            h2t.ignore_images = True
            h2t.body_width = 0  # Don't wrap lines
            h2t.unicode_snob = True
            h2t.ignore_emphasis = False
            
            markdown_text = h2t.handle(str(content_soup))
            logger.info(f"[DEBUG] Markdown text length: {len(markdown_text)} chars")
            
            # Clean up excessive whitespace
            logger.info(f"[DEBUG] Cleaning up Markdown...")
            lines = [line.rstrip() for line in markdown_text.split('\n')]
            # Remove excessive blank lines (more than 2 consecutive)
            cleaned_lines = []
            blank_count = 0
            for line in lines:
                if line.strip():
                    cleaned_lines.append(line)
                    blank_count = 0
                else:
                    blank_count += 1
                    if blank_count <= 2:
                        cleaned_lines.append(line)
            
            content = '\n'.join(cleaned_lines).strip()
            logger.info(f"[DEBUG] Clean Markdown length: {len(content)} chars, {len(cleaned_lines)} lines")
            
            # Validate content
            if len(content) < 100:
                logger.warning(f"[DEBUG] Content too short: {len(content)} chars (minimum 100)")
                logger.warning(f"[DEBUG] Content preview: {content[:200]}")
                return {
                    'status': 'no_content',
                    'error': f'Content too short: {len(content)} chars'
                }
            
            logger.info(f"[DEBUG] ✓ Successfully fetched {len(content)} chars from {url}")
            logger.info(f"[DEBUG] Content preview (first 200 chars): {content[:200]}")
            
            return {
                'status': 'success',
                'content': content,
                'title': title
            }
            
        except TimeoutException:
            error = f"Page load timeout after {self.timeout}s"
            logger.error(f"[DEBUG] Timeout error: {error}")
            return {
                'status': 'failed',
                'error': error
            }
            
        except WebDriverException as e:
            error = f"WebDriver error: {str(e)}"
            logger.error(f"[DEBUG] WebDriver exception: {error}")
            return {
                'status': 'failed',
                'error': error
            }
            
        except Exception as e:
            error = f"Error: {str(e)}"
            logger.error(f"[DEBUG] Unexpected exception: {type(e).__name__}")
            logger.error(f"[DEBUG] Exception message: {error}")
            logger.error(f"[DEBUG] Full traceback:", exc_info=True)
            return {
                'status': 'failed',
                'error': error
            }
            
        finally:
            if driver:
                logger.info(f"[DEBUG] Closing Chrome driver...")
                try:
                    driver.quit()
                    logger.info(f"[DEBUG] Driver closed successfully")
                except:
                    logger.warning(f"[DEBUG] Error closing driver (may be already closed)")
