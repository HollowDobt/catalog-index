"""
=================================================
|src/infrastracture/LLM_providers/qwen_client.py|
=================================================

# QWEN LLM specific implementation of the LLMClient class
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


class QwenInitConnectError(RuntimeError):
    """
    Failed to get 200 code when initialization.
    """

class QwenConnectError(RuntimeError):
    """
    Failed to get 200 code.
    """


@dataclass
@LLMClient.register("qwen")
class QwenClient(LLMClient):
    """
    Qwen LLM specific implementation of the LLMClient class
    """
    
    # The request function "_headers" header is automatically generated in subsequent requests 
    # and does not need to be generated during initialization.
    model: str
    
    _headers: Dict[str, str] = field(default_factory=dict, init=False)
    _raw_timeout: str | None = os.getenv("TIME_OUT_LIMIT")
    
    api_key: str | None = os.getenv("QWEN_API_KEY")
    base_url: str | None = os.getenv("QWEN_BASE_URL")
    end_point: str | None = os.getenv("QWEN_ENDPOINT")
    time_out: int | None = int(_raw_timeout) if _raw_timeout else None


    def __post_init__(self) -> None:
        """
        After initialization, the transaction hook tests whether the connection is available.
        """
        self._headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self._health_check()
    
    def _health_check(self) -> None:
        """
        Initiate a standard request to determine if there is a normal response
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
                temperature=0.0,
                max_tokens=1,
                user=str(uuid.uuid4())
            )
            _response = response["choices"][0]["message"]["content"] #noqa: B018
        except Exception as exc:
            print("Qwen initalize error. This often happens when base_url, api, or end_point are incorrect.")
            raise QwenInitConnectError("Unable to connect to Qwen server") from exc
        
        
    def _post(
        self,
        request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Post request to Qwen Client
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
            raise QwenConnectError(
                f"No correct return value was obtained. Details: [{response.status_code}] {response.text[:300]}"
            )
        return response.json()
    
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]], 
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        call LLM chat-completions, return Json dictionary
        """
        request = {
            "model": self.model,
            "messages": messages,
            **kwargs,
        }
        return self._post(request=request)
    
    def analyze(
        self,
        article: str,
    ) -> str:
        """
        Analyze article
        """
        ...
    
    
    def find_connect(
        self,
        article: str,
        user_query: str
    ) -> str:
        """
        Find Connect
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