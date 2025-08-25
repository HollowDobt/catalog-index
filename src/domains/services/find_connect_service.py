"""
# src/domains/services/find_connect_service.py

Find the relationship between user needs and existing literature

寻找用户需求与已有文献之间的关系
"""


import re
import logging
from typing import Dict, Any, Optional

from src.infrastructure import LLMClient


logger = logging.getLogger(__name__)


def evaluate_abstract_relevance(llm_embedding: LLMClient, abstract: str, user_query: str) -> float:
    """
    Evaluate the relevance between paper abstract/summary and user query.
    """
    system_prompt = (
        "You are a research relevance evaluator. "
        "Assess how relevant a paper abstract is to a user's research query. "
        "Return ONLY a decimal number between 0.0 and 1.0, where:\n"
        "- 0.0-0.3: Not relevant or tangentially related\n"
        "- 0.4-0.6: Somewhat relevant, overlapping concepts\n"
        "- 0.7-0.9: Highly relevant, directly addresses the query\n"
        "- 1.0: Perfectly matches the query requirements\n"
        "Response format: Just the number, nothing else (e.g., '0.75')"
    )
    
    user_prompt = (
        f"User query: {user_query}\n\n"
        f"Paper abstract: {abstract}\n\n"
        "Relevance score:"
    )
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    try:
        response = llm_embedding.chat_completion(messages=messages, temperature=0.1)
        response_content = response["choices"][0]["message"]["content"].strip()


def find_connect(llm_embedding: LLMClient, article: str, user_query: str) -> str:
    """
    Resolve associations between the article and user query.
    Returns text with EXACTLY 4 sections:
    - Query Decomposition:
    - Document Profiles:
    - Multi-Layer Matching Analysis:
    - Confidence Scoring:
    """
    system_prompt = (
        "You are a concise relevance analyst. "
        "Answer in English using EXACTLY these four headings and nothing else:\n"
        "Query Decomposition:\n"
        "Document Profiles:\n"
        "Multi-Layer Matching Analysis:\n"
        "Confidence Scoring:\n"
        "Rules: ground claims in the provided article; include a 0-100 primary relevance rating "
        "under 'Confidence Scoring'. No extra sections, no preface or closing."
    )

    user_prompt = (
        f"User query: {user_query}\n\n"
        "Task: assess how the article relates to the query following the four sections above.\n\n"
        f"Article:\n{article}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    resp = llm_embedding.chat_completion(messages=messages)
    return resp["choices"][0]["message"]["content"]
