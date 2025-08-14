"""
# src/infrastructure/clients/llm/base_llm_client.py

Large model client component base class

大模型客户端组件基类
"""


from abc import ABC, abstractmethod
from typing import Dict, Any, List
from src.infrastructure.base_registries import LIStandard


class LLMClient(LIStandard, ABC):
    """
    Abstract large model tools class
    """

    ### Required functions for subclasses
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Call the LLM and return all messages and metadata.

        params
        ------
        messages: conversation history for the model
        **kwargs: additional request parameters

        return
        ------
        JSON response from the LLM
        """

    @abstractmethod
    def _health_check(self) -> None:
        """
        Send a minimum session request to ensure that the url/key is valid

        Success conditions: HTTP 200 and the 'choices' field can be obtained

        Using DEFAUL_LIGHT_MODEL
        """

    @abstractmethod
    def _post(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload content and request a large model reply.

        params
        ------
        request: payload sent to the API

        return
        ------
        JSON response from the API
        """