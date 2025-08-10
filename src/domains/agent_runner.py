"""
=============================
|src/domains/agent_runner.py|
=============================

# Main function: Entry point utilities for running IntelligentResearchAgent
"""

from typing import Any, Dict
from domains import IntelligentResearchAgent


def main(
    interface: str,
    raw_message_process_llm: str,
    raw_message_process_llm_model: str,
    api_generate_llm: str,
    api_generate_llm_model: str,
    embedding_llm: str,
    embedding_llm_model: str,
    max_workers_llm=8,
    max_search_retries=3,
) -> str:
    """
    Intelligent Research Agent - Advanced AI system with state-based planning

    params
    ------
    interface: str - Interface type ("debug", etc.)
    raw_message_process_llm: str - LLM provider for query processing
    raw_message_process_llm_model: str - Model for query processing
    api_generate_llm: str - LLM provider(RAG) for API generation
    api_generate_llm_model: str - Model for API generation
    embedding_llm: str - LLM provider for embedding and finding connections
    embedding_llm_model: str - Model for embedding and finding connections
    max_workers_llm: int - Maximum concurrent workers for LLM processing
    max_search_retries: int - Maximum search retry attempts

    return
    ------
    str - Final research results or execution summary
    """

    # Configuration for the intelligent agent
    agent_config = {
        "interface": interface,
        "raw_message_process_llm": raw_message_process_llm,
        "raw_message_process_llm_model": raw_message_process_llm_model,
        "api_generate_llm": api_generate_llm,
        "api_generate_llm_model": api_generate_llm_model,
        "embedding_llm": embedding_llm,
        "embedding_llm_model": embedding_llm_model,
        "max_workers_llm": max_workers_llm,
        "max_search_retries": max_search_retries,
    }

    # Create and execute the intelligent research agent
    agent = IntelligentResearchAgent(agent_config)
    return agent.execute()
