"""
==================================
|/src/infrastructure/io_stream.py|
==================================

# Abstract IO Stream tools class
"""


from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List


class IOStream(ABC):
    """
    Abstract large model tools class
    """
    
    _registry: Dict[str, Type["IOStream"]] = {}
    
    
    ### Function used when instantiating the abstract base class
    @classmethod
    def register(cls, name: str):
        """
        Register an IOStream subclass under a provider name.

        params
        ------
        name: provider name used for registration

        return
        ------
        Decorator that registers the subclass
        """
        def decorator(subcls: Type["IOStream"]):
            if name in cls._registry:
                raise KeyError(f"IOStream provider '{name}' cannot be registered again.")
            cls._registry[name] = subcls
            return subcls
        return decorator
    
    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "IOStream":
        """
        Instantiate a registered IOStream subclass by name.

        params
        ------
        provider_name: name of the registered provider
        **kwargs: parameters forwarded to the subclass constructor

        return
        ------
        Instance of the specified IOStream subclass
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown IOStream provider name '{provider_name}'. Available: {valid}")
        return subcls(**kwargs)
    
    
    ### Required functions for subclasses
    @abstractmethod
    def input(self, query: str, **kwargs: Any) -> str:
        """
        Standard IO input.

        params
        ------
        query: prompt shown to the user
        **kwargs: additional parameters

        return
        ------
        User-provided string
        """
    
    
    @abstractmethod
    def output(self, query: str, **kwargs: Any) -> Any:
        """
        Standard IO output.

        params
        ------
        query: text to output
        **kwargs: additional parameters

        return
        ------
        Result of the output operation
        """
