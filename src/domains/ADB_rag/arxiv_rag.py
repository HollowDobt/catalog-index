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


ALLOWED_CATEGORIES: set = {
    # Computer Science categories (cs.*)
    'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV', 'cs.CY',
    'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL', 'cs.GL', 'cs.GR',
    'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO', 'cs.MA', 'cs.MM', 'cs.MS',
    'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS', 'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC',
    'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY',
    # Economics categories (econ.*)
    'econ.EM', 'econ.GN', 'econ.TH',
    # Electrical Engineering and Systems Science categories (eess.*)
    'eess.AS', 'eess.IV', 'eess.SP', 'eess.SY',
    # Mathematics categories (math.*)
    'math.AC', 'math.AG', 'math.AP', 'math.AT', 'math.CA', 'math.CO', 'math.CT',
    'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GR',
    'math.GT', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MG', 'math.MP',
    'math.NA', 'math.NT', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RA',
    'math.RT', 'math.SG', 'math.SP', 'math.ST',
    # Physics categories and related older archives
    'astro-ph.CO', 'astro-ph.EP', 'astro-ph.GA', 'astro-ph.HE', 'astro-ph.IM', 'astro-ph.SR',
    'cond-mat.dis-nn', 'cond-mat.mes-hall', 'cond-mat.mtrl-sci', 'cond-mat.other',
    'cond-mat.quant-gas', 'cond-mat.soft', 'cond-mat.stat-mech', 'cond-mat.str-el',
    'cond-mat.supr-con', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math-ph',
    'nlin.AO', 'nlin.CD', 'nlin.CG', 'nlin.PS', 'nlin.SI', 'nucl-ex', 'nucl-th',
    'physics.acc-ph', 'physics.ao-ph', 'physics.app-ph', 'physics.atm-clus', 'physics.atom-ph',
    'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph', 'physics.comp-ph', 'physics.data-an',
    'physics.ed-ph', 'physics.flu-dyn', 'physics.gen-ph', 'physics.geo-ph', 'physics.hist-ph',
    'physics.ins-det', 'physics.med-ph', 'physics.optics', 'physics.plasm-ph', 'physics.pop-ph',
    'physics.soc-ph', 'physics.space-ph', 'quant-ph',
    # Quantitative Biology categories (q-bio.*)
    'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC', 'q-bio.OT', 'q-bio.PE',
    'q-bio.QM', 'q-bio.SC', 'q-bio.TO',
    # Quantitative Finance categories (q-fin.*)
    'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM', 'q-fin.PR', 'q-fin.RM',
    'q-fin.ST', 'q-fin.TR',
    # Statistics categories (stat.*)
    'stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH',
}

# Allowed field prefixes for search_query (as per arXiv API documentation)
ALLOWED_FIELD_PREFIXES: set = {'ti', 'au', 'abs', 'co', 'jr', 'cat', 'rn', 'all', 'id'}

# Field prefix mapping
FIELD_PREFIX_SYNONYMS = {
    "title": "ti",
    "author": "au", 
    "authors": "au",
    "abstract": "abs",
    "comment": "co",
    "comments": "co", 
    "journal": "jr",
    "category": "cat",
    "categories": "cat",
    "report": "rn",
    "reportnumber": "rn",
    "report-number": "rn"
}


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
        Generates an ArXiv API search query string for a given input text.
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
            ss = re.compile(r'\\"').sub('', ss)
            return ast.literal_eval(ss)
            
        except Exception as exc:
            # Returns a simple query based on the original input as a fallback
            fallback_query = f"all:{user_input.replace(' ', '+')}"
            ss = json.dumps([fallback_query])
            ss = re.compile(r'\\"').sub('', ss)
            return ast.literal_eval(ss)
    
    
    def _build_system_prompt(self) -> str:
        """Build system prompt words"""
        return (
            "You are an expert search query generator for the arXiv API. "
            "Given some keywords and a key sentence, output a Python list of search query strings that the arXiv API can use. "
            "Each string in the list must strictly follow arXiv API syntax:\n"
            "- Use field prefixes like ti: (Title), au: (Author), abs: (Abstract), co: (Comment), jr: (Journal Reference), cat: (Category), rn: (Report Number), id: (ArXiv ID), all: (All fields).\n"
            "- Use Boolean operators AND, OR, ANDNOT (in all caps) to combine conditions. Use '+' in place of spaces in the query (as in URL encoding).\n"
            "- If a search term has multiple words and should be treated as a phrase, put it in quotes (e.g., abs:\"machine learning\").\n"
            "- Only use valid arXiv category codes after 'cat:'. (For example, use 'cat:cs.AI' or 'cat:hep-th'. Do NOT invent new category names.)\n"
            "- If the input is not in English, translate or use English equivalents for the search terms, since arXiv papers are mostly in English.\n"
            "- Output *only* the list of query strings, with no extra text. The list should be a valid Python array, e.g. ['all:term+AND+ti:term2+OR+au:author', 'cat:cs.AI', ...].\n"
        )
    
    
    def _parse_llm_response(self, content: str) -> List[str]:
        """Parsing LLM response content"""
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
                raise ArxivRAGIllegalFormatError(f"The parsed content is not a list: {queries}")
            return queries
            
        except Exception:
            # If direct parsing fails, try extracting the list part
            return self._extract_list_from_content(content)
    
    
    def _extract_list_from_content(self, content: str) -> List[str]:
        """Extracting a list from content"""
        list_start = content.find("[")
        list_end = content.rfind("]")
        
        if list_start != -1 and list_end != -1 and list_end > list_start:
            list_str = content[list_start:list_end+1]
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
        """Validate and cleanse query lists"""
        # Make sure all elements are strings
        string_queries = [q for q in queries if isinstance(q, str) and q.strip()]
        
        valid_queries = []
        for query in string_queries:
            cleaned_query = self._clean_single_query(query.strip())
            if cleaned_query and cleaned_query not in valid_queries:
                valid_queries.append(cleaned_query)
        
        return valid_queries
    
    
    def _clean_single_query(self, query: str) -> Optional[str]:
        """Cleans a single query string"""
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
            query = query.strip('+ ')
            
            return query if query else None
            
        except Exception as e:
            return None
    
    
    def _normalize_field_prefixes(self, query: str) -> str:
        """Standardize field prefixes"""
        # Split the query to process individual parts
        segments = re.split(r'(\+(?:AND|OR|ANDNOT)\+)', query, flags=re.IGNORECASE)
        new_segments = []
        
        for seg in segments:
            if re.match(r'^\+(?:AND|OR|ANDNOT)\+$', seg, re.IGNORECASE):
                new_segments.append(seg.upper())
            elif seg.strip():
                new_segments.append(self._normalize_field_segment(seg))
        
        return "".join(new_segments)
    
    
    def _normalize_field_segment(self, segment: str) -> str:
        """Standardize a single field segment"""
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
        """Verify that the field prefix is valid"""
        segments = re.split(r'\+(?:AND|OR|ANDNOT)\+', query, flags=re.IGNORECASE)
        
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
        """Clean up invalid category codes"""
        segments = re.split(r'(\+(?:AND|OR|ANDNOT)\+)', query, flags=re.IGNORECASE)
        
        # Check if there are mixed operators
        operators = [s.upper() for s in segments if re.match(r'^\+(?:AND|OR|ANDNOT)\+$', s, re.IGNORECASE)]
        has_and = any(op in ['+AND+', '+ANDNOT+'] for op in operators)
        has_or = any(op == '+OR+' for op in operators)
        mixed_ops = has_and and has_or
        
        # If there are mixed operators and there are invalid categories, abandon the entire query
        if mixed_ops and self._has_invalid_category(segments):
            return ""
        
        # Remove invalid category segments
        valid_segments = []
        skip_next_operator = False
        
        for i, seg in enumerate(segments):
            if re.match(r'^\+(?:AND|OR|ANDNOT)\+$', seg, re.IGNORECASE):
                if not skip_next_operator:
                    valid_segments.append(seg.upper())
                skip_next_operator = False
            elif seg.strip():
                if self._is_invalid_category_segment(seg):
                    # Remove the previous operator (if present)
                    if valid_segments and re.match(r'^\+(?:AND|OR|ANDNOT)\+$', valid_segments[-1]):
                        valid_segments.pop()
                    skip_next_operator = True
                else:
                    valid_segments.append(seg)
        
        return "".join(valid_segments)
    
    
    def _has_invalid_category(self, segments: List[str]) -> bool:
        """Check for invalid categories"""
        for seg in segments:
            if self._is_invalid_category_segment(seg):
                return True
        return False
    
    
    def _is_invalid_category_segment(self, segment: str) -> bool:
        """Checks if the segment is an invalid category segment"""
        segment = segment.strip()
        if segment.lower().startswith("cat:"):
            cat_value = segment[4:]
            return cat_value not in ALLOWED_CATEGORIES
        return False