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
        IO stream client registration function, returns a decorator function

params
------
name: The name of the IO stream provider, used to identify different IO stream implementation classes

return
------
Returns a decorator function, used to decorate a specific IO stream implementation class

Example:
@IOStream.register("console")
class ConsoleStream(IOStream):
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
Creates an IO stream instance corresponding to the provider name.

params
------
provider_name: The name of the IO stream provider, which must be a registered name.
**kwargs: Keyword arguments passed to the subclass constructor when creating the instance.

return
------
Returns the IOStream instance corresponding to the provider.
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
Standard IO input interface, processing input queries

params
------
query: Input query string
**kwargs: Other input-related keyword arguments

return
------
Returns the processed input string
        """
    
    
    @abstractmethod
    def output(self, query: str, **kwargs: Any) -> Any:
        """
Standard IO output interface, handles output queries

params
------
query: The query string to be output
**kwargs: Other output-related keyword arguments

return
------
Returns the output result; the type depends on the specific implementation.
        """