# AI 日报生成工具 Cocoon Breaker - MVP 版 PRD

## 1. 产品目标

解决用户"信息茧房"和"信息杂乱"问题，通过订阅主题自动抓取、筛选并生成每日重要信息报告。

### 目标用户
- 需要跟踪特定领域信息的专业人士
- 关注多个主题但时间有限的用户
- 希望突破信息茧房、获取多元化信息的用户

### 核心价值
- **省时高效**：自动化信息收集，每日仅需 5 分钟了解关键内容
- **精准筛选**：AI 驱动的内容筛选，过滤噪音信息
- **打破茧房**：多源信息聚合，避免算法推荐的单一视角

## 2. 核心功能模块

### 2.1 用户订阅主题

**功能描述**  
用户输入 1-3 个核心关键词作为订阅主题。

**交互设计**
- 主题输入框支持多个关键词，逗号分隔
- 显示当前已订阅主题列表
- 支持主题的增删改

**验收标准**
- 系统准确识别关键词并用于后续信息筛选
- 关键词持久化存储，重启后不丢失
- 输入验证：拒绝空白或超长关键词

### 2.2 信息爬取与存储

**功能描述**  
每日按用户设定时间，从搜索引擎爬取订阅主题 24 小时内的相关信息，存入本地 SQLite 数据库。

**技术实现**
- 爬虫框架：`requests` + `BeautifulSoup4`（轻量级，满足 MVP 需求）
- 搜索源（MVP 阶段）：
  - 百度新闻搜索（网页爬取）
  - 必应搜索（国内可直接访问，作为备选）
- 后续扩展：RSS Feed、知乎、微博等
- 数据清洗：去重、去除无效链接、提取正文

**数据模型（SQLite）**
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    content TEXT,
    source TEXT,  -- 百度/谷歌
    keyword TEXT,  -- 关联的订阅主题
    crawled_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    published_at DATETIME
);
```

**验收标准**
- 单条信息包含标题、链接、内容摘要、来源、抓取时间
- 存储成功率 ≥ 90%（考虑网络波动和反爬限制）
- 去重机制：URL 唯一性约束
- 异常处理：爬取失败时记录日志并重试，不中断整体流程

### 2.3 日报生成与定时发送

**功能描述**  
大语言模型根据订阅主题从当日爬取信息中筛选 5-7 条重要内容，生成含标题和核心摘要的日报，按用户设定时间推送。

**AI 筛选策略**
- 使用 Deepseek API 分析内容相关性（性价比高，中文能力强）
- 评分维度：
  - 与订阅主题的相关性（权重 50%）
  - 信息重要性和新颖度（权重 30%）
  - 内容质量和可读性（权重 20%）
- 去除重复或高度相似内容

**日报格式**

日报输出为 HTML 文件，支持直接在浏览器中查看，也可生成图片分享。采用 **LLM 直接生成 HTML** 方案，通过 Prompt 指导 Deepseek 生成符合模板结构的完整 HTML。

**页面布局**：
- 页面尺寸：1080px × 1440px+（移动端友好）
- 主题色：#e60012（红色）
- 字体：微软雅黑/SimHei

**模板结构**：
```
┌────────────────────────────────────────────────┐
│  🔴 AI 信息差                    2026-01-13  │  <- header
│  关键字：[人工智能] [大模型] [AGI]     [星期一]  │
├────────────────────────────────────────────────┤
│  ❗ 省流版必读：XXX重大突破，YYY正式发布！    │  <- today-must-read
├────────────────────────────────────────────────┤
│  1. 🔴 [新闻标题] [来源]                    │  <- info-list
│     新闻摘要内容，支持<span class="highlight">高亮</span> │
│                                                │
│  2. 🟡 [新闻标题] [来源]                    │
│     新闻摘要内容...                           │
│                                                │
│  ...(共 5-7 条)                               │
│                                                │
│  ┌──────────────────────────────────────────┐  │
│  │           @小牛聊AI                     │  │  <- footer-banner
│  └──────────────────────────────────────────┘  │
└────────────────────────────────────────────────┘
```

**重要度标记**：
- 🔴 高优先级（重大突破/紧急事件）
- 🟡 中优先级（值得关注）
- 🟢 一般优先级

**LLM 生成策略**：
1. 提供完整 HTML 模板作为 Prompt 示例
2. 传入筛选后的新闻列表（标题、摘要、来源、重要度）
3. Deepseek 直接输出完整 HTML 文件
4. 保存到 `reports/{keyword}_{date}.html`

**输出方式（MVP 阶段）**
- 生成 HTML 文件到 `reports/` 目录
- Web 页面内嵌 iframe 预览
- 支持下载 HTML 文件

**验收标准**
- 日报包含 5-7 条与主题相关的内容
- 定时任务触发误差 ≤ 5 分钟
- HTML 页面在浏览器中渲染正常，布局符合模板规范
- 生成失败时记录错误日志，不影响下次执行

## 3. 非功能需求

### 技术栈

**后端**
- **开发语言**：Python 3.10+
- **Web 框架**：FastAPI（自带 API 文档，异步支持好）
- **数据库**：SQLite（轻量级，无需额外部署）
- **定时任务**：`schedule` 库（简单易用，满足 MVP 需求）
- **网页爬取**：`requests` + `BeautifulSoup4`
- **AI 集成**：Deepseek API
  - 优势：价格低廉、中文能力强、响应速度快
  - API 文档：https://platform.deepseek.com/

**前端**
- **框架**：Vue 3（CDN 引入，无需构建工具）
- **UI 组件**：原生 CSS 或 TailwindCSS（CDN）
- **HTTP 请求**：Axios
- **部署**：FastAPI 静态文件托管（单体部署）

### 性能要求
- 单次爬取时间 ≤ 5 分钟（3 个主题，每个主题 20 条结果）
- 日报生成时间 ≤ 2 分钟
- 数据库查询响应时间 ≤ 100ms

### 可靠性
- 爬虫遇到反爬时自动重试 3 次，间隔递增（1s, 3s, 5s）
- AI API 调用失败时降级为关键词匹配筛选
- 日志记录所有关键操作和异常

### 安全性
- API Key 通过环境变量或配置文件管理，不提交到代码库
- 用户数据（订阅主题）本地存储，不上传云端

### 扩展性（后续版本考虑）
- 支持更多信息源（Twitter、Reddit、RSS）
- 多用户管理
- Web 界面或移动端 App
- 自定义日报模板

## 4. 用户界面（前后端分离）

### 4.1 系统架构

```
┌─────────────────┐     HTTP/JSON      ┌─────────────────┐
│                 │  ◄──────────────►  │                 │
│   Vue 3 前端    │                    │  FastAPI 后端   │
│   (静态页面)    │                    │   (REST API)    │
│                 │                    │                 │
└─────────────────┘                    └────────┬────────┘
                                                │
                                       ┌────────▼────────┐
                                       │     SQLite      │
                                       │   + Deepseek    │
                                       └─────────────────┘
```

### 4.2 Web 页面设计

**主页面布局**
```
┌────────────────────────────────────────────────────────┐
│  🥚 Cocoon Breaker                        [立即生成]   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  订阅主题管理                                          │
│  ┌──────────────────────────────────┐  ┌──────────┐   │
│  │ 输入关键词，如：人工智能          │  │  + 添加  │   │
│  └──────────────────────────────────┘  └──────────┘   │
│                                                        │
│  当前订阅：                                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐        │
│  │ 人工智能 ✕ │ │ 大模型  ✕  │ │ AGI    ✕   │        │
│  └────────────┘ └────────────┘ └────────────┘        │
│                                                        │
├────────────────────────────────────────────────────────┤
│  定时设置                                              │
│  每日生成时间：[08:00 ▼]                              │
│                                                        │
├────────────────────────────────────────────────────────┤
│  历史日报                                              │
│  ┌─────────────────────────────────────────────────┐  │
│  │ 📄 2026-01-13 人工智能日报          [查看] [下载]│  │
│  │ 📄 2026-01-12 人工智能日报          [查看] [下载]│  │
│  │ 📄 2026-01-11 大模型日报            [查看] [下载]│  │
│  └─────────────────────────────────────────────────┘  │
│                                                        │
└────────────────────────────────────────────────────────┘
```

**功能说明**
- 订阅主题：支持添加/删除关键词，最多 5 个
- 定时设置：下拉选择每日生成时间
- 立即生成：手动触发日报生成（显示加载状态）
- 历史日报：列表展示，支持在线查看和下载 Markdown

### 4.3 REST API 设计

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/subscriptions` | 获取所有订阅主题 |
| POST | `/api/subscriptions` | 添加订阅主题 |
| DELETE | `/api/subscriptions/{id}` | 删除订阅主题 |
| GET | `/api/schedule` | 获取定时设置 |
| PUT | `/api/schedule` | 更新定时设置 |
| POST | `/api/generate` | 立即生成日报 |
| GET | `/api/reports` | 获取历史日报列表 |
| GET | `/api/reports/{id}` | 获取日报详情 |
| GET | `/api/reports/{id}/download` | 下载日报 Markdown |

**请求/响应示例**
```json
// POST /api/subscriptions
// Request
{ "keyword": "人工智能" }

// Response
{ "id": 1, "keyword": "人工智能", "created_at": "2026-01-13T10:00:00" }

// GET /api/reports
// Response
{
  "reports": [
    { "id": 1, "keyword": "人工智能", "date": "2026-01-13", "article_count": 6 },
    { "id": 2, "keyword": "大模型", "date": "2026-01-12", "article_count": 5 }
  ]
}
```

### 4.4 配置文件
```yaml
# config.yaml
server:
  host: 127.0.0.1
  port: 8000

subscriptions:
  max_keywords: 5  # 最大订阅数
  
schedule:
  default_time: "08:00"
  
output:
  format: html
  directory: ./reports
  template: ./templates/report.html  # HTML模板文件
  
llm:
  provider: deepseek
  api_key: ${DEEPSEEK_API_KEY}
  model: deepseek-reasoner
  base_url: https://api.deepseek.com

crawler:
  sources: ["baidu", "bing"]
  request_interval: [1, 3]  # 随机间隔秒数
  max_results_per_keyword: 20
```

## 5. MVP 开发计划

### Phase 1：后端基础（1 周）

#### 1.1 项目初始化
- [ ] 创建目录结构（src/, tests/ut/, data/, logs/, reports/）
- [ ] 创建 requirements.txt（fastapi, uvicorn, requests, beautifulsoup4, schedule, pyyaml, pytest）
- [ ] 创建 config.example.yaml 配置模板
- [ ] **测试**：tests/ut/test_config.py - 配置加载测试

#### 1.2 配置模块
- [ ] 实现 src/config.py - YAML 加载 + 环境变量覆盖
- [ ] 支持 ${VAR} 格式的环境变量替换
- [ ] **测试**：配置文件解析、环境变量覆盖、默认值处理

#### 1.3 数据库模块
- [ ] 实现 src/db/database.py - SQLite 连接管理
- [ ] 实现 src/db/models.py - Article, Subscription, Report 数据模型
- [ ] 实现 src/db/repository.py - CRUD 操作（INSERT OR IGNORE 去重）
- [ ] 创建数据库初始化脚本
- [ ] **测试**：tests/ut/test_db/test_repository.py - 增删改查、去重逻辑

#### 1.4 FastAPI 基础框架
- [ ] 实现 src/main.py - FastAPI 应用入口
- [ ] 配置 CORS、静态文件托管
- [ ] 实现健康检查端点 GET /api/health
- [ ] 配置日志系统（logging 模块）
- [ ] **测试**：tests/ut/test_api/test_health.py - 健康检查接口

---

### Phase 2：核心功能（1 周）

#### 2.1 爬虫模块
- [ ] 实现 src/crawler/base.py - 爬虫基类（统一接口）
- [ ] 实现 src/crawler/baidu.py - 百度新闻爬取
- [ ] 实现 src/crawler/bing.py - 必应搜索爬取
- [ ] User-Agent 轮换、请求间隔随机化
- [ ] **测试**：tests/ut/test_crawler/test_baidu.py, test_bing.py - Mock 网页响应测试

#### 2.2 Deepseek AI 集成
- [ ] 实现 src/ai/deepseek.py - API 调用封装
- [ ] 实现内容筛选 Prompt（相关性、重要性评分）
- [ ] 实现摘要生成 Prompt
- [ ] 错误处理：超时重试 3 次
- [ ] **测试**：tests/ut/test_ai/test_deepseek.py - Mock API 响应测试

#### 2.3 日报生成模块
- [ ] 实现 src/report/generator.py - Markdown 模板生成
- [ ] 支持日报格式：标题、核心摘要、精选内容列表
- [ ] 文件输出到 reports/ 目录
- [ ] **测试**：tests/ut/test_report/test_generator.py - 模板渲染测试

#### 2.4 定时任务模块
- [ ] 实现 src/scheduler/tasks.py - schedule 任务定义
- [ ] 实现完整流程：爬取 → 筛选 → 生成日报
- [ ] 后台线程运行定时任务
- [ ] **测试**：tests/ut/test_scheduler/test_tasks.py - 任务调度测试

---

### Phase 3：前端开发（1 周）

#### 3.1 订阅管理 API
- [ ] 实现 src/api/subscriptions.py
  - GET /api/subscriptions - 获取列表
  - POST /api/subscriptions - 添加订阅
  - DELETE /api/subscriptions/{id} - 删除订阅
- [ ] Pydantic 请求/响应模型
- [ ] **测试**：tests/ut/test_api/test_subscriptions.py

#### 3.2 日报管理 API
- [ ] 实现 src/api/reports.py
  - GET /api/reports - 获取历史列表
  - GET /api/reports/{id} - 获取详情
  - GET /api/reports/{id}/download - 下载 Markdown
  - POST /api/generate - 立即生成日报
- [ ] **测试**：tests/ut/test_api/test_reports.py

#### 3.3 定时设置 API
- [ ] 实现 src/api/schedule.py
  - GET /api/schedule - 获取当前设置
  - PUT /api/schedule - 更新定时时间
- [ ] **测试**：tests/ut/test_api/test_schedule.py

#### 3.4 前端页面
- [ ] 创建 src/static/index.html - Vue 3 单页应用
- [ ] 创建 src/static/js/app.js - Vue 组件和逻辑
- [ ] 创建 src/static/css/style.css - 样式
- [ ] 实现订阅管理界面（添加/删除关键词）
- [ ] 实现日报列表和查看界面
- [ ] 实现定时设置界面
- [ ] **测试**：手动测试 + API 集成测试

---

### Phase 4：测试上线（0.5 周）

#### 4.1 集成测试
- [ ] 端到端流程测试（爬取 → AI 筛选 → 生成 → 展示）
- [ ] 异常场景测试（网络失败、API 超时）
- [ ] 并发请求测试

#### 4.2 文档完善
- [ ] 编写 README.md（安装、配置、运行说明）
- [ ] 更新 config.example.yaml 注释
- [ ] API 文档检查（Swagger UI）

#### 4.3 部署准备
- [ ] 生产环境配置检查
- [ ] 日志级别调整
- [ ] 性能验证（单次流程 ≤ 10 分钟）

## 6. 潜在风险与应对

| 风险 | 影响 | 应对策略 |
|------|------|----------|
| 搜索平台反爬虫 | 高 | User-Agent 轮换、请求间隔随机化、失败重试机制 |
| Deepseek API 不可用 | 中 | 本地缓存最近成功的日报，API 异常时跳过本次生成 |
| 信息质量不佳 | 中 | 优化 Prompt 提示词，增加筛选条件 |
| 用户数据隐私 | 低 | 所有数据本地存储，API Key 通过环境变量管理 |

## 7. 成功指标（MVP）

- **功能完整性**：三大核心模块全部可用
- **系统稳定性**：连续运行 7 天，日报生成成功率 ≥ 90%
- **性能达标**：单次完整流程（爬取+生成）≤ 10 分钟
- **可维护性**：代码有基本注释，README 可指导他人运行

---

**文档版本**：v1.0  
**创建日期**：2026-01-13  
**负责人**：[待填写]  
**最后更新**：2026-01-13
