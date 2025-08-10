"""
==================================
|/src/infrastructure/LLMClient.py|
==================================

# Abstract academicDB_RAG tools class
"""

from abc import ABC, abstractmethod
from typing import List
from infrastructure import LIStandard


class AcademicDBRAG(LIStandard, ABC):
    """
    Abstract large model tools class
    """

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
