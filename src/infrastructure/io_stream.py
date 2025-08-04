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
        Large model client registration function, 
        the return value is the decorator function
        
        Example:
            @IOStream.register("deepseek")
            class DeepSeekClient(IOStream):
                ...
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
        Find the instantiation method of the corresponding subclass by name
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
        Standard IO input
        """
    
    
    @abstractmethod
    def output(self, query: str, **kwargs: Any) -> Any:
        """
        Standard IO output
        """