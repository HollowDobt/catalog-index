# 智库索引(Catalog Index/Library Index)

## 使用方法(针对 Alpha 0.2 以后)

### 安装环境(Darwin/Linux)

在终端执行下列命令, 并按照 `example.env` 设置好环境变量

```bash
chmod +x ./setup_env.sh
./setup_env.sh
source .venv/bin/activate
```

### 在解释器中直接调用

在**该项目根目录**中执行  `python3` 然后执行下面程序完成导入

```python
from src import *
```

而后直接调用 `main` 函数. 如

```python
main(interface="terminal", raw_message_process_llm="qwen", raw_message_process_llm_model="qwen-plus", api_generate_llm="qwen", api_generate_llm_model="qwen3-coder-plus", embedding_llm="qwen", embedding_llm_model="qwen-plus")
```
