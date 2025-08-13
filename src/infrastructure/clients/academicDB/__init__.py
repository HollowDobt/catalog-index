"""
# src/infrastructure/clients/academicDB

Research database components

科研数据库组件
"""


from .base_ADB_client import AcademicDBClient
from .arxiv_client import ArxivClient


__all__= ["AcademicDBClient", "ArxivClient"]