"""
=======================================
|src/infrastructure/database_client.py|
=======================================

Abstract Acdemic Data Base(ADB) tools class
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
        ADB client registration function,
        the return value is the decorator function

        Example:
            @AcademicDBClient("arxiv")
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
        Find the instantiation method of the corresponding subclass by name
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
        Get metadata from AcademicDB API through Regular expression search.
        This function will return a list of metadata which meet requirements.
        """

    @abstractmethod
    def single_metadata_parser(self, meta_data: Dict[str, Any]) -> str:
        """
        Get a single article through metadata.
        """

    @abstractmethod
    def _health_check(self) -> None:
        """
        Health check function (initialization check and debug mode enablement)
        """
