"""
=================================================
|src/infrastracture/LLM_providers/qwen_client.py|
=================================================

# QWEN LLM specific implementation of the LLMClient class
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


class QwenInitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """

class QwenConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """


@dataclass
@LLMClient.register("qwen")
class QwenClient(LLMClient):
    """
    Qwen LLM specific implementation of the LLMClient class
    """
    
    # The request function "_headers" header is automatically generated in subsequent requests 
    # and does not need to be generated during initialization.
    model: str
    
    _headers: Dict[str, str] = field(default_factory=dict, init=False)
    _raw_timeout: str | None = os.getenv("TIME_OUT_LIMIT")
    
    api_key: str | None = os.getenv("QWEN_API_KEY")
    base_url: str | None = os.getenv("QWEN_BASE_URL")
    end_point: str | None = os.getenv("QWEN_ENDPOINT")
    time_out: int | None = int(_raw_timeout) if _raw_timeout else None


    def __post_init__(self) -> None:
        """
After initialization, sets request headers and performs a connection test.

params
------
No parameters

return
------
No return value
        """
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self._health_check()
    
    def _health_check(self) -> None:
        """
Initiates a standard request to determine whether the Qwen server is connectable.

params
------
No parameters

return
------
No return value. An exception is thrown if the connection fails.
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
                temperature=0.0,
                max_tokens=1,
                user=str(uuid.uuid4())
            )
            _response = response["choices"][0]["message"]["content"] #noqa: B018
        except Exception as exc:
            print("Qwen initalize error. This often happens when base_url, api, or end_point are incorrect.")
            raise QwenInitConnectError("Unable to connect to Qwen server") from exc
        
        
    def _post(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
Sends a POST request to the Qwen server.

params
------
request: A dictionary containing request parameters, including model, message, and other information.

return
------
Returns the server's response as a JSON dictionary.
        """
        assert self.base_url, "base_url required"
        assert self.end_point, "end_point required"
        url = self.base_url.rstrip("/") + self.end_point
        response = requests.post(
            url,
            headers=self._headers,
            data=json.dumps(request),
            timeout=self.time_out
        )
        if response.status_code // 100 != 2:
            raise QwenConnectError(
                f"No correct return value was obtained. Details: [{response.status_code}] {response.text[:300]}"
            )
        return response.json()
    
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
Calls the Qwen LLM conversation completion interface.

params
------
messages: A list of conversation messages, each containing the role and content fields.
**kwargs: Other request parameters, such as temperature and max_tokens.

return
------
Returns the complete JSON dictionary of the LLM response.
        """
        request = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        return self._post(request=request)
    
    def analyze(
        self,
        article: str,
    ) -> str:
        """
Parses the article into a structured text format.

params
------
article: The article content string to be parsed.

return
------
Returns the structured parsed article content string.
        """
        ...
    
    
    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
Analyzes the relevance of structured article content to the user's query.

params
------
article: A string containing the structured article content.
user_query: A string containing the user's query.

return
------
Returns a string containing the relevance analysis results, including a relevance score and analysis report.
        """
        ...