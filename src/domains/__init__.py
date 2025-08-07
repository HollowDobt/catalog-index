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
from .article_process import ArticleStructuring # noqa: F401
from .orchestrator import main # noqa: F401

__all__: List[str] = [
    "AcademicDBRAG",
    "main",
    "ArticleStructuring"
]


# Automatically import python lib from ADB_rag/
_provider_pkg_name = f"{__name__}.ADB_rag"
_provider_pkg_path = Path(__file__).parent / "ADB_rag"

for _file in _provider_pkg_path.glob("*.py"):
    if _file.stem.startswith("_") or _file.stem == "__init__":
        continue
    import_module(f"{_provider_pkg_name}.{_file.stem}")