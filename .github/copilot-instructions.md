# Copilot Instructions for Cocoon Breaker

## 🚨 核心工作原则

### 方案确认原则
**在执行任何重大改动前，必须先向用户说明方案并获得明确同意。**

重大改动包括但不限于：
- 更换技术栈或依赖库（如从 Playwright 切换到 requests）
- 修改架构设计（如从同步改为异步）
- 删除或重构核心功能模块
- 批量修改多个文件
- 添加新的外部依赖

**工作流程**：
1. 分析问题，提出 2-3 个解决方案
2. 说明每个方案的优缺点、影响范围、风险
3. **等待用户明确选择方案**
4. 用户确认后再执行实施

**禁止行为**：
- ❌ 自行决定重大技术选型
- ❌ 未经同意就更换依赖库
- ❌ 遇到问题就立即换方案而不询问
- ❌ 假设用户会同意某个方案就直接执行

## Project Overview

AI 日报生成工具，解决"信息茧房"问题。自动爬取用户订阅主题的新闻，通过 AI 筛选生成每日精选日报。

- **语言**：Python 3.10+
- **后端框架**：FastAPI
- **前端框架**：Vue 3（CDN 引入）
- **数据库**：SQLite
- **AI 服务**：Deepseek API
- **运行环境**：本地 Web 服务

## Architecture & Structure

```
cocoon-breaker/
├── src/
│   ├── main.py              # FastAPI 应用入口（lifespan manager）
│   ├── config.py            # 配置加载（YAML + 环境变量）
│   ├── api/                  # REST API 路由（11 endpoints total）
│   │   ├── subscriptions.py  # 订阅管理 API (5 endpoints)
│   │   ├── reports.py        # 日报 API (5 endpoints)
│   │   ├── schedule.py       # 定时设置 API (2 endpoints)
│   │   └── articles.py       # 文章 API（新增）
│   ├── crawler/              # 爬虫模块（继承 BaseCrawler）
│   │   ├── base.py           # 抽象基类（含 User-Agent 轮换）
│   │   ├── baidu.py          # 百度新闻搜索
│   │   ├── yahoo.py          # Yahoo 搜索（国内可访问）
│   │   ├── bing.py           # 必应搜索（备选）
│   │   ├── google.py         # Google Custom Search API（可选）
│   │   ├── tavily.py         # Tavily AI 搜索（可选）
│   │   ├── kr36.py           # 36氪 RSS 爬取
│   │   ├── huxiu.py          # 虎嗅网 RSS 爬取
│   │   ├── toutiao.py        # 今日头条（实验性）
│   │   ├── content_fetcher.py # 文章正文提取（Playwright）
│   │   └── search_utils.py   # 搜索工具函数
│   ├── db/                   # 数据库模块
│   │   ├── database.py       # SQLite 异步连接（aiosqlite）
│   │   ├── models.py         # 数据模型（dataclass）
│   │   ├── repository.py     # CRUD + 评分系统
│   │   └── migrations.py     # Schema 版本管理（新增）
│   ├── ai/                   # AI 集成
│   │   ├── deepseek.py       # Deepseek API 客户端（重试逻辑）
│   │   └── article_analyzer.py # 文章分析器（时效性）
│   ├── report/               # 日报生成
│   │   └── generator.py      # HTML 日报生成器（LLM 驱动）
│   ├── scheduler/            # 定时任务
│   │   └── tasks.py          # schedule 任务（多源爬取 + 评分）
│   ├── utils/                # 工具模块
│   │   └── log_buffer.py     # 实时日志缓冲（用于前端展示）
│   └── static/               # 前端静态文件
│       ├── index.html        # Vue 3 单页应用（主页）
│       ├── articles.html     # 文章管理页面（新增）
│       ├── css/style.css     # 统一设计系统
│       └── js/
│           ├── app.js        # Vue 应用逻辑
│           └── vue.global.prod.js # Vue 3 CDN 文件
├── templates/
│   └── report.html           # 日报 HTML 模板（供 LLM 参考）
├── tests/
│   ├── ut/                   # 单元测试（60+ tests）
│   │   ├── test_crawler/
│   │   ├── test_db/
│   │   ├── test_ai/
│   │   ├── test_report/
│   │   └── test_api/
│   └── integration/          # 集成测试
│       └── test_workflow.py
├── docs/                     # 技术文档
│   ├── PRD.md               # 产品需求文档
│   ├── NEWS_FRESHNESS_FEATURE.md # 时效性功能说明
│   └── 36KR_THEPAPER_INTEGRATION.md # RSS 集成指南
├── config.yaml               # 用户配置文件
├── config.example.yaml       # 配置模板（125 lines）
├── reports/                  # 生成的日报输出目录（HTML文件）
├── data/                     # SQLite 数据库文件
├── logs/                     # 日志文件（带轮转）
└── requirements.txt          # Python 依赖
```

**模块职责**：
- `api/`：REST API 路由，使用 `APIRouter`，在 `main.py` 中注册
- `crawler/`：网页爬取，继承 `BaseCrawler`，返回 `List[Article]`，失败返回空列表不抛异常
- `db/`：异步 SQLite 操作，使用 `INSERT OR IGNORE` 去重，`get_by_keyword_with_scoring()` 实现混合评分
- `ai/`：Deepseek API 调用（超时 30s，重试 3 次），`ArticleAnalyzer` 分析时效性和重要性
- `report/`：通过 LLM 直接生成完整 HTML，参考 `templates/report.html` 模板
- `scheduler/`：`schedule` 库实现定时任务，使用 asyncio 异步爬取，`_running` 标志防止重复执行
- `static/`：Vue 3 通过 CDN 引入，无需 npm 构建，使用 Options API 风格

## Development Workflow

### Setup
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt
cp config.example.yaml config.yaml
# 设置环境变量 DEEPSEEK_API_KEY
```

### Run
```bash
# 开发模式（热重载）
uvicorn src.main:app --reload --port 8000

# 生产模式
python src/main.py
```

### Testing
```bash
pytest tests/ut/ -v                    # 运行所有单元测试
pytest tests/ut/test_crawler/ -v       # 测试爬虫模块
pytest tests/ut/ -v --cov=src          # 带覆盖率报告
```

### API Documentation
启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Code Conventions

### Naming
- **文件/模块**：`snake_case.py`
- **类名**：`PascalCase`
- **函数/变量**：`snake_case`
- **常量**：`UPPER_SNAKE_CASE`
- **API 路由**：`/api/resource` (RESTful 风格)

### Patterns
- **配置**：YAML 文件（`config.yaml`）+ 环境变量覆盖（`${VAR_NAME}`格式），敏感信息（API Key）仅用环境变量
- **日志**：使用 `logging` 模块，RotatingFileHandler（10MB/file，5个备份），实时日志缓冲见 `log_buffer.py`
- **错误处理**：爬虫/API 失败不中断流程，记录日志后继续，Deepseek API 超时重试 3 次（指数退避）
- **数据模型**：使用 `@dataclass` 定义（`db/models.py`），与 SQLite 表对应
- **API 响应**：统一使用 Pydantic `BaseModel`，返回 JSON，所有路由使用 `APIRouter(prefix="/api/...")`
- **异步模式**：Database 使用 `aiosqlite` 异步连接，FastAPI 路由用 `async def`，爬虫用 `asyncio.gather()` 并发
- **数据库迁移**：`migrations.py` 管理 schema 版本，使用 `schema_version` 表跟踪，避免数据丢失
- **评分系统**：`ArticleRepository.get_by_keyword_with_scoring()` 实现混合评分（质量 0.7 + 时效性 0.3），时间衰减用指数函数

### 示例：数据模型
```python
@dataclass
class Article:
    id: int | None
    title: str
    url: str
    content: str
    source: str  # "baidu" | "bing"
    keyword: str
    crawled_at: datetime

# Pydantic 用于 API
class ArticleResponse(BaseModel):
    id: int
    title: str
    url: str
    summary: str
```

## Key Files & Directories

- `config.yaml` - 订阅主题、定时时间、服务器配置
- `src/main.py` - FastAPI 应用入口
- `src/api/` - REST API 路由定义
- `src/ai/deepseek.py` - AI 筛选核心逻辑
- `src/report/generator.py` - HTML 日报生成器
- `templates/report.html` - 日报 HTML 模板（LLM 参考）
- `src/static/` - Vue 3 前端文件
- `reports/` - 日报 HTML 文件输出
- `data/cocoon.db` - SQLite 数据库
- `tests/ut/` - 单元测试

## External Dependencies

### Deepseek API（必需）
- 文档：https://platform.deepseek.com/
- 模型：`deepseek-reasoner`（reasoning + generation）
- 认证：Bearer Token（环境变量 `DEEPSEEK_API_KEY`，启动时必须存在）
- 错误处理：超时 30s，重试 3 次（指数退避），失败后跳过本次生成
- 用途：文章筛选（`ArticleFilter`）+ 完整 HTML 生成（`ReportGenerator`）

### 爬虫数据源
**免费爬虫**（默认启用）：
- Baidu（百度新闻）：BeautifulSoup 解析，User-Agent 轮换，随机 1-3s 间隔
- Yahoo（雅虎搜索）：国内可访问，无需代理
- Kr36（36氪 RSS）：feedparser 解析，tech/business 内容
- Huxiu（虎嗅网 RSS）：深度商业报道

**API 源**（可选，需配置）：
- Google Custom Search：环境变量 `GOOGLE_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID`，免费 100 次/天
- Tavily API：环境变量 `TAVILY_API_KEY`，AI 优化搜索，支持 `basic`/`advanced` 模式

**爬虫规范**：
- 继承 `BaseCrawler`，实现 `crawl(keyword: str, max_results: int) -> List[Article]`
- 失败返回 `[]` 不抛异常，记录日志 `logger.error()`
- URL 去重通过 `INSERT OR IGNORE` 自动处理
- `content_fetcher.py` 使用 Playwright 提取完整正文（可选）

## Common Tasks

### 添加新的信息源
1. 在 `src/crawler/` 下创建新模块（如 `weibo.py`）
2. 继承 `BaseCrawler`，实现 `crawl(keyword: str, max_results: int) -> List[Article]`
   ```python
   class WeiboCrawler(BaseCrawler):
       def crawl(self, keyword: str, max_results: int = 20) -> List[Article]:
           try:
               # 爬取逻辑
               return articles
           except Exception as e:
               logger.error(f"Weibo crawl failed: {e}")
               return []  # 失败返回空列表
   ```
3. 在 `config.yaml` 的 `crawler.sources` 中添加 `weibo`
4. 在 `src/scheduler/tasks.py` 的 `initialize()` 中实例化爬虫
5. 在 `tests/ut/test_crawler/test_weibo.py` 编写单元测试

### 添加新的 API 端点
1. 在 `src/api/` 下创建或修改路由模块
2. 使用 Pydantic 定义请求/响应模型（继承 `BaseModel`）
3. 使用 `APIRouter(prefix="/api/resource", tags=["resource"])` 创建路由
4. 在 `src/main.py` 的 `app.include_router()` 中注册
5. 在 `tests/ut/test_api/` 下编写测试（使用 `TestClient`）

### 修改日报格式
1. 编辑 `templates/report.html` 中的 HTML/CSS 模板（LLM 参考）
2. 修改 `src/report/generator.py` 的 `_generate_html_with_ai()` 中的 Prompt
3. 日报为 1080x1440px 移动端友好设计，主题色 #e60012
4. 更新 `tests/ut/test_report/test_generator.py` 测试用例

### 添加数据库字段
1. 修改 `src/db/models.py` 中的 `@dataclass` 定义
2. 在 `src/db/migrations.py` 添加新迁移函数 `_migration_00X_description()`
3. 在 `migrations` 列表中注册新版本号
4. 运行服务，迁移自动应用（见日志 "Applying migration X..."）
5. 更新 `repository.py` 中的 SQL 语句

### 调整时效性/质量权重
编辑 `config.yaml`：
```yaml
report:
  time_range_hours: 24        # 仅选择最近 24 小时的新闻
  quality_weight: 0.7         # 质量权重（0-1）
  freshness_weight: 0.3       # 时效性权重（0-1）
  time_decay_lambda: 0.1      # 时间衰减系数（越大衰减越快）
```

## Notes for AI Agents

**配置与环境**：
- **不要修改** `config.yaml` 中的 API Key 占位符，保持 `${DEEPSEEK_API_KEY}` 格式
- 启动时 `DEEPSEEK_API_KEY` 必须存在，否则服务启动失败（500 错误）
- Google/Tavily API 可选，未配置时相应爬虫自动跳过

**数据库操作**：
- **SQLite** 使用 `url` 字段唯一约束（`UNIQUE`），插入时用 `INSERT OR IGNORE` 自动去重
- `aiosqlite` 异步操作，所有 DB 方法必须 `await`，例如：`await repo.create(article)`
- 新增字段需编写迁移（`migrations.py`），不要直接修改表结构
- `ArticleRepository.create()` 插入成功返回 ID，重复返回 `None`

**爬虫规范**：
- **爬虫模块**返回 `List[Article]` 或 `[]`，不抛异常（`logger.error()` 记录）
- `BaseCrawler` 提供 `_make_request()` 方法（含重试、User-Agent 轮换）
- `_random_delay()` 添加 1-3s 随机延迟，避免被封
- RSS 爬虫（kr36, huxiu）使用 `feedparser`，不需要 `_random_delay()`

**API 开发**：
- **FastAPI** 路由使用 `router = APIRouter(prefix="/api/...", tags=[...])`
- 在 `main.py` 的 `app.include_router(router)` 统一注册
- Pydantic 模型使用 `Field(..., min_length=1, description="...")`
- 依赖注入：`db: Database = Depends(get_db)`

**前端规范**：
- **Vue 3** CDN 引入（`vue.global.prod.js`），无需 npm/构建步骤
- Options API 风格：`data()`, `computed`, `methods`, `mounted`
- 统一设计：紫色渐变主题 `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`，卡片圆角 `12px`
- 长列表必须分页（20 条/页），搜索加防抖（500ms）

**日报生成**：
- 日报文件名格式：`{keyword}_{YYYY-MM-DD}_{HHMMSS}.html`（带时间戳避免覆盖）
- 通过 Deepseek 直接生成完整 HTML（`_generate_html_with_ai()`），参考 `templates/report.html`
- 筛选使用 `ArticleFilter.filter_and_rank()`，返回 7 篇文章
- 评分公式：`final_score = 0.7 × quality + 0.3 × exp(-0.1 × hours)`

**测试要求**：
- **每个模块必须有对应的单元测试**，放在 `tests/ut/` 对应子目录
- 使用 `pytest tests/ut/` 运行，覆盖率 `--cov=src`
- API 测试使用 `TestClient`，异步测试用 `pytest-asyncio` 的 `@pytest.mark.asyncio`

**依赖管理**：
- 优先使用标准库（`asyncio`, `logging`, `datetime`）
- 第三方库：`fastapi`, `uvicorn`, `aiosqlite`, `requests`, `beautifulsoup4`, `schedule`, `pyyaml`, `feedparser`, `playwright`
- 添加新依赖前必须询问用户（见"方案确认原则"）

## Development Standards & Quality Control

### 代码编辑效率
- **批量操作优先**：当需要对同一文件进行多个独立编辑时，使用 `multi_replace_string_in_file` 一次性完成，避免多次调用 `replace_string_in_file`
- **精确匹配**：使用 `replace_string_in_file` 时，必须包含目标代码前后 3-5 行的上下文，确保匹配唯一性
- **避免猜测**：如果不确定代码确切内容，先用 `read_file` 或 `grep_search` 确认，再进行编辑
- **文件检查**：编辑前先检查文件是否存在和完整性，避免操作损坏的或不存在的文件

### 视觉风格统一
- **设计系统**：项目使用统一的设计语言
  - 主题色：紫色渐变 `linear-gradient(135deg, #667eea 0%, #764ba2 100%)`
  - 次要色：蓝色渐变 `linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)`
  - 危险色：粉红渐变 `linear-gradient(135deg, #f093fb 0%, #f5576c 100%)`
  - 卡片圆角：`12px`
  - 卡片阴影：`0 4px 6px rgba(0, 0, 0, 0.1)`
  - 过渡时间：`0.3s`
  - hover 效果：向上浮动 2-4px + 增强阴影

- **按钮规范**：
  - 主要按钮：紫色渐变背景
  - 次要按钮：蓝色渐变背景
  - 危险按钮：粉红渐变背景
  - 所有按钮 hover 时：`transform: translateY(-2px)` + `box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2)`
  - 圆角：`6px`
  - 内边距：`10px 20px`

- **卡片规范**：
  - 背景：白色
  - 圆角：`12px`
  - 阴影：`0 4px 6px rgba(0, 0, 0, 0.1)`
  - 内边距：`24px`
  - hover 时：`transform: translateY(-4px)` + 增强阴影

- **色彩一致性**：
  - 链接颜色：`#667eea`（主题紫）
  - 链接 hover：`#764ba2`（深紫）
  - 激活状态：使用主题渐变
  - 边框 hover：`#667eea`

### 前端开发规范
- **Vue 3 模式**：
  - 使用 CDN 引入，无需构建步骤
  - 使用 Composition API 风格（`data()`, `computed`, `methods`）
  - 响应式数据使用 `v-model`, `v-for`, `v-if` 等指令
  - 事件处理使用 `@click`, `@change` 等语法

- **性能优化**：
  - 长列表必须实现分页，默认每页 20 条
  - 搜索功能使用防抖（debounce），延迟 500ms
  - 图片懒加载，避免一次性加载大量资源
  - 使用 computed 缓存计算结果

- **用户体验**：
  - 所有异步操作显示 loading 状态
  - 表单验证即时反馈
  - 操作成功/失败给出明确提示
  - 翻页后自动滚动到顶部 `window.scrollTo({ top: 0, behavior: 'smooth' })`
  - 键盘快捷键支持（如 Ctrl+F 聚焦搜索，Esc 重置）

### 功能实现流程
1. **需求分析**：理解用户需求，明确功能边界
2. **方案设计**：考虑多个实现方案，权衡利弊
3. **分步实施**：将复杂功能拆解为多个小步骤
4. **增量开发**：先实现核心功能，再逐步完善
5. **即时测试**：每完成一个模块立即测试验证
6. **风格统一**：确保新功能与现有风格一致
7. **文档更新**：重要功能变更同步更新文档

### 质量检查清单
- [ ] 代码符合项目命名规范（snake_case, PascalCase）
- [ ] 新增功能有对应的单元测试
- [ ] 前端样式与设计系统一致（颜色、圆角、阴影、动画）
- [ ] 按钮和卡片使用统一的 hover 效果
- [ ] 所有过渡动画使用 `0.3s` 时长
- [ ] 长列表实现了分页功能
- [ ] 搜索功能使用了防抖
- [ ] 异步操作有 loading 状态
- [ ] 错误处理不会中断用户流程
- [ ] API 返回使用 Pydantic 模型
- [ ] 代码有适当的注释和文档字符串

### Git 提交规范
- **提交信息格式**：
  ``
  <type>: <subject>
  
  <body>
  ``
  
- **Type 类型**：
  - `feat`: 新功能
  - `fix`: Bug 修复
  - `style`: 样式调整（UI/UX）
  - `refactor`: 重构代码
  - `perf`: 性能优化
  - `docs`: 文档更新
  - `test`: 测试相关
  - `chore`: 构建/工具链配置

- **提交内容**：
  - Subject：简明扼要说明变更（50字内）
  - Body：详细说明变更内容，使用列表格式
  - 包含变更的原因、实现方式、影响范围

### 错误处理原则
- **用户友好**：错误信息简洁明了，避免技术术语
- **不中断流程**：单个模块失败不影响整体功能
- **日志记录**：所有异常都要记录到日志，包含上下文信息
- **优雅降级**：服务不可用时提供备选方案或友好提示
- **重试机制**：网络请求失败时自动重试 2-3 次，使用指数退避

### 性能考虑
- **数据库查询**：
  - 使用索引优化常用查询字段
  - 避免 SELECT *，只查询需要的字段
  - 大量数据使用分页加载
  - 考虑使用缓存减少数据库压力

- **API 响应**：
  - 返回数据精简，避免冗余字段
  - 大文件使用流式传输
  - 适当使用 HTTP 缓存头

- **前端渲染**：
  - 长列表虚拟滚动或分页
  - 图片压缩和懒加载
  - 使用 CSS transform 而非 position 做动画
  - 防抖和节流控制高频事件

### 代码审查要点
- 命名是否清晰且符合规范
- 逻辑是否清晰易懂
- 是否有潜在的性能问题
- 错误处理是否完善
- 是否有安全隐患（SQL注入、XSS等）
- 是否有充分的测试覆盖
- UI 是否与设计系统一致
- 用户体验是否流畅
