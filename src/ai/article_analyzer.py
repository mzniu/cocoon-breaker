"""
Article analyzer using Deepseek AI
"""
import logging
import json
from datetime import datetime
from typing import Dict, Optional
from src.ai.deepseek import DeepseekClient
from src.config import Config

logger = logging.getLogger(__name__)


class ArticleAnalyzer:
    """Analyze articles using Deepseek AI"""
    
    def __init__(self, config=None):
        """
        Initialize analyzer with Deepseek client
        
        Args:
            config: Optional config object. If None, will load from default location.
        """
        if config is None:
            config = Config()
        
        self.client = DeepseekClient(
            api_key=config.llm.api_key,
            model=config.llm.model,
            base_url=config.llm.base_url,
            timeout=60  # 60 second timeout for analysis (deepseek-reasoner needs time to think)
        )
    
    def analyze(self, title: str, content: str, crawled_at: datetime) -> Dict[str, any]:
        """
        Analyze article and extract metadata
        
        Args:
            title: Article title
            content: Article summary/content
            crawled_at: When the article was crawled
            
        Returns:
            Dict with keys:
                - actual_published_at: ISO 8601 datetime string or None
                - actual_source: Source name string or None
                - importance_score: Float 0-100
                - analysis_status: 'success' | 'failed'
                - error: Error message if failed
        """
        try:
            logger.info(f"[ANALYZER] Analyzing article: {title[:50]}...")
            
            # Build prompt
            prompt = self._build_prompt(title, content, crawled_at)
            
            # Call Deepseek API
            logger.info(f"[ANALYZER] Calling Deepseek API...")
            response_text = self.client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,  # Higher temperature for better reasoning
                max_tokens=2000  # Increased token limit for complete responses
            )
            
            if not response_text:
                logger.error(f"[ANALYZER] No response from API")
                return self._failed_result("No response from API")
            
            # Extract response text
            logger.info(f"[ANALYZER] API response: {response_text[:200]}...")
            
            # Parse JSON response
            try:
                # Try to extract JSON from markdown code block if present
                if '```json' in response_text:
                    start = response_text.find('```json') + 7
                    end = response_text.find('```', start)
                    response_text = response_text[start:end].strip()
                elif '```' in response_text:
                    start = response_text.find('```') + 3
                    end = response_text.find('```', start)
                    response_text = response_text[start:end].strip()
                
                result = json.loads(response_text)
                
                # Validate and normalize
                analyzed_data = {
                    'actual_published_at': result.get('actual_published_at'),
                    'actual_source': result.get('actual_source'),
                    'importance_score': float(result.get('importance_score', 50.0)),
                    'analysis_status': 'success',
                    'error': None
                }
                
                # Validate importance_score range
                if not (0 <= analyzed_data['importance_score'] <= 100):
                    logger.warning(f"[ANALYZER] Score out of range: {analyzed_data['importance_score']}, clamping to 0-100")
                    analyzed_data['importance_score'] = max(0, min(100, analyzed_data['importance_score']))
                
                logger.info(f"[ANALYZER] ✓ Analysis complete: source={analyzed_data['actual_source']}, score={analyzed_data['importance_score']}")
                return analyzed_data
                
            except json.JSONDecodeError as e:
                logger.error(f"[ANALYZER] JSON parse error: {e}, response: {response_text}")
                return self._failed_result(f"JSON parse error: {str(e)}")
                
        except Exception as e:
            logger.error(f"[ANALYZER] Analysis error: {e}", exc_info=True)
            return self._failed_result(str(e))
    
    def _build_prompt(self, title: str, content: str, crawled_at: datetime) -> str:
        """Build analysis prompt"""
        return f"""分析以下新闻文章，提取关键元数据信息。

**文章标题**：{title}

**文章摘要**：
{content[:500]}

**爬取时间**：{crawled_at.strftime('%Y-%m-%d %H:%M:%S')}

---

请以严格的 JSON 格式返回分析结果（不要添加任何其他文字说明）：

{{
  "actual_published_at": "真实发布时间（ISO 8601格式，如2026-01-16T10:30:00，如果无法确定则返回null）",
  "actual_source": "真实信息来源（如'新华社'、'路透社'、'央视新闻'，如果无法确定则返回null）",
  "importance_score": 重要程度评分（0-100的数字）,
  "reasoning": "评分理由（50字内）"
}}

**评分标准**：
- 80-100分：重大新闻（国际大事、重要政策、重大突发事件）
- 60-79分：较重要（行业重要动态、地区重要新闻）
- 40-59分：一般重要（常规新闻、行业资讯）
- 20-39分：次要信息（娱乐八卦、琐碎消息）
- 0-19分：无价值信息（广告、垃圾信息）

请仅返回JSON，不要包含其他解释文字。"""
    
    def _failed_result(self, error_msg: str) -> Dict[str, any]:
        """Return failed analysis result"""
        return {
            'actual_published_at': None,
            'actual_source': None,
            'importance_score': 50.0,  # Default middle score
            'analysis_status': 'failed',
            'error': error_msg
        }
