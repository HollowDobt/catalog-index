"""
=======================================
|src/application/prompt_to_metadata.py|
=======================================
# This file integrates the entire process from user input to output of scientific research database API code. 
# The internal function return value is a list of API access codes: List[str].
"""


from dataclasses import dataclass
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import threading
import queue
from infrastructure import *
from domains import *


@dataclass
class ArxivRateLimiter:
    """
    ArXiv API rate limiter - strictly adheres to official documentation requirements
    """
    # def __init__(self, min_interval=3.0):
    #     self.min_interval = min_interval
    #     self.last_request_time = 0
    #     self.lock = threading.Lock()
    min_interval: int
    last_request_time = 0
    lock = threading.Lock()
    
    def wait_if_needed(self):
        """
        Ensure that the request interval is >= 3 seconds
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

def process_raw_article_with_llm(
    raw_article: str, 
    meta_id: str, 
    memory: Mem0Client, 
    LLM_client_for_raw_message: LLMClient, 
    raw_message: str, 
    result_queue: queue.Queue
    ) -> None:
    """
    Processing original articles using a large model
    Can be executed concurrently. Speed depends on the service provider
    """
    try:
        # Analytical Articles
        ana_article = LLM_client_for_raw_message.analyze(raw_article)
        
        # Save to Memory
        memory.add_memory(
            messages=ana_article,
            metadata={"id": f"{meta_id}"}
        )
        
        # Find Connections
        result = LLM_client_for_raw_message.find_connect(
            article=ana_article, 
            user_query=raw_message
        )
        
        # Put the results into the queue
        result_queue.put(result)
        print(f"✓ Processing metadata successfully {meta_id}")
        
    except Exception as exc:
        error_msg = f"Error when prcessing metadata: {meta_id}. [Details] {exc}"
        result_queue.put(error_msg)
        print(f"✗ {error_msg}")

def main(
        interface: str,
        raw_message_process_llm: str,
        raw_message_process_llm_model: str,
        api_generate_llm: str,
        api_generate_llm_model: str,
        max_workers_llm=8   # Maximum number of threads for large model processing
    ) -> int:
    """
    From user input to output of scientific research database API code
    
    Strategy:
    1. Serially obtain arXiv search results and file contents (strictly abide by API restrictions)
    2. Parallel processing of large model analysis tasks
    
    Available Param
    -----
    interface: str. "debug"
    raw_message_process/api_generate_llm: str. "deepseek", "qwen"
    raw_message_process_llm_model/api_generate_llm_model: str.
        "deepseek": "deepseek-chat", "deepseek-reasoner"
        "qwen": "qwen3-coder-plus" ...
    max_workers_llm: int. Maximum number of threads for large model processing
    """
    
    operate_interface = IOStream.create(interface)
    raw_message = operate_interface.input("科研人, 今天您来这里是想求证什么呢?")
    
    LLM_client_for_raw_message = LLMClient.create(raw_message_process_llm, model=raw_message_process_llm_model)
    procsee1_message = LLM_client_for_raw_message.chat_completion(
        [{"role": "system", "content": "你是一个关键词与关键句生成器. 根据用户输入的内容生成多个用于检索的关键词和关键句, 用句号分割. 要求, 仅仅输出关键词和关键句, 不得出现其他任何内容(包括'好的'等描述性语句)"},
         {"role": "user", "content": raw_message}]
    )
    
    operate_interface.output(procsee1_message["choices"][0]["message"]["content"])
    add_message = operate_interface.input("上面是我认为可行的关键词和关键句, 您认为还需要补充些什么嘛?(直接输入关键词, 以', '分割)")
    
    LLM_client_for_api_generate = LLMClient.create(api_generate_llm, model=api_generate_llm_model)
    API_RAG = AcademicDBRAG.create("arxiv", LLM_client=LLM_client_for_api_generate)
    api_code = API_RAG.api_coding(procsee1_message["choices"][0]["message"]["content"]+", "+add_message)

    metadata_client = AcademicDBClient.create("arxiv")
    memory = Mem0Client()
    
    print(f"Start processing NUMBER = **{len(api_code)}** API code nodes...")
    
    # Used to collect all metadata
    all_metadata = []
    # Blocking queue for LLM processing results
    result_queue = queue.Queue()
    # Thread pool used to concurrently process large model tasks
    llm_executor = ThreadPoolExecutor(max_workers=max_workers_llm)
    
    try:
        start_time = time.time()
        
        # Process each API code node serially
        for i, api_code_node in enumerate(api_code):
            print(f"\n[{i+1}/{len(api_code)}] (Currently processed API nodes): {api_code_node}")
            
            # Get metadata serially (strictly adhere to arXiv restrictions)
            print("  → Retrieving search results...")
            arxiv_rate_limiter.wait_if_needed()
            
            try:
                metadata_list = metadata_client.search_get_metadata(query=api_code_node, max_num=2)
                all_metadata.extend(metadata_list)
                print(f"  ✓ Get **{len(metadata_list)}** metadata items")
            except Exception as exc:
                print(f"  ✗ Failed to obtain metadata: {exc}")
                continue
            
            # Process each metadata serially
            for j, meta in enumerate(metadata_list):
                print(f"    [{j+1}/{len(metadata_list)}] (Processing metadata): {meta.get('id', 'unknown')}")
                
                # Check Memory
                ana_article_lst = memory.search_metadata(meta['id'])
                if ana_article_lst:
                    print("    ✓ Get analysis results from memory")
                    ana_article = ana_article_lst[0]["memory"]
                    # Directly handle connection lookup (this part can also be concurrent)
                    try:
                        result = LLM_client_for_raw_message.find_connect(
                            article=ana_article, 
                            user_query=raw_message
                        )
                        result_queue.put(result)
                        print(f"    ✓ Completed processing (from memory)")
                    except Exception as exc:
                        result_queue.put(f"Error when processing memory. (ID): **{meta['id']}**. Details: {exc}")
                else:
                    # Serial access to original articles (strictly following arXiv restrictions)
                    print("    → Retrieving article content...")
                    arxiv_rate_limiter.wait_if_needed()
                    try:
                        raw_article = metadata_client.single_metadata_parser(meta)
                        print("    ✓ Successfully obtained article content")
                        
                        # Submit to the thread pool for concurrent large model processing
                        llm_executor.submit(
                            process_raw_article_with_llm,
                            raw_article,
                            meta['id'],
                            memory,
                            LLM_client_for_raw_message,
                            raw_message,
                            result_queue
                        )
                        print("    → Submitted to the large model processing thread pool")
                        
                    except Exception as exc:
                        error_msg = f"Failed to obtain article content **{meta['id']}**. Details: {exc}"
                        result_queue.put(error_msg)
                        print(f"    ✗ {error_msg}")
        
        # Wait for all large model processing tasks to complete
        print(f"\nWait for all large model processing tasks to complete...")
        llm_executor.shutdown(wait=True)
        
        elapsed_time = time.time() - start_time
        print(f"\nAll processing completed, total time: {elapsed_time:.1f} 秒")
        
        # Collect all results
        ans: List[str] = []
        while not result_queue.empty():
            ans.append(result_queue.get())
        
        print(f"Number of total generation results: **{len(ans)}**")
        
        # Output all results
        for result in ans:
            operate_interface.output(result)
            operate_interface.output(" ")
        
        return 0
            
    except KeyboardInterrupt:
        print("\nUser interrupted, resources are being cleaned up...")
        llm_executor.shutdown(wait=False)
        raise
    except Exception as exc:
        print(f"\nAn error occurred during processing: {exc}")
        llm_executor.shutdown(wait=False)
        raise
    finally:
        # Make sure the thread pool is shut down
        if not llm_executor._shutdown:
            llm_executor.shutdown(wait=False)
            return 0