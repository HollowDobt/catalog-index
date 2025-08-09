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
        Register an AcademicDBClient subclass under a provider name.

        params
        ------
        name: provider name used for registration

        return
        ------
        Decorator that registers the subclass
        """

        def decorator(subcls: Type["AcademicDBClient"]):
            if name in cls._registry:
                raise KeyError(
                    f"AcademicDBClient provider '{name}' cannot be registered again."
                )
            cls._registry[name] = subcls
            return subcls

        return decorator

    @classmethod
    def create(cls, provider_name: str, **kwargs: Any) -> "AcademicDBClient":
        """
        Instantiate a registered AcademicDBClient subclass by name.

        params
        ------
        provider_name: name of the registered provider
        **kwargs: parameters forwarded to the subclass constructor

        return
        ------
        Instance of the specified AcademicDBClient subclass
        """
        subcls = cls._registry.get(provider_name)
        if subcls is None:
            valid = ", ".join(cls._registry.keys())
            raise ValueError(
                f"Unknown AcademicDBClient provider name '{provider_name}'. Available: {valid}"
            )
        return subcls(**kwargs)

    ### Required function for subclasses
    @abstractmethod
    def search_get_metadata(self, query: str, max_num: int) -> List[Dict[str, Any]]:
        """
        Get metadata from the AcademicDB API.

        params
        ------
        query: regular expression search query
        max_num: maximum number of results to return

        return
        ------
        List of metadata records matching the query
        """

    @abstractmethod
    def single_metadata_parser(self, meta_data: Dict[str, Any]) -> str:
        """
        Get a single article through metadata.

        params
        ------
        meta_data: metadata describing the paper

        return
        ------
        Content of the article
        """

    @abstractmethod
    def _health_check(self) -> None:
        """
        Health check function (initialization check and debug mode enablement)
        """

    @abstractmethod
    def multi_metadata_parser(self, meta_data_list: List[Dict[str, Any]]) -> List[str]:
        """
        Get multiple articles through metadata.

        params
        ------
        meta_data_list: list of metadata records

        return
        ------
        List of article contents
        """
