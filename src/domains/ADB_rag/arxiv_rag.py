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


class ArxivRAGIllegalFormatError(RuntimeError):
    """
    Parsing the return value into an illegal format
    """


@dataclass
@AcademicDBRAG.register("arxiv")
class ArxivRAG(AcademicDBRAG):
    """
    Convert user needs into search expressions
    """
    LLM_client: LLMClient
    
    def api_coding(self, request: str) -> str:
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
        response = self.LLM_client.chat_completion(messages=messages)
        content = response["choices"][0]["message"]["content"].strip()
        
        if content[:3] == "```":
            content = content.strip("`")
            if content[:6] == "json\n":
                content = content[len("json\n"):]
            content = content.strip()
        
        queries: List[str]
        try:
            queries = ast.literal_eval(content)
            if not isinstance(queries, list):
                raise ValueError(f"Parsed content is not a list: {queries}")
        except Exception as exc:
            # If direct eval failed (maybe the model output extra text around the list),
            # try to extract the list part
            list_start = content.find("[")
            list_end = content.rfind("]")
            
            if list_start != -1 and list_end != -1 and list_end > list_start:
                list_str = content[list_start:list_end+1]
                try:
                    queries = ast.literal_eval(list_str)
                    if not isinstance(queries, list):
                        raise ArxivRAGIllegalFormatError(f"Parsing the return value into an illegal format: {queries}")
                except:
                    try:
                        queries = json.loads(list_str)
                    except Exception as exc:
                        queries = [content.strip('" ')]
                        
            else:
                queries = [content.strip('" ')] if content else []
                
        # Ensure all elements are strings (filter out any non-string just in case)
        queries = [q for q in queries if isinstance(q, str)]
        valid_queries: List[str] = []
        for query in queries:
            q = query.strip()
            if not q:
                continue
            
            # Replace common field prefix synonyms with correct abbreviations (if any)
            # e.g., "title:" -> "ti:", "author:" -> "au:", "abstract:" -> "abs:", etc.
            # We'll do a simple replacement on each segment separated by spaces or plus signs around the colon.
            # We need to replace only at the start of each field segment.
            # Split on the known operators to isolate field segments
            segments = re.split(r'(\+ANDNOT\+|\+AND\+|\+OR\+)', q)
            # segments will include operators as separate elements
            new_segments: List[str] = []
            invalid_structure = False
            
            for seg in segments:
                if seg.upper() in ["+AND+", "+OR+", "+ANDNOT+"]:
                    # No additional processing is required for "+AND+", "+OR+", and "+ANDNOT+"
                    new_segments.append(seg.upper())
                elif seg == "":
                    continue
                else:
                    # This is a field segment like "ti:term" or "cat:code" or "abs:\"some phrase\""
                    # Check and correct field prefix if needed
                    part = seg
                    if ":" in seg:
                        prefix, rest = part.split(":", 1)
                        prefix_lower = prefix.lower()
                        
                        synonym_map = {
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
                        
                        if prefix_lower in synonym_map:
                            prefix = synonym_map[prefix_lower]
                        
                        # Use lowercase for standard prefixes (arxiv expects lowercase field tags)
                        prefix = prefix.lower()
                        part = prefix + ":" + rest

                        if prefix not in ALLOWED_FIELD_PREFIXES:
                            invalid_structure = True
                            break
                        
                        new_segments.append(part)
                
            if invalid_structure:
                continue
                
            q_reconstructed = "".join(new_segments)
            
            # Now validate category codes and remove invalid ones if present
            # Split again by operators to isolate each condition
            segments2 = re.split(r'(\+ANDNOT\+|\+AND\+|\+OR\+)', q_reconstructed)
            
            # Determine if there's a mix of AND/OR operators (for deciding removal strategy)
            has_and = any(s.upper() == "+AND+" or s.upper() == "+ANDNOT+" for s in segments2)
            has_or = any(s.upper() == "+OR+" for s in segments2)
            mixed_ops = has_and and has_or
            
            # Identify and remove invalid cat segments
            # We will build a new list of segments (third pass) excluding invalid category conditions.
            final_segments: List[str] = []
            skip_next_operator = False
            
            for idx, seg in enumerate(segments2):
                
                if seg.upper() in ["+AND+", "+OR+", "+ANDNOT+"]:
                    # Decide later whether to include this operator or not, depending on adjacent removals
                    # For now, don't append operators immediately; handle them when adding segments
                    final_segments.append(seg.upper())
                    continue
                
                if seg.strip() == "":
                    continue
                
                # If this segment is a category filter
                if seg.lower().startswith("cat:"):
                    cat_value = seg[4:]
                    if cat_value not in ALLOWED_CATEGORIES:
                        # Invalid category code found
                        if len(segments2) == 1:
                            skip_next_operator = False
                            final_segments = []
                            break
                        
                        # If operators are mixed (AND/OR), it's safer to drop the whole query to avoid logic errors
                        if mixed_ops:
                            skip_next_operator = False
                            final_segments = []
                            invalid_structure = True
                            break
                        
                        # If only one type of operator (pure AND chain or pure OR chain), we can remove this segment safely
                        # Remove this category segment and the appropriate connecting operator.
                        # We will skip adding this segment, and also handle adjacent operators below.
                        # Mark to skip adding the next operator in final_segments (which is the operator after this segment if any).
                        skip_next_operator = True
                        
                        # Remove the operator before this segment in final_segments (if present at end)
                        if final_segments:
                            prev = final_segments[-1]
                            if prev.upper() in ["+AND+", "+OR+", "+ANDNOT+"]:
                                final_segments.pop()  # remove the previous operator
                        
                        continue
                    
                    # If category is valid, keep the segment
                    # (Also, if previously we marked to skip its operator, that was handled above by removing prev operator)
                    final_segments.append(seg)
                
                else:
                    # Not a category segment, keep it normally
                    final_segments.append(seg)
                
                if skip_next_operator:
                    # Skip the next operator in the loop by resetting the flag and ensure we don't double-add operators
                    skip_next_operator = False
                    # In the normal flow, the next loop iteration would append the next operator, but since we removed the segment,
                    # we already popped the previous operator. We continue to next iteration which will find the next operator and handle normally.
            if invalid_structure:
                continue  # drop this query entirely due to structural issues
            # After processing all segments, reconstruct query string
            cleaned_query = "".join(final_segments)
            cleaned_query = cleaned_query.strip('+ ')  # remove any leading/trailing '+' if any remain
            if cleaned_query == "":
                continue
            # Finally, ensure the cleaned query is not a duplicate of one already added
            if cleaned_query not in valid_queries:
                valid_queries.append(cleaned_query)
        # If no valid queries remain, we can optionally return an empty list or a broad search query as fallback.
        # Here we return an empty list if nothing valid, else the filtered queries.
        result_list = valid_queries if valid_queries else []
        # Return the list as a JSON-formatted string
        return json.dumps(result_list, ensure_ascii=False)