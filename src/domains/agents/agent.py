"""
# src/domians/agents/agent.py

Define the functions corresponding to all states and wrap them in the core class IntelligentResearchAgent

定义所有状态对应的函数与状态间关系, 包装在核心类 IntelligentResearchAgent 中
"""


from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue
import logging

from src.infrastructure import (
    RateLimiter,
    LLMClient,
    AcademicDBAPIGenerator,
    AcademicDBClient,
    Mem0Client,
    PDFToMarkdownConverter,
    ArticleStructuring
)
from src.config import CONFIG
from src.domains.agents.agent_states import ActionType, AgentState
from src.domains.entities import ExecutionContext
from src.domains.services import (
    evaluate_search_quality,
    generate_adaptive_keywords,
    intelligent_synthesis_merge,
    find_connect,
    evaluate_abstract_relevance
)


logger = logging.getLogger(__name__)

ADB_rate_limiter = RateLimiter(min_interval=CONFIG["ADB_RATE_LIMITER"])


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
        self.api_rag = AcademicDBAPIGenerator.create("arxiv", LLM_client=self.llm_api_generator)
        self.metadata_client = AcademicDBClient.create("arxiv")
        self.memory = Mem0Client()
        self.pdf_parser = PDFToMarkdownConverter()
        self.article_processor = ArticleStructuring(
            llm=config["raw_message_process_llm"],
            llm_model=config["raw_message_process_llm_model"],
        )

        # Thread management
        # self.max_workers = config.get("max_workers_llm", 8)
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

        logger.info(f"Agent State Changes: {old_state.name} → {new_state.name}")
        self.context.add_execution_record(ActionType.QUERY_ANALYSIS, transition_details)
        
        
    ### STATE FUNCTION
    # Startup Function
    def _handle_initialization(self) -> AgentState:
        """
        Initialize the agent and gather user input
        """
        logger.info("⁽⁽٩(๑˃̶͈̀ ᗨ ˂̶͈́)۶⁾⁾ Library Index has been launched")

        user_query = input("⁽⁽٩(๑˃̶͈̀ ᗨ ˂̶͈́)۶⁾⁾ 科研人, 今天你来此地是为了寻找什么?")
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
        logger.info("(*ˇωˇ*人) Generating keywords...")

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
        print(
            f"(*ˇωˇ*人) 这些检索对象是否足够了? 不够请继续补充, 我会带上一起找: \n**{initial_keywords}**"
        )
        additional_keywords = input(
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
        logger.info("╮(╯∀╰)╭ Planning a search strategy...")

        api_queries = self.api_rag.api_coding(self.context.current_keywords)

        search_plan = {
            "total_queries": len(api_queries),
            "max_papers_per_query": CONFIG["ADB_SEARCH_MAX_RESULTS"],
            "expected_total_papers": len(api_queries) * CONFIG["ADB_SEARCH_MAX_RESULTS"],
            "search_strategy": "systematic_parallel",
        }

        logger.info(
            f"Search Plan: In total *{search_plan['total_queries']}*, expected *{search_plan['expected_total_papers']}* papers"
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
        logger.info("ε٩(๑> ₃ <)۶з Executing search strategies...")

        all_metadata: List[Dict[str, Any]] = []
        papers_found_in_attempt = False

        for i, search_item in enumerate(self.context.search_results):
            if search_item["status"] != "pending":
                continue

            query = search_item["query"]
            logger.info(f"[{i+1}/{len(self.context.search_results)}] Execute query: *{query}*")

            ADB_rate_limiter.wait_if_needed()

            try:
                metadata_list = self.metadata_client.search_get_metadata(
                    query=query, max_num=CONFIG["ADB_SEARCH_MAX_RESULTS"]
                )

                # Retrieve available results
                if metadata_list:
                    papers_found_in_attempt = True
                    all_metadata.extend(metadata_list)
                    search_item["status"] = "completed"
                    search_item["results"] = metadata_list
                    logger.info(f"  ✓ Found articles number: {len(metadata_list)}")
                # No available results
                else:
                    search_item["status"] = "no_results"
                    logger.warning(f"  ⚠ No metadata found")

            except Exception as exc:
                search_item["status"] = "error"
                search_item["error"] = str(exc)
                logger.warning(f"Retrieval failed. Details: {exc}")

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
    
    
    def _process_single_paper(self, meta: Dict[str, Any]) -> None:
        """
        Process a single paper with error handling
        """
        try:
            ADB_rate_limiter.wait_if_needed()
            raw_article_address = self.metadata_client.single_metadata_parser(meta)

            # Analyze the article
            ana_article = self.article_processor.analyze(
                self.pdf_parser.convert(raw_article_address).markdown_text
            )
            self.memory.add_memory(messages=ana_article, metadata={"id": meta["id"]})

            # Find connections
            self.result_queue.put(
                find_connect(
                    llm_embedding=self.llm_embedding ,article=ana_article, user_query=self.context.user_query
                )
            )
            self.context.successful_analyses += 1
            logger.info(f"Successfully processed: {meta['id']}")

        except Exception as exc:
            error_message = f"Processing failed (ID: {meta['id']}): {exc}"
            self.result_queue.put(error_message)
            self.context.failed_analyses += 1
            logger.warning(f"{error_message}")
    
    
    ### STATE FUNCTION
    # Structuring the paper into prompt words
    def _handle_result_processing(self) -> AgentState:
        """
        Process the found papers using LLM analysis
        """
        logger.info("ヾ(●゜▽゜●)♡ Processing paper content...")

        if not hasattr(self, "all_metadata") or not self.all_metadata:
            logger.warning("No metadata found")
            return AgentState.EVALUATING_RESULTS
        
        # Filter papers by abstract relevance first
        relevant_metadata: List[Dict[str, Any]] = []
        filtered_count = 0
        
        for meta in self.all_metadata:
            paper_id = meta.get("id", "unknown")
            abstract = meta.get("summary", "")
            
            if not abstract.strip():
                logger.warning(f"No abstract found for paper {paper_id}, skipping relevance check")
                relevant_metadata.append(meta)
                continue
            
            # Evaluate abstract relevance
            try:
                relevance_score = evaluate_abstract_relevance(
                    llm_embedding=self.llm_embedding,
                    abstract=abstract,
                    user_query=self.context.user_query
                )
                
                if relevance_score >= CONFIG["MINIMUM_RELEVANCE_THRESHOLD"]:
                    relevant_metadata.append(meta)
                    logger.info(f"Paper {paper_id} passed relevance filter (score: {relevance_score:.2f})")
                else:
                    filtered_count += 1
                    logger.info(f"Paper {paper_id} filtered out (score: {relevance_score:.2f} < {CONFIG['MINIMUM_RELEVANCE_THRESHOLD']})")
                    
            except Exception as exc:
                logger.warning(f"Error evaluating relevance for {paper_id}: {exc}, including paper anyway")
                relevant_metadata.append(meta)
        
        logger.info(f"Abstract relevance filtering: {len(relevant_metadata)} papers passed, {filtered_count} filtered out")
        
        if not relevant_metadata:
            logger.warning("No papers passed relevance filtering")
            return AgentState.EVALUATING_RESULTS
        
        with ThreadPoolExecutor(
            max_workers=CONFIG["MAX_WORKERS"], thread_name_prefix="LI-llm_worker"
        ) as executor:
            futures = []

            for meta in relevant_metadata:
                logger.info(f"ヾ(●゜▽゜●)♡ Processing papers: {meta.get('id', 'unknown')}")

                # Check memory first
                cached_analysis = self.memory.search_metadata(meta["id"])
                if cached_analysis:
                    logger.info("✓ Get analysis results from the memory layer")
                    try:
                        result = find_connect(
                            llm_embedding=self.llm_embedding,
                            article=cached_analysis[0]["memory"],
                            user_query=self.context.user_query
                        )
                        self.result_queue.put(result)
                        self.context.successful_analyses += 1
                    except Exception as exc:
                        self.result_queue.put(
                            f"记忆层处理错误 (ID: {meta['id']}): {exc}"
                        )
                        self.context.failed_analyses += 1
                        logger.warning(f"Memory layer processing errors (ID: {meta['id']}): {exc}")

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
                    logger.warning(f"Paper processing failed: {exc}")

        self.context.processed_papers = len(relevant_metadata)

        # Logging
        self.context.add_execution_record(
            action=ActionType.RESULT_PROCESSING,
            details={
                "total_found": len(self.all_metadata),
                "filtered_by_relevance": filtered_count,
                "total_processed": self.context.processed_papers,
                "successful": self.context.successful_analyses,
                "failed": self.context.failed_analyses,
                "relevance_threshold": CONFIG["MINIMUM_RELEVANCE_THRESHOLD"],
                "summary": f"处理完成：通过相关性过滤 {len(relevant_metadata)}/{len(self.all_metadata)} 篇，成功分析 {self.context.successful_analyses}/{self.context.processed_papers} 篇",
            },
        )

        return AgentState.EVALUATING_RESULTS
    
    
    ### STATE FUNCTION
    # Evaluator for search results
    def _handle_result_evaluation(self) -> AgentState:
        """
        Evaluate the quality of results and decide next action
        """
        logger.info("ฅ●ω●ฅ Evaluate search result quality...")

        evaluation = evaluate_search_quality(self.context)

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
            and self.context.search_attempts < CONFIG[""]
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
        logger.info("▼・ᴥ・▼ Optimize search strategy...")

        evaluation = evaluate_search_quality(self.context)
        new_keywords = generate_adaptive_keywords(evaluation=evaluation, context=self.context, llm_query_processor=self.llm_query_processor)

        logger.info(f"ฅ^•ﻌ•^ฅ Keyword optimization: Original keywords: {self.context.current_keywords}; New Keywords: {new_keywords}")

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
        logger.info("o(☆Ф∇Ф☆)o Comprehensive analysis results...")

        # Collect all results
        results = []
        while not self.result_queue.empty():
            results.append(self.result_queue.get())

        self.context.analysis_results = results

        if results:
            logger.info(f"(＊゜ー゜)b Collecting analysis results(NUM): {len(results)}; Start integrating all the information...")

            # Use intelligent synthesis merge instead of simple concatenation
            intelligently_merged_content = intelligent_synthesis_merge(results, context=self.context, llm_query_processor=self.llm_query_processor, max_workers=CONFIG["MAX_WORKERS"])

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