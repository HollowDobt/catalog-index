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
       Registers a large language model client, returning a decorator function.

params
------
name: The name of the large language model provider, used to identify different LLM implementation classes.

return
------
Returns a decorator function used to decorate a specific LLM client implementation class.

Example:
@LLMClient.register("deepseek")
class DeepSeekClient(LLMClient):
...
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
Creates an LLM client instance corresponding to the provider name.

params
------
provider_name: The name of the LLM provider, which must be a registered name.
**kwargs: Keyword arguments passed to the subclass constructor when creating the instance.

return
------
Returns the LLMClient instance for the corresponding provider.
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
        Call the LLM client to complete the conversation.

params
------
messages: A list of conversation messages, each containing the role and content fields.
**kwargs: Additional request parameters, such as temperature and max_tokens.

return
------
Returns a complete response dictionary containing all messages and information.
        """
    
    
    @abstractmethod
    def _health_check(self) -> None:
        """
        Send a minimal session request to ensure URL and key validity.

params
------
No parameters

return
------
No return value. Success condition: HTTP 200 status code and ability to retrieve the choices field.
        """
    
    
    @abstractmethod
    def _post(
        self, 
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
Upload content and request a response from the large language model.

params
------
request: A dictionary containing request parameters, including model, message, and other information.

return
------
Returns the response dictionary from the large language model.
        """
    
    @abstractmethod
    def analyze(
        self,
        article: str,
    ) -> str:
        """
Analyzes article content and extracts structured information.

params
------
article: The article content string to be analyzed.

return
------
Returns the analyzed structured article content string.
        """
        
    @abstractmethod
    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
Finds the correlation between article content and user query.

params
------
article: Article content string
user_query: User query string

return
------
Returns the correlation analysis result string
        """