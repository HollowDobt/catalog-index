"""
============================
|src/domains/agent_state.py|
============================

# Defines all states and intermediate states of the state machine
"""

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List
import time


class AgentState(Enum):
    """
    Agent execution states
    """

    INITIALIZING = (
        auto()
    )  # Initialize the agent, load resources, and prepare the environment.
    ANALYZING_QUERY = (
        auto()
    )  # Analyze the query or task entered by the user to understand the intent.
    PLANNING_SEARCH = (
        auto()
    )  # Develop a search plan, such as selecting keywords, data sources, and API call methods.
    EXECUTING_SEARCH = (
        auto()
    )  # Perform search operations (calling an API, querying a database, etc.).
    PROCESSING_RESULTS = (
        auto()
    )  # Perform preliminary processing on search results (deduplication, screening, and structuring).
    EVALUATING_RESULTS = (
        auto()
    )  # Evaluate the quality of the results and determine whether they meet the requirements.
    REFINING_STRATEGY = (
        auto()
    )  # If the results are not satisfactory, adjust the strategy (change keywords, change data sources, etc.).
    SYNTHESIZING = (
        auto()
    )  # Organize and integrate the final results into output content.
    COMPLETED = auto()  # Mission accomplished.
    ERROR = (
        auto()
    )  # An error occurred (such as network anomaly, data parsing failure, etc.).


class ActionType(Enum):
    """
    Types of actions the agent can take
    """

    QUERY_ANALYSIS = auto()  # Parse the input query, identify intent, and split tasks.
    KEYWORD_GENERATION = auto()  # Generate search keywords or query expressions.
    SEARCH_EXECUTION = auto()  # Perform a search directly
    RESULT_PROCESSING = auto()  # Parse, clean, and format the raw results.
    STRATEGY_REFINEMENT = (
        auto()
    )  # Adjust search/processing strategies to achieve better results.
    SYNTHESIS = auto()  # Synthesize the processed information into a final answer.



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