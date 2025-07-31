"""
==================================================
|src/infrastracture/ADB_providers/arxiv_client.py|
==================================================

# Arxiv ADB specific implementation of the academicDBClient class
"""


import os
from dotenv import load_dotenv
import xml.etree.ElementTree as ET
import requests

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pathlib import Path

from infrastructure.academicDB_client import AcademicDBClient


DOT_ENV_PATH_PUBLIC = Path(__file__).parent.parent.parent.parent / ".public.env"
DOT_ENV_PATH_PRIVATE = Path(__file__).parent.parent.parent.parent / ".private.env"
load_dotenv(DOT_ENV_PATH_PUBLIC)
load_dotenv(DOT_ENV_PATH_PRIVATE)


class ArxivInitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """
    
class ArxivConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """
    
    
@dataclass
@AcademicDBClient.register("arxiv")
class ArxivClient(AcademicDBClient):
    """
    Arxiv ADB specific implementation of the academicDBClient class
    """
    
    _raw_delay: str | None = os.getenv("ARXIV_ACCESS_RATE")
    _time_out: str | None = os.getenv("TIME_OUT_LIMIT")

    base_url: str | None = os.getenv("ARXIV_BASE_URL")
    end_point: str | None = os.getenv("ARXIV_ENDPOINT")
    time_out: int | None = int(_time_out) if _time_out is not None else None
    access_rate: float | None = float(_raw_delay) if _raw_delay is not None else None
    
    
    def __post_init__(self) -> None:
        """
        After initialization, the transaction hook tests whether the connection is available.
        """
        self._health_check()
    
    
    def _health_check(self) -> None:
        """
        Initiate a standard request to determine if there is a normal response
        """
        missing_value = (
            "base_url"    if self.base_url    is None else
            "time_out"    if self.time_out    is None else
            "access_rate" if self.access_rate is None else
            None
        )
        
        if missing_value:
            raise ValueError(f"{missing_value} is not found in .private.env and .public.env")
        
        assert self.base_url is not None, "base_url required"
        assert self.time_out is not None, "time_out required"
        
        try:
            response = self.search_get_metadata(query="cat:cs.LG", max_num=1)
            if not response:
                print(f"Unexpected Response: from arxiv.org, details: '{response}'")
                raise ArxivInitConnectError("ArxivClient initalize error. This often happens when base_url or end_point is incorrect.")
        
        except Exception as exc:
            print(f"Unable to connect to test endpoint, details: '{exc}'")
            print(f"Testing whether the root node connection is OK...")
            
            try:
                test_url = f"{self.base_url.rstrip("/")}{self.end_point}search_query=all:electron&max_results=1"
                response = requests.get(url=test_url, timeout=self.time_out)
                print(f"Arxiv API Endpoint Test: Status {response.status_code}")
                if response.status_code // 100 != 2:
                    raise ArxivConnectError(f"Unable to access to arxiv.org with 200.")
                raise ArxivInitConnectError("ArxivClient initalize error but test succeed. Please check if the end_point is correct.")
            
            except Exception as exc:
                raise ArxivConnectError(f"Unable to connect to arxiv.org. You may have entered the wrong base_url. Details: {exc}") from exc
    
    
    def search_get_metadata(self, query: str, max_num: int) -> List[Dict[str, Any]]:
        """
        Get metadata of hte list of articles.
        Query is Official API access expression, e.g.: all:electron+AND+cat:cs.LG
        """
        if max_num <= 0:
            raise ValueError("Illegal parameters passed in, 'max_num' must be greater than 0.")
        
        params = {
            "search_query": query,
            "max_results": max_num,
        }
        assert self.base_url is not None, "base_url required"
        url = f"{self.base_url.rstrip("/")}{self.end_point}"
        
        try:
            response = requests.get(url, params=params, timeout=self.time_out)
            if response.status_code // 100 != 2:
                raise ArxivConnectError(f"[{response.status_code}] {response.text[:200]}")
            return self._parse_atom_response(xml_text=response.text)
        
        except Exception as exc:
            raise ArxivConnectError(f"Request failed: {exc}") from exc
        
        
    def _parse_atom_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Parse xml fields into json
        """
        NS = {
            "atom": "http://www.w3.org/2005/Atom",
            "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
            "arxiv": "http://arxiv.org/schemas/atom",
        }
        
        try:
            root = ET.fromstring(xml_text)
            result: List[Dict[str, Any]] = []
            
            # Standard: Atom Feed
            for entry in root.findall("atom:entry", NS):
                data: Dict[str, Any] = {}
                
                # Basic fields
                for tag in ("title", "id", "published", "updated", "summary"):
                    elem = entry.find(f"atom:{tag}", NS)
                    if elem is not None and elem.text:
                        data[tag] = elem.text
                
                # Author fields
                authors: List[Dict[str, Any]] = []
                for author in entry.findall("atom:author", NS):
                    name_elem = author.find("atom:name", NS)
                    aff_elem = author.find("arxiv:affiliation", NS)
                    author_info: Dict[str, Any] = {}
                    
                    if name_elem is not None:
                        author_info["name"] = name_elem.text
                    if aff_elem is not None:
                        author_info["affiliation"] = aff_elem.text
                    if author_info is not None:
                        authors.append(author_info)
                    
                if authors:
                    data["authors"] = authors
                
                # Categories fields
                categories: List[str] = []
                for category_elem in entry.findall("atom:category", NS):
                    term = category_elem.attrib.get("term")
                    if term:
                        categories.append(term)
                if categories:
                    data["categories"] = categories
                
                # Links fields
                links: List[Dict[str, Any]] = []
                for link in entry.findall("atom:link", NS):
                    links.append(
                        {
                            "herf": link.attrib.get("href", ""),
                            "rel": link.attrib.get("rel", ""),
                            "type": link.attrib.get("type", ""),
                            **({"title": link.attrib["title"]} if "title" in link.attrib else {}),
                        }
                    )
                if links:
                    data["links"] = links
                
                # Arxiv other expand contents
                primary_cat = entry.find("arxiv:primary_category", NS)
                if primary_cat is not None and "term" in primary_cat.attrib:
                    data["arxiv_primary_category"] = primary_cat.attrib["term"]
                
                for tag in ("comment", "journal_ref", "doi"):
                    elem = entry.find(f"arxiv:{tag}", NS)
                    if elem is not None and elem.text:
                        data[f"arxiv_{tag}"] = elem.text
                
                result.append(data)
            return result
        except Exception as exc:
            raise ArxivConnectError(f"Failed to parse XML response: {exc}") from exc