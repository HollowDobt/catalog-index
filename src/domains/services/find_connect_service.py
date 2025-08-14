"""
# src/domains/services/find_connect_service.py

Find the relationship between user needs and existing literature

寻找用户需求与已有文献之间的关系
"""


from src.infrastructure import LLMClient


def find_connect(llm_embedding: LLMClient, article: str, user_query: str) -> str:
    """
    Resolve associations between the article and user query.
    Returns text with EXACTLY 4 sections:
    - Query Decomposition:
    - Document Profiles:
    - Multi-Layer Matching Analysis:
    - Confidence Scoring:
    """
    system_prompt = (
        "You are a concise relevance analyst. "
        "Answer in English using EXACTLY these four headings and nothing else:\n"
        "Query Decomposition:\n"
        "Document Profiles:\n"
        "Multi-Layer Matching Analysis:\n"
        "Confidence Scoring:\n"
        "Rules: ground claims in the provided article; include a 0-100 primary relevance rating "
        "under 'Confidence Scoring'. No extra sections, no preface or closing."
    )

    user_prompt = (
        f"User query: {user_query}\n\n"
        "Task: assess how the article relates to the query following the four sections above.\n\n"
        f"Article:\n{article}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    resp = llm_embedding.chat_completion(messages=messages)
    return resp["choices"][0]["message"]["content"]
