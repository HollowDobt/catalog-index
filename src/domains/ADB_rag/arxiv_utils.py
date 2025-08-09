"""
====================================
|src/domains/ADB_rag/arxiv_utils.py|
====================================

# Utility functions for processing and validating arXiv search queries
"""

import re
from typing import List, Optional
from arxiv_categories import *


def clean_single_query(query: str) -> Optional[str]:
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
        query = normalize_field_prefixes(query)

        # Validation field prefix
        if not validate_field_prefixes(query):
            return None

        # Clean up invalid category codes
        query = clean_category_codes(query)

        # Clean up query format
        query = query.strip("+ ")

        return query if query else None

    except Exception as e:
        return None

def normalize_field_prefixes(query: str) -> str:
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
            new_segments.append(normalize_field_segment(seg))

    return "".join(new_segments)

def normalize_field_segment(segment: str) -> str:
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

def validate_field_prefixes(query: str) -> bool:
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

def clean_category_codes(query: str) -> str:
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
    if mixed_ops and has_invalid_category(segments):
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
            if is_invalid_category_segment(seg):
                # Remove the previous operator (if present)
                if valid_segments and re.match(
                    r"^\+(?:AND|OR|ANDNOT)\+$", valid_segments[-1]
                ):
                    valid_segments.pop()
                skip_next_operator = True
            else:
                valid_segments.append(seg)

    return "".join(valid_segments)

def has_invalid_category(segments: List[str]) -> bool:
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
        if is_invalid_category_segment(seg):
            return True
    return False

def is_invalid_category_segment(segment: str) -> bool:
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


__all__ = [
    "clean_single_query",
    "normalize_field_prefixes",
    "validate_field_prefixes",
    "clean_category_codes",
    "has_invalid_category",
    "is_invalid_category_segment",
]