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
from .mem0_client import Mem0Client
from .document_parsers import DocumentParser, PaperParser

__all__: List[str] = [
    "LLMClient",
    "Mem0Client",
    "DocumentParser",
    "PaperParser",
]


# Automatically import python lib from LLM_providers/
_provider_pkg_name = f"{__name__}.LLM_providers"
_provider_pkg_path = Path(__file__).parent / "LLM_providers"

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")