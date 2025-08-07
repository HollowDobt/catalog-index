"""
================================
|src/domains/article_process.py|
================================

# Article processor to analyze articles
"""


from typing import List
from dataclasses import dataclass, field
from infrastructure import LLMClient


SYSTEM_PROMPT: str = """
# Role: Academic Paper Structure Analyzer & Prompt Generator

## Mission
Extract comprehensive structural information from academic papers and generate bilingual (Chinese-English) structured prompts optimized for vector embedding and retrieval.

## Core Capabilities
1. Paper Structure Recognition: Identify title, abstract, sections, methodology, results, conclusions
2. Key Information Extraction: Extract core concepts, experimental data, findings, terminology
3. Bilingual Prompt Generation: Create structured prompts in both Chinese and English
4. Vector-Friendly Formatting: Generate prompts optimized for embedding and similarity search

## Analysis Framework

### Phase 1: Document Structure Parsing
- Identify paper sections (Abstract, Introduction, Methods, Results, Discussion, Conclusion)
- Extract metadata (title, authors, affiliations, keywords)
- Detect figures, tables, and their captions
- Identify citation patterns and references

### Phase 2: Content Extraction
- Core arguments and hypotheses
- Methodology details
- Key experimental data and results
- Statistical findings
- Author conclusions and implications
- Technical terminology and definitions

### Phase 3: Prompt Generation Rules
1. Each prompt must be self-contained and meaningful
2. Use consistent formatting for vector retrieval
3. Include semantic markers for better embedding
4. Maintain factual accuracy from source
5. Create both Chinese and English versions

## Output Format Requirements

Generate structured prompts in the following categories:

1. **Title & Topic Prompts / 标题与主题提示词**
   - Format: "Paper Title: [title] | Topic: [main topic] | Field: [research field]"
   - 格式: "论文标题：[标题] | 主题：[主要议题] | 领域：[研究领域]"

2. **Abstract Summary Prompts / 摘要总结提示词**
   - Format: "Abstract Key Points: [point1; point2; point3] | Main Finding: [finding]"
   - 格式: "摘要要点：[要点1；要点2；要点3] | 主要发现：[发现]"

3. **Methodology Prompts / 方法学提示词**
   - Format: "Method: [method name] | Application: [how applied] | Data: [data type]"
   - 格式: "方法：[方法名称] | 应用：[如何应用] | 数据：[数据类型]"

4. **Results & Findings Prompts / 结果与发现提示词**
   - Format: "Finding: [specific finding] | Evidence: [supporting data] | Significance: [p-value/metric]"
   - 格式: "发现：[具体发现] | 证据：[支持数据] | 显著性：[p值/指标]"

5. **Key Terms & Concepts Prompts / 关键术语与概念提示词**
   - Format: "Term: [term] | Definition: [brief definition] | Context: [usage context]"
   - 格式: "术语：[术语] | 定义：[简要定义] | 语境：[使用语境]"

6. **Conclusions & Implications Prompts / 结论与影响提示词**
   - Format: "Conclusion: [main conclusion] | Implication: [practical implication] | Future Work: [suggested direction]"
   - 格式: "结论：[主要结论] | 影响：[实际影响] | 未来工作：[建议方向]"

7. **Figure & Table Description Prompts / 图表描述提示词**
   - Format: "Figure/Table: [identifier] | Content: [what it shows] | Key Data: [important values]"
   - 格式: "图/表：[标识符] | 内容：[展示内容] | 关键数据：[重要数值]"

8. **Citation & Reference Prompts / 引用与参考提示词**
   - Format: "Cites: [key references] | Build Upon: [previous work] | Contribution: [novel aspect]"
   - 格式: "引用：[关键文献] | 基于：[前期工作] | 贡献：[创新点]"

## Segmentation Strategy
For long papers, process in chunks of approximately 3000 characters while maintaining semantic coherence.
Ensure each segment contains complete thoughts and maintain context across segments.

## Quality Standards
- Accuracy: All extracted information must be directly traceable to the source
- Completeness: Cover all major aspects of the paper
- Consistency: Use uniform formatting throughout
- Clarity: Each prompt should be immediately understandable
- Bilingual Parity: Chinese and English versions should convey identical meaning
"""


@dataclass
class ArticleStructuring:
    """
    Tools for structuring articles
    """
    
    llm: str
    llm_model: str
    _LLM_client: LLMClient = field(init=False)
    
    
    def __post_init___(self) -> None:
        """
        After initialization, The LLM client will be automatically instantiated
        """
        self._LLM_client = LLMClient.create(self.llm, model=self.llm_model)
    
    
    def _chunk_article(self, text: str, chunk_size: int = 4000) -> List[str]:
        """
        Split article into manageable chunks while preserving paragraph integrity.
        
        params
        ------
        text: raw article content
        chunk_size: the size of a processing block
        
        return
        ------
        A list of the structured article chunks.
        """
        paragraphs = text.split("\n\n")
        chunks: List[str] = []
        current_chunk: str = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if chunk_size:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
                
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks

    
    def analyze(self, article: str) -> str:
        """
        Parse the paper into structured prompt words
        
        params
        ------
        article: a raw article
        
        return
        ------
        A structured article
        """
        chunks = self._chunk_article(text=article)
        all_prompts = []
        
        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""
## Task
Extract structured information from paper segment {i+1}/{len(chunks)}

### Paper Segment
{chunk}

### Instructions
1. Extract all relevant information from this segment
2. Generate bilingual structured prompts according to the format requirements
3. Ensure prompts are self-contained and optimized for vector embedding
4. Maintain factual accuracy and avoid interpretation beyond the text

### Output
Generate structured prompts for all applicable categories found in this segment.
"""

            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": chunk_prompt}
            ]
            
            response = self._LLM_client.chat_completion(
                messages=messages, 
                temperature=0.3,
                max_tokens=4000
            )
            
            all_prompts.append(response["choices"][0]["message"]["content"])
            
        out_article: str = ""
        consolidation_prompt = ""
        for prompt in all_prompts:
            consolidation_prompt = f"""
## Task: Consolidate and organize two extracted prompts(May be empty)

### Extracted Prompt 1
{out_article}

### Extracted Prompt 2
{prompt}

### Instructions
1. Merge and deduplicate prompts from all segments
2. Organize by category maintaining the 8-category structure
3. Ensure bilingual consistency
4. Add paper-level summary prompts
5. Format for optimal vector retrieval

### Final Output Format
Provide a complete, structured set of bilingual prompts covering the entire paper.
"""

            final_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": consolidation_prompt}
            ]
            
            out_article = self._LLM_client.chat_completion(
                messages=final_messages,
                temperature=0.2,
                max_tokens=20000
            )["choices"][0]["message"]["content"]
        
        return out_article