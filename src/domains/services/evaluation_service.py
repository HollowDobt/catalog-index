"""
# src/domains/services/evaluation_service.py

Search results and relevance evaluator

搜索结果与相关性评估器
"""


from typing import Dict, Any
import logging

from domains.entities.execution_context import ExecutionContext
from config import CONFIG


logger = logging.getLogger(__name__)

def evaluate_search_quality(context: ExecutionContext) -> Dict[str, Any]:
    """
    Evaluate the quality of current search results
    """
    
    # Storage of Assessment Content
    evaluation = {
        "papers_found": context.total_papers_found,
        "success_rate": (
            context.successful_analyses / max(1, context.processed_papers)
        ),
        "search_efficiency": context.total_papers_found / max(1, context.search_attempts),
        "needs_refinement": False,
        "suggested_action": "continue",
    }
    
    # If a search fails, must search again("0" means some errors may occur).
    if context.total_papers_found == 0:
        logger.warning("No papers found. Try again")
        evaluation["needs_refinement"] = True
        evaluation["suggested_action"] = "expand_keywords"
    
    # If the percentage of successfully parsed papers is too low, must search again
    elif evaluation["success_rate"] < CONFIG["MIN_PAPER_ANALYSIS_SUCCESS_RATE"]:
        logger.warning(f"Analysis success rate is too low: {evaluation['success_rate']}")
        evaluation["needs_refinement"] = True
        evaluation["suggested_action"] = "refine_keywords"

    # If the search returns too few results and the number of visits allows, must search again
    elif context.total_papers_found < CONFIG["MIN_SEARCH_RESULTS"] and context.search_attempts < CONFIG["MAXIMUM_NUM_OF_RETRIES"]:
        evaluation["needs_refinement"] = True
        evaluation["suggested_action"] = "broaden_search"
    
    return evaluation