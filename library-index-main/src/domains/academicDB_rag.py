"""
==================================
|/src/infrastructure/LLMClient.py|
==================================

# Abstract academicDB_RAG tools class
"""


from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List


class AcademicDBRAG(ABC):
    """
    Abstract large model tools class
    """
    
    _registry: Dict[str, Type["AcademicDBRAG"]] = {}
    
    
    ### Function used when instantiating the abstract base class
    @classmethod
    def register(cls, name: str, **kwargs: Any):
        """
        Academic Database RAG registration function, 
        the return value is the decorator function
        
        Example:
            @LLMClient.register("deepseek")
            class DeepSeekClient(LLMClient):
                ...
        """
        def decorator(subcls: Type["AcademicDBRAG"]):
            if name in cls._registry:
                raise KeyError(f"Academic RAG provider '{name}' cannot be registered again.")
            cls._registry[name] = subcls
            return subcls
        return decorator
    
    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "AcademicDBRAG":
        """
        Find the instantiation method of the corresponding subclass by name
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown LLMClient provider name '{provider_name}'. Available: {valid}")
        return subcls(**kwargs)
    
    
    ### Required functions for subclasses
    @abstractmethod
    def api_coding(self, request: str) -> List[str]:
        """
        Generate arxiv API search query strings for the given input text (keywords and key sentence).
        """