"""
=======================================
|src/application/prompt_to_metadata.py|
=======================================

# This file integrates the entire process from user input to output of scientific research database API code. 
# The internal function return value is a list of API access codes: List[str].
"""

from typing import List
from infrastructure import *
from domains import *

def prompt_to_metadata(
        interface: str,
        raw_message_process_llm: str,
        raw_message_process_llm_model: str,
        api_generate_llm: str,
        api_generate_llm_model: str
    ) -> List[str]:
    """
    From user input to output of scientific research database API code
    
    Available Param
    -----
    interface: str. "debug"
    raw_message_process/api_generate_llm: str. "deepseek", "qwen"
    raw_message_process_llm_model/api_generate_llm_model: str.
        "deepseek": "deepseek-chat", "deepseek-reasoner"
        "qwen": "qwen3-coder-plus" ...
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
    return API_RAG.api_coding(procsee1_message["choices"][0]["message"]["content"]+", "+add_message)