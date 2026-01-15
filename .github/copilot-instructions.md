# Copilot Instructions for Cocoon Breaker

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
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置加载（YAML + 环境变量）
│   ├── api/                  # REST API 路由
│   │   ├── __init__.py
│   │   ├── subscriptions.py  # 订阅管理 API
│   │   ├── reports.py        # 日报 API
│   │   └── schedule.py       # 定时设置 API
│   ├── crawler/              # 爬虫模块
│   │   ├── __init__.py
│   │   ├── base.py           # 爬虫基类
│   │   ├── baidu.py          # 百度新闻爬取
│   │   └── bing.py           # 必应搜索爬取
│   ├── db/                   # 数据库模块
│   │   ├── __init__.py
│   │   ├── database.py       # SQLite 连接管理
│   │   ├── models.py         # 数据模型（dataclass）
│   │   └── repository.py     # CRUD 操作
│   ├── ai/                   # AI 集成
│   │   ├── __init__.py
│   │   └── deepseek.py       # Deepseek API 调用
│   ├── report/               # 日报生成
│   │   ├── __init__.py
│   │   └── generator.py      # HTML 日报生成器
│   ├── scheduler/            # 定时任务
│   │   ├── __init__.py
│   │   └── tasks.py          # schedule 任务定义
│   └── static/               # 前端静态文件
│       ├── index.html        # Vue 3 单页应用
│       ├── css/
│       │   └── style.css
│       └── js/
│           └── app.js        # Vue 应用逻辑
├── templates/
│   └── report.html           # 日报 HTML 模板（LLM 参考）
├── tests/
│   └── ut/                   # 单元测试目录
│       ├── __init__.py
│       ├── test_config.py
│       ├── test_crawler/
│       │   ├── test_baidu.py
│       │   └── test_bing.py
│       ├── test_db/
│       │   └── test_repository.py
│       ├── test_ai/
│       │   └── test_deepseek.py
│       ├── test_report/
│       │   └── test_generator.py
│       └── test_api/
│           ├── test_subscriptions.py
│           ├── test_reports.py
│           └── test_schedule.py
├── config.yaml               # 用户配置文件
├── config.example.yaml       # 配置模板
├── reports/                  # 生成的日报输出目录（HTML文件）
├── data/                     # SQLite 数据库文件
├── logs/                     # 日志文件
└── requirements.txt          # Python 依赖
```

**模块职责**：
- `api/`：REST API 路由，处理 HTTP 请求
- `crawler/`：网页爬取，返回标准化的文章列表
- `db/`：数据持久化，文章去重
- `ai/`：调用 Deepseek 筛选和摘要
- `report/`：Markdown 格式日报生成
- `scheduler/`：定时任务管理
- `static/`：Vue 3 前端页面

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
- **配置**：YAML 文件 + 环境变量覆盖，敏感信息（API Key）仅用环境变量
- **日志**：使用 `logging` 模块，格式 `[时间] [级别] [模块] 消息`
- **错误处理**：爬虫/API 失败不中断流程，记录日志后继续
- **数据模型**：使用 dataclass 定义，与 SQLite 表对应
- **API 响应**：统一使用 Pydantic 模型，返回 JSON

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

### Deepseek API
- 文档：https://platform.deepseek.com/
- 模型：`deepseek-reasoner`
- 认证：Bearer Token（环境变量 `DEEPSEEK_API_KEY`）
- 错误处理：超时重试 3 次，失败后跳过本次生成

### 爬虫注意事项
- 请求间隔：随机 1-3 秒
- User-Agent：轮换常见浏览器 UA
- 反爬失败：记录日志，返回空列表不抛异常

## Common Tasks

### 添加新的信息源
1. 在 `src/crawler/` 下创建新模块（如 `zhihu.py`）
2. 继承 `BaseCrawler` 基类，实现 `crawl(keyword: str) -> List[Article]`
3. 在 `config.yaml` 的 `crawler.sources` 中添加
4. 在 `tests/ut/test_crawler/` 下编写单元测试

### 添加新的 API 端点
1. 在 `src/api/` 下创建或修改路由模块
2. 使用 Pydantic 定义请求/响应模型
3. 在 `src/main.py` 中注册路由
4. 在 `tests/ut/test_api/` 下编写测试

### 修改日报格式
1. 编辑 `templates/report.html` 中的 HTML/CSS 模板
2. 修改 `src/report/generator.py` 中的 LLM Prompt
3. 日报格式为 HTML，支持浏览器直接查看
4. 更新对应的单元测试

## Notes for AI Agents

- **不要修改** `config.yaml` 中的 API Key 占位符，保持 `${DEEPSEEK_API_KEY}` 格式
- **爬虫模块**返回空列表而非抛异常，保证流程健壮性
- **SQLite** 使用 `url` 字段唯一约束去重，插入时用 `INSERT OR IGNORE`
- 日报文件名格式：`{keyword}_{YYYY-MM-DD}.html`
- **FastAPI** 路由使用 `APIRouter`，在 `main.py` 中统一注册
- **前端** Vue 3 通过 CDN 引入，无需 npm 构建
- 优先使用标准库，第三方依赖限于：`fastapi`, `uvicorn`, `requests`, `beautifulsoup4`, `schedule`, `pyyaml`
- **每个模块必须有对应的单元测试**，测试文件放在 `tests/ut/` 对应子目录
- **日报生成**：通过 Deepseek 直接生成完整 HTML，参考 `templates/report.html` 模板

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
