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
from .pdf_parser import PDFParser # noqa: F401
from .io_stream import IOStream # noqa: F401


__all__: List[str] = [
    "LLMClient",
    "AcademicDBClient",
    "Mem0Client",
    "PDFParser",
    "IOStream"
]


# Automatically import python lib from LLM_providers/
_provider_pkg_name = f"{__name__}.LLM_providers"
_provider_pkg_path = Path(__file__).parent / "LLM_providers"

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")

# Automatically import python lib from ADB_providers/
_provider_pkg_name = f"{__name__}.ADB_providers"
_provider_pkg_path = Path(__file__).parent / "ADB_providers"

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")
    
# Automatically import python lib from IO_templates/
_provider_pkg_name = f"{__name__}.IO_templates"
_provider_pkg_path = Path(__file__).parent / "IO_templates"

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")