"""
Daily report HTML generator using Deepseek AI
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

from src.ai.deepseek import DeepseekClient, ArticleFilter
from src.db.models import Article

logger = logging.getLogger(__name__)


class ReportGenerator:
    """Generate daily HTML reports"""
    
    def __init__(
        self,
        deepseek_client: DeepseekClient,
        template_path: str = "templates/report.html",
        output_dir: str = "reports"
    ):
        """
        Initialize report generator
        
        Args:
            deepseek_client: Deepseek API client
            template_path: Path to HTML template file
            output_dir: Directory to save generated reports
        """
        self.deepseek_client = deepseek_client
        self.article_filter = ArticleFilter(deepseek_client)
        self.template_path = template_path
        self.output_dir = Path(output_dir)
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load template
        self.template = self._load_template()
    
    def _load_template(self) -> str:
        """Load HTML template"""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            logger.error(f"Template not found: {self.template_path}")
            raise
        except Exception as e:
            logger.error(f"Failed to load template: {e}")
            raise
    
    def generate_report(
        self,
        keyword: str,
        articles: List[Article],
        date: datetime = None
    ) -> str:
        """
        Generate daily report HTML
        
        Args:
            keyword: Topic keyword
            articles: List of crawled articles
            date: Report date (default: today)
            
        Returns:
            Path to generated HTML file
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y-%m-%d")
        
        logger.info(f"Generating report for {keyword} on {date_str} with {len(articles)} articles")
        
        # Filter and rank articles
        filtered_articles = self.article_filter.filter_and_rank(
            articles,
            keyword,
            target_count=7
        )
        
        if not filtered_articles:
            logger.warning(f"No articles after filtering for {keyword}")
            # Generate empty report
            return self._generate_empty_report(keyword, date_str)
        
        # Generate summary
        summary = self.article_filter.generate_summary(keyword, filtered_articles)
        
        # Build prompt for HTML generation
        html_content = self._generate_html_with_ai(
            keyword,
            date_str,
            summary,
            filtered_articles
        )
        
        if not html_content:
            logger.error("Failed to generate HTML content")
            return None
        
        # Save report with timestamp to avoid overwriting
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{keyword}_{date_str}_{timestamp}.html"
        filepath = self.output_dir / filename
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            logger.info(f"Report saved to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Failed to save report: {e}")
            return None
    
    def _generate_html_with_ai(
        self,
        keyword: str,
        date_str: str,
        summary: str,
        filtered_articles: List[Dict[str, Any]]
    ) -> str:
        """Generate HTML using Deepseek AI"""
        # Build articles list for prompt
        articles_list = []
        for idx, item in enumerate(filtered_articles, 1):
            article = item['article']
            priority = item['priority']
            
            # Map priority to emoji
            priority_emoji = {
                'high': '🔴',
                'medium': '🟡',
                'low': '🟢'
            }.get(priority, '🟡')
            
            articles_list.append({
                'number': idx,
                'title': article.title,
                'url': article.url,
                'content': article.content[:300],  # Limit content length
                'priority': priority,
                'emoji': priority_emoji
            })
        
        # Build prompt
        prompt = self._build_html_generation_prompt(
            keyword,
            date_str,
            summary,
            articles_list
        )
        
        messages = [
            {"role": "system", "content": "你是一个专业的前端开发者，擅长生成优美的HTML页面。"},
            {"role": "user", "content": prompt}
        ]
        
        html_response = self.deepseek_client.chat_completion(
            messages,
            temperature=0.7,
            max_tokens=40000
        )
        
        if html_response:
            # Extract HTML from response
            return self._extract_html(html_response)
        else:
            # Fallback: use simple template replacement
            logger.warning("AI HTML generation failed, using fallback method")
            return self._fallback_html_generation(keyword, date_str, summary, articles_list)
    
    def _build_html_generation_prompt(
        self,
        keyword: str,
        date_str: str,
        summary: str,
        articles_list: List[Dict[str, Any]]
    ) -> str:
        """Build prompt for HTML generation"""
        articles_text = "\n".join([
            f"{item['number']}. {item['emoji']} {item['title']}\n   链接：{item['url']}\n   内容：{item['content']}"
            for item in articles_list
        ])
        
        prompt = f"""请参考以下模板结构，生成一份完整的HTML日报页面。

关键词：{keyword}
日期：{date_str}
今日要点：{summary}

文章列表：
{articles_text}

报告模版：
{self.template}

要求：
1. 使用提供的报告模版结构（1080x1440px移动端布局）
2. 主题色为 #e60012（红色）
3. 包含header区域（标题+关键词+日期卡片）
4. 包含今日要点区域（today-must-read），显示摘要内容，适当用红色和黑色加粗重点词汇
5. 包含文章列表区域（info-list），每篇文章带优先级标识
6. 包含关键词区域（keywords），显示今日关键词，由所有文章标题提炼而来，3-4个词汇
7. footer显示"@小牛聊AI"
8. 保持responsive设计和优美样式
9. 文章内容适当增加红色和黑色加粗重点突出显示
请直接返回完整的HTML代码，使用<!DOCTYPE html>开头。"""
        
        return prompt
    
    def _extract_html(self, response: str) -> str:
        """Extract HTML from AI response"""
        # Find HTML tags
        html_start = response.find('<!DOCTYPE html>')
        if html_start == -1:
            html_start = response.find('<html>')
        
        if html_start == -1:
            # No HTML found, return as-is
            return response
        
        html_end = response.rfind('</html>') + 7
        if html_end < 7:
            return response
        
        return response[html_start:html_end]
    
    def _fallback_html_generation(
        self,
        keyword: str,
        date_str: str,
        summary: str,
        articles_list: List[Dict[str, Any]]
    ) -> str:
        """Fallback HTML generation using simple template replacement"""
        # Build articles HTML
        articles_html = ""
        for item in articles_list:
            articles_html += f"""
                    <div class="info-item">
                        <div class="item-priority">{item['emoji']}</div>
                        <div class="item-content">
                            <h3 class="item-title">
                                <a href="{item['url']}" target="_blank">{item['title']}</a>
                            </h3>
                            <p class="item-desc">{item['content'][:200]}...</p>
                        </div>
                    </div>
"""
        
        # Replace template variables
        html = self.template.replace('{{date}}', date_str)
        html = html.replace('{{keywords}}', keyword)
        html = html.replace('{{summary}}', summary)
        
        # Replace articles section
        # Find the info-list section and replace its content
        list_start = html.find('<div class="info-list">')
        list_end = html.find('</div>', list_start + 100)  # Skip to end of info-list
        
        if list_start != -1 and list_end != -1:
            # Find all closing </div> to get the correct end
            depth = 1
            pos = list_start + len('<div class="info-list">')
            while depth > 0 and pos < len(html):
                if html[pos:pos+6] == '<div c' or html[pos:pos+5] == '<div>':
                    depth += 1
                elif html[pos:pos+6] == '</div>':
                    depth -= 1
                    if depth == 0:
                        list_end = pos + 6
                        break
                pos += 1
            
            new_list = f'<div class="info-list">\n{articles_html}\n            </div>'
            html = html[:list_start] + new_list + html[list_end:]
        
        return html
    
    def _generate_empty_report(self, keyword: str, date_str: str) -> str:
        """Generate empty report when no articles available"""
        html = self.template.replace('{{date}}', date_str)
        html = html.replace('{{keywords}}', keyword)
        html = html.replace('{{summary}}', f"今日{keyword}领域暂无重要资讯。")
        
        # Empty articles list
        empty_html = '<div class="info-list"><p style="text-align:center;padding:40px;color:#999;">暂无资讯</p></div>'
        
        list_start = html.find('<div class="info-list">')
        if list_start != -1:
            list_end = html.find('</div>', list_start)
            # Find proper closing tag
            depth = 1
            pos = list_start + len('<div class="info-list">')
            while depth > 0 and pos < len(html):
                if html[pos:pos+5] == '<div ' or html[pos:pos+5] == '<div>':
                    depth += 1
                elif html[pos:pos+6] == '</div>':
                    depth -= 1
                    if depth == 0:
                        list_end = pos + 6
                        break
                pos += 1
            
            html = html[:list_start] + empty_html + html[list_end:]
        
        # Save empty report
        filename = f"{keyword}_{date_str}.html"
        filepath = self.output_dir / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)
        
        logger.info(f"Empty report saved to {filepath}")
        return str(filepath)
