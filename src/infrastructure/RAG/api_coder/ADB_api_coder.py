"""
# src/infrastructure/RAG/api_coder/ADB_api_coder.py

ADB API code generator base class

ADB api code 生成器基类
"""


from abc import ABC, abstractmethod
from typing import List
from infrastructure.base_registries import LIStandard


class AcademicDBAPIGenerator(LIStandard, ABC):
    """
    Abstract large model tools class
    """
    
    @abstractmethod
    def api_coding(self, request: str) -> List[str]:
        """
        Generate academic DB API search query strings for given input text.
        """