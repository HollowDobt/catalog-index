"""
----------------------------
src/infrastructure/config.py
----------------------------

# Get and store most internal variables
"""
from typing import List, Dict
from dotenv import load_dotenv
import uuid
import os

load_dotenv()

NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

# Light Model & Cannot Coding
DEFAULT_LIGHT_MODEL = "deepseek-chat"



# DeepSeek Model Chat Class
# (It is recommended to use an open source conversation model optimized for this subject)
DEFAULT_MODEL = "deepseek-chat"

# DeepSeek Model Reasoner Class
# (It is recommended to use open source reasoning models optimized for this discipline)
PARSER_MODEL = "deepseek-reasoner"

# Mem0 Server Path
MEM0_BASE_URL = "https://api.mem0.ai"

# Mem0 Server API
MEM0_API_KEY = os.getenv("MEM0_API_KEY")

# Endpoint
DEFAULT_CHAT_PATH = "/v1/chat/completions"

# Test Message
LLMCLIENT_TEST_PING_MESSAGES: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a ping agent."},
        {"role": "user", "content": "ping"},
]
MEM0_PING_CONTENT = f"__health_{uuid.uuid4()}__"
MEM0_PING_MESSAGES: List[Dict[str, str]] = [
        {
                "role": "user",
                "content": MEM0_PING_CONTENT
        }
]