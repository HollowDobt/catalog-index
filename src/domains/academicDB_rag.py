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
        Register an AcademicDBRAG subclass under a provider name.

        params
        ------
        name: provider name used for registration
        **kwargs: extra parameters passed to the subclass

        return
        ------
        Decorator that registers the subclass
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
        Instantiate a registered AcademicDBRAG subclass by name.

        params
        ------
        provider_name: name of the registered provider
        **kwargs: parameters forwarded to the subclass constructor

        return
        ------
        Instance of the specified AcademicDBRAG subclass
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
        Generate arXiv API search query strings for given input text.

        params
        ------
        request: keywords and key sentence from the user

        return
        ------
        List of query strings compatible with the ArXiv API
        """

