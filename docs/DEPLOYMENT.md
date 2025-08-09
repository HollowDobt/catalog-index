# 部署指南

## 环境要求

### 系统要求

- **操作系统**: Linux/macOS/Windows
- **Python版本**: 3.8 或更高版本
- **内存**: 最少 4GB RAM，推荐 8GB+
- **存储**: 最少 10GB 可用空间
- **网络**: 稳定的互联网连接

### 软件依赖

- **Git**: 用于代码管理
- **Python**: 3.8+
- **pip**: Python包管理器
- **虚拟环境**: 推荐 (venv, conda)

## 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd Library-Index
```

### 2. 创建虚拟环境

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 使用 conda
conda create -n library-index python=3.8
conda activate library-index
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
# 复制配置模板
cp example.public.env .public.env
cp example.private.env .private.env

# 编辑配置文件
nano .public.env
nano .private.env
```

### 5. 验证安装

```bash
# 运行测试
python -m pytest tests/

# 启动服务
python -m uvicorn src.application.app:app --reload
```

## 详细配置

### 环境变量配置

#### 公共配置 (.public.env)

```bash
# mem0 配置
MEM0_BASE_URL=https://api.mem0.ai

# 默认模型配置
DEFAULT_LLM_PROVIDER=deepseek
DEFAULT_LLM_MODEL=deepseek-chat

# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

#### 私有配置 (.private.env)

```bash
# API 密钥
MEM0_API_KEY=your_mem0_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
QWEN_API_KEY=your_qwen_api_key_here

# 数据库配置（如果使用本地数据库）
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your_neo4j_password
```

### 服务配置

#### 开发环境

```bash
# 启动开发服务器
python -m uvicorn src.application.app:app --reload --host 0.0.0.0 --port 8000
```

#### 生产环境

```bash
# 使用 gunicorn 启动
pip install gunicorn
gunicorn src.application.app:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000

# 使用 systemd 服务
sudo systemctl start library-index
sudo systemctl enable library-index
```

## Docker 部署

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.application.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2. 构建 Docker 镜像

```bash
docker build -t library-index .
```

### 3. 运行容器

```bash
docker run -d \
  --name library-index \
  -p 8000:8000 \
  -v $(pwd)/.public.env:/app/.public.env \
  -v $(pwd)/.private.env:/app/.private.env \
  library-index
```

### 4. Docker Compose 部署

```yaml
version: '3.8'

services:
  library-index:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MEM0_BASE_URL=https://api.mem0.ai
    env_file:
      - .public.env
      - .private.env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

启动服务：
```bash
docker-compose up -d
```

## 云平台部署

### AWS 部署

#### 1. 使用 EC2

```bash
# 启动 EC2 实例
aws ec2 run-instances \
  --image-id ami-0c55b159cbfafe1f0 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-12345678

# 连接并部署
ssh -i your-key-pair.pem ec2-user@instance-ip
```

#### 2. 使用 ECS

```yaml
# task-definition.yaml
family: library-index
networkMode: awsvpc
requiresCompatibilities:
  - FARGATE
cpu: '1024'
memory: '2048'
executionRoleArn: arn:aws:iam::account:role/ecsTaskExecutionRole
containerDefinitions:
  - name: library-index
    image: your-account.dkr.ecr.region.amazonaws.com/library-index:latest
    portMappings:
      - containerPort: 8000
    environment:
      - name: MEM0_BASE_URL
        value: https://api.mem0.ai
    secrets:
      - name: MEM0_API_KEY
        valueFrom: arn:aws:secretsmanager:region:account:secret:mem0-api-key
```

### Google Cloud 部署

#### 1. 使用 Compute Engine

```bash
# 创建实例
gcloud compute instances create library-index \
  --machine-type=e2-medium \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud

# 部署应用
gcloud compute scp --recurse ./library-index user@library-index:~
```

#### 2. 使用 Cloud Run

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/library-index', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/library-index']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'library-index', '--image', 'gcr.io/$PROJECT_ID/library-index']
```

## 监控和日志

### 日志配置

```python
# logging_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler('logs/library-index.log', maxBytes=10*1024*1024, backupCount=5),
            logging.StreamHandler()
        ]
    )
```

### 健康检查

```python
# health_check.py
from fastapi import FastAPI
from infrastructure.memory_layer import Mem0Client

app = FastAPI()

@app.get("/health")
async def health_check():
    try:
        # 检查 mem0 连接
        mem0_client = Mem0Client()
        return {"status": "healthy", "services": {"mem0": "ok"}}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Prometheus 监控

```python
# metrics.py
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('library_index_requests_total', 'Total requests')
REQUEST_DURATION = Histogram('library_index_request_duration_seconds', 'Request duration')

@app.middleware("http")
async def metrics_middleware(request, call_next):
    REQUEST_COUNT.inc()
    start_time = time.time()
    response = await call_next(request)
    REQUEST_DURATION.observe(time.time() - start_time)
    return response
```

## 性能优化

### 缓存配置

```python
# cache_config.py
from cachetools import TTLCache

# 配置缓存
research_cache = TTLCache(maxsize=1000, ttl=3600)  # 1小时缓存
paper_cache = TTLCache(maxsize=5000, ttl=86400)   # 24小时缓存
```

### 数据库优化

```python
# database_config.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 并发配置

```python
# concurrency_config.py
import asyncio
from concurrent.futures import ThreadPoolExecutor

# 配置线程池
thread_pool = ThreadPoolExecutor(max_workers=8)

# 配置异步任务
async def async_process_papers(papers):
    tasks = [process_paper(paper) for paper in papers]
    await asyncio.gather(*tasks)
```

## 安全配置

### HTTPS 配置

```nginx
# nginx.conf
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 防火墙配置

```bash
# UFW 配置
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### API 密钥管理

```python
# key_management.py
import os
from cryptography.fernet import Fernet

def encrypt_api_key(key):
    fernet_key = os.getenv('FERNET_KEY')
    fernet = Fernet(fernet_key)
    return fernet.encrypt(key.encode())

def decrypt_api_key(encrypted_key):
    fernet_key = os.getenv('FERNET_KEY')
    fernet = Fernet(fernet_key)
    return fernet.decrypt(encrypted_key).decode()
```

## 备份和恢复

### 数据备份

```bash
# 备份脚本
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/library-index"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
pg_dump -h localhost -U username database_name > $BACKUP_DIR/db_$DATE.sql

# 备份配置文件
cp .public.env $BACKUP_DIR/config_$DATE.public.env
cp .private.env $BACKUP_DIR/config_$DATE.private.env

# 压缩备份
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz $BACKUP_DIR/*_$DATE.*

# 清理旧备份
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
```

### 恢复数据

```bash
# 恢复脚本
#!/bin/bash
BACKUP_FILE=$1

# 解压备份
tar -xzf $BACKUP_FILE

# 恢复数据库
psql -h localhost -U username database_name < db_*.sql

# 恢复配置
cp config_*.public.env .public.env
cp config_*.private.env .private.env
```

## 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查端口占用
lsof -i :8000

# 检查日志
tail -f logs/library-index.log

# 检查依赖
pip check
```

#### 2. API 连接问题

```bash
# 测试 mem0 连接
python -c "from infrastructure.memory_layer import Mem0Client; Mem0Client()"

# 测试 LLM 连接
python -c "from infrastructure.llm_client import LLMClient; LLMClient.create('deepseek')"
```

#### 3. 内存使用过高

```bash
# 监控内存使用
ps aux | grep library-index

# 重启服务
sudo systemctl restart library-index
```

### 性能调优

#### 1. 调整并发数

```python
# 在配置中调整
MAX_WORKERS_LLM = min(32, (os.cpu_count() or 1) * 4)
MAX_SEARCH_RETRIES = 3
```

#### 2. 优化缓存策略

```python
# 调整缓存大小和TTL
CACHE_MAX_SIZE = 2000
CACHE_TTL = 7200  # 2小时
```

#### 3. 数据库优化

```sql
-- 创建索引
CREATE INDEX idx_paper_id ON papers(id);
CREATE INDEX idx_user_query ON search_results(user_query);
```

## 更新和维护

### 版本更新

```bash
# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 运行迁移
python migrate.py

# 重启服务
sudo systemctl restart library-index
```

### 定期维护

```bash
# 清理日志
find logs/ -name "*.log" -mtime +30 -delete

# 清理缓存
rm -rf __pycache__/
rm -rf .pytest_cache/

# 更新系统
sudo apt update && sudo apt upgrade -y
```

## 联系支持

如果遇到部署问题，请：

1. 检查日志文件
2. 查看故障排除部分
3. 提交 GitHub Issue
4. 联系技术支持

---

*最后更新: 2024-01-XX*