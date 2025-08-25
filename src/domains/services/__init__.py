"""
# src/domains/services

Service components for agents, including keyword generator, result evaluator, and result summarizer

对 agents 的服务组件，包括关键词生成器，结果评估器，结果总结器
"""


from .evaluation_service import evaluate_search_quality
from .keywords_optimizer import generate_adaptive_keywords
from .synthesis_service import intelligent_synthesis_merge
from .find_connect_service import find_connect, evaluate_abstract_relevance, calculate_embedding_similarity


__all__ = ["evaluate_search_quality", "generate_adaptive_keywords", "intelligent_synthesis_merge", "find_connect", "evaluate_abstract_relevance", "calculate_embedding_similarity"]