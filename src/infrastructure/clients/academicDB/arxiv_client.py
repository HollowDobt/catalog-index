"""
# src/infrastructure/clients/academicDB/arxiv_client.py

Arxiv client component library and access code generator for the client

arxiv 客户端组件库与该客户端的访问代码生成器
"""


import os
import logging
import xml.etree.ElementTree as ET
import requests
from typing import List, Dict, Any, Optional
from pathlib import Path

from infrastructure.clients.academicDB.base_ADB_client import AcademicDBClient
from config import CONFIG


logger = logging.getLogger(__name__)


@AcademicDBClient.register("arxiv")
class ArxivClient(AcademicDBClient):
    """
    Arxiv ADB request tools
    """
    
    def __init__(self) -> None:
        self.base_url: Optional[str] = CONFIG["ARXIV_BASE_URL"]
        self.end_point: Optional[str] = CONFIG["ARXIV_ENDPOINT"]
        self.time_out: Optional[int] = CONFIG["ARXIV_TIMEOUT_LIMIT"]
        
        self._health_check()
        
    def _health_check(self) -> None:
        """
        Initiate a standard request to determine if there is a normal response
        """
        assert self.base_url, "base_url required"
        assert self.time_out, "time_out required"

        try:
            response = self.search_get_metadata(query="cat:cs.LG", max_num=1)
            if not response:
                logger.warning(f"No expected response. Details: '{response}'")
            else:
                logger.info(f"Connect test succeed.")

        except Exception as exc:
            logger.warning(f"Unable to connect to test endpoint, details: '{exc}'")
            logger.info(f"Testing whether the root node connection is OK")

            try:
                test_url = f"{self.base_url.rstrip("/")}{self.end_point}search_query=all:electron&max_results=1"
                response = requests.get(url=test_url, timeout=self.time_out)
                logger.info(f"Arxiv API Endpoint Test: Status {response.status_code}")
                if response.status_code // 100 != 2:
                    logger.error(f"Return code is not 200. Details: [{response.status_code}] {response.text[:300]}")
                    raise RuntimeError(f"Return code is not 200. Details: [{response.status_code}] {response.text[:300]}")
                logger.warning(f"Health check failed but test succeed")

            except Exception as exc:
                logger.error(f"Self-check connection error. Details: {exc}")
    
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
            logger.warning(f"Invalid max_num: *{max_num}*. Set to default value 1")

        assert self.base_url, "base_url required"
        assert self.end_point, "end_point required"
        url = f"{self.base_url.rstrip("/")}/{self.end_point.lstrip("/")}search_query={query}&max_results={max_num}"

        try:
            response = requests.get(url, timeout=self.time_out)
            if response.status_code // 100 != 2:
                logger.warning(f"Return code is not 200. Return None. Details: [{response.status_code}] {response.text[:300]}")
                return []
                
            return self._parse_atom_response(xml_text=response.text)

        except Exception as exc:
            logger.error(f"Metadata get failed. Details: {exc}")
            raise RuntimeError(f"Metadata get failed. Details: {exc}")
    
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
                    text_val = entry.findtext(
                        f"atom:{field}", default="", namespaces=NS
                    )
                    if text_val:
                        data[field] = text_val.strip()

                # Author fields
                authors: List[Dict[str, Any]] = []
                for author in entry.findall("atom:author", NS):
                    # name_elem = author.find("atom:name", NS)
                    name_elem = author.findtext(
                        "atom:name", default="", namespaces=NS
                    ).strip()
                    # aff_elem = author.find("arxiv:affiliation", NS)
                    affs: List[str] = []
                    for aff_elem in author.findall("arxiv:affiliation", NS):
                        if aff_elem.text and aff_elem.text.strip():
                            affs.append(aff_elem.text.strip())
                    if name_elem or affs:
                        authors.append(
                            {
                                "name": name_elem,
                                **({"affiliations": affs} if affs else {}),
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
                            **(
                                {"title": link.attrib["title"]}
                                if "title" in link.attrib
                                else {}
                            ),
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
            
            logger.info(f"Metadata get succeed")
            return result

        except Exception as exc:
            logger.error(f"Failed to get metadata. response: {exc}")
            raise RuntimeError(f"Failed to get metadata. response: {exc}")
    
    def single_metadata_parser(self, meta_data: Dict[str, Any]) -> str:
        """
        Download the PDF associated with a metadata record.

        params
        ------
        meta_data: metadata describing the paper

        return
        ------
        Path to the downloaded PDF file. "" means downloading failed.
        """

        # Locate PDF URL
        pdf_url: Optional[str] = None
        for link in meta_data.get("links", []):
            if link.get("type") == "application/pdf":
                pdf_url = link.get("href")
                break

        # Fallback: construct from arXiv id
        if pdf_url is None and meta_data.get("id"):
            id_part = meta_data["id"].rsplit("/", 1)[-1]
            pdf_url = f"https://arxiv.org/pdf/{id_part}.pdf"

        if pdf_url is None:
            logger.warning(f"Unable to obtain the specified PDF file(*matadata*: {meta_data["id"]})")
            return ""

        # Build target path
        file_name: str = ""
        try:
            arxiv_id = meta_data["id"].rsplit("/", 1)[-1]
            file_name = f"{arxiv_id}.pdf"
        except Exception as exc:
            logger.warning(f"No specific id provided. Use default one: 'undefined.pdf'")
            file_name = "undefined.pdf"

        cache_root = Path(os.getenv("XDG_CACHE_HOME", Path.home() / ".cache"))
        target_dir = cache_root / "library-index" / "download-files" / "arxiv"
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / file_name

        # Download (skip if already present)
        # TODO 此处需要改进, 考虑到可能出现 pdf 文件不完整的情况
        if file_path.exists() and file_path.stat().st_size > 0:
            return f"{file_path}"

        try:
            with requests.get(pdf_url, stream=True, timeout=self.time_out) as response:
                if response.status_code // 100 != 2:
                    logger.warning(f"Return code is not 200. Return None. Details: [{response.status_code}] {response.text[:300]}")

                with open(file_path, "wb") as fh:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
            logger.info(f"Download complete. ID: {file_path}")
            return f"{file_path}"

        except Exception as exc:
            logger.error(f"Metadata parses failed. Details: {exc}")
            raise RuntimeError(f"Metadata parses failed. Details: {exc}")