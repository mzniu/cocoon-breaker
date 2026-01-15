"""
Deepseek AI integration for content filtering and summarization
"""
import json
import logging
import time
from typing import List, Dict, Any, Optional

import requests

from src.db.models import Article

logger = logging.getLogger(__name__)


class DeepseekClient:
    """Client for Deepseek API"""
    
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-reasoner",
        base_url: str = "https://api.deepseek.com",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize Deepseek client
        
        Args:
            api_key: Deepseek API key
            model: Model name
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts on failure
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.max_retries = max_retries
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 30000
    ) -> Optional[str]:
        """
        Call Deepseek chat completion API
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            
        Returns:
            Response content or None on failure
        """
        url = f"{self.base_url}/v1/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Log input
        logger.info(f"[Deepseek API] Request - Model: {self.model}, Temperature: {temperature}, Max Tokens: {max_tokens}")
        logger.debug(f"[Deepseek API] Input Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
        
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract content from response
                content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # Log output
                logger.info(f"[Deepseek API] Response received, length: {len(content)} chars")
                logger.debug(f"[Deepseek API] Output Content: {content[:500]}..." if len(content) > 500 else f"[Deepseek API] Output Content: {content}")
                
                # Log token usage if available
                if 'usage' in result:
                    usage = result['usage']
                    logger.info(f"[Deepseek API] Token Usage - Prompt: {usage.get('prompt_tokens', 0)}, Completion: {usage.get('completion_tokens', 0)}, Total: {usage.get('total_tokens', 0)}")
                
                if content:
                    return content
                else:
                    logger.warning("[Deepseek API] Empty response from Deepseek API")
                    return None
                    
            except requests.exceptions.Timeout:
                logger.warning(f"Deepseek API timeout (attempt {attempt + 1}/{self.max_retries})")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                continue
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Deepseek API request failed (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                continue
                
            except Exception as e:
                logger.error(f"Unexpected error calling Deepseek API: {e}")
                return None
        
        logger.error("All Deepseek API retry attempts failed")
        return None


class ArticleFilter:
    """Filter and rank articles using Deepseek AI"""
    
    def __init__(self, deepseek_client: DeepseekClient):
        self.client = deepseek_client
    
    def filter_and_rank(
        self,
        articles: List[Article],
        keyword: str,
        target_count: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Filter and rank articles by relevance and importance
        
        Args:
            articles: List of Article objects
            keyword: Search keyword/topic
            target_count: Target number of articles to return
            
        Returns:
            List of dicts with article info, priority, and enhanced content
        """
        if not articles:
            logger.warning("No articles to filter")
            return []
        
        # Build prompt for AI filtering
        prompt = self._build_filter_prompt(articles, keyword, target_count)
        
        messages = [
            {"role": "system", "content": "你是一个专业的新闻资讯总结大师，擅长从众多新闻中筛选并提炼关键信息，特别注重国际新闻和知名企业、人物的相关资讯。你会仔细分析新闻内容的真实性和相关性，而不是仅凭标题判断。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat_completion(messages, temperature=0.7, max_tokens=30000)
        
        if not response:
            logger.warning("AI filtering failed, using fallback method")
            return self._fallback_filter(articles, target_count)
        
        # Parse AI response
        try:
            filtered_articles = self._parse_filter_response(response, articles)
            logger.info(f"AI filtered {len(articles)} articles to {len(filtered_articles)}")
            return filtered_articles
        except Exception as e:
            logger.error(f"Failed to parse AI filter response: {e}")
            return self._fallback_filter(articles, target_count)
    
    def _build_filter_prompt(
        self,
        articles: List[Article],
        keyword: str,
        target_count: int
    ) -> str:
        """Build prompt for article filtering"""
        from datetime import datetime
        
        articles_text = "\n\n".join([
            f"[{idx}] 标题：{article.title}\n内容：{article.content[:500]}\n来源：{article.source}\n爬取时间：{article.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}"
            for idx, article in enumerate(articles)
        ])
        
        current_date = datetime.now().strftime("%Y年%m月%d日")
        
        prompt = f"""# 角色
你是一个专业的新闻资讯总结大师，擅长从众多新闻中筛选并提炼关键信息，为用户提供当日最重要的新闻摘要。

## 技能
### 技能 1: 总结每日新闻

1. 根据当前日期（{current_date}）总结出关于"{keyword}"主题当日最重要的{target_count}条新闻。
2. 对相似新闻进行去重或整合处理。
3. 每条新闻的content内容不要超过120字。
4. **每条新闻的标题不要超过25个字，去掉标题中的新闻来源（如"央视新闻"、"新华社"等）。**
5. **优先选择知名企业和人物相关的新闻。**
6. **优先选择爬取时间最近的新闻，在同等质量和重要性的情况下，选择更新的内容。**
7. **按照新闻重要性和时效性综合排序，时效性越强的新闻优先级越高。**

## 注意：
- 查看具体内容是否与"{keyword}"关系密切，而不是只看到标题有相关字样就算做符合条件。
- 去掉台湾相关企业及信息。
- 新闻的时效性非常重要，爬取时间越晚的新闻说明发布越新，应该优先考虑。

## 限制:
- 仅返回{target_count}条新闻。
- 请通过分析内容核实新闻中涉及的真实人物和信息，确保信息来源准确。

新闻列表：
{articles_text}

请返回JSON格式，包含筛选后的新闻序号、优先级（high/medium/low）、简短评价、**整理后的标题（25字以内，去掉来源）**和**整理后的内容摘要（120字以内）**：
```json
[
    {{"index": 0, "priority": "high", "reason": "知名企业重大突破", "title": "整理后的标题", "content": "整理后的内容摘要"}},
    {{"index": 2, "priority": "medium", "reason": "行业重要动态", "title": "整理后的标题", "content": "整理后的内容摘要"}}
]
```"""
        
        return prompt
    
    def _parse_filter_response(
        self,
        response: str,
        articles: List[Article]
    ) -> List[Dict[str, Any]]:
        """Parse AI filter response"""
        # Extract JSON from response
        json_start = response.find('[')
        json_end = response.rfind(']') + 1
        
        if json_start == -1 or json_end == 0:
            raise ValueError("No JSON found in response")
        
        json_str = response[json_start:json_end]
        filtered = json.loads(json_str)
        
        result = []
        for item in filtered:
            idx = item.get('index')
            if idx is None or idx >= len(articles):
                continue
            
            article = articles[idx]
            
            # Get refined title and content from AI
            refined_title = item.get('title', article.title) 
            refined_content = item.get('content', article.content)  
            
            # Create a copy of article with refined title and content
            from copy import copy
            refined_article = copy(article)
            refined_article.title = refined_title
            refined_article.content = refined_content
            
            result.append({
                'article': refined_article,
                'priority': item.get('priority', 'medium'),
                'reason': item.get('reason', '')
            })
        
        return result
    
    def _fallback_filter(
        self,
        articles: List[Article],
        target_count: int
    ) -> List[Dict[str, Any]]:
        """Fallback filtering when AI fails (simple keyword matching)"""
        # Simply return first N articles
        return [
            {
                'article': article,
                'priority': 'medium',
                'reason': 'Fallback selection'
            }
            for article in articles[:target_count]
        ]
    
    def generate_summary(self, keyword: str, filtered_articles: List[Dict[str, Any]]) -> str:
        """
        Generate summary for daily report
        
        Args:
            keyword: Topic keyword
            filtered_articles: List of filtered article dicts
            
        Returns:
            Summary text
        """
        if not filtered_articles:
            return f"今日{keyword}领域暂无重要资讯。"
        
        # Build prompt
        articles_text = "\n".join([
            f"{idx+1}. {item['article'].title}"
            for idx, item in enumerate(filtered_articles)
        ])
        
        prompt = f"""请根据以下关于"{keyword}"的新闻标题，挑选三个最重要的新闻，生成一段3句话的今日要点总结：

{articles_text}

要求：
- 简洁明了，突出重点
- 涵盖主要事件和趋势
- 字数在80-120字之间
"""
        
        messages = [
            {"role": "system", "content": "你是一个专业的新闻编辑，擅长撰写新闻摘要。"},
            {"role": "user", "content": prompt}
        ]
        
        response = self.client.chat_completion(messages, temperature=0.7, max_tokens=1500)
        
        if response:
            return response.strip()
        else:
            # Fallback summary
            return f"今日{keyword}领域共有{len(filtered_articles)}条重要资讯，涵盖行业动态和最新发展。"
