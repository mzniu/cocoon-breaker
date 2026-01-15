# 新闻时效性优化功能

## 概述

实现了三个层次的新闻时效性优化方案，确保日报能够选择最新、最相关的新闻内容。

## 实现方案

### 方案1：时间过滤配置

**配置文件**：`config.yaml` 和 `config.example.yaml`

```yaml
report:
  time_range_hours: 24  # 时间范围（小时），0表示不限制
  quality_weight: 0.7    # 质量权重
  freshness_weight: 0.3  # 时效性权重
  time_decay_lambda: 0.1 # 时间衰减参数
```

**配置类**：`src/config.py`

- 添加了 `ReportConfig` 数据类，包含4个参数
- 在 `Config` 类中集成了 `report` 配置对象

**使用说明**：
- `time_range_hours=24`：只选择最近24小时的新闻
- `time_range_hours=0`：不限制时间范围，获取所有新闻

### 方案2：AI提示词优化

**文件**：`src/ai/deepseek.py`

**修改内容**：

1. 在文章列表中添加爬取时间信息：
```python
f"[{idx}] 标题：{article.title}\n内容：{article.content[:500]}\n来源：{article.source}\n爬取时间：{article.crawled_at.strftime('%Y-%m-%d %H:%M:%S')}"
```

2. 在提示词中新增时间优先级要求：
- 第6条：**优先选择爬取时间最近的新闻，在同等质量和重要性的情况下，选择更新的内容。**
- 第7条：**按照新闻重要性和时效性综合排序，时效性越强的新闻优先级越高。**

3. 在注意事项中强调：
- 新闻的时效性非常重要，爬取时间越晚的新闻说明发布越新，应该优先考虑。

### 方案4：混合评分系统

**文件**：`src/db/repository.py`

**新增方法**：`get_by_keyword_with_scoring()`

**评分公式**：

```
final_score = quality_weight × quality_score + freshness_weight × freshness_score

其中：
- quality_score = min(1.0, content_length / 1000)
  - 基于内容长度的质量评分
  - 知名来源（baidu、bing、google、tavily）获得1.2倍加成
  
- freshness_score = e^(-lambda × hours_old)
  - 指数时间衰减函数
  - hours_old = 从爬取时间到现在的小时数
  - lambda = time_decay_lambda（默认0.1）
```

**参数说明**：

- `quality_weight`（默认0.7）：质量得分的权重
- `freshness_weight`（默认0.3）：时效性得分的权重
- `time_decay_lambda`（默认0.1）：时间衰减速率
  - 值越大，时间惩罚越严重
  - 例如：lambda=0.1时，24小时前的新闻freshness_score约为0.09

**使用示例**：

```python
# Lambda = 0.1 的时间衰减示例
1小时前：e^(-0.1×1) ≈ 0.90（90%新鲜度）
6小时前：e^(-0.1×6) ≈ 0.55（55%新鲜度）
12小时前：e^(-0.1×12) ≈ 0.30（30%新鲜度）
24小时前：e^(-0.1×24) ≈ 0.09（9%新鲜度）
```

### 集成应用

**文件**：`src/scheduler/tasks.py`

**修改内容**：

将原来的简单时间过滤改为混合评分系统：

```python
# 使用混合评分获取文章
recent_articles = await self.article_repo.get_by_keyword_with_scoring(
    keyword,
    hours=time_range,
    quality_weight=self.config.report.quality_weight,
    freshness_weight=self.config.report.freshness_weight,
    time_decay_lambda=self.config.report.time_decay_lambda
)
```

**优势**：
- 自动平衡内容质量和时效性
- 通过配置文件灵活调整权重
- 自动对文章排序，无需手动处理

## 使用指南

### 配置调整建议

**场景1：强调时效性（新闻类）**
```yaml
report:
  time_range_hours: 12
  quality_weight: 0.5
  freshness_weight: 0.5
  time_decay_lambda: 0.15
```

**场景2：平衡质量和时效（默认）**
```yaml
report:
  time_range_hours: 24
  quality_weight: 0.7
  freshness_weight: 0.3
  time_decay_lambda: 0.1
```

**场景3：强调质量（深度分析）**
```yaml
report:
  time_range_hours: 0  # 不限制时间
  quality_weight: 0.9
  freshness_weight: 0.1
  time_decay_lambda: 0.05
```

## 技术细节

### 评分算法工作流程

1. **获取候选文章**：
   - 如果 `time_range_hours > 0`，使用时间过滤
   - 否则获取所有文章
   - 获取数量为 `limit × 2`，留出排序余地

2. **计算质量得分**：
   - 基准分 = min(1.0, 内容长度 / 1000)
   - 知名来源加成 × 1.2
   - 归一化到 [0, 1]

3. **计算时效得分**：
   - 计算文章年龄（小时）
   - 应用指数衰减：e^(-lambda × hours)
   - 自动归一化到 [0, 1]

4. **计算最终得分**：
   - 加权求和
   - 按得分降序排序
   - 返回前 `limit` 个结果

### AI处理流程

1. **数据库预筛选**：混合评分系统提供初步排序
2. **AI深度分析**：Deepseek API 根据提示词进行内容质量和时效性综合判断
3. **最终输出**：生成包含最新、最相关新闻的HTML日报

## 测试建议

### 测试参数组合

```python
# 测试1：极端时效性（1小时内新闻）
time_range_hours=1, quality_weight=0.3, freshness_weight=0.7, lambda=0.2

# 测试2：中等时效性（24小时）
time_range_hours=24, quality_weight=0.7, freshness_weight=0.3, lambda=0.1

# 测试3：无时间限制
time_range_hours=0, quality_weight=0.8, freshness_weight=0.2, lambda=0.05
```

### 验证方法

1. 查看日志输出：
```
Found X articles within Y hours for keyword (scored)
```

2. 检查日报时间戳：文章应该按时效性和质量综合排序

3. 调整lambda值观察衰减效果

## 注意事项

1. **权重归一化**：`quality_weight + freshness_weight` 无需等于1，系统会自动加权
2. **Lambda参数**：建议范围 0.05-0.2，过大会导致旧新闻完全被排除
3. **时间范围**：`time_range_hours=0` 时仍会应用时间衰减函数
4. **候选数量**：系统获取 `limit × 2` 个候选，确保排序后有足够结果

## 未来优化方向

1. 基于用户反馈的质量得分动态调整
2. 不同来源的差异化质量权重
3. 基于阅读量的内容流行度评分
4. 个性化的lambda参数（不同主题不同衰减速率）
