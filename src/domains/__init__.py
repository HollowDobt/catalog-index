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

# Import from ADB_rag
_import_submodules(__name__, "ADB_rag")