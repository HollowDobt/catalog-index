"""
===================================================
|src/infrastracture/IO_templates/debug_terminal.py|
===================================================
"""


import os

from dataclasses import dataclass
from typing import Any
from infrastructure.io_stream import IOStream
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime


DOT_ENV_PATH_PUBLIC = Path(__file__).parent.parent.parent.parent / ".public.env"
load_dotenv(DOT_ENV_PATH_PUBLIC)


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
        """
        Save the file to the cache directory
        """
        cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        target_dir = cache_root / "library-index" / "results"
        target_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        filepath = target_dir / f"{timestamp}.md"
        
        # Append text to a file (UTF-8 encoding)
        with filepath.open("a", encoding="utf-8") as f:
            f.write(query)
            if not query.endswith("\n"):
                f.write("\n")