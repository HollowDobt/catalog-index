"""
==================================
|/src/infrastructure/LLMClient.py|
==================================

# Abstract large model tools class
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
        Large model client registration function, 
        the return value is the decorator function
        
        Example:
            @LLMClient.register("deepseek")
            class DeepSeekClient(LLMClient):
                ...
        """
        def decorator(subcls: Type["LLMClient"]):
            if name in cls._registry:
                raise KeyError(f"LLMClinet provider '{name}' cannot be registered again.")
            cls._registry[name] = subcls
            return subcls
        return decorator
    
    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "LLMClient":
        """
        Find the instantiation method of the corresponding subclass by name
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown provider name '{provider_name}'. Available: {valid}")
        return subcls(**kwargs)
    
    
    ### Required functions for subclasses
    @abstractmethod
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Call LLMClient
        
        Return All Messages & Information
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
        Upload content and request large model reply
        """
    
    @abstractmethod
    def api_coding(
        self,
        request: str
    ) -> str:
        """
        Generate API requests to scientific databases upon request 
        """
    
    @abstractmethod
    def analyze(
        self,
        article: str
    ) -> str:
        """
        Parse the article into structured text
        """
    
    @abstractmethod
    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
        Resolve associations with user goals 
        based on incoming structured article content
        """
