# API 参考文档

## 概述

Library Index 提供了完整的RESTful API接口，支持科研文献的智能检索和分析。

## 基础信息

- **Base URL**: `http://localhost:8000`
- **Content-Type**: `application/json`
- **Authentication**: 无需认证（开发环境）

## 端点列表

### POST /research

执行智能研究检索任务。

#### 请求参数

**Headers:**
```
Content-Type: application/json
```

**Body:**
```json
{
  "interface": "debug",
  "raw_message_process_llm": "deepseek",
  "raw_message_process_llm_model": "deepseek-chat",
  "api_generate_llm": "deepseek",
  "api_generate_llm_model": "deepseek-chat",
  "embedding_llm": "deepseek",
  "embedding_llm_model": "deepseek-chat",
  "max_workers_llm": 8,
  "max_search_retries": 2
}
```

#### 参数说明

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `interface` | string | 是 | - | 交互接口类型（"debug", "cli"等） |
| `raw_message_process_llm` | string | 是 | - | 查询处理LLM提供商 |
| `raw_message_process_llm_model` | string | 是 | - | 查询处理模型名称 |
| `api_generate_llm` | string | 是 | - | API生成LLM提供商 |
| `api_generate_llm_model` | string | 是 | - | API生成模型名称 |
| `embedding_llm` | string | 是 | - | 嵌入LLM提供商 |
| `embedding_llm_model` | string | 是 | - | 嵌入模型名称 |
| `max_workers_llm` | integer | 否 | 8 | 最大并发处理数 |
| `max_search_retries` | integer | 否 | 2 | 最大搜索重试次数 |

#### 支持的LLM提供商

- `deepseek`: DeepSeek AI
- `qwen`: 阿里云通义千问
- 其他OpenAI兼容API

#### 响应格式

**成功响应 (200 OK):**
```json
{
  "result": "# 🎯 智库索引执行报告\n\n## 📋 执行概况\n- 查询分析: ✓\n- 搜索尝试: 2 次\n- 找到论文: 4 篇\n- 成功分析: 3 篇\n- 分析成功率: 75.0%\n\n## 📚 研究发现\n[详细的研究结果内容...]"
}
```

**错误响应 (4xx/5xx):**
```json
{
  "detail": "错误信息描述"
}
```

## 错误处理

### 常见错误码

| HTTP状态码 | 错误类型 | 说明 |
|------------|----------|------|
| 400 | Bad Request | 请求参数格式错误 |
| 422 | Validation Error | 参数验证失败 |
| 500 | Internal Server Error | 服务器内部错误 |
| 503 | Service Unavailable | 外部服务不可用 |

### 错误示例

**参数验证错误:**
```json
{
  "detail": [
    {
      "loc": ["body", "raw_message_process_llm"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

**LLM服务错误:**
```json
{
  "detail": "Failed to connect to LLM service: Connection timeout"
}
```

## 使用示例

### cURL 示例

```bash
curl -X POST "http://localhost:8000/research" \
  -H "Content-Type: application/json" \
  -d '{
    "interface": "debug",
    "raw_message_process_llm": "deepseek",
    "raw_message_process_llm_model": "deepseek-chat",
    "api_generate_llm": "deepseek",
    "api_generate_llm_model": "deepseek-chat",
    "embedding_llm": "deepseek",
    "embedding_llm_model": "deepseek-chat"
  }'
```

### Python 示例

```python
import requests

url = "http://localhost:8000/research"
payload = {
    "interface": "debug",
    "raw_message_process_llm": "deepseek",
    "raw_message_process_llm_model": "deepseek-chat",
    "api_generate_llm": "deepseek",
    "api_generate_llm_model": "deepseek-chat",
    "embedding_llm": "deepseek",
    "embedding_llm_model": "deepseek-chat"
}

response = requests.post(url, json=payload)
result = response.json()
print(result["result"])
```

### JavaScript 示例

```javascript
const response = await fetch('http://localhost:8000/research', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    interface: 'debug',
    raw_message_process_llm: 'deepseek',
    raw_message_process_llm_model: 'deepseek-chat',
    api_generate_llm: 'deepseek',
    api_generate_llm_model: 'deepseek-chat',
    embedding_llm: 'deepseek',
    embedding_llm_model: 'deepseek-chat'
  })
});

const result = await response.json();
console.log(result.result);
```

## 性能考虑

### 请求处理时间

- **简单查询**: 30-60秒
- **复杂查询**: 2-5分钟
- **大并发**: 建议限制并发请求数

### 资源使用

- **内存**: 每个请求约100-500MB
- **CPU**: 多核并行处理
- **网络**: 依赖外部LLM和arXiv API

### 优化建议

1. **并发控制**: 建议最大并发数不超过服务器CPU核心数
2. **缓存利用**: 相同查询会利用记忆层缓存
3. **批量处理**: 对于大量查询，建议分批处理

## 监控指标

### 关键指标

- **响应时间**: 请求处理总时间
- **成功率**: 成功完成的查询比例
- **论文数量**: 平均每个查询找到的论文数
- **缓存命中率**: 记忆层缓存使用率

### 日志格式

```
[timestamp] INFO: Research request started
[timestamp] INFO: Query analysis completed
[timestamp] INFO: Found X papers
[timestamp] INFO: Processing completed
[timestamp] INFO: Research request completed
```

## 安全考虑

### 输入验证

- 所有输入参数都经过Pydantic验证
- 防止SQL注入和XSS攻击
- 限制参数长度和格式

### 速率限制

- 建议在反向代理层实现速率限制
- arXiv API调用遵循3秒间隔限制
- LLM API调用遵循提供商限制

### 数据保护

- 不存储用户查询历史
- API密钥通过环境变量保护
- 临时文件自动清理

## 版本兼容性

### API版本

- 当前版本: v1
- 向后兼容: 保证
- 废弃通知: 提前30天

### 依赖服务

- **arXiv API**: 标准REST API
- **LLM服务**: OpenAI兼容API
- **mem0服务**: v1.1+ API

## 故障排除

### 常见问题

1. **请求超时**
   - 检查网络连接
   - 验证外部服务状态
   - 增加超时时间

2. **LLM服务错误**
   - 验证API密钥
   - 检查服务配额
   - 尝试备用模型

3. **搜索结果为空**
   - 优化查询关键词
   - 增加重试次数
   - 检查arXiv API状态

### 调试模式

启用调试模式查看详细日志：

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 更新日志

### v1.0.0 (2024-01-XX)
- 初始版本发布
- 支持基础研究检索功能
- 集成arXiv和LLM服务