"""
==================================
|/src/infrastructure/io_stream.py|
==================================

# Abstract IO Stream tools class
"""

from abc import ABC, abstractmethod
from typing import Type, Dict, Any, List
from infrastructure import LIStandard


class IOStream(LIStandard, ABC):
    """
    Abstract large model tools class
    """

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
