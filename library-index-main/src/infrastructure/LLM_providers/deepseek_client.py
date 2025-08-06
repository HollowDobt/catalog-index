"""
=====================================================
|src/infrastracture/LLM_providers/deepseek_client.py|
=====================================================

# DeepSeek LLM specific implementation of the LLMClient class
"""


import os
import uuid
import json
import requests

from pathlib import Path
from dotenv import load_dotenv
from dataclasses import dataclass, field
from typing import Dict, List, Any
from infrastructure.llm_client import LLMClient


DOT_ENV_PATH_PUBLIC = Path(__file__).parent.parent.parent.parent / ".public.env"
DOT_ENV_PATH_PRIVATE = Path(__file__).parent.parent.parent.parent / ".private.env"
load_dotenv(DOT_ENV_PATH_PUBLIC)
load_dotenv(DOT_ENV_PATH_PRIVATE)


class DeepSeekInitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """

class DeepSeekConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """


@dataclass
@LLMClient.register("deepseek")
class DeepSeekClient(LLMClient):
    """
    DeepSeek LLM specific implementation of the LLMClient class
    """
    
    # The request function "_headers" header is automatically generated in subsequent requests 
    # and does not need to be generated during initialization.
    model: str
    
    _headers: Dict[str, str] = field(default_factory=dict, init=False)
    _raw_timeout: str | None = os.getenv("TIME_OUT_LIMIT")
    
    api_key: str | None = os.getenv("DEEPSEEK_API_KEY")
    base_url: str | None = os.getenv("DEEPSEEK_BASE_URL")
    end_point: str | None = os.getenv("DEEPSEEK_ENDPOINT")
    time_out: int | None = int(_raw_timeout) if _raw_timeout else None
    
    
    def __post_init__(self) -> None:
        """
After initialization, sets request headers and performs a connection test.

params
------
No parameters

return
------
No return value
        """
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        self._health_check()
    
    
    def _health_check(self) -> None:
        """

Initiates a standard request to determine whether the DeepSeek server is connectable.

params
------
No parameters

return
------
No return value. An exception is thrown if the connection fails.
        """
        
        # First confirm that the client variable has been set
        missing_value = (
            "api_key"   if self.api_key   is None else
            "base_url"  if self.base_url  is None else
            "end_point" if self.end_point is None else
            "time_out"  if self.time_out  is None else
            None
        )
        if missing_value:
            raise ValueError(f"{missing_value} is not found in .private.env and .public.env")

        try:
            response = self.chat_completion(
                messages=[
                    {"role": "system", "content": "You are a ping test agent."},
                    {"role": "user", "content": "ping test"}
                ],
                model=self.model,
                temperature=0.0,
                max_tokens=1,
                user=str(uuid.uuid4())
            )
            _response = response["choices"][0]["message"]["content"] #noqa: B018
        except Exception as exc:
            print("DeepSeek initalize error. This often happens when base_url, api, or end_point are incorrect.")
            raise DeepSeekInitConnectError("Unable to connect to DeepSeek server") from exc
        
    
    def _post(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """

Initiates a standard request to determine whether the DeepSeek server is connectable.

params
------
No parameters

return
------
No return value. An exception is thrown if the connection fails.
        """
        assert self.base_url, "base_url required"
        assert self.end_point, "end_point required"
        url = self.base_url.rstrip("/") + self.end_point
        response = requests.post(
            url,
            headers=self._headers,
            data=json.dumps(request),
            timeout=self.time_out
        )
        if response.status_code // 100 != 2:
            raise DeepSeekConnectError(
                f"No correct return value was obtained. Details: [{response.status_code}] {response.text[:300]}"
            )
        return response.json()
    
    
    ### Public methods
    def chat_completion(
        self,
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
Calls the DeepSeek LLM conversation completion interface.

params
------
messages: A list of conversation messages, each containing a role and content field.
**kwargs: Additional request parameters, such as temperature and max_tokens.

return
------
Returns the complete JSON dictionary of the LLM response.
        """
        request = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        return self._post(request=request)


    def analyze(
        self,
        article: str
    ) -> str:
        """
Parses the article into a structured text format.

params
------
article: The article content string to be parsed.

return
------
Returns the structured parsed article content string.
        """
        system_prompt="""
# Role: Document Analysis Expert

## Profile
- language: English
- description: A professional specializing in comprehensive document parsing and analysis, capable of extracting key information and generating structured summaries.
- background: Trained in information extraction, text analysis, and knowledge management systems.
- personality: Detail-oriented, methodical, and precise in handling textual data.
- expertise: Document processing, information retrieval, summarization techniques.
- target_audience: Researchers, analysts, and professionals requiring document insights.

## Skills

1. Core Analytical Skills
   - Text Parsing: Extract and interpret document content accurately
   - Summarization: Condense documents while preserving key information
   - Metadata Extraction: Identify and categorize document elements
   - Information Structuring: Organize findings in logical formats

2. Technical Processing Skills
   - Keyword Analysis: Identify and validate relevant terms
   - Citation Management: Track and format references properly
   - Format Compliance: Maintain consistent output structures
   - Cross-document Comparison: Differentiate between multiple sources

## Rules

1. Processing Principles:
   - Complete Analysis: Examine entire documents without omissions
   - Neutral Interpretation: Maintain objectivity in all summaries
   - Source Attribution: Clearly identify document origins
   - Context Preservation: Retain meaningful relationships between concepts

2. Output Standards:
   - Structured Formatting: Use consistent section headers and spacing
   - Discrete Sections: Keep summaries of different documents separate
   - Verbatim Extraction: Quote key phrases when required
   - Term Standardization: Normalize terminology across outputs

3. Operational Constraints:
   - Document Limitations: Process only provided materials
   - No Speculation: Avoid drawing conclusions beyond evidence
   - No Content Modification: Preserve original document meaning
   - No External References: Rely solely on given documents

        """
        user_prompt=f"""
## Workflows

- Goal: Produce structured document summaries with key metadata
1. Document Ingestion: Receive and verify input documents
2. Comprehensive Reading: Analyze full document content
3. Metadata Extraction: Identify title, abstract, address, keywords
4. Content Analysis: Extract answers related to identified keywords
5. Summary Composition: Generate formatted output per document
6. Quality Verification: Check for completeness and accuracy

- Expected Outcome: Neatly formatted summaries for each document, with all required elements clearly separated and properly attributed

##Attention
Please do not appear other statements that have nothing to do with the answers in these documents, that is, do not have some introduction statements at the beginning and end.

##Format requirements
It can only be divided into four sections: title, summary, keywords, content and result summary

## Initialization
As a Document Analysis Expert, you must adhere to the above Rules and follow the Workflows precisely when performing tasks.            
        """
        messages=[{"role":"system","content":system_prompt},
                  {"role":"user","content":user_prompt}]
        article="""
            
        """
        response=self.chat_completion(
            messages=messages
        )
        return response['choices'][0]['message']['content']
    

    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
Analyzes the relevance of structured article content to the user's query.

params
------
article: A string containing the structured article content.
user_query: A string containing the user's query.

return
------
Returns a string containing the relevance analysis results, including a relevance score and analysis report.
        """
        system_prompt="""
# Role: Advanced Demand Analysis Specialist

## Profile
- language: English
- description: Expert in comprehensive document-query relevance analysis with advanced semantic understanding and contextual evaluation capabilities
- background: 10+ years in information science with specialization in semantic search algorithms and relevance modeling
- personality: Methodical, detail-oriented, and intellectually curious
- expertise: Deep semantic analysis, contextual relevance modeling, multi-document comparison
- target_audience: Enterprise clients, academic researchers, legal professionals, market analysts

## Skills

1. Core Analytical Competencies
   - Semantic Network Analysis: Mapping complex conceptual relationships between documents and queries
   - Contextual Relevance Modeling: Evaluating documents within their full situational context
   - Term Vector Analysis: Advanced statistical analysis of term distributions and co-occurrences
   - Cross-Document Correlation: Identifying inter-document relationships and patterns

2. Advanced Evaluation Techniques
   - Latent Semantic Indexing: Uncovering hidden conceptual connections
   - Sentiment-Weighted Analysis: Incorporating emotional tone in relevance assessment
   - Temporal Relevance Analysis: Evaluating time-sensitive document importance
   - Domain-Specific Adaptation: Customizing analysis for specialized fields (legal, medical, technical)

## Rules

1. Analytical Framework:
   - Multi-Dimensional Scoring: Employ 5-axis relevance assessment (semantic, contextual, temporal, structural, domain-specific)
   - Evidence-Based Judgment: Require explicit textual support for all relevance claims
   - Dynamic Weighting: Adjust term importance based on query context and domain
   - Version-Aware Analysis: Track and account for document revisions and updates

2. Professional Standards:
   - Audit-Ready Documentation: Maintain complete records of analysis methodology
   - Ethical Neutrality: Avoid any political, commercial, or ideological bias
   - Continuous Calibration: Regularly update analysis models based on feedback
   - Confidentiality Assurance: Implement strict data protection protocols

3. Operational Boundaries:
   - No content generation or summarization beyond specified parameters
   - No predictive analysis or future projections
   - No interpretation of implied meanings without explicit textual evidence
   - No combination of separate documents into composite analyses unless specified            
        """
        user_prompt=f"""
## Workflows

- Primary Objective: Deliver comprehensive relevance assessment for {user_query} related documents
- Phase 1: Query Decomposition - Break down query: into semantic components and contextual elements
- Phase 2: Document Profiling - Create detailed semantic profiles for each document
- Phase 3: Multi-Layer Matching - Execute parallel analysis of surface-level and deep semantic connections
- Phase 4: Confidence Scoring - Assign weighted relevance scores with confidence indicators
- Deliverable: Detailed relevance report including:
  * Primary relevance rating (0-100 scale)
  * Supporting evidence matrix
  * Contextual relevance indicators
  * Potential limitations or caveats

##Output format
Query Decomposition:
Document Profiles:
Multi-Layer Matching Analysis:
Confidence Scoring:
It can only contains these 4 parts
## Initialization
As an Advanced Demand Analysis Specialist, you are required to strictly follow the defined analytical protocols while maintaining the highest professional standards in all assessments.
        """

        messages=[{"role":"system","content":system_prompt},
                  {"role":"user","content":user_prompt+"\narticle:"+article}]
        response=self.chat_completion(
            messages=messages,
        )
        return response['choices'][0]['message']['content']



### -------------------------------------------------------
### USE FOR TEST
### -------------------------------------------------------

if __name__ == "__main__":
    client = DeepSeekClient()
    reply = client.chat_completion(
        [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "hello"},
        ],
        max_tokens = 100,
    )
    
    print("[DeepSeek 💭] Reply ->", reply["choices"][0]["message"]["content"])