"""
# src/infrastructure/RAG/api_coder/arxiv/arxiv_rag.py

Enhanced api coder generator class, arixv RAG

加强 api coder 生成器类, arixv RAG
"""

from typing import List
import ast
import json
import re
import logging

from infrastructure.RAG.api_coder.arxiv.arxiv_allowed_constants import *
from infrastructure.RAG.api_coder.arxiv.arxiv_utils import *
from infrastructure.RAG.api_coder.ADB_api_coder import AcademicDBAPIGenerator
from infrastructure.clients import LLMClient


logger = logging.getLogger(__name__)


@AcademicDBAPIGenerator.register("arxiv")
class ArxivAPIGenerator(AcademicDBAPIGenerator):
    """
    RAG class that converts user requirements into ArXiv search expressions
    """
    
    def __init__(self, LLM_client: LLMClient) -> None:
        self.LLM_client: LLMClient = LLM_client
    
    def api_coding(self, request: str) -> List[str]:
        """
        API code generation function
        """
        if not request or not request.strip():
            logger.warning("The request is empty, no valid value")
            return ast.literal_eval(json.dumps([]))

        user_input = request.strip()
        
        system_prompt = self._build_system_prompt()
        user_prompt = f"Generate the arxiv search query: (user_input)[{user_input}]"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        try:
            # Call LLM to get the raw output
            response = self.LLM_client.chat_completion(messages=messages)
            content = response["choices"][0]["message"]["content"].strip()

            # Parsing LLM Response
            queries = parse_llm_response(content)

            # Validating and cleaning queries
            valid_queries = validate_and_clean_queries(queries)

            ss = json.dumps(valid_queries, ensure_ascii=False)
            ss = re.compile(r'\\"').sub("", ss)
            
            logger.info(f"API code generation completed: *{ss}*")
            return ast.literal_eval(ss)

        except Exception as exc:
            # Returns a simple query based on the original input as a fallback
            fallback_query = f"all:{user_input.replace(' ', '+')}"
            ss = json.dumps([fallback_query])
            ss = re.compile(r'\\"').sub("", ss)
            
            logger.warning(f"If generation fails, directly use the information entered by the user for retrieval")
            return ast.literal_eval(ss)

    def _build_system_prompt(self) -> str:
        """
        Build system prompt words

        return
        ------
        System prompt string used for query generation
        """
        return (
            "You are an expert search query generator for the arXiv API. "
            "Given some keywords and a key sentence, output a Python list of search query strings that the arXiv API can use. "
            "Each string in the list must strictly follow arXiv API syntax:\n"
            "- Use field prefixes like ti: (Title), au: (Author), abs: (Abstract), co: (Comment), jr: (Journal Reference), cat: (Category), rn: (Report Number), id: (ArXiv ID), all: (All fields).\n"
            "- Use Boolean operators AND, OR, ANDNOT (in all caps) to combine conditions. Use '+' in place of spaces in the query (as in URL encoding).\n"
            '- If a search term has multiple words and should be treated as a phrase, put it in quotes (e.g., abs:"machine learning").\n'
            "- Only and must use valid arXiv category codes after 'cat:'. (For example, use 'cat:cs.AI' or 'cat:hep-th'. Do NOT invent new category names.)\n"
            "- If the input is not in English, translate or use English equivalents for the search terms, since arXiv papers are mostly in English.\n"
            "- Output *only* the list of query strings, with no extra text. The list should be a valid Python array, e.g. ['all:term+AND+ti:term2+OR+au:author', 'cat:cs.AI', ...].\n"
            "- Do not combine all keywords with OR. e.g., ['all:term', 'ti:term2+OR+au:author'] is better than [all:term+OR+ti:term2+OR+au:author]. But the maximum number of elements in the list is 10."
        )