"""
=====================================================
|src/infrastracture/LLM_providers/deepseek_client.py|
=====================================================

# DeepSeek LLM specific implementation of the LLMClient class
"""


import os
import uuid
import json
import requests

from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Dict, List, Any
from infrastructure.llm_client import LLMClient


DOT_ENV_PATH_PUBLIC = Path(__file__).parent.parent.parent.parent / ".public.env"
DOT_ENV_PATH_PRIVATE = Path(__file__).parent.parent.parent.parent / ".private.env"
load_dotenv(DOT_ENV_PATH_PUBLIC)
load_dotenv(DOT_ENV_PATH_PRIVATE)


class DeepSeekInitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """

class DeepSeekConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """


@dataclass
@LLMClient.register("deepseek")
class DeepSeekClient(LLMClient):
    """
    DeepSeek LLM specific implementation of the LLMClient class
    """
    
    # The request function "_headers" header is automatically generated in subsequent requests 
    # and does not need to be generated during initialization.
    _headers: Dict[str, str] = field(default_factory=dict, init=False)
    _raw_timeout: str | None = os.getenv("TIME_OUT_LIMIT")
    
    api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    base_url: str | None = os.getenv("DEEPSEEK_BASE_URL")
    end_point: str | None = os.getenv("DEEPSEEK_ENDPOINT")
    time_out: int | None = int(_raw_timeout) if _raw_timeout is not None else None
    
    
    def __post_init__(self) -> None:
        """
        After initialization, the transaction hook tests whether the connection is available.
        """
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self._health_check()
    
    
    def _health_check(self) -> None:
        """
        Health check function (initialization check and debug mode enablement)
        """
        
        # First confirm that the client variable has been set
        missing_value = (
            "api_key"   if self.api_key   is None else
            "base_url"  if self.base_url  is None else
            "end_point" if self.end_point is None else
            "time_out"  if self.time_out  is None else
            None
        )
        if missing_value:
            raise ValueError(f"{missing_value} is not found in .private.env and .public.env")

        try:
            response = self.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a ping test agent."},
                    {"role": "user", "content": "ping test"}
                ],
                model="deepseek-chat",
                temperature=0.0,
                max_tokens=1,
                user=str(uuid.uuid4())
            )
            _response = response["choices"][0]["message"]["content"] #noqa: B018
        except Exception as exc:
            print(f"DeepSeek initalize error. This often happens when base_url, api, or end_point are incorrect.")
            raise DeepSeekInitConnectError("Unable to connect to DeepSeek server") from exc
        
    
    def _post(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post request to DeepSeek Client
        """
        assert self.base_url is not None, "base_url required"
        assert self.end_point is not None, "end_point required"
        url = self.base_url.rstrip("/") + self.end_point
        response = requests.post(
            url,
            headers=self._headers,
            data=json.dumps(request),
            timeout=self.time_out
        )
        if response.status_code // 100 != 2:
            raise DeepSeekConnectError(
                f"No correct return value was obtained. Details: [{response.status_code}] {response.text[:300]}"
            )
        return response.json()
    
    
    ### Public methods
    def chat_completion(
        self,
        messages: List[Dict[str, str]], 
        model: str, 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        call LLM chat-completions, return Json dictionary
        """
        request = {
            "model": model,
            "messages": messages,
            **kwargs,
        }
        return self._post(request=request)
    
    
    def api_coding(self, request: str) -> str:
        ...
    
    
    def analyze(self, article: str) -> str:
        ...

    
    def find_connect(self, article: str, user_query: str) -> str:
        ...


### -------------------------------------------------------
### USE FOR TEST
### -------------------------------------------------------

if __name__ == "__main__":
    client = DeepSeekClient()
    reply = client.chat_completion(
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hello"},
        ],
        model="deepseek-chat",
        max_tokens = 100,
    )
    
    print("[DeepSeek 💭] Reply ->", reply["choices"][0]["message"]["content"])