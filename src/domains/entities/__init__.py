"""
# src/domains/entities

A module that implements a buffer. The buffer is responsible for caching the context 
and search results of this round of conversation

实现缓冲区的模块. 缓冲区负责缓存本轮对话的上下文与搜索结果
"""


from .execution_context import ExecutionContext


__all__ = ["ExecutionContext"]