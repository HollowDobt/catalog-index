"""
# src/config/settings.py

Configuration management and reading classes, environment variable processing components

配置管理与读取类, 环境变量处理组件
"""


from __future__ import annotations
from pathlib import Path
from dotenv import dotenv_values
from typing import Dict, Any
from .constants import CONSTANT_CONFIG
import logging


logger = logging.getLogger(__name__)

CONFIG: Dict[str, Any] = dotenv_values(Path(__file__).parent.parent.parent / ".env")
CONFIG.update(CONSTANT_CONFIG)

# Environment variable integrity check; Empty values or unset values will result in an error
for item in ("DEEPSEEK_API_KEY", "MEM0_API_KEY", "QWEN_API_KEY"):
    if item not in CONFIG or not str(CONFIG.get(item)).strip():
        logger.critical(f"The value *{item}* is not set or is empty")
        raise KeyError(f"The value *{item}* is not set or is empty")


__all__ = ["CONFIG"]