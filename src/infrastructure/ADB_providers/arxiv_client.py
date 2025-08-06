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
from tqdm import tqdm
import time

from dataclasses import dataclass
from typing import List, Dict, Any
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

class ArxivMissingMetadataError(RuntimeError):
    """
    Missing metadata
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
    time_out: int | None = int(_time_out) if _time_out else None
    
    
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
            None
        )
        
        if missing_value:
            raise ValueError(f"{missing_value} is not found in .private.env and .public.env")
        
        assert self.base_url, "base_url required"
        assert self.time_out, "time_out required"
        
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
        Get metadata for a list of articles.

        params
        ------
        query: official arXiv API search expression
        max_num: maximum number of results to retrieve

        return
        ------
        List of metadata dictionaries
        """
        if max_num <= 0:
            raise ValueError("Illegal parameters passed in, 'max_num' must be greater than 0.")
        
        assert self.base_url, "base_url required"
        assert self.end_point, "end_point required"
        url = f"{self.base_url.rstrip("/")}/{self.end_point.lstrip("/")}search_query={query}&max_results={max_num}"
        
        try:
            response = requests.get(url, timeout=self.time_out)
            if response.status_code // 100 != 2:
                raise ArxivConnectError(f"[{response.status_code}] {response.text[:200]}")
            return self._parse_atom_response(xml_text=response.text)
        
        except Exception as exc:
            raise ArxivConnectError(f"Request failed: {exc}") from exc
        
        
    def _parse_atom_response(self, xml_text: str) -> List[Dict[str, Any]]:
        """
        Parse XML fields into JSON structures.

        params
        ------
        xml_text: XML response text from arXiv

        return
        ------
        List of metadata dictionaries parsed from the XML
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
                for field in ("title", "id", "published", "updated", "summary"):
                    text_val = entry.findtext(f"atom:{field}", default="", namespaces=NS)
                    if text_val:
                        data[field] = text_val.strip()
                
                # Author fields
                authors: List[Dict[str, Any]] = []
                for author in entry.findall("atom:author", NS):
                    # name_elem = author.find("atom:name", NS)
                    name_elem = author.findtext("atom:name", default="", namespaces=NS).strip()
                    # aff_elem = author.find("arxiv:affiliation", NS)
                    affs: List[str] = []
                    for aff_elem in author.findall("arxiv:affiliation", NS):
                        if aff_elem.text and aff_elem.text.strip():
                            affs.append(aff_elem.text.strip())
                    if name_elem or affs:
                        authors.append(
                            {
                                "name": name_elem,
                                **({"affiliations": affs} if affs else {})
                            }
                        )
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
                            "href": link.attrib.get("href", ""),
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
    
    
    def single_metadata_parser(self, meta_data: Dict[str, Any]) -> str:
        """
        Download the PDF associated with a metadata record.

        params
        ------
        meta_data: metadata describing the paper

        return
        ------
        Path to the downloaded PDF file
        """
        
        # Locate PDF URL
        pdf_url: str | None = None
        for link in meta_data.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href")
                break
        
        # Fallback: construct from arXiv id
        if pdf_url is None and meta_data.get("id"):
            id_part = meta_data["id"].rsplit("/", 1)[-1]
            pdf_url = f"https://arxiv.org/pdf/{id_part}.pdf"
        
        if pdf_url is None:
            raise ArxivConnectError("Unable to obtain the specified PDF file. Please check whether the network connection or metadata is normal."
                                    f"matadata: {meta_data["id"]}")
        
        # Build target path
        file_name: str = ""
        try:
            arxiv_id = meta_data["id"].rsplit("/", 1)[-1]
            file_name = f"{arxiv_id}.pdf"
        except Exception as exc:
            raise ArxivMissingMetadataError("Missing key metadata: id")
        
        cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        target_dir = cache_root / "library-index" / "download-files" / "arxiv"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / file_name
        
        # Download (skip if already present)
        if file_path.exists() and file_path.stat().st_size > 0:
            return f"{file_path}"
        
        try:
            with requests.get(pdf_url, stream=True, timeout=self.time_out) as response:
                if response.status_code // 100 != 2:
                    raise ArxivConnectError(f"Download failed: {response.reason[:200]}")
                
                with open(file_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
            
            return f"{file_path}"
        
        except Exception as exc:
            raise ArxivConnectError(f"Unable to connect to arxiv.org to get pdf files.")
        
    
    def multi_metadata_parser(self, meta_data_list: List[Dict[str, Any]]) -> List[str]:
        """
        Download multiple PDFs based on metadata list.

        params
        ------
        meta_data_list: list of metadata records

        return
        ------
        List of paths to downloaded PDF files
        """
        download_paths: List[str] = []
        
        # Displaying a progress bar using tqdm
        for meta_data in tqdm(meta_data_list, desc="Downloading PDFs", unit="file"):
            start_time = time.time()
            try:
                path = self.single_metadata_parser(meta_data=meta_data)
                download_paths.append(path)
            except Exception as exc:
                raise ArxivConnectError(f"Failed to download PDF, {meta_data}: {exc}")
            
            elapsed = time.time() - start_time
            if elapsed < 3:
                time.sleep(elapsed)
            
        return download_paths
