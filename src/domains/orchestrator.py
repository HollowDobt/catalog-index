"""
=============================
|src/domains/orchestrator.py|
=============================

# Intelligent Research Agent
# Advanced AI Agent with State Planning and Adaptive Execution
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from infrastructure import *
from domains import *
from enum import Enum, auto

import time
import threading
import queue
import json
import uuid
import math
import re
from collections import defaultdict


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


@dataclass
class ArxivRateLimiter:
    """
    ArXiv API rate limiter - strictly adheres to official documentation requirements
    """

    min_interval: int
    last_request_time = 0
    lock = threading.Lock()

    def wait_if_needed(self):
        """
        Ensure that the request interval >= 3 seconds
        """
        with self.lock:

            current_time = time.time()
            time_since_last = current_time - self.last_request_time

            if time_since_last < self.min_interval:
                sleep_time = self.min_interval - time_since_last
                time.sleep(sleep_time)

            self.last_request_time = time.time()


# Global rate limiter
arxiv_rate_limiter = ArxivRateLimiter(min_interval=3)


class IntelligentResearchAgent:
    """
    Advanced AI Agent with state-based planning and adaptive execution
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Minimum parameters provided: front-end interactive interface,
        original paper processing LLM, API generator, embedding model
        """
        self.config = config

        # State Log -> context
        self.context = ExecutionContext(
            current_state=AgentState.INITIALIZING,
            search_attempts=0,
            total_papers_found=0,
            processed_papers=0,
            successful_analyses=0,
            failed_analyses=0,
            current_keywords="",
            user_query="",
        )

        # Initialize clients
        self.interface = IOStream.create(config["interface"])
        self.llm_query_processor = LLMClient.create(
            config["raw_message_process_llm"],
            model=config["raw_message_process_llm_model"],
        )
        self.llm_api_generator = LLMClient.create(
            config["api_generate_llm"], model=config["api_generate_llm_model"]
        )
        self.llm_embedding = LLMClient.create(
            config["embedding_llm"], model=config["embedding_llm_model"]
        )

        # Initialize tools
        self.api_rag = AcademicDBRAG.create("arxiv", LLM_client=self.llm_api_generator)
        self.metadata_client = AcademicDBClient.create("arxiv")
        self.memory = Mem0Client()
        self.pdf_parser = PDFToMarkdownConverter()
        self.article_processor = ArticleStructuring(
            llm=config["raw_article_process_llm"],
            llm_model=config["raw_message_process_llm_model"],
        )

        # Thread management
        self.max_workers = config.get("max_workers_llm", 8)
        self.max_search_retries = config.get("max_search_retries", 3)
        self.result_queue = queue.Queue()

        # Agent decision system
        # State Mapping Table: From state to function
        self.state_handlers = {
            AgentState.INITIALIZING: self._handle_initialization,
            AgentState.ANALYZING_QUERY: self._handle_query_analysis,
            AgentState.PLANNING_SEARCH: self._handle_search_planning,
            AgentState.EXECUTING_SEARCH: self._handle_search_execution,
            AgentState.PROCESSING_RESULTS: self._handle_result_processing,
            AgentState.EVALUATING_RESULTS: self._handle_result_evaluation,
            AgentState.REFINING_STRATEGY: self._handle_strategy_refinement,
            AgentState.SYNTHESIZING: self._handle_synthesis,
        }

    def _transition_state(
        self, new_state: AgentState, context_data: Optional[Dict[str, Any]] = None
    ):
        """
        Handle state transitions with logging
        """
        # Record the current status and then update the current status for the next step
        old_state = self.context.current_state
        self.context.current_state = new_state

        # Prepare log data. If context_data is None, use None
        transition_details = {
            "from_state": getattr(old_state, "name", None),
            "to_state": getattr(old_state, "name", None),
            "context_data": context_data,
        }

        print(f"🔄 Agent State: {old_state.name} → {new_state.name}")
        self.context.add_execution_record(ActionType.QUERY_ANALYSIS, transition_details)

    # Search Key-words Enhance Need Assess
    def _evaluate_search_quality(self) -> Dict[str, Any]:
        """
        Evaluate the quality of current search results
        """
        # Storage of Assessment Content
        evaluation = {
            "papers_found": self.context.total_papers_found,
            "success_rate": (
                self.context.successful_analyses / max(1, self.context.processed_papers)
            ),
            "search_efficiency": self.context.total_papers_found
            / max(1, self.context.search_attempts),
            "needs_refinement": False,
            "suggested_action": "continue",
        }

        # Decision logic based on results

        # If a search fails, must search again.
        if self.context.total_papers_found == 0:
            evaluation["needs_refinement"] = True
            evaluation["suggested_action"] = "expand_keywords"

        # If the percentage of successfully parsed papers is too low, must search again.
        elif evaluation["success_rate"] < 0.3:
            evaluation["needs_refinement"] = True
            evaluation["suggested_action"] = "refine_keywords"

        # If the search returns too few results and the number of visits allows, must search again
        elif (
            self.context.total_papers_found < 3
            and self.context.search_attempts < self.max_search_retries
        ):
            evaluation["needs_refinement"] = True
            evaluation["suggested_action"] = "broaden_search"

        return evaluation

    # Search Key-words Enhance Generate
    def _generate_adaptive_keywords(self, evaluation: Dict[str, Any]) -> str:
        """
        Generate adaptive keywords based on search evaluation
        """
        prompt_context = f"""
### 原始查询: {self.context.user_query}
### 当前关键词: {self.context.current_keywords}
### 搜索尝试次数: {self.context.search_attempts}
### 找到论文数量: {self.context.total_papers_found}
### 处理成功率: {evaluation['success_rate']:.2f}
### 建议行动: {evaluation['suggested_action']}
        
## 执行历史摘要:
{self._summarize_execution_history()}
        
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

        response = self.llm_query_processor.chat_completion(
            messages=message, temperature=0.3
        )

        return response["choices"][0]["message"]["content"]

    # Return the summary of the last few records in the log
    def _summarize_execution_history(self) -> str:
        """
        Summarize execution history for context
        """
        if not self.context.execution_history:
            return "无执行历史"

        recent_actions = self.context.execution_history[
            -min(4, len(self.context.execution_history)) :
        ]  # Last 4 actions
        summary = []
        for action in recent_actions:
            summary.append(
                f"- {action['action']}: {action.get('details', {}).get('summary', '执行完成')}"
            )

        return "\n".join(summary)

    # Filter invalid information to reduce token consumption
    def _filter_invalid_content(self, content: str) -> str:
        """
        Filter out invalid or meaningless content from analysis results

        params
        ------
        content: Original find_connect return value

        return
        ------
        Pure valid information after filtering the original value
        """
        if not content or not isinstance(content, str):
            return ""

        # Define patterns for invalid content
        invalid_patterns = [
            # Chinese
            r"没有?找到.*?关联",
            r"未能?找到.*?连接",
            r"无法.*?建立联系",
            r"缺乏.*?相关性",
            r"不存在.*?直接关系",
            r"无相关.*?信息",
            r"无法.*?确定关联",
            r"未发现.*?联系",
            r"抱歉.*?没有找到",
            r"很抱歉.*?无法",
            r"对不起.*?找不到",
            r"没有相关.*?内容"
            # English
            r"not\s+found.*?(connection|link|relation|association)",
            r"unable\s+to\s+find.*?(connection|link|relation|association)",
            r"cannot\s+(establish|create|make).*?(connection|link|relation|association)",
            r"lack(s)?\s+.*?(relevance|relevancy|relation|association)",
            r"no\s+.*?(direct\s+relation|direct\s+link|direct\s+connection)",
            r"no\s+related.*?(information|content|data)",
            r"cannot\s+determine.*?(relation|association|connection)",
            r"(not\s+found|did\s+not\s+find).*(contact|connection|relation|link)",
            r"sorry.*?(no|not\s+found|unable)",
            r"apologies.*?(no|not\s+found|unable)",
            r"no\s+related.*?(content|information|data)",
        ]

        # Check if content contains too many invalid patterns
        invalid_count = 0
        for pattern in invalid_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                invalid_count += 1

        # If more than half the content is invalid patterns, filter it out
        total_sentences = len(re.split(r"[。！？.!?\n]", content))
        if invalid_count > total_sentences * 0.5:  # 50% threshold
            return ""

        # Remove specific invalid sentences but keep the rest
        filtered_content = content
        for pattern in invalid_patterns:
            filtered_content = re.sub(
                pattern + r"[。！？]*", "", filtered_content, flags=re.IGNORECASE
            )

        # Clean up extra whitespace
        filtered_content = re.sub(r"\n\s*\n", "\n", filtered_content.strip())

        # Return empty if too short after filtering
        if len(filtered_content.strip()) < 50:
            return ""

        return filtered_content.strip()

    # Let the AI merge the results of the two diffenret find_connect calls
    def _merge_two_contents(
        self, content1: str, content2: str, max_tokens: int, level: int
    ) -> str:
        """
        Merge two content pieces using LLM with specified token limit

        params
        ------
        content1 & content2: Two result segments that need to be merged
        max_tokens: The maximum number of tokens allowed to be consumed
        level:

        return
        ------

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
{self.context.user_query}

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

            response = self.llm_query_processor.chat_completion(
                messages=message, temperature=0.3, max_tokens=max_tokens
            )

            merged_content = response["choices"][0]["message"]["content"].strip()

            # Final filtering of the merged content
            final_content = self._filter_invalid_content(merged_content)
            return final_content if final_content else (content1 or content2)

        except Exception as exc:
            print(f"  ⚠️ 合并失败 (级别 {level}): {exc}")
            # Fallback: simple concatenation with filtering
            fallback = f"{content1}\n\n{content2}"
            return self._filter_invalid_content(fallback) or (content1 or content2)

    # The final step is to combine multiple results into one
    def _intelligent_synthesis_merge(self, results: List[str]) -> str:
        """
        Use binary tree merging with thread pool for intelligent content synthesis
        """
        if not results:
            return ""

        # Filter out invalid results first
        valid_results: List[str] = []
        for result in results:
            filtered_result = self._filter_invalid_content(result)
            if filtered_result:
                valid_results.append(filtered_result)

        if not valid_results:
            return ""

        if len(valid_results) == 1:
            return valid_results[0]

        print(f"🧠 开始智能信息整合，共 {len(valid_results)} 个有效结果")

        current_level = valid_results.copy()
        level = 0

        while len(current_level) > 1:
            level += 1
            # Dynamic token allocation: increase tokens as we go up the merge tree
            base_tokens = 1000  # Base tokens for first level
            max_tokens = min(base_tokens + (level * 500), 4000)  # Cap at 4000 tokens

            print(
                f"  📊 合并级别 {level}，处理 {len(current_level)} 个片段，允许 {max_tokens} tokens"
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
                max_workers=min(self.max_workers, len(pairs)),
                thread_name_prefix="LI-merge_worker",
            ) as executor:
                future_to_pair = {}
                for idx, (content1, content2) in enumerate(pairs):
                    future = executor.submit(
                        self._merge_two_contents, content1, content2, max_tokens, level
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
                        print(
                            f"    ✓ 完成合并对: {pair_idx}, {pair_idx + 1}. 总长度: {len(pairs)}"
                        )
                    except Exception as exc:
                        print(f"    ✗ 合并对 {pair_idx}, {pair_idx + 1} 失败: {exc}")
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
            print(f"  ✅ 级别 {level} 完成，剩余 {len(current_level)} 个片段")

        final_result = current_level[0] if current_level else ""
        print(f"🎯 智能整合完成，最终结果长度: {len(final_result)} 字符")

        return final_result

    # Generate a prompt-word paper abstract based on a single metadata
    def _process_single_paper(self, meta: Dict[str, Any]) -> None:
        """
        Process a single paper with error handling
        """
        try:
            arxiv_rate_limiter.wait_if_needed()
            raw_article_address = self.metadata_client.single_metadata_parser(meta)

            # Analyze the article
            ana_article = self.article_processor.analyze(
                self.pdf_parser.convert(raw_article_address).markdown_text
            )
            self.memory.add_memory(messages=ana_article, metadata={"id": meta["id"]})

            # Find connections
            self.result_queue.put(
                self.llm_embedding.find_connect(
                    article=ana_article, user_query=self.context.user_query
                )
            )
            self.context.successful_analyses += 1
            print(f"    ✓ 成功处理: {meta['id']}")

        except Exception as exc:
            error_message = f"处理失败 (ID: {meta['id']}): {exc}"
            self.result_queue.put(error_message)
            self.context.failed_analyses += 1
            print(f"    ✗ {error_message}")

    ### STATE FUNCTION
    # Startup Function
    def _handle_initialization(self) -> AgentState:
        """
        Initialize the agent and gather user input
        """
        print("🤖 智库索引已启动")

        user_query = self.interface.input("科研人, 今天你来此地是为了寻找什么?")
        self.context.user_query = user_query

        # Logging
        self.context.add_execution_record(
            action=ActionType.QUERY_ANALYSIS,
            details={"user_query": user_query, "summary": "用户已发送检索请求"},
        )

        return AgentState.ANALYZING_QUERY

    ### STATE FUNCTION
    # Keyword generation function
    def _handle_query_analysis(self) -> AgentState:
        """
        Analyze user query and generate initial keywords
        """
        print("🔍 分析用户查询中...")

        analysis_prompt = """
你是一个科研查询分析专家。分析用户的研究问题，生成高质量的搜索关键词。

## 要求：
    1. 提取核心研究概念和方法
    2. 识别相关研究领域和子领域
    3. 生成多样化的关键词组合
    4. 考虑技术术语和通用术语的平衡
    5. 输出格式：仅输出关键词，用句号分割
"""

        message = [
            {"role": "system", "content": analysis_prompt},
            {"role": "user", "content": self.context.user_query},
        ]

        response = self.llm_query_processor.chat_completion(
            messages=message, temperature=0.7
        )

        initial_keywords = response["choices"][0]["message"]["content"]
        self.context.current_keywords = initial_keywords

        # Show generated keywords to user for feedback
        self.interface.output(
            f"这些检索对象是否足够了? 不够请继续补充, 我会带上一起找: \n**{initial_keywords}**"
        )
        additional_keywords = self.interface.input(
            "(直接输入关键词, 用逗号分割, 或按回车跳过)"
        )

        if additional_keywords.strip():
            self.context.current_keywords += ", " + additional_keywords

        # Logging
        self.context.add_execution_record(
            action=ActionType.KEYWORD_GENERATION,
            details={
                "initial_keywords": initial_keywords,
                "additional_keywords": additional_keywords,
                "final_keywords": self.context.current_keywords,
                "summary": "关键词生成完成",
            },
        )

        return AgentState.PLANNING_SEARCH

    ### STATE FUNCTION
    # Function for accessing code generation
    def _handle_search_planning(self) -> AgentState:
        """
        Plan the search strategy based on current context
        """
        print("📋 规划搜索策略...")

        api_queries = self.api_rag.api_coding(self.context.current_keywords)

        search_plan = {
            "total_queries": len(api_queries),
            "max_papers_per_query": 2,
            "expected_total_papers": len(api_queries) * 2,
            "search_strategy": "systematic_parallel",
        }

        print(
            f"📊 搜索计划: {search_plan['total_queries']} 个查询节点, 预期找到 {search_plan['expected_total_papers']} 篇论文"
        )

        # Logging
        self.context.add_execution_record(
            action=ActionType.SEARCH_EXECUTION,
            details={
                "api_queries": api_queries,
                "search_plan": search_plan,
                "summary": f"生成 {len(api_queries)} 个搜索查询",
            },
        )

        # Store queries in context for execution
        self.context.search_results = [
            {"query": query, "status": "pending"} for query in api_queries
        ]

        return AgentState.EXECUTING_SEARCH

    ### STATE FUNCTION
    # Function for searching through accessing code
    def _handle_search_execution(self) -> AgentState:
        """
        Execute the planned searches
        """
        print("🔎 执行搜索策略...")

        all_metadata: List[Dict[str, Any]] = []
        papers_found_in_attempt = False

        for i, search_item in enumerate(self.context.search_results):
            if search_item["status"] != "pending":
                continue

            query = search_item["query"]
            print(f"[{i+1}/{len(self.context.search_results)}] 执行查询: {query}")

            # Strictly require access speed to be less than 1 time per 3 seconds on ARXIV_STANDARD
            arxiv_rate_limiter.wait_if_needed()

            try:
                metadata_list = self.metadata_client.search_get_metadata(
                    query=query, max_num=2
                )

                # Retrieve available results
                if metadata_list:
                    papers_found_in_attempt = True
                    all_metadata.extend(metadata_list)
                    search_item["status"] = "completed"
                    search_item["results"] = metadata_list
                    print(f"  ✓ 找到 {len(metadata_list)} 篇论文")
                # No available results
                else:
                    search_item["status"] = "no_results"
                    print(f"  ⚠ 此查询未找到论文")

            except Exception as exc:
                search_item["status"] = "error"
                search_item["error"] = str(exc)
                print(f"  ✗ 搜索失败: {exc}")

        # Logging
        self.context.total_papers_found = len(all_metadata)
        self.context.search_attempts += 1
        self.context.add_execution_record(
            action=ActionType.SEARCH_EXECUTION,
            details={
                "papers_found": len(all_metadata),
                "attempt_number": self.context.search_attempts,
                "summary": f"搜索完成，找到 {len(all_metadata)} 篇论文",
            },
        )

        # Store metadata for processing
        self.all_metadata = all_metadata

        if papers_found_in_attempt:
            return AgentState.PROCESSING_RESULTS
        else:
            return AgentState.EVALUATING_RESULTS

    ### STATE FUNCTION
    # Structuring the paper into prompt words
    def _handle_result_processing(self) -> AgentState:
        """
        Process the found papers using LLM analysis
        """
        print("🧠 处理论文内容...")

        if not hasattr(self, "all_metadata") or not self.all_metadata:
            return AgentState.EVALUATING_RESULTS

        with ThreadPoolExecutor(
            max_workers=self.max_workers, thread_name_prefix="LI-llm_worker"
        ) as executor:
            futures = []

            for meta in self.all_metadata:
                print(f"  📄 处理论文: {meta.get('id', 'unknown')}")

                # Check memory first
                cached_analysis = self.memory.search(meta["id"])
                if cached_analysis:
                    print("    ✓ 从记忆层获取分析结果")
                    try:
                        result = self.llm_embedding.find_connect(
                            article=cached_analysis[0]["memory"],
                            user_query=self.context.user_query,
                        )
                        self.result_queue.put(result)
                        self.context.successful_analyses += 1
                    except Exception as exc:
                        self.result_queue.put(
                            f"记忆层处理错误 (ID: {meta['id']}): {exc}"
                        )
                        self.context.failed_analyses += 1

                # Direct parsing of non-indexed content in the memory layer
                else:
                    # Submit to process
                    future = executor.submit(self._process_single_paper, meta)
                    futures.append(future)

            # Wait for all processing to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    print(f"  ✗ 论文处理失败: {exc}")

        self.context.processed_papers = len(self.all_metadata)

        # Logging
        self.context.add_execution_record(
            action=ActionType.RESULT_PROCESSING,
            details={
                "total_processed": self.context.processed_papers,
                "successful": self.context.successful_analyses,
                "failed": self.context.failed_analyses,
                "summary": f"处理完成：{self.context.successful_analyses}/{self.context.processed_papers} 成功",
            },
        )

        return AgentState.EVALUATING_RESULTS

    ### STATE FUNCTION
    # Evaluator for search results
    def _handle_result_evaluation(self) -> AgentState:
        """
        Evaluate the quality of results and decide next action
        """
        print("📊 评估搜索结果质量...")

        evaluation = self._evaluate_search_quality()

        print(f"  📈 评估结果：")
        print(f"    - 找到论文: {evaluation['papers_found']}")
        print(f"    - 成功率: {evaluation['success_rate']:.2%}")
        print(f"    - 搜索效率: {evaluation['search_efficiency']:.2f}")
        print(f"    - 建议行动: {evaluation['suggested_action']}")

        # Logging
        self.context.add_execution_record(
            action=ActionType.STRATEGY_REFINEMENT,
            details={
                "evaluation": evaluation,
                "summary": f"评估完成，建议: {evaluation['suggested_action']}",
            },
        )

        if (
            evaluation["needs_refinement"]
            and self.context.search_attempts < self.max_search_retries
        ):
            return AgentState.REFINING_STRATEGY
        else:
            return AgentState.SYNTHESIZING

    ### STATE FUNCTION
    # Avoid generating the same keywords and regenerate based on it
    def _handle_strategy_refinement(self) -> AgentState:
        """
        Refine search strategy based on evaluation
        """
        print("🔧 优化搜索策略...")

        evaluation = self._evaluate_search_quality()
        new_keywords = self._generate_adaptive_keywords(evaluation)

        print(f"  🔄 关键词优化:")
        print(f"    原关键词: {self.context.current_keywords}")
        print(f"    新关键词: {new_keywords}")

        self.context.current_keywords = new_keywords

        # Logging
        self.context.add_execution_record(
            action=ActionType.STRATEGY_REFINEMENT,
            details={
                "old_keywords": self.context.current_keywords,
                "new_keywords": new_keywords,
                "summary": "完成搜索策略优化",
            },
        )

        return AgentState.PLANNING_SEARCH

    ### STATE FUNCTION
    # Combining all the previous papers to generate the final results with intelligent synthesis
    def _handle_synthesis(self) -> AgentState:
        """
        Synthesize all results using intelligent binary-merge algorithm and present to user
        """
        print("🔬 综合分析结果...")

        # Collect all results
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get())

        self.context.analysis_results = results

        if results:
            print(f"📄 收集到 {len(results)} 个分析结果，开始整合所有信息...")

            # Use intelligent synthesis merge instead of simple concatenation
            intelligently_merged_content = self._intelligent_synthesis_merge(results)

            synthesis_summary = f"""

# 🎯 智库索引执行报告

## 📋 执行概况
- 查询分析: ✓
- 搜索尝试: {self.context.search_attempts} 次
- 找到论文: {self.context.total_papers_found} 篇
- 成功分析: {self.context.successful_analyses} 篇
- 分析成功率: {(self.context.successful_analyses/max(1,self.context.processed_papers)):.1%}

## 📚 研究发现
{intelligently_merged_content}
"""
            print("✨ 全整合完成")
            print(synthesis_summary)
            self.interface.output(synthesis_summary)

        else:
            no_result_message = f"""
# 🎯 智库索引执行报告

经过 {self.context.search_attempts} 次智能搜索尝试，未能找到与您的查询直接相关的高质量论文。

## 建议
1. 尝试更通用或相关的关键词
2. 扩展搜索到相关研究领域
3. 检查查询的具体性是否合适
"""
            print(no_result_message)
            self.interface.output(no_result_message)

        # Logging
        self.context.add_execution_record(
            action=ActionType.SYNTHESIS,
            details={
                "total_results": len(results),
                "execution_summary": {
                    "search_attempts": self.context.search_attempts,
                    "papers_found": self.context.total_papers_found,
                    "successful_analyses": self.context.successful_analyses,
                },
                "summary": "已完成解析与提示词索引生成",
            },
        )

        return AgentState.COMPLETED

    # Process execution function
    # The only directly callable function of this class
    def execute(self) -> str:
        """
        Main execution method with state-based planning.
        """
        try:
            while self.context.current_state not in [
                AgentState.COMPLETED,
                AgentState.ERROR,
            ]:
                current_state = self.context.current_state

                if current_state in self.state_handlers:
                    next_state = self.state_handlers[current_state]()
                    self._transition_state(next_state)
                else:
                    print(f"⚠️ 未定义状态: {current_state}")
                    self._transition_state(AgentState.ERROR)
                    break

            if self.context.current_state == AgentState.COMPLETED:
                print(f"✅ 智能研究助手执行完成")
                return (
                    "\n".join(self.context.analysis_results)
                    if self.context.analysis_results
                    else "执行完成，但未找到相关结果"
                )
            else:
                print(f"❌ 运行时异常终止")
                return "执行中发生错误"

        except KeyboardInterrupt:
            print(f"❌ 执行被手动终止")
            return "用户手动终止检索"

        except Exception as exc:
            print(f"❌ 执行异常: {exc}")
            self._transition_state(AgentState.ERROR)
            return f"执行异常: {exc}"


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
