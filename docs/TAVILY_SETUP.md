# Tavily API 集成说明

## 概述

Tavily 是一个专为 AI 应用设计的高级搜索 API，已集成到 Cocoon Breaker 作为新闻爬虫源。

## 配置步骤

### 1. 安装依赖

```bash
pip install tavily-python
```

或者更新所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置 config.yaml

在 `config.yaml` 中添加 Tavily 配置（如果没有该文件，先复制 `config.example.yaml`）：

```yaml
tavily:
  enabled: true              # 启用 Tavily 爬虫
  api_key: ${TAVILY_API_KEY}  # API Key（通过环境变量设置）
  search_depth: advanced     # 搜索深度：basic 或 advanced
  max_results: 20            # 每次搜索最大结果数
```

### 3. 设置 API Key

在环境变量中设置您的 Tavily API Key：

**Windows (PowerShell):**
```powershell
$env:TAVILY_API_KEY="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"
```

**Windows (CMD):**
```cmd
set TAVILY_API_KEY=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
```

**Linux/Mac:**
```bash
export TAVILY_API_KEY="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"
```

或者在 `.env` 文件中添加：
```
TAVILY_API_KEY=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
```

### 4. 启动服务

配置完成后重启服务：

```bash
python src/main.py
```

## 配置选项

### enabled
- **类型**：布尔值
- **默认**：`false`
- **说明**：是否启用 Tavily 爬虫。设为 `true` 后才会使用 Tavily API

### api_key
- **类型**：字符串
- **默认**：`""`
- **说明**：Tavily API Key。建议使用环境变量 `${TAVILY_API_KEY}` 而不是硬编码

### search_depth
- **类型**：字符串
- **可选值**：`basic` 或 `advanced`
- **默认**：`advanced`
- **说明**：
  - `basic`：快速搜索，返回基本结果
  - `advanced`：深度搜索，返回更详细和相关的结果（推荐）

### max_results
- **类型**：整数
- **默认**：`20`
- **说明**：每个关键词搜索时返回的最大结果数。注意 API 配额限制

## 特性

- **统一配置**：与其他爬虫源（Baidu、Yahoo、Google）使用相同的配置管理方式
- **灵活控制**：可通过 `enabled` 开关轻松启用/禁用
- **高级搜索**：支持 `advanced` 深度搜索获取更优质结果
- **容错处理**：API 失败不会影响其他爬虫源
- **环境变量支持**：API Key 通过环境变量安全存储

## 日志输出

启用成功时会在日志中看到：
```
[INFO] [src.scheduler.tasks] Tavily crawler enabled (depth=advanced)
```

未配置或禁用时会显示：
```
[INFO] [src.scheduler.tasks] Tavily crawler disabled (not enabled in config or API key not set)
```

## 数据库标识

Tavily 爬取的文章在数据库中的 `source` 字段为 `'tavily'`，便于区分来源。

## API 配额

请注意 Tavily API 的使用配额：
- 开发版 API Key 有每月请求限制
- 建议升级到付费版以获得更高配额
- 详情访问：https://tavily.com/pricing

## 故障排查

1. **导入错误**：确保已安装 `tavily-python` 包
2. **API Key 错误**：检查环境变量是否正确设置
3. **未启用**：确认 `config.yaml` 中 `tavily.enabled` 为 `true`
4. **请求失败**：查看日志中的详细错误信息
5. **结果为空**：确认 API Key 有效且未超出配额

## 示例配置

完整的 `config.yaml` 配置示例：

```yaml
# Google Custom Search API 配置（可选）
google:
  enabled: false
  api_key: ${GOOGLE_API_KEY}
  search_engine_id: ${GOOGLE_SEARCH_ENGINE_ID}

# Tavily API 配置（可选）
tavily:
  enabled: true              # 启用 Tavily
  api_key: ${TAVILY_API_KEY}
  search_depth: advanced     # 使用高级搜索
  max_results: 20            # 每次最多 20 条结果
```

## 相关文件

- `src/crawler/tavily.py` - Tavily 爬虫实现
- `src/scheduler/tasks.py` - 爬虫初始化和调度
- `src/config.py` - 配置管理
- `config.example.yaml` - 配置模板
- `requirements.txt` - 依赖配置
