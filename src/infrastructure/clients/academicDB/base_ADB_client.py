"""
# src/infrsatructure/clients/academicDB/base_ADB_client.py

Scientific research database query component and API access code generator

科研数据库查询组件与 api 访问代码生成器
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from infrastructure.base_registries import LIStandard


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