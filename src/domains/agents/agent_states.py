"""
# src/domains/agents/agent_states.py

Define all states of the agent

定义智能体的所有状态
"""


from enum import Enum, auto


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