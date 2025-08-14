"""
# src/domains/entities/execution_context.py

Context buffer

上下文缓存器
"""


from dataclasses import dataclass, field
from typing import List, Dict, Any
import time

from src.domains.agents import ActionType, AgentState


@dataclass
class ExecutionContext:
    """
    Context information for agent decisions
    """

    current_state: AgentState
    search_attempts: int
    total_papers_found: int
    processed_papers: int
    successful_analyses: int
    failed_analyses: int
    current_keywords: str
    user_query: str
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    search_results: List[Dict[str, Any]] = field(default_factory=list)
    analysis_results: List[str] = field(default_factory=list)

    # Log component function
    def add_execution_record(self, action: ActionType, details: Dict[str, Any]):
        """
        Record an execution step
        """
        self.execution_history.append(
            {
                "timestamp": time.time(),
                "action": action.name,
                "state": self.current_state.name,
                "details": details,
            }
        )