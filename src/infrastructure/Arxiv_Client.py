"""
-------------------------------------
src/infrastructure/arxiv_client.py
-------------------------------------

A lightweight wrapper for the Arxiv API, implemented as ArxivClient class.

# WARN 1: Each time the ArxivClient class is instantiated,
# it will first send a simple request to test the connection.
# If the test fails, the error is returned and output to the log.

# WARN 2: The Arxiv API has rate limits (3 seconds between requests recommended)
# and maximum result limits (2000 per request, ~50,000 total).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import time
import xml.etree.ElementTree as ET
import requests

class ArxivConnectionError(RuntimeError):
    """
    Failed to pass health check during initialization.
    Generally means the API is unavailable or rate limited.
    """
class ArxivAPIError(RuntimeError):
    """
     A non-2xx error code is returned when calling the Arxiv API.
    Or the response XML cannot be parsed.
    """

### -------------------------------------------------------
### Arxiv API Wrapper
### -------------------------------------------------------

@dataclass
class ArxivClient:
    base_url: str="http://export.arxiv.org"
    timeout:int=30
    delay:float=3.0

    _last_request_time:float=field(default=0.0,init=False)

    #Public:Search papers
    def search_papers(
            self,
            search_query:Optional[str]=None,
            id_list: Optional[List[str]]=None,
            start:int=0,
            max_results: int = 10,
            sort_by: Optional[str] = None,
            sort_order: Optional[str] = None,
    )->Dict[str, Any]:
        """
                Search papers on Arxiv using the query API.

                Parameters
                ----------
                search_query : str, optional
                    Search query string using Arxiv's query syntax
                id_list : List[str], optional
                    List of Arxiv paper IDs to fetch
                start : int
                    Pagination start index (0-based), default 0
                max_results : int
                    Maximum number of results to return (1-2000), default 10
                sort_by : str, optional
                    Sorting field: 'relevance', 'lastUpdatedDate', or 'submittedDate'
                sort_order : str, optional
                    Sorting order: 'ascending' or 'descending'

                Returns
                -------
                Dict[str, Any]
                    Parsed response containing paper entries and metadata
        """
        params={}

        if search_query:
            params["search_query"] = search_query
        if id_list:
            params["id_list"] = ",".join(id_list)
        if start:
            params["start"] = str(start)
        if max_results:
            params["max_results"] = str(max_results)
        if sort_by:
            params["sortBy"] = sort_by
        if sort_order:
            params["sortOrder"] = sort_order

        return self._get("query",params)

    # When initialize: Do a ping test
    def __post_init__(self) -> None:
        self._health_check()

    # Http Get with rate limiting

    def _get(
        self,
        path: str,
        params: Dict[str, str]
    ) -> Dict[str, Any]:
        # Enforce rate limiting
        self._enforce_delay()

        url = f"{self.base_url.rstrip('/')}/api/{path}"

        try:
            response = requests.get(
                url,
                params=params,
                timeout=self.timeout,
            )

            if response.status_code // 100 != 2:
                raise ArxivAPIError(
                    f"[{response.status_code}] {response.text[:200]}"
                )

            return self._parse_atom_response(response.text)

        except requests.RequestException as exc:
            raise ArxivAPIError(f"Request failed: {exc}") from exc

    def _enforce_delay(self) -> None:
        current_time = time.time()
        elapsed = current_time - self._last_request_time
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self._last_request_time = time.time()

    def _parse_atom_response(self, xml_text: str) -> Dict[str, Any]:
        try:
            root = ET.fromstring(xml_text)
            result = {
                "feed_metadata": {},
                "entries": []
            }

            # Parse feed metadata
            for elem in ["title", "id", "updated"]:
                if (e := root.find(f".//{{{root.tag.split('}')[0]}}}{elem}")) is not None:
                    result["feed_metadata"][elem] = e.text

            # Parse opensearch metadata
            for elem in ["totalResults", "startIndex", "itemsPerPage"]:
                if (e := root.find(f".//{{http://a9.com/-/spec/opensearch/1.1/}}{elem}")) is not None:
                    result["feed_metadata"][elem] = e.text

            # Parse entries
            for entry in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                entry_data = {}

                # Basic fields
                for field in ["title", "id", "published", "updated", "summary"]:
                    if (e := entry.find(f".//{{{entry.tag.split('}')[0]}}}{field}")) is not None:
                        entry_data[field] = e.text

                # Authors
                authors = []
                for author in entry.findall(".//{http://www.w3.org/2005/Atom}author"):
                    if (name := author.find(".//{http://www.w3.org/2005/Atom}name")) is not None:
                        authors.append(name.text)
                if authors:
                    entry_data["authors"] = authors

                # Categories
                categories = []
                for category in entry.findall(".//{http://www.w3.org/2005/Atom}category"):
                    if "term" in category.attrib:
                        categories.append(category.attrib["term"])
                if categories:
                    entry_data["categories"] = categories

                # Links
                links = []
                for link in entry.findall(".//{http://www.w3.org/2005/Atom}link"):
                    link_data = {
                        "href": link.attrib.get("href", ""),
                        "rel": link.attrib.get("rel", ""),
                        "type": link.attrib.get("type", ""),
                    }
                    if "title" in link.attrib:
                        link_data["title"] = link.attrib["title"]
                    links.append(link_data)
                if links:
                    entry_data["links"] = links

                # Arxiv-specific extensions
                arxiv_ns = "{http://arxiv.org/schemas/atom}"
                for field in ["primary_category", "comment", "journal_ref", "doi", "affiliation"]:
                    if (e := entry.find(f".//{arxiv_ns}{field}")) is not None:
                        entry_data[f"arxiv_{field}"] = e.text if field != "primary_category" else e.attrib.get("term",
                                                                                                               "")

                result["entries"].append(entry_data)

            return result

        except ET.ParseError as exc:
            raise ArxivAPIError(f"Failed to parse XML response: {exc}") from exc

    # 修改 _health_check 方法如下：
    def _health_check(self) -> None:
        """
        Send a simple request to ensure the API is accessible.
        If it fails, ArxivConnectionError is thrown for the upper layer to capture.
        """
        try:
            # 使用更通用的查询，确保能返回结果
            result = self.search_papers(
                search_query="cat:cs.LG",  # 机器学习分类
                max_results=1
            )

            if not result.get("entries"):
                # 提供更详细的错误信息
                print("[Arxiv] Debug: Full response:", result)
                raise ArxivConnectionError("Health check returned no papers. Possible API changes or network issues.")

        except Exception as exc:
            print(f"[Arxiv] Initialize Error Details: {str(exc)}")
            print("[Arxiv] Trying to verify API endpoint...")

            # 尝试直接访问API根端点
            try:
                test_url = f"{self.base_url.rstrip('/')}/api/query?search_query=all:electron&max_results=1"
                response = requests.get(test_url, timeout=self.timeout)
                print(f"[Arxiv] API Endpoint Test: Status {response.status_code}")
                if response.status_code != 200:
                    raise ArxivConnectionError(f"API endpoint returned {response.status_code}")
            except Exception as endpoint_exc:
                print(f"[Arxiv] API Endpoint Test Failed: {endpoint_exc}")

            raise ArxivConnectionError(
                "Failed to connect to Arxiv API. Possible reasons:\n"
                "1. API endpoint changed (current: {self.base_url})\n"
                "2. Network connectivity issues\n"
                "3. Arxiv service temporarily unavailable"
            ) from exc

### -------------------------------------------------------
### USE FOR TEST
### -------------------------------------------------------

if __name__=="__main__":
    client = ArxivClient()

    # Search for papers about machine learning
    papers = client.search_papers(
        search_query="cat:cs.LG",  # Machine learning category
        max_results=5,
        sort_by="submittedDate",
        sort_order="descending"
    )

    print("Latest 5 machine learning papers:")
    for i, paper in enumerate(papers["entries"]):
        print(f"{i + 1}. {paper.get('title', 'No title')}")
        print(f"   Published: {paper.get('published', 'Unknown date')}")
        print(f"   Authors: {', '.join(paper.get('authors', ['Unknown']))}")
        print(f"   Link: {paper.get('id', 'No link')}")
        print()


