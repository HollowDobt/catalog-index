"""
# src/infrastructure/utils/content_filter.py

Regular expression-based tools, including a text invalid content cleaner 
and an AI return content extractor

基于正则表达式的工具, 包括文本无效内容清洗器和 ai 返回内容的提取器
"""


import logging
import re
from config import CONFIG


logger = logging.getLogger(__name__)

def filter_invalid_content(content: str) -> str:
    """
    Filter out invalid or meaningless content from analysis results
    """
    
    if not content or not isinstance(content, str):
        logger.warning("Content is empty. Text filtering completed")
        return ""
    
    invalid_patterns = [
        # Chinese
        r"没有?找到.*?(相关|匹配|合适|对应|符合).*?(信息|数据|内容|结果)",
        r"未能?找到.*?(符合|相关|匹配).*?(要求|条件|信息|结果)",
        r"找不到.*?(相关|匹配|合适).*?(信息|数据|内容)",
        r"未检索到.*?(相关|匹配).*?(结果|数据)",
        r"未搜索到.*?(相关|符合|匹配).*?(记录|结果)",
        r"无.*?(匹配|符合|相关).*?(记录|数据|内容)",
        r"无可用.*?(信息|数据|内容)",
        r"没有匹配的.*?(数据|结果|内容)",
        r"没有符合条件的.*?(结果|数据)",
        r"暂时.*?(没有|无).*?(数据|结果|记录)",
        r"查无.*?(结果|数据|记录)",
        r"检索结果为空",
        r"搜索结果为空",
        r"无搜索结果",
        r"无匹配项",
        r"无符合条件的记录",
        r"暂无相关.*?(信息|数据|内容)",
        r"没有查到.*?(信息|数据|内容)",
    
        # English
        r"no\s+(matching|relevant|appropriate|corresponding).*(information|data|content|result)",
        r"not\s+able\s+to\s+find.*?(matching|relevant|appropriate|corresponding).*(result|data|content)",
        r"could\s+not\s+find.*?(matching|relevant|appropriate|corresponding).*(record|result|data)",
        r"did\s+not\s+return\s+any\s+(result|data|record|match)",
        r"returned\s+no\s+(result|data|record|match)",
        r"search\s+result(s)?\s+are\s+empty",
        r"no\s+result(s)?\s+found",
        r"nothing\s+found",
        r"there\s+is\s+no\s+(data|result|record|match)",
        r"currently\s+no\s+(data|result|record|match)",
        r"no\s+available\s+(data|information|content)",
        r"unable\s+to\s+retrieve\s+(data|information|content)",
        r"no\s+matching\s+entries\s+found",
        r"no\s+entries\s+match\s+your\s+criteria",
    ]
    
    # Check if content contains too many invalid patterns
    invalid_count = 0
    for pattern in invalid_patterns:
        if re.search(pattern=pattern, string=content, flags=re.IGNORECASE):
            invalid_count += 1
    
    # If more than half the content is invalid patterns, filter it out
    total_sentences = len(re.split(r"[。！？.!?\n]", content))
    if invalid_count > total_sentences * CONFIG["FILTER_CONDITIONS"]:  # 50% threshold
        logger.warning("There is too little content after filtering, and the return value is empty")
        return ""
    
    # Remove specific invalid sentences but keep the rest
    filtered_content = content
    for pattern in invalid_patterns:
        filtered_content = re.sub(
            pattern + r"[。！？]*", "", filtered_content, flags=re.IGNORECASE
        )
    
    # Clean up extra whitespace
    filtered_content = re.sub(r"\n\s*\n", "\n\n", filtered_content.strip())
    
    # Return empty if too short after filtering
    if len(filtered_content.strip()) < CONFIG["FILTER_MIN_NUMBER"]:
        logger.warning("There is too little content after filtering, and the return value is empty")
        return ""
    
    return filtered_content.strip()