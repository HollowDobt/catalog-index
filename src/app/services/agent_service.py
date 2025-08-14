"""
# src/app/services/agent_service.py

Manage the lifecycle of the services provided by orchestrator_service.py in the same directory, 
and (plan to) set up thread pools and process managers to provide multi-user services for the front end.

将同目录下 orchestrator_service.py 中提供的服务进行生命周期管理, (计划)设置线程池和进程管理器等为前端提供多用户等服务
"""


import os
from pathlib import Path
from datetime import datetime
import logging
import sys

from src.domains import IntelligentResearchAgent, AgentState


logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """
    Log settings when the main function starts;
    Using Python's logging library
    """
    cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
    log_dir = cache_root / "library-index" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m%d %H:%M%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_dir / f"{datetime.now().strftime('%Y%m%d%H%M%S')}.log", encoding="utf-8")
        ]
    )
    

# LISM -> Library Index State Machine
def LIExecute(LISM: IntelligentResearchAgent) -> str:
    """
    Main execution method with state-based planning
    """
    try:
        while LISM.context.current_state not in [
            AgentState.COMPLETED,
            AgentState.ERROR,
        ]:
            current_state = LISM.context.current_state

            if current_state in LISM.state_handlers:
                next_state = LISM.state_handlers[current_state]()
                LISM._transition_state(next_state)
            else:
                logger.critical(f"Undefined State: {current_state}")
                LISM._transition_state(AgentState.ERROR)
                break

        if LISM.context.current_state == AgentState.COMPLETED:
            logger.info(f"LI task completed")
            return (
                "\n".join(LISM.context.analysis_results)
                if LISM.context.analysis_results
                else "Execution completed, but no relevant results were found"
            )
        else:
            logger.error(f"Abnormal runtime termination")
            return "An error occurred during execution"

    except KeyboardInterrupt:
        logger.info(f"Execution was manually terminated")
        sys.exit(1)

    except Exception as exc:
        logger.error(f"Execution exception: {exc}")
        LISM._transition_state(AgentState.ERROR)
        return f"Execution exception: {exc}"


def main(
    interface: str,
    raw_message_process_llm: str,
    raw_message_process_llm_model: str,
    api_generate_llm: str,
    api_generate_llm_model: str,
    embedding_llm: str,
    embedding_llm_model: str,
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

    setup_logging()
    # Configuration for the intelligent agent
    agent_config = {
        "interface": interface,
        "raw_message_process_llm": raw_message_process_llm,
        "raw_message_process_llm_model": raw_message_process_llm_model,
        "api_generate_llm": api_generate_llm,
        "api_generate_llm_model": api_generate_llm_model,
        "embedding_llm": embedding_llm,
        "embedding_llm_model": embedding_llm_model,
    }

    # Create and execute the intelligent research agent
    agent = IntelligentResearchAgent(agent_config)
    return LIExecute(agent)