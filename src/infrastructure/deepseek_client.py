"""
-------------------------------------
src/infrastructure/deepseek_client.py
-------------------------------------

# In order to ensure compatibility and access scalability to the greatest extent, 
# the OpenAI library is not used here, but this class is written separately.

# Simple encapsulation of requests to deepseek servers, 
# implemented as DeepSeekClient class.

# Each time the DeepSeekClient class is instantiated, 
# it will first send a request to the determined server address 
# using the corresponding API to test whether it works properly. 
# If the test fails, the error type is returned and output to the log.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import uuid
import requests
import config

### -------------------------------------------------------
### Exception class definition
### -------------------------------------------------------


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

### -------------------------------------------------------
### DeepSeek API Wrapper
### -------------------------------------------------------

@dataclass
class DeepSeekClient:
    """
    Lightweight DeepSeek API wrapper
    
    Parameters
    ----------
    base_url : str
        DeepSeek server url, default is "https://api.deepseek.com"
    api_key : str
    timeout : int, optional
        HTTP timeout (seconds), default is 100.
    """
    
    api_key: str
    base_url: str = "https://api.deepseek.com"
    timeout: int = 100
    
    _headers: Dict[str, str] = field(default_factory=dict, init=False)
    
    # Public: Chat Completion.
    # "**kwargs: Any" allows other parameters to be passed directly to the model
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = config.DEFAULT_MODEL,
        endpoint: str = config.DEFAULT_CHAT_PATH,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Call /v1/chat/completions, return JSON dictionary.
        
        Parameters
        ----------
        messages : list
            OpenAI-style message array.
        model : str
            DeepSeek model name.
        kwargs : Any
            Other parameters passed to DeepSeek, such as temperature, tools, etc.
        """
        payload = {
            "model": model,
            "messages": messages,
            **kwargs,
        }
        return self._post(endpoint, payload)
    
    # When initialize: Do a ping test
    def __post_init__(self) -> None:
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self._health_check()
    
    # Http Post
    def _post(
        self,
        path: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        url = self.base_url.rstrip("/") + path
        response = requests.post(
            url,
            headers=self._headers,
            data=json.dumps(payload),
            timeout=self.timeout,
        )
        if response.status_code // 100 != 2:
            raise DeepSeekAPIError(
                f"[{response.status_code}] {response.text[:200]}"
            )
        return response.json()

    # check if connection correct
    def _health_check(self) -> None:
        """
        Send a minimum session request to ensure that the url/key is valid
        
        Success conditions: HTTP 200 and the 'choices' field can be obtained.
        If it fails, DeepSeek ConnectionError is thrown for the upper layer to capture.
        """
        try:
            result = self.chat_completion(
                config.PING_MESSAGES,
                model=config.DEFAULT_MODEL,
                temperature=0.0,
                max_token=1,
                user=str(uuid.uuid4()),
            )
            _ = result["choices"][0]["message"]["content"] # noqa: B018
        except Exception as exc:  # pylint: disable=broad-except
            
            # TODO: 接入 logging 组件替换 print
            
            print(f"[DeepSeek] Initialize Error: {exc}")
            raise DeepSeekConnectionError(
                "Deepseek url or qri is incorrect"
            ) from exc
            

### -------------------------------------------------------
### USE FOR TEST
### -------------------------------------------------------

# if __name__ == "__main__":
#     import os
#     from dotenv import load_dotenv
#     load_dotenv()

#     client = DeepSeekClient(
#         base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
#         api_key=os.getenv("DEEPSEEK_API_KEY", ""),
#     )
#     reply = client.chat_completion(
#         [
#             {"role": "system", "content": "You are a helpful assistant."},
#             {"role": "user", "content": "hello"},
#         ],
#         temperature=0.2,
#         max_tokens=10,
#     )
#     print("[DeepSeek] hello ->", reply["choices"][0]["message"]["content"])