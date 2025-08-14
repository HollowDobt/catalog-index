"""
# src/infrastructure/io/terminal_io.py

Input and output devices on the local terminal

本地终端上的输入输出器
"""


from typing import Dict, Any
from src.infrastructure.io.base_io_stream import IOStream, IOInStream, IOOutStream


@IOStream.register("terminal")
class TerminalIO(IOStream):
    """
    Non-TUI: Alpha/Beta version use
    """
    def input(self, query: IOInStream, **kwargs: Any) -> Dict[str, Any]:
        """
        Read input from the terminal
        """
        ...
    
    def output(self, query: IOOutStream, **kwargs: Any) -> Any:
        """
        """
        ...