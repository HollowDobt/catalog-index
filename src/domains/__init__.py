"""
=========================
|src/domains/__init__.py|
=========================

# 
"""


from importlib import import_module
from pathlib import Path
from typing import List

from .academicDB_rag import AcademicDBRAG # noqa: F401


__all__: List[str] = [
    "AcademicDBRAG",
]


# Automatically import python lib from ADB_rag/
_provider_pkg_name = f"{__name__}.ADB_rag"
_provider_pkg_path = Path(__file__).parent / ""

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")