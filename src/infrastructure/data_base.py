from typing import List, Dict, Any
import requests
import time
from urllib.parse import urlencode
import feedparser


class DataBase:
    """
    A unified abstraction layer for scientific research databases. 
    Currently implements the arXiv.org API standard.
    arXiv is open-access and free to use with no API requirements.

    Attributes:
        base_url (str): Base URL for arXiv API
        delay (float): Delay between requests in seconds (to respect API rate limits)
    """

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query?"
        self.delay = 0.34  # ~3 requests per second rate limit

    def request(self, query: str) -> List[Dict[str, Any]]:
        """
        Fetch metadata from arXiv API feed.
        Respects rate limit of 3 requests per second.

        Args:
            query: Search query string

        Returns:
            List of dictionaries containing paper metadata

        Raises:
            ValueError: If API request fails
        """
        params = {
            'search_query': query,
            'start': 0,
            'max_results': 10  # Default to 10 results
        }
        url = self.base_url + urlencode(params)

        try:
            response = requests.get(url)
            response.raise_for_status()
            feed = feedparser.parse(response.content)

            # Respect API rate limit
            time.sleep(self.delay)

            # Extract metadata
            metadata_list = []
            for entry in feed.entries:
                metadata = {
                    'title': entry.title,
                    'authors': [author.name for author in entry.authors],
                    'published': entry.published,
                    'summary': entry.summary,
                    'arxiv_id': entry.id.split('/abs/')[-1],
                    'pdf_url': None  # Will be populated below
                }

                # Find PDF and HTML links
                for link in entry.links:
                    if link.rel == 'alternate' and link.type == 'text/html':
                        metadata['arxiv_url'] = link.href
                    elif link.title == 'pdf':
                        metadata['pdf_url'] = link.href

                metadata_list.append(metadata)

            return metadata_list

        except requests.exceptions.RequestException as e:
            raise ValueError(f"API request failed: {str(e)}")

    def fetch_and_parser(self, meta_data: Dict[str, Any]) -> str:
        """
        Fetch and parse paper content based on metadata.

        Args:
            meta_data: Dictionary containing paper metadata, must contain either 
                     'pdf_url' or 'arxiv_id'

        Returns:
            Extracted text content of the paper

        Raises:
            ValueError: If paper cannot be retrieved
        """
        if 'pdf_url' in meta_data and meta_data['pdf_url']:
            url = meta_data['pdf_url']
        elif 'arxiv_id' in meta_data:
            url = f"https://arxiv.org/pdf/{meta_data['arxiv_id']}.pdf"
        else:
            raise ValueError("Metadata missing both pdf_url and arxiv_id")

        try:
            # Respect API rate limit
            time.sleep(self.delay)

            response = requests.get(url)
            response.raise_for_status()

            # Placeholder for PDF parsing logic
            # In production, implement proper PDF parsing using PyPDF2/pdfminer etc.
            return f"PDF content (requires parsing): {url}"

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Failed to fetch paper: {str(e)}")
