"""
-------------------------------------
src/infrastructure/deepseek_client.py
-------------------------------------

# Simple encapsulation of requests to deepseek servers, 
# implemented as DeepSeekClient class.

# Each time the DeepSeekClient class is instantiated, 
# it will first send a request to the determined server address 
# using the corresponding API to test whether it works properly. 
# If the test fails, the error type is returned and output to the log.

# Encapsulates some common functions of the OpenAI library 
# to facilitate calls and modularization of other parts.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
import uuid
import requests


### Exception class definition

class DeepSeekConnectionError(RuntimeError):
    """
    Failed to pass health check during initialization.
    Generally, the user enters an error URL or API.
    """

class DeepSeekAPIError(RuntimeError):
    """
    A non-2xx error code is returned when calling the DeepSeek API.
    Further analysis is required based on the error code.
    """

