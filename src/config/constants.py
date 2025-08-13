"""
# src/config/constants.py

All customizable public constant definitions

所有可自定义公有常量定义处
"""


from typing import Dict, Any
import uuid


MEM0_PING_CONTENT = f"__health_{uuid.uuid4()}__"


CONSTANT_CONFIG: Dict[str, Any] = {
    # Main: Full process
    "MAXIMUM_NUM_OF_RETRIES": 3,
    "MAX_WORKERS": 8,
    
    # LLM
    "LLM_TIMEOUT_LIMIT": 1000, # Unit: ms
    "QWEN_TIMEOUT_LIMIT": 300, # Unit: ms
    "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
    "DEEPSEEK_ENDPOINT": "/chat/completions",
    "QWEN_BASE_URL": "https://dashscope.aliyuncs.com",
    "QWEN_ENDPOINT": "/compatible-mode/v1/chat/completions",
    # Academic DB
    "ARXIV_BASE_URL": "https://export.arxiv.org",
    "ARXIV_ENDPOINT": "/api/query?",
    "ARXIV_TIMEOUT_LIMIT": 1000, # Unit: ms
    # Mem0
    "MEM0_BASE_URL": "https://api.mem0.ai",
    "MEM0_PING_CONTENT": MEM0_PING_CONTENT,
    "MEM0_PING_MESSAGES": [{"role": "user", "content": f"{MEM0_PING_CONTENT}"}],
    # PDF Converter
    "PDF_CONVERTER_IMAGE_SCALE": 2.0,
    "PDF_CONVERTER_IMAGE_GENERATOR": True,
    # Content Filter
    "FILTER_CONDITIONS": 0.5, # Ignore text if its irrelevance exceeds this value
    "FILTER_MIN_NUMBER": 50, # If the number of valid characters in the text is less than this value, the text will be ignored.
    # Chunk Size
    "MAX_CHUNK_LENGTH": 20000, # The maximum length of text allowed when processing a segment
    # Global ADB rate limiter
    "ADB_RATE_LIMITER": 3, # Three seconds each time
    # Minimum allowable paper analysis success rate & minimum search results
    "MIN_PAPER_ANALYSIS_SUCCESS_RATE": 0.3,
    "MIN_SEARCH_RESULTS": 3,
    # The upper limit of the number of search results in ADB 
    "ADB_SEARCH_MAX_RESULTS": 1,
}