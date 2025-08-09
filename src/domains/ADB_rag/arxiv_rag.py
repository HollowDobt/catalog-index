"""
==================================
|src/domains/ADB_rag/arxiv_rag.py|
==================================
"""

import re
import ast
import json

from typing import List, Any
from domains.academicDB_rag import AcademicDBRAG
from infrastructure import LLMClient
from dataclasses import dataclass
from arxiv_categories import *
from arxiv_utils import *


class ArxivRAGIllegalFormatError(RuntimeError):
    """
    Exception when parsing return value is in illegal format.
    """


@dataclass
@AcademicDBRAG.register("arxiv")
class ArxivRAG(AcademicDBRAG):
    """
    RAG class that converts user requirements into ArXiv search expressions.
    """

    LLM_client: LLMClient

    def api_coding(self, request: str) -> List[str]:
        """
        Generate ArXiv API search query strings for the given input text.

        params
        ------
        request: input text to be converted into query strings

        return
        ------
        List of query strings formatted for the ArXiv API
        """
        if not request or not request.strip():
            return ast.literal_eval(json.dumps([]))

        user_input = request.strip()

        # Build system prompt words
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
            queries = self._parse_llm_response(content)

            # Validating and cleaning queries
            valid_queries = self._validate_and_clean_queries(queries)

            ss = json.dumps(valid_queries, ensure_ascii=False)
            ss = re.compile(r'\\"').sub("", ss)
            return ast.literal_eval(ss)

        except Exception as exc:
            # Returns a simple query based on the original input as a fallback
            fallback_query = f"all:{user_input.replace(' ', '+')}"
            ss = json.dumps([fallback_query])
            ss = re.compile(r'\\"').sub("", ss)
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

    def _parse_llm_response(self, content: str) -> List[str]:
        """
        Parse LLM response content.

        params
        ------
        content: raw response text from the LLM

        return
        ------
        List of query strings extracted from the response
        """
        # Handling code block formatting
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json\n"):
                content = content[5:].strip()
            elif content.startswith("python\n"):
                content = content[7:].strip()

        try:
            # Try parsing directly
            queries = ast.literal_eval(content)
            if not isinstance(queries, list):
                raise ArxivRAGIllegalFormatError(
                    f"The parsed content is not a list: {queries}"
                )
            return queries

        except Exception:
            # If direct parsing fails, try extracting the list part
            return self._extract_list_from_content(content)

    def _extract_list_from_content(self, content: str) -> List[str]:
        """
        Extract a list of queries from raw content.

        params
        ------
        content: text containing a Python list representation

        return
        ------
        Extracted list of query strings
        """
        list_start = content.find("[")
        list_end = content.rfind("]")

        if list_start != -1 and list_end != -1 and list_end > list_start:
            list_str = content[list_start : list_end + 1]
            try:
                queries = ast.literal_eval(list_str)
                if isinstance(queries, list):
                    return queries
            except Exception:
                try:
                    return json.loads(list_str)
                except Exception:
                    pass

        # The last backup plan
        cleaned_content = content.strip('" ')
        return [cleaned_content] if cleaned_content else []

    def _validate_and_clean_queries(self, queries: List[Any]) -> List[str]:
        """
        Validate and cleanse query lists.

        params
        ------
        queries: raw query strings returned by the LLM

        return
        ------
        List of sanitized query strings
        """
        # Make sure all elements are strings
        string_queries = [q for q in queries if isinstance(q, str) and q.strip()]

        valid_queries = []
        for query in string_queries:
            cleaned_query = clean_single_query(query.strip())
            if cleaned_query and cleaned_query not in valid_queries:
                valid_queries.append(cleaned_query)

        return valid_queries