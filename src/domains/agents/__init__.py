"""
# src/domains/agents

Core module, main logic IntelligentResearchAgent, defines the relationship between state functions and states

核心模块, 主要逻辑 IntelligentResearchAgent, 定义状态函数与状态之间的关系
"""


from .agent_states import ActionType, AgentState
from .agent import IntelligentResearchAgent


__all__ = ["ActionType", "AgentState", "IntelligentResearchAgent"]