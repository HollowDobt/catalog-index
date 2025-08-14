"""
# src/domains/services/keywords_service.py

Keyword Optimizer

关键词优化器
"""


from typing import Dict, Any
from src.domains.entities.execution_context import ExecutionContext
from src.infrastructure import LLMClient


def summarize_execution_history(context: ExecutionContext) -> str:
    """
    Summarize execution history for context
    """
    if not context.execution_history:
        return "无执行历史"

    recent_actions = context.execution_history[
        -min(4, len(context.execution_history)) :
    ]  # Last 4 actions
    summary = []
    for action in recent_actions:
        summary.append(
            f"- {action['action']}: {action.get('details', {}).get('summary', '执行完成')}"
        )

    return "\n".join(summary)


def generate_adaptive_keywords(evaluation: Dict[str, Any], context: ExecutionContext, llm_query_processor: LLMClient) -> str:
    """
    Generate adaptive keywords based on search evaluation
    """
    prompt_context = f"""
### 原始查询: {context.user_query}
### 当前关键词: {context.current_keywords}
### 搜索尝试次数: {context.search_attempts}
### 找到论文数量: {context.total_papers_found}
### 处理成功率: {evaluation['success_rate']:.2f}
### 建议行动: {evaluation['suggested_action']}
        
## 执行历史摘要:
{summarize_execution_history(context)}
        
## 基于以上信息，生成优化的搜索关键词策略：
    1. 如果没找到论文，扩展搜索范围，使用更通用术语
    2. 如果成功率低，精炼关键词，提高相关性
    3. 如果论文数量少，尝试相关领域或同义词
    4. 结合执行历史避免重复无效搜索
        
## 输出格式：仅输出关键词，用句号分割，不要其他内容
"""
    message = [
        {
            "role": "system",
            "content": "你是一个智能搜索策略优化器，根据搜索历史和结果质量生成最优关键词组合。",
        },
        {"role": "user", "content": prompt_context},
    ]

    response = llm_query_processor.chat_completion(
        messages=message, temperature=0.3
    )

    return response["choices"][0]["message"]["content"]