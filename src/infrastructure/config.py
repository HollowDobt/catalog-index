"""
----------------------------
src/infrastructure/config.py
----------------------------

# Get and store most internal variables
"""
from typing import List, Dict


DEFAULT_MODEL = "deepseek-chat"
DEFAULT_CHAT_PATH = "/v1/chat/completions"
PING_MESSAGES: List[Dict[str, str]] = [
        {"role": "system", "content": "You are a ping agent."},
        {"role": "user", "content": "ping"},
]