# 开发指南

## 开发环境设置

### 前置要求

- Python 3.8+
- Git
- 文本编辑器（推荐 VS Code）

### 环境配置

1. **克隆并设置开发环境**

```bash
git clone <repository-url>
cd Library-Index
python -m venv dev_env
source dev_env/bin/activate  # Linux/macOS
# 或 dev_env\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 开发依赖
```

2. **配置开发环境变量**

```bash
cp example.public.env .public.env
cp example.private.env .private.env
# 编辑配置文件，添加开发用的API密钥
```

3. **安装 pre-commit hooks**

```bash
pre-commit install
```

## 代码结构

### 目录结构

```
src/
├── application/          # 应用层
│   ├── app.py           # FastAPI 应用
│   └── test.py          # 测试入口
├── domains/             # 领域层
│   ├── orchestrator.py  # 核心业务逻辑
│   ├── academicDB_rag.py # RAG 抽象类
│   ├── article_process.py # 文章处理
│   └── ADB_rag/         # 具体实现
├── infrastructure/      # 基础设施层
│   ├── llm_client.py    # LLM 客户端
│   ├── memory_layer.py  # 记忆层
│   ├── pdf_parser.py    # PDF 解析
│   └── providers/       # 服务提供商
└── adapters/           # 适配器层
```

### 代码规范

#### Python 代码风格

- 遵循 PEP 8 规范
- 使用 Black 进行代码格式化
- 使用 isort 进行导入排序
- 使用 flake8 进行代码检查

#### 类型注解

```python
from typing import List, Dict, Any, Optional

def process_papers(
    papers: List[Dict[str, Any]],
    max_workers: int = 8
) -> Dict[str, Any]:
    """处理论文列表"""
    pass
```

#### 文档字符串格式

```python
def search_papers(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    根据查询搜索论文
    
    Args:
        query: 搜索查询字符串
        limit: 返回结果最大数量
        
    Returns:
        包含论文元数据的字典列表
        
    Raises:
        ValueError: 当查询为空时
        ConnectionError: 当无法连接到搜索服务时
    """
```

## 核心组件开发

### 1. 添加新的 LLM 提供商

#### 步骤 1: 创建 LLM 客户端类

```python
# src/infrastructure/LLM_providers/new_provider.py
from infrastructure.llm_client import LLMClient
from typing import List, Dict, Any
import requests

@LLMClient.register("new_provider")
class NewProviderClient(LLMClient):
    def __init__(self, api_key: str, model: str = "default-model"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.newprovider.com/v1"
        self._health_check()
    
    def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """实现聊天完成功能"""
        payload = {
            "model": self.model,
            "messages": messages,
            **kwargs
        }
        return self._post(payload)
    
    def _health_check(self) -> None:
        """健康检查"""
        test_payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1
        }
        response = self._post(test_payload)
        if "choices" not in response:
            raise ConnectionError("Health check failed")
    
    def _post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """发送POST请求"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=request
        )
        response.raise_for_status()
        return response.json()
    
    def find_connect(self, article: str, user_query: str) -> str:
        """查找文章与查询的关联"""
        prompt = f"""
        分析以下文章与用户查询的关联性：
        
        文章内容：{article}
        用户查询：{user_query}
        
        请详细描述它们之间的关联。
        """
        
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        response = self.chat_completion(messages)
        return response["choices"][0]["message"]["content"]
```

#### 步骤 2: 注册和测试

```python
# 测试新提供商
from infrastructure.llm_client import LLMClient

client = LLMClient.create("new_provider", api_key="your-api-key")
response = client.chat_completion([
    {"role": "user", "content": "Hello, world!"}
])
print(response)
```

### 2. 添加新的学术数据库

#### 步骤 1: 创建 RAG 实现类

```python
# src/domains/ADB_rag/new_db.py
from domains.academicDB_rag import AcademicDBRAG
from infrastructure import LLMClient
from typing import List
import re

@AcademicDBRAG.register("new_db")
class NewDBRAG(AcademicDBRAG):
    def __init__(self, LLM_client: LLMClient):
        self.LLM_client = LLM_client
    
    def api_coding(self, request: str) -> List[str]:
        """生成新数据库的API查询"""
        if not request or not request.strip():
            return []
        
        system_prompt = """
        你是专家搜索查询生成器。将用户输入转换为NewDB API搜索查询。
        
        格式要求：
        - 使用field:search_term格式
        - 支持布尔运算符AND, OR, NOT
        - 短语用引号包围
        - 输出Python列表格式
        """
        
        user_prompt = f"生成NewDB搜索查询: {request}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        try:
            response = self.LLM_client.chat_completion(messages)
            content = response["choices"][0]["message"]["content"]
            
            # 解析响应
            queries = self._parse_response(content)
            return self._validate_queries(queries)
            
        except Exception as e:
            # 降级到简单查询
            return [f"all:{request.replace(' ', '+')}"]
    
    def _parse_response(self, content: str) -> List[str]:
        """解析LLM响应"""
        # 实现解析逻辑
        pass
    
    def _validate_queries(self, queries: List[str]) -> List[str]:
        """验证和清理查询"""
        # 实现验证逻辑
        pass
```

#### 步骤 2: 创建数据库客户端

```python
# src/infrastructure/ADB_providers/new_db_client.py
from infrastructure.academicDB_client import AcademicDBClient
from typing import List, Dict, Any
import requests

@AcademicDBClient.register("new_db")
class NewDBClient(AcademicDBClient):
    def __init__(self):
        self.base_url = "https://api.newdb.com"
        self.api_key = "your-api-key"
    
    def search_get_metadata(self, query: str, max_num: int = 10) -> List[Dict[str, Any]]:
        """搜索并获取元数据"""
        params = {
            "query": query,
            "limit": max_num,
            "api_key": self.api_key
        }
        
        response = requests.get(
            f"{self.base_url}/search",
            params=params
        )
        response.raise_for_status()
        
        results = response.json()
        return self._format_metadata(results)
    
    def single_metadata_parser(self, meta: Dict[str, Any]) -> str:
        """解析单个元数据并返回PDF链接"""
        # 实现解析逻辑
        pass
    
    def _format_metadata(self, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """格式化元数据"""
        # 实现格式化逻辑
        pass
```

### 3. 添加新的交互接口

```python
# src/infrastructure/IO_templates/web_interface.py
from infrastructure.io_stream import IOStream
from typing import Dict, Any

@IOStream.register("web")
class WebInterface(IOStream):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
    
    def input(self, prompt: str) -> str:
        """Web界面输入"""
        # 实现Web输入逻辑
        pass
    
    def output(self, content: str) -> None:
        """Web界面输出"""
        # 实现Web输出逻辑
        pass
```

## 测试开发

### 单元测试

```python
# tests/test_orchestrator.py
import pytest
from domains.orchestrator import IntelligentResearchAgent
from unittest.mock import Mock, patch

class TestIntelligentResearchAgent:
    @pytest.fixture
    def agent_config(self):
        return {
            "interface": "debug",
            "raw_message_process_llm": "deepseek",
            "raw_message_process_llm_model": "deepseek-chat",
            "api_generate_llm": "deepseek",
            "api_generate_llm_model": "deepseek-chat",
            "embedding_llm": "deepseek",
            "embedding_llm_model": "deepseek-chat"
        }
    
    @pytest.fixture
    def agent(self, agent_config):
        with patch('domains.orchestrator.IOStream'), \
             patch('domains.orchestrator.LLMClient'), \
             patch('domains.orchestrator.AcademicDBRAG'), \
             patch('domains.orchestrator.AcademicDBClient'), \
             patch('domains.orchestrator.Mem0Client'), \
             patch('domains.orchestrator.PDFToMarkdownConverter'), \
             patch('domains.orchestrator.ArticleStructuring'):
            return IntelligentResearchAgent(agent_config)
    
    def test_agent_initialization(self, agent):
        assert agent is not None
        assert agent.context.current_state.name == "INITIALIZING"
    
    def test_query_analysis(self, agent):
        # Mock LLM response
        agent.llm_query_processor.chat_completion.return_value = {
            "choices": [{"message": {"content": "machine learning, AI"}}]
        }
        
        with patch.object(agent.interface, 'input', return_value=""):
            next_state = agent._handle_query_analysis()
            assert next_state.name == "PLANNING_SEARCH"
```

### 集成测试

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from src.application.app import app

client = TestClient(app)

def test_research_endpoint():
    response = client.post("/research", json={
        "interface": "debug",
        "raw_message_process_llm": "deepseek",
        "raw_message_process_llm_model": "deepseek-chat",
        "api_generate_llm": "deepseek",
        "api_generate_llm_model": "deepseek-chat",
        "embedding_llm": "deepseek",
        "embedding_llm_model": "deepseek-chat"
    })
    
    assert response.status_code == 200
    assert "result" in response.json()
```

### 性能测试

```python
# tests/test_performance.py
import time
import pytest
from domains.orchestrator import IntelligentResearchAgent

def test_concurrent_processing():
    """测试并发处理性能"""
    config = {
        "interface": "debug",
        "raw_message_process_llm": "deepseek",
        "raw_message_process_llm_model": "deepseek-chat",
        "api_generate_llm": "deepseek",
        "api_generate_llm_model": "deepseek-chat",
        "embedding_llm": "deepseek",
        "embedding_llm_model": "deepseek-chat",
        "max_workers_llm": 16
    }
    
    # Mock 所有依赖
    with patch.multiple('domains.orchestrator',
                       IOStream=Mock, LLMClient=Mock, AcademicDBRAG=Mock,
                       AcademicDBClient=Mock, Mem0Client=Mock,
                       PDFToMarkdownConverter=Mock, ArticleStructuring=Mock):
        
        agent = IntelligentResearchAgent(config)
        
        # 模拟多个论文处理
        start_time = time.time()
        # 添加性能测试逻辑
        end_time = time.time()
        
        processing_time = end_time - start_time
        assert processing_time < 30  # 应该在30秒内完成
```

## 调试技术

### 1. 日志调试

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def debug_function():
    logger.debug("开始调试")
    logger.info("处理信息")
    logger.error("发生错误")
```

### 2. 断点调试

```python
import pdb

def debug_with_breakpoints():
    x = 10
    y = 20
    pdb.set_trace()  # 断点
    z = x + y
    return z
```

### 3. 内存调试

```python
import tracemalloc

def debug_memory():
    tracemalloc.start()
    
    # 执行代码
    result = some_memory_intensive_function()
    
    # 显示内存使用
    snapshot = tracemalloc.take_snapshot()
    top_stats = snapshot.statistics('lineno')
    
    for stat in top_stats[:10]:
        print(stat)
```

## 代码审查清单

### 提交前检查

- [ ] 代码遵循 PEP 8 规范
- [ ] 所有测试通过
- [ ] 类型注解完整
- [ ] 文档字符串存在
- [ ] 无语法错误
- [ ] 性能影响已考虑
- [ ] 安全问题已检查

### 代码质量检查

```bash
# 运行代码检查
black src/
isort src/
flake8 src/
mypy src/
```

### 测试覆盖率

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term-missing
```

## 性能优化

### 1. 异步处理

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def async_process_data(data):
    """异步处理数据"""
    loop = asyncio.get_event_loop()
    
    with ThreadPoolExecutor() as executor:
        tasks = [
            loop.run_in_executor(executor, process_item, item)
            for item in data
        ]
        
        results = await asyncio.gather(*tasks)
        return results
```

### 2. 缓存优化

```python
from functools import lru_cache
from cachetools import TTLCache

# LRU缓存
@lru_cache(maxsize=1000)
def expensive_computation(x, y):
    return x * y

# TTL缓存
cache = TTLCache(maxsize=1000, ttl=3600)

def cached_operation(key):
    if key in cache:
        return cache[key]
    
    result = perform_expensive_operation(key)
    cache[key] = result
    return result
```

### 3. 内存优化

```python
# 生成器减少内存使用
def process_large_file(file_path):
    with open(file_path, 'r') as f:
        for line in f:
            yield process_line(line)

# 使用更高效的数据结构
from collections import defaultdict

def optimize_data_structure():
    # 使用 defaultdict 代替普通 dict
    data = defaultdict(list)
    data['key'].append('value')
    return data
```

## 部署和发布

### 1. 版本管理

```python
# src/__init__.py
__version__ = "1.0.0"

# setup.py
from setuptools import setup, find_packages

setup(
    name="library-index",
    version=__version__,
    packages=find_packages(),
    # 其他配置...
)
```

### 2. CI/CD 配置

```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.8
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run tests
        run: pytest
      - name: Code quality
        run: |
          black --check src/
          flake8 src/
          mypy src/
```

### 3. 发布流程

```bash
# 创建发布
git tag v1.0.0
git push origin v1.0.0

# 构建和发布
python setup.py sdist bdist_wheel
twine upload dist/*
```

## 贡献指南

### 1. Fork 和克隆

```bash
# Fork 项目到个人账户
git clone https://github.com/your-username/Library-Index.git
cd Library-Index
git remote add upstream https://github.com/original-repository/Library-Index.git
```

### 2. 开发流程

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发代码
# 编写测试
# 提交更改
git add .
git commit -m "Add new feature"

# 推送到个人仓库
git push origin feature/new-feature

# 创建 Pull Request
```

### 3. 代码审查

- 确保 CI 测试通过
- 响应审查意见
- 更新代码直到合并

## 常见问题

### Q: 如何处理大型PDF文件？

A: 使用流式处理和分块解析：

```python
def process_large_pdf(pdf_path):
    """分块处理大型PDF文件"""
    chunk_size = 1000  # 每次处理1000页
    
    for i in range(0, total_pages, chunk_size):
        chunk = extract_pdf_chunk(pdf_path, i, chunk_size)
        yield process_chunk(chunk)
```

### Q: 如何优化LLM调用成本？

A: 实现智能缓存和批处理：

```python
class LLMCache:
    def __init__(self):
        self.cache = {}
    
    def get_cached_response(self, prompt_hash):
        if prompt_hash in self.cache:
            return self.cache[prompt_hash]
        return None
    
    def cache_response(self, prompt_hash, response):
        self.cache[prompt_hash] = response
```

### Q: 如何处理API速率限制？

A: 实现指数退避重试：

```python
import time
import random

def retry_with_backoff(func, max_retries=3):
    for i in range(max_retries):
        try:
            return func()
        except RateLimitError:
            wait_time = (2 ** i) + random.random()
            time.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

---

*本开发指南将持续更新，请定期查看最新版本。*