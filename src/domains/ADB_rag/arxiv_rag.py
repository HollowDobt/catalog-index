"""
==================================
|src/domains/ADB_rag/arxiv_rag.py|
==================================
"""


import re
import ast
import json

from typing import List, Dict, Any
from domains.academicDB_rag import AcademicDBRAG
from infrastructure import LLMClient
from dataclasses import dataclass, field


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



@dataclass
@AcademicDBRAG.register("arxiv")
class ArxivRAG(AcademicDBRAG):
    """
    Convert user needs into search expressions
    """
    LLM_client: LLMClient
    
    def api_coding(self, request: str) -> List[str]:
        """
        Generate arXiv API search query strings for the given input text (keywords and key sentence).
        
        The input `request` is expected to contain some keywords and a key sentence (possibly separated by a comma).
        This method will:
          1. Use the Qwen LLM (via chat_completion) to generate a list of query strings following arXiv API syntax.
          2. Validate and post-process the generated queries:
             - Ensure only valid field prefixes are used (ti, au, abs, co, jr, cat, rn, all, id).
             - Ensure any `cat:` field value is one of the allowed arXiv subject categories.
             - Remove or correct any invalid parts of queries to strictly comply with arXiv API rules.
          3. Return the final list of query strings as a JSON-formatted string (e.g., '["all:term+AND+ti:term2", "ti:\\"phrase\\"+OR+cat:cs.AI"]').
        
        Returns:
            A JSON string representation of a list of query strings suitable for arXiv API `search_query` parameter.
        """
        user_input = request.strip()
        
        system_prompt: str = (
            "You are an expert search query generator for the arXiv API. "
            "Given some keywords and a key sentence, output a Python list of search query strings that the arXiv API can use. "
            "Each string in the list must strictly follow arXiv API syntax:\n"
            "- Use field prefixes like ti: (Title), au: (Author), abs: (Abstract), co: (Comment), jr: (Journal Reference), cat: (Category), rn: (Report Number), id: (ArXiv ID), all: (All fields).\n"
            "- Use Boolean operators AND, OR, ANDNOT (in all caps) to combine conditions. Use '+' in place of spaces in the query (as in URL encoding).\n"
            "- If a search term has multiple words and should be treated as a phrase, put it in quotes (e.g., abs:\"machine learning\").\n"
            "- Only use valid arXiv category codes after 'cat:'. (For example, use 'cat:cs.AI' or 'cat:hep-th'. Do NOT invent new category names.)\n"
            "- If the input is not in English, translate or use English equivalents for the search terms, since arXiv papers are mostly in English.\n"
            "- Output *only* the list of query strings, with no extra text. The list should be a valid Python array, e.g. [\"all:term+AND+ti:term2+OR+au:ankel\", \"cat:cs.AI\", ...]."
        )
        
        user_prompt = f"Generate the arxiv search query: (user_input)[{user_input}]"
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        # Call the LLM to get the raw output
        