"""
==================================
|src/domains/ADB_rag/arxiv_rag.py|
==================================
"""

import re
import ast
import json

from typing import List, Any, Optional
from domains.academicDB_rag import AcademicDBRAG
from infrastructure import LLMClient
from dataclasses import dataclass
from arxiv_categories import *


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
            cleaned_query = self._clean_single_query(query.strip())
            if cleaned_query and cleaned_query not in valid_queries:
                valid_queries.append(cleaned_query)

        return valid_queries

    def _clean_single_query(self, query: str) -> Optional[str]:
        """
        Clean a single query string.

        params
        ------
        query: query string to be normalized and validated

        return
        ------
        Cleaned query string or None if invalid
        """
        if not query:
            return None

        try:
            # Standardize field prefixes
            query = self._normalize_field_prefixes(query)

            # Validation field prefix
            if not self._validate_field_prefixes(query):
                return None

            # Clean up invalid category codes
            query = self._clean_category_codes(query)

            # Clean up query format
            query = query.strip("+ ")

            return query if query else None

        except Exception as e:
            return None

    def _normalize_field_prefixes(self, query: str) -> str:
        """
        Standardize field prefixes within a query.

        params
        ------
        query: query string containing field prefixes

        return
        ------
        Query string with normalized prefixes
        """
        # Split the query to process individual parts
        segments = re.split(r"(\+(?:AND|OR|ANDNOT)\+)", query, flags=re.IGNORECASE)
        new_segments = []

        for seg in segments:
            if re.match(r"^\+(?:AND|OR|ANDNOT)\+$", seg, re.IGNORECASE):
                new_segments.append(seg.upper())
            elif seg.strip():
                new_segments.append(self._normalize_field_segment(seg))

        return "".join(new_segments)

    def _normalize_field_segment(self, segment: str) -> str:
        """
        Standardize a single field segment.

        params
        ------
        segment: single segment of a query containing a field prefix

        return
        ------
        Segment with normalized field prefix
        """
        if ":" not in segment:
            return segment

        prefix, rest = segment.split(":", 1)
        prefix_lower = prefix.lower()

        # Using synonym maps
        if prefix_lower in FIELD_PREFIX_SYNONYMS:
            prefix = FIELD_PREFIX_SYNONYMS[prefix_lower]
        else:
            prefix = prefix_lower

        return f"{prefix}:{rest}"

    def _validate_field_prefixes(self, query: str) -> bool:
        """
        Verify that the field prefixes in a query are valid.

        params
        ------
        query: query string to inspect

        return
        ------
        True if all prefixes are allowed, otherwise False
        """
        segments = re.split(r"\+(?:AND|OR|ANDNOT)\+", query, flags=re.IGNORECASE)

        for seg in segments:
            seg = seg.strip()
            if not seg:
                continue

            if ":" in seg:
                prefix = seg.split(":", 1)[0].lower()
                if prefix not in ALLOWED_FIELD_PREFIXES:
                    return False

        return True

    def _clean_category_codes(self, query: str) -> str:
        """
        Clean up invalid category codes in a query.

        params
        ------
        query: query string containing category specifications

        return
        ------
        Query string with invalid categories removed
        """
        segments = re.split(r"(\+(?:AND|OR|ANDNOT)\+)", query, flags=re.IGNORECASE)

        # Check if there are mixed operators
        operators = [
            s.upper()
            for s in segments
            if re.match(r"^\+(?:AND|OR|ANDNOT)\+$", s, re.IGNORECASE)
        ]
        has_and = any(op in ["+AND+", "+ANDNOT+"] for op in operators)
        has_or = any(op == "+OR+" for op in operators)
        mixed_ops = has_and and has_or

        # If there are mixed operators and there are invalid categories, abandon the entire query
        if mixed_ops and self._has_invalid_category(segments):
            return ""

        # Remove invalid category segments
        valid_segments = []
        skip_next_operator = False

        for i, seg in enumerate(segments):
            if re.match(r"^\+(?:AND|OR|ANDNOT)\+$", seg, re.IGNORECASE):
                if not skip_next_operator:
                    valid_segments.append(seg.upper())
                skip_next_operator = False
            elif seg.strip():
                if self._is_invalid_category_segment(seg):
                    # Remove the previous operator (if present)
                    if valid_segments and re.match(
                        r"^\+(?:AND|OR|ANDNOT)\+$", valid_segments[-1]
                    ):
                        valid_segments.pop()
                    skip_next_operator = True
                else:
                    valid_segments.append(seg)

        return "".join(valid_segments)

    def _has_invalid_category(self, segments: List[str]) -> bool:
        """
        Check whether any query segment contains an invalid category.

        params
        ------
        segments: list of query segments to evaluate

        return
        ------
        True if an invalid category is found, otherwise False
        """
        for seg in segments:
            if self._is_invalid_category_segment(seg):
                return True
        return False

    def _is_invalid_category_segment(self, segment: str) -> bool:
        """
        Determine whether a segment is an invalid category segment.

        params
        ------
        segment: query segment to check

        return
        ------
        True if the segment has an invalid category code, otherwise False
        """
        segment = segment.strip()
        if segment.lower().startswith("cat:"):
            cat_value = segment[4:]
            return cat_value not in ALLOWED_CATEGORIES
        return False
