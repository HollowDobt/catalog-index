"""
================================
|src/infrastructure/__init__.py|
================================

# Export "DeepSeekClient" & "Mem0Client"
# LLM Clients & Memory Clients Preprocessing library
"""


from importlib import import_module
from pathlib import Path
from typing import List

from .llm_client import LLMClient # noqa: F401
from .academicDB_client import AcademicDBClient # noqa: F401
from .memory_layer import Mem0Client # noqa: F401
from .pdf_parser import PDFToMarkdownConverter # noqa: F401
from .io_stream import IOStream # noqa: F401


__all__: List[str] = [
    "LLMClient",
    "AcademicDBClient",
    "Mem0Client",
    "PDFToMarkdownConverter",
    "IOStream"
]


# Automatically import python lib from LLM_providers/
def _import_submodules(base_name, subdir_name):
    """Helper function to dynamically import submodules"""
    try:
        pkg_path = Path(__file__).parent / subdir_name
        if not pkg_path.exists():
            print(f"Warning: Directory {pkg_path} does not exist")
            return
            
        for _file in pkg_path.glob("*.py"):
            if _file.stem.startswith("_") or _file.stem == "__init__":
                continue
            try:
                import_module(f"{base_name}.{subdir_name}.{_file.stem}")
            except ImportError as e:
                print(f"Warning: Failed to import {base_name}.{subdir_name}.{_file.stem}: {e}")
                continue
    except Exception as e:
        print(f"Warning: Error importing from {subdir_name}: {e}")

# Import from subdirectories
_import_submodules(__name__, "LLM_providers")
_import_submodules(__name__, "ADB_providers")
_import_submodules(__name__, "IO_templates")