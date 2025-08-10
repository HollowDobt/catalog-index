"""
=======================================
|src/infrastructure/database_client.py|
=======================================

# Abstract Acdemic Data Base(ADB) tools class
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from infrastructure import LIStandard

class AcademicDBClient(LIStandard, ABC):
    """
    Abstract ADB tools class
    """
    
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