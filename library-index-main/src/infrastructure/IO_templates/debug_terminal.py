"""
===================================================
|src/infrastracture/IO_templates/debug_terminal.py|
===================================================
"""


from dataclasses import dataclass
from typing import Any
from infrastructure.io_stream import IOStream


@dataclass
@IOStream.register("debug")
class DebugTerminalIO(IOStream):
    """
    IO utils based on terminal
    Only in debug time
    """
    
    def input(self, query: str, **kwargs) -> str:
        return input(query)
    
    def output(self, query: str, **kwargs: Any) -> Any:
        return print(query)