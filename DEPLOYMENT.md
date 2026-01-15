# 🚀 部署检查清单

## 部署前检查

### 环境准备
- [ ] Python 3.10+ 已安装
- [ ] 虚拟环境已创建并激活
- [ ] 所有依赖已安装 (`pip install -r requirements.txt`)
- [ ] 配置文件 `config.yaml` 已创建

### 配置检查
- [ ] `DEEPSEEK_API_KEY` 环境变量已设置
- [ ] `server.host` 已设为 `0.0.0.0`（允许外部访问）
- [ ] `server.debug` 已设为 `false`
- [ ] `logging.level` 已调整为 `INFO` 或 `WARNING`
- [ ] CORS 配置已根据需要限制（`src/main.py` 中的 `allow_origins`）

### 目录权限
- [ ] `data/` 目录可写（SQLite 数据库）
- [ ] `logs/` 目录可写（日志文件）
- [ ] `reports/` 目录可写（HTML 日报）

### 安全性
- [ ] API Key 未硬编码在配置文件中
- [ ] 生产环境使用 HTTPS（建议使用 Nginx 反向代理）
- [ ] 防火墙规则已配置（仅开放必要端口）
- [ ] 敏感端口未对外暴露

## 部署方式选择

### 方式 1: 直接运行（简单）

```bash
# 设置环境变量
export DEEPSEEK_API_KEY="your-key"

# 启动服务
python src/main.py
```

**优点**：简单快速  
**缺点**：进程管理不便，不支持自动重启

---

### 方式 2: Systemd 服务（推荐 Linux）

创建 `/etc/systemd/system/cocoon-breaker.service`:

```ini
[Unit]
Description=Cocoon Breaker - AI Daily Report Service
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/cocoon-breaker
Environment="DEEPSEEK_API_KEY=your-key-here"
ExecStart=/path/to/.venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable cocoon-breaker
sudo systemctl start cocoon-breaker
sudo systemctl status cocoon-breaker
```

管理命令：
```bash
sudo systemctl stop cocoon-breaker     # 停止
sudo systemctl restart cocoon-breaker  # 重启
sudo journalctl -u cocoon-breaker -f   # 查看日志
```

**优点**：自动重启、日志管理、开机自启  
**缺点**：仅限 Linux

---

### 方式 3: Docker 容器（推荐）

创建 `Dockerfile`:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

# 创建必要目录
RUN mkdir -p data logs reports

# 环境变量占位符
ENV DEEPSEEK_API_KEY=""

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["python", "src/main.py"]
```

构建并运行：
```bash
# 构建镜像
docker build -t cocoon-breaker .

# 运行容器
docker run -d \
  --name cocoon-breaker \
  -p 8000:8000 \
  -e DEEPSEEK_API_KEY="your-key" \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/reports:/app/reports \
  --restart unless-stopped \
  cocoon-breaker
```

Docker Compose (`docker-compose.yml`):
```yaml
version: '3.8'

services:
  cocoon-breaker:
    build: .
    container_name: cocoon-breaker
    ports:
      - "8000:8000"
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./reports:/app/reports
      - ./config.yaml:/app/config.yaml
    restart: unless-stopped
```

启动：
```bash
docker-compose up -d
```

**优点**：隔离环境、易于迁移、跨平台  
**缺点**：需要 Docker 环境

---

### 方式 4: Nginx 反向代理（推荐生产环境）

Nginx 配置 (`/etc/nginx/sites-available/cocoon-breaker`):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重定向到 HTTPS（推荐）
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL 证书配置
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # 反向代理到 FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持（如需）
    location /ws {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置：
```bash
sudo ln -s /etc/nginx/sites-available/cocoon-breaker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**优点**：HTTPS、负载均衡、静态文件缓存  
**缺点**：配置复杂

---

## 部署后验证

### 功能测试
```bash
# 1. 健康检查
curl http://localhost:8000/api/health

# 2. 访问 Web 界面
http://your-domain.com/static/index.html

# 3. 查看 API 文档
http://your-domain.com/docs

# 4. 测试添加订阅
curl -X POST http://localhost:8000/api/subscriptions \
  -H "Content-Type: application/json" \
  -d '{"keyword":"测试"}'
```

### 性能测试
```bash
# 使用 ab (Apache Bench)
ab -n 1000 -c 10 http://localhost:8000/api/health

# 使用 wrk
wrk -t4 -c100 -d30s http://localhost:8000/api/health
```

### 日志监控
```bash
# 实时查看日志
tail -f logs/cocoon.log

# 查看错误日志
grep ERROR logs/cocoon.log

# 查看最近 100 行
tail -n 100 logs/cocoon.log
```

---

## 性能优化建议

### 1. 限制订阅数量
- 建议 ≤5 个主题
- 避免高频词（如"新闻"）

### 2. 调整爬虫配置
```yaml
crawler:
  max_results_per_keyword: 15  # 降低爬取数量
  request_interval: [2, 4]      # 增加间隔，避免被封
```

### 3. 数据库优化
- 定期清理旧文章（30 天以上）
- 考虑迁移到 PostgreSQL（高并发场景）

### 4. 缓存策略
- 使用 Redis 缓存 API 响应（可选）
- 静态文件使用 CDN 加速

---

## 故障排查

### 常见问题

**Q: 服务启动失败？**
```bash
# 检查端口占用
netstat -tuln | grep 8000
# 或
lsof -i :8000

# 查看详细错误
python src/main.py
```

**Q: 定时任务不执行？**
- 检查 `config.yaml` 中 `schedule.enabled` 是否为 `true`
- 查看日志文件确认调度器是否启动
- 确认系统时间正确

**Q: Deepseek API 调用失败？**
- 验证 API Key 是否正确
- 检查网络连接（可能需要代理）
- 查看 Deepseek 平台余额

**Q: 前端无法访问？**
- 确认静态文件目录存在 (`src/static/`)
- 检查 CORS 配置
- 浏览器控制台查看错误

---

## 监控与维护

### 日常维护
- 每周检查日志文件，清理无用日志
- 每月备份数据库 (`data/cocoon.db`)
- 关注 Deepseek API 用量和余额

### 监控指标
- API 响应时间
- 爬虫成功率
- 日报生成成功率
- 磁盘使用率

### 告警设置
- 磁盘空间 < 10%
- 日志文件错误率 > 5%
- API 连续失败 > 3 次

---

## 安全加固

1. **限制 API 访问**：添加 API Key 认证（可选）
2. **数据加密**：敏感配置使用加密存储
3. **定期更新**：及时更新依赖库修复漏洞
4. **备份策略**：定期备份数据库和配置

---

**部署完成后，建议保留此文档供运维参考。**
