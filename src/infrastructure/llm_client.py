"""
==================================
|/src/infrastructure/LLMClient.py|
==================================

# Abstract LLM tools class
"""


from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List


class LLMClient(ABC):
    """
    Abstract large model tools class
    """
    
    _registry: Dict[str, Type["LLMClient"]] = {}
    
    
    ### Function used when instantiating the abstract base class
    @classmethod
    def register(cls, name: str):
        """
        Register an LLMClient subclass under a provider name.

        params
        ------
        name: provider name used for registration

        return
        ------
        Decorator that registers the subclass
        """
        def decorator(subcls: Type["LLMClient"]):
            if name in cls._registry:
                raise KeyError(f"LLMClient provider '{name}' cannot be registered again.")
            cls._registry[name] = subcls
            return subcls
        return decorator
    
    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "LLMClient":
        """
        Instantiate a registered LLMClient subclass by name.

        params
        ------
        provider_name: name of the registered provider
        **kwargs: parameters forwarded to the subclass constructor

        return
        ------
        Instance of the specified LLMClient subclass
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown LLMClient provider name '{provider_name}'. Available: {valid}")
        return subcls(**kwargs)
    
    
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
    def _post(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Upload content and request a large model reply.

        params
        ------
        request: payload sent to the API

        return
        ------
        JSON response from the API
        """
    
    @abstractmethod
    def analyze(
        self,
        article: str,
    ) -> str:
        """
        Analyze article content.

        params
        ------
        article: raw article content

        return
        ------
        Structured text produced by the model
        """
        
    @abstractmethod
    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
        Find connections between an article and the user query.

        params
        ------
        article: structured article content
        user_query: user's research question

        return
        ------
        Text describing the connections
        """
