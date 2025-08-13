"""
# src/infrastructure/clients/llm/OpenAI_standard_client.py

Universal client based on OpenAI standards

基于 OpenAI 标准的通用客户端
"""


import uuid
import json
import requests
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin
import logging

from infrastructure.clients.llm.base_llm_client import LLMClient
from config import CONFIG


logger = logging.getLogger(__name__)


class OAIClient(LLMClient):
    """
    Client base class based on OpenAI standards
    """
    
    def __init__(
        self,
        model: str,
        prefix: str
    ) -> None:
        raw_time_out = CONFIG[f"{prefix}_TIMEOUT_LIMIT"]
        
        self.model: str = model
        self.time_out: Optional[int] = int(raw_time_out) if raw_time_out else None
        self.base_url: Optional[str] = CONFIG[f"{prefix}_BASE_URL"]
        self.end_point: Optional[str] = CONFIG[f"{prefix}_ENDPOINT"]
        self.api_key: Optional[str] = CONFIG[f"{prefix}_API_KEY"]
        self.prefix: Optional[str] = prefix
        self._headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        self._health_check()
    
    def _health_check(self) -> None:
        """
        Initiate a standard request to determine if there is a normal response
        """
        try:
            self.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a ping agent."},
                    {"role": "user", "content": "ping test"}
                ],
                model=self.model,
                temperature=0.0,
                max_tokens=1,
                user=str(uuid.uuid4()),
            )
            logger.info(f"*{self.prefix}* Connect test succeed.")
        except Exception as exc:
            logger.error(f"*{self.prefix}* Connect test failed. Details: {exc}")
            raise RuntimeError(f"*{self.prefix}* Connect test failed. Details: {exc}")
    
    def _post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send POST request to Qwen server
        """
        
        assert self.base_url, "base_url required"
        assert self.end_point, "end_point required"
        response = requests.post(
            url = urljoin(self.base_url.rstrip("/") + "/", self.end_point.lstrip("/")),
            headers=self._headers,
            data=json.dumps(request),
            timeout=self.time_out
        )
        
        if response.status_code // 100 != 2:
            logger.error(f"Return code is not 200. Details: [{response.status_code}] {response.text[:300]}")
        else:
            logger.info(f"Connection successful")
        
        return response.json()
    
    def chat_completion(self, messages: List[Dict[str, str]], **kwargs: Any) -> Dict[str, Any]:
        """
        Call the Qwen chat-completions endpoint
        """
        request = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        return self._post(request=request)


@LLMClient.register("qwen")
class QwenClient(OAIClient):
    """
    Qwen Client
    Allows connection to custom standard Qwen servers
    """
    def __init__(self, model: str) -> None:
        super().__init__(
            model=model,
            prefix="QWEN"
        )


@LLMClient.register("deepseek")
class DeepSeekClient(OAIClient):
    """
    DeepSeek Client
    Allows connection to custom standard DeepSeek servers
    """
    def __init__(self, model: str) -> None:
        super().__init__(
            model=model,
            prefix="DEEPSEEK"
        )