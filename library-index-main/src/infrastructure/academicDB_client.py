"""
=======================================
|src/infrastructure/database_client.py|
=======================================

# Abstract Acdemic Data Base(ADB) tools class
"""


from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List


class AcademicDBClient(ABC):
    """
    Abstract ADB tools class
    """
    
    _registry: Dict[str, Type["AcademicDBClient"]] = {}
    
    
    ### Function used when instantiating the abstract base class
    @classmethod
    def register(cls, name: str):
        """
        Academic database client registration function, returns a decorator function.

params
------
name: The name of the academic database provider, used to identify different database implementation classes.

return
------
Returns a decorator function used to decorate a specific academic database client implementation class.

Example:
@AcademicDBClient.register("arxiv")
class ArxivClient(AcademicDBClient):
...
        """
        def decorator(subcls: Type["AcademicDBClient"]):
            if name in cls._registry:
                raise KeyError(f"AcademicDBClient provider '{name}' cannot be registered again.")
            cls._registry[name] = subcls
            return subcls
        return decorator
    
    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "AcademicDBClient":
        """
Creates an AcademicDBClient instance corresponding to the provider name.

params
------
provider_name: The name of the AcademicDB provider, which must be a registered name.
**kwargs: Keyword arguments passed to the subclass constructor when creating the instance.

return
------
Returns the AcademicDBClient instance for the corresponding provider.
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(f"Unknown AcademicDBClient provider name '{provider_name}'. Available: {valid}")
        return subcls(**kwargs)
    
    
    ### Required function for subclasses
    @abstractmethod
    def search_get_metadata(self, query: str, max_num: int) -> List[Dict[str, Any]]:
        """
Retrieves metadata from the academic database API using a regular expression search.

params
------
query: Search query string, using the academic database query syntax.
max_num: Maximum number of results to return, must be greater than 0.

return
------
Returns a list of metadata dictionaries that meet the requirements.
        """
    
    
    @abstractmethod
    def single_metadata_parser(self, meta_data: Dict[str, Any]) -> str:
        """
Retrieve the corresponding article file from a single metadata entry.

params
------
meta_data: A dictionary containing article metadata.

return
------
Returns a string containing the local path to the downloaded article file.
        """
    
    
    @abstractmethod
    def _health_check(self) -> None:
        """
Health check function, used for initial checks and enabling debug mode.

params
------
No parameters

return
------
No return value. Exceptions are thrown if a connection error occurs.
        """


    @abstractmethod
    def multi_metadata_parser(self, meta_data_list: List[Dict[str, Any]]) -> List[str]:
        """
Batch retrieves corresponding article files based on multiple metadata.

params
------
meta_data_list: A list containing multiple article metadata dictionaries.

return
------
Returns a list of strings containing the local paths of all downloaded article files.
        """