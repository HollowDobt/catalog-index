"""
# src/infrastructure/io/base_io_stream.py

Input and output device base class

输入输出器基类
"""


from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from dataclasses import dataclass
from src.infrastructure.base_registries import LIStandard


@dataclass
class IOInStream:
    """
    Input Stream
    """
    event: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class IOOutStream:
    """
    Output Stream
    """
    event: str
    content: str
    metadata: Optional[Dict[str, Any]] = None


class IOStream(LIStandard, ABC):
    """
    Abstract large model tools class
    """

    ### Required functions for subclasses
    @abstractmethod
    def input(self, query: IOInStream, **kwargs: Any) -> Dict[str, Any]:
        """
        Standard IO input.
        """

    @abstractmethod
    def output(self, query: IOOutStream, **kwargs: Any) -> Any:
        """
        Standard IO output.
        """
