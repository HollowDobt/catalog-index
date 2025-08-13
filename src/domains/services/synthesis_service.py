"""
# src/domains/services/synthesis_service.py

Content merger, used to organize the relevance analysis results of all papers 
when finally outputting them to users

内容合并器, 用于最终向用户输出时整理所有论文的相关性分析结果
"""


from typing import List
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from domains.entities.execution_context import ExecutionContext
from infrastructure import LLMClient, filter_invalid_content


logger = logging.getLogger(__name__)

def merge_two_contents(
    content1: str, content2: str, max_tokens: int, level: int, context: ExecutionContext, 
    llm_query_processor: LLMClient
) -> str:
    """
    Merge two content pieces using LLM with specified token limit
    """

    # If both are empty, return empty
    if not content1 and not content2:
        return ""

    # If either content is empty after filtering, return the other
    if not content1:
        return content2
    if not content2:
        return content1

    system_prompt = f"""
你是一个专业的学术信息整合专家。擅长将多个研究内容合并为结构化、逻辑清晰的综合报告。请将用户提供的两段研究内容进行智能合并，要求：

1. **保持信息完整性**：不丢失重要的研究发现和核心观点
2. **消除冗余**：合并重复信息，避免不必要的重复
3. **逻辑整理**：按照逻辑关系重新组织内容结构
4. **语言优化**：确保合并后的内容语言流畅、条理清晰
5. **突出关联**：强调内容间的关联性和互补性
6. **控制长度**：合并后的内容应控制在{max_tokens}个token以内
"""

    merge_prompt = f"""
## 用户原始查询
{context.user_query}

## 内容A
{content1}

## 内容B  
{content2}

## 合并要求
- 围绕用户查询进行内容整合
- 突出两个内容的互补性和关联性
- 去除冗余信息，保留核心观点
- 确保合并后内容逻辑清晰、结构完整
- 输出简洁且信息密度高的整合结果

请直接输出合并后的内容，不要包含任何说明文字：
"""

    try:
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": merge_prompt},
        ]

        response = llm_query_processor.chat_completion(
            messages=message, temperature=0.3, max_tokens=max_tokens
        )

        merged_content = response["choices"][0]["message"]["content"].strip()

        # Final filtering of the merged content
        final_content = filter_invalid_content(merged_content)
        return final_content if final_content else (content1 or content2)

    except Exception as exc:
        logger.warning(f"Merge failed. (Level: {level}): {exc}")
        # Fallback: simple concatenation with filtering
        fallback = f"{content1}\n\n{content2}"
        return filter_invalid_content(fallback) or (content1 or content2)


# The final step is to combine multiple results into one
def intelligent_synthesis_merge(results: List[str], context: ExecutionContext, llm_query_processor: LLMClient, max_workers: int) -> str:
    """
    Use binary tree merging with thread pool for intelligent content synthesis
    """
    if not results:
        logger.warning("No valid information. Returns None")
        return ""

    # Filter out invalid results first
    valid_results: List[str] = []
    for result in results:
        filtered_result = filter_invalid_content(result)
        if filtered_result:
            valid_results.append(filtered_result)

    if not valid_results:
        logger.warning("No valid information. Returns None")
        return ""

    if len(valid_results) == 1:
        return valid_results[0]

    logger.info(f"Start integration, a total of *{len(valid_results)}* valid results")

    current_level = valid_results.copy()
    level = 0

    while len(current_level) > 1:
        level += 1
        # Dynamic token allocation: increase tokens as we go up the merge tree
        base_tokens = 1000  # Base tokens for first level
        max_tokens = min(base_tokens + (level * 500), 4000)  # Cap at 4000 tokens

        logger.info(
            f"Now processing level: {level}; Total: *{len(current_level)}*,  allow *{max_tokens}* tokens"
        )

        # Create pairs for merging
        pairs = []
        for i in range(0, len(current_level), 2):
            if i + 1 < len(current_level):
                pairs.append((current_level[i], current_level[i + 1]))
            else:
                # Odd number: the last item goes to next level directly
                pairs.append((current_level[i], ""))

        # Merge pairs in parallel using thread pool
        next_level = []
        with ThreadPoolExecutor(
            max_workers=min(max_workers, len(pairs)),
            thread_name_prefix="LI-merge_worker",
        ) as executor:
            future_to_pair = {}
            for idx, (content1, content2) in enumerate(pairs):
                future = executor.submit(
                    merge_two_contents, content1, content2, max_tokens, level, context, llm_query_processor
                )
                future_to_pair[future] = idx

            # Collect results in order
            pair_results = [""] * len(pairs)
            for future in as_completed(future_to_pair):
                pair_idx = future_to_pair[future]
                try:
                    merged_result = future.result()
                    if merged_result:  # Only keep non-empty results
                        pair_results[pair_idx] = merged_result
                    logger.info(
                        f"Complete the merger: {pair_idx}, {pair_idx + 1}. Total length now: *{len(pairs)}*"
                    )
                except Exception as exc:
                    logger.warning(f"Merge failed: {pair_idx}, {pair_idx + 1}; Details: {exc}")
                    # Fallback: use the first content of the pair
                    pair_results[pair_idx] = (
                        pairs[pair_idx][0] if pairs[pair_idx][0] else ""
                    )

            # Filter out None and empty results
            next_level = [
                result for result in pair_results if result and result.strip()
            ]

        if not next_level:
            # If all merging failed, return the best we have
            return valid_results[0] if valid_results else ""

        current_level = next_level
        logger.info(f"Now level processing finished: *{level}*; remaining: *{len(current_level)}*")

    final_result = current_level[0] if current_level else ""
    logger.info(f"Intelligent integration is completed, the final result length: {len(final_result)}")

    return final_result