# 🦋 Cocoon Breaker - AI 日报生成工具

打破信息茧房，解决信息过载问题的 AI 驱动日报工具。自动爬取订阅主题新闻，通过 Deepseek AI 筛选生成精选日报。

## ✨ 功能特性

- 🔍 **多源信息爬取**：百度 + Yahoo + Google API（可选） + Tavily API（可选） + 36氪 RSS + 虎嗅网 RSS
- 🔥 **新闻时效性优化**：时间过滤 + AI 时间优先级 + 混合评分系统（质量权重 0.7 + 时效权重 0.3）
- 🤖 **AI 智能筛选**：Deepseek 驱动的内容相关性与重要性分析
- 📊 **精美日报**：HTML 格式，1080x1440px 移动端友好设计
- ⏰ **定时自动化**：每日定时自动生成，schedule 调度器
- 🌐 **Web 管理界面**：Vue 3 CDN 单页应用，无需构建
- 📈 **完整 REST API**：11 个端点，支持订阅/日报/定时管理
- 💾 **轻量级存储**：SQLite 数据库，无需额外服务
- 🧪 **完善测试**：60+ 单元测试，覆盖核心模块

## 快速开始

### 环境要求

- Python 3.10+
- Windows/Linux/macOS

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/mzniu/cocoon-breaker.git
cd cocoon-breaker

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml（可选，使用默认配置即可）
```

### ⚠️ 配置 Deepseek API Key（必须）

> **重要提示**：未配置 API Key 将导致服务启动失败或功能异常（500 错误）

1. 访问 [Deepseek Platform](https://platform.deepseek.com/) 注册账号
2. 获取 API Key
3. **必须**设置环境变量：

**Windows PowerShell（每次启动终端需重新设置）：**
```powershell
# 将 sk-xxx 替换为你的真实 API Key
$env:DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**Linux/macOS（每次启动终端需重新设置）：**
```bash
# 将 sk-xxx 替换为你的真实 API Key
export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**持久化配置（强烈推荐，设置一次永久生效）：**
- **Windows**: 
  1. 搜索"环境变量" → "编辑系统环境变量"
  2. 点击"环境变量"按钮
  3. 在"用户变量"中新建变量：`DEEPSEEK_API_KEY`
  4. 重启终端或 VS Code
- **Linux/Mac**: 
  ```bash
  echo 'export DEEPSEEK_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"' >> ~/.bashrc
  source ~/.bashrc  # 或重启终端
  ```

**验证配置是否成功：**
```powershell
# Windows PowerShell
echo $env:DEEPSEEK_API_KEY

# Linux/macOS
echo $DEEPSEEK_API_KEY
```
应该输出你的 API Key，而不是空白

### 配置 Google 搜索（可选）

如果需要使用 Google 搜索获取更高质量的结果，可以配置 Google Custom Search API：

**1. 获取 API 凭据：**
- 访问 [Google Custom Search](https://developers.google.com/custom-search/v1/overview)
- 创建 API Key 和 Search Engine ID

**2. 设置环境变量：**
```powershell
# Windows PowerShell
$env:GOOGLE_API_KEY="your_api_key"
$env:GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"

# Linux/macOS
export GOOGLE_API_KEY="your_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"
```

**3. 启用 Google 搜索：**
编辑 `config.yaml`，设置：
```yaml
google:
  enabled: true  # 改为 true
```

**注意事项：**
- ✅ 免费额度：100 次/天
- ✅ 付费：$5/1000 次查询
- ✅ 国内可访问（无需代理）
- ✅ 结果质量最高

### 配置 Tavily 搜索（可选）

Tavily 是一个专为 AI 优化的搜索 API，支持深度搜索：

**1. 获取 API Key：**
- 访问 [Tavily AI](https://tavily.com/)
- 注册并获取 API Key

**2. 设置环境变量：**
```powershell
# Windows PowerShell
$env:TAVILY_API_KEY="tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# Linux/macOS
export TAVILY_API_KEY="tvly-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

**3. 启用 Tavily：**
编辑 `config.yaml`：
```yaml
tavily:
  enabled: true
  search_depth: advanced  # basic 或 advanced
```

### 运行服务

> **⚠️ 运行前检查**：确保已设置 `DEEPSEEK_API_KEY` 环境变量（见上方配置说明）

**开发模式（热重载）：**
```bash
uvicorn src.main:app --reload --port 8000
```

**生产模式：**
```bash
python src/main.py
```

> 💡 **启动失败？** 检查终端输出的错误信息，常见问题：
> - ❌ 未设置 API Key → 设置 `DEEPSEEK_API_KEY` 环境变量
> - ❌ 端口被占用 → 修改 `config.yaml` 中的 `server.port`
> - ❌ 依赖缺失 → 运行 `pip install -r requirements.txt`

**访问应用：**
- 🌐 Web 界面: http://localhost:8000/static/index.html
- 📚 API 文档: http://localhost:8000/docs
- 📖 ReDoc: http://localhost:8000/redoc
- 💚 健康检查: http://localhost:8000/api/health

### 使用流程

1. **添加订阅**：在 Web 界面添加感兴趣的主题（如"AI"、"Python"）
2. **手动生成**：点击"立即生成"按钮触发日报生成
3. **查看日报**：在日报列表中查看生成的 HTML 报告
4. **定时设置**：配置每日自动生成时间

## 📂 项目结构

```
cocoon-breaker/
├── src/                      # 源代码
│   ├── api/                  # REST API 路由
│   │   ├── subscriptions.py  # 订阅管理 (5 endpoints)
│   │   ├── reports.py        # 日报管理 (5 endpoints)
│   │   └── schedule.py       # 定时配置 (2 endpoints)
│   ├── crawler/              # 爬虫模块
│   │   ├── base.py           # 抽象基类
│   │   ├── baidu.py          # 百度搜索
│   │   ├── yahoo.py          # Yahoo 搜索
│   │   ├── google.py         # Google API
│   │   ├── tavily.py         # Tavily API
│   │   ├── kr36.py           # 36氪 RSS
│   │   └── huxiu.py          # 虎嗅网 RSS
│   ├── db/                   # 数据库层
│   │   ├── models.py         # 数据模型
│   │   ├── database.py       # 连接管理
│   │   └── repository.py     # CRUD 操作
│   ├── ai/                   # AI 集成
│   │   └── deepseek.py       # Deepseek 客户端
│   ├── report/               # 日报生成
│   │   └── generator.py      # HTML 生成器
│   ├── scheduler/            # 定时任务
│   │   └── tasks.py          # Schedule 调度器
│   ├── static/               # 前端静态文件
│   │   ├── index.html        # Vue 3 单页应用
│   │   ├── css/style.css     # 样式
│   │   └── js/app.js         # 应用逻辑
│   ├── config.py             # 配置管理
│   └── main.py               # FastAPI 入口
├── templates/                # HTML 模板
│   └── report.html           # 日报模板（LLM 参考）
├── tests/ut/                 # 单元测试（60+ 用例）
├── reports/                  # 生成的日报输出
├── data/                     # SQLite 数据库
├── logs/                     # 日志文件
├── config.yaml               # 用户配置
├── config.example.yaml       # 配置模板
└── requirements.txt          # Python 依赖
```

## 🔌 API 端点

### 订阅管理
- `GET /api/subscriptions` - 获取所有订阅
- `POST /api/subscriptions` - 创建订阅
- `DELETE /api/subscriptions/{id}` - 删除订阅
- `PATCH /api/subscriptions/{id}/enabled` - 启用/禁用订阅

### 日报管理
- `GET /api/reports` - 获取日报列表
- `GET /api/reports/{id}` - 获取日报详情
- `GET /api/reports/{id}/download` - 下载日报
- `GET /api/reports/keyword/{keyword}/{date}` - 按主题和日期查询
- `POST /api/reports/generate` - 手动触发生成

### 定时配置
- `GET /api/schedule` - 获取定时配置
- `PUT /api/schedule` - 更新定时配置

## 🧪 开发

### 运行测试

```bash
# 运行所有测试
pytest tests/ut/ -v

# 带覆盖率报告
pytest tests/ut/ -v --cov=src --cov-report=html

# 测试特定模块
pytest tests/ut/test_crawler/ -v
pytest tests/ut/test_api/ -v
```

### 代码风格

- **命名规范**：snake_case（文件/函数/变量）、PascalCase（类）
- **类型提示**：使用 Python 3.10+ 类型注解
- **文档字符串**：Google 风格 docstrings
- **日志**：使用 `logging` 模块，格式化输出

### 添加新的信息源

1. 在 `src/crawler/` 创建新爬虫类继承 `BaseCrawler`
2. 实现 `crawl(keyword, max_results)` 方法
3. 在 `config.yaml` 的 `crawler.sources` 添加配置
4. 编写单元测试

## 🚀 部署

### 生产环境配置检查

- ✅ 设置 `DEEPSEEK_API_KEY` 环境变量
- ✅ 修改 `config.yaml` 中的 `server.host` 为 `0.0.0.0`
- ✅ 调整 `logging.level` 为 `INFO` 或 `WARNING`
- ✅ 配置 CORS 允许的源（`main.py` 中的 `allow_origins`）
- ✅ 确保 `data/`、`logs/`、`reports/` 目录有写权限

### 使用 Systemd（Linux）

创建 `/etc/systemd/system/cocoon-breaker.service`:

```ini
[Unit]
Description=Cocoon Breaker Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/cocoon-breaker
Environment="DEEPSEEK_API_KEY=your-key"
ExecStart=/path/to/.venv/bin/python src/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable cocoon-breaker
sudo systemctl start cocoon-breaker
```

### Docker 部署（可选）

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV DEEPSEEK_API_KEY=""
EXPOSE 8000
CMD ["python", "src/main.py"]
```

## 📝 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## ⚠️ 注意事项

- **API 限流**：Deepseek API 有调用频率限制，请合理设置订阅数量
- **爬虫礼仪**：请求间隔 1-3 秒，避免过于频繁访问
- **数据存储**：SQLite 适合单机部署，大规模使用请考虑 PostgreSQL
- **安全性**：生产环境请使用 HTTPS，配置防火墙规则

## 🆕 新增功能

### 🔥 新闻时效性优化

针对“信息茧房”问题，新增三层时效性优化：

**1. 时间过滤配置**
```yaml
report:
  time_range_hours: 24  # 只选择最近24小时的新闻（0=不限制）
```

**2. AI 时间优先级**
- AI 提示词自动强调时效性
- 爬取时间作为上下文传递给 AI
- 同等质量下优先选择更新的内容

**3. 混合评分系统**
```yaml
report:
  quality_weight: 0.7        # 内容质量权重
  freshness_weight: 0.3      # 时效权重
  time_decay_lambda: 0.1     # 时间衰减系数
```

评分公式：`最终得分 = 质量权重 × 质量分 + 时效权重 × e^(-λ × 小时数)`

时间衰减示例（λ=0.1）：
- 1小时前：90%新鲜度
- 6小时前：55%新鲜度
- 12小时前：30%新鲜度
- 24小时前：9%新鲜度

详细文档：[docs/NEWS_FRESHNESS_FEATURE.md](docs/NEWS_FRESHNESS_FEATURE.md)

### 🆕 新增信息源

**36氪 (36Kr)**
- 科技创业、商业资讯
- RSS: https://36kr.com/feed
- 原创深度分析，行业洞察

**虎嗅网 (Huxiu)**
- 商业科技深度报道
- RSS: https://www.huxiu.com/rss/0.xml
- 独立观点，商业洞察力强

**Tavily API**
- 专为 AI 优化的搜索 API
- 支持 advanced 深度搜索
- 适合全网智能搜索

配置示例：
```yaml
kr36:
  enabled: true
  max_results: 20

huxiu:
  enabled: true
  max_results: 20

tavily:
  enabled: true
  api_key: ${TAVILY_API_KEY}
  search_depth: advanced
```

详细文档：
- [docs/36KR_THEPAPER_INTEGRATION.md](docs/36KR_THEPAPER_INTEGRATION.md)
- [docs/TAVILY_SETUP.md](docs/TAVILY_SETUP.md)

## ⚠️ 使用注意

- **API 限流**：Deepseek API 有调用频率限制，请合理设置订阅数量
- **爬虫礼仪**：请求间隔 1-3 秒，避免过于频繁访问
- **数据存储**：SQLite 适合单机部署，大规模使用请考虑 PostgreSQL
- **安全性**：生产环境请使用 HTTPS，配置防火墙规则

## 📞 联系方式

- 项目主页: [GitHub](https://github.com/mzniu/cocoon-breaker)
- 问题反馈: [Issues](https://github.com/mzniu/cocoon-breaker/issues)
- 邮箱: aindy.niu@gmail.com


