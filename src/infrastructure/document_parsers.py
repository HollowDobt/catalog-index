"""
src/infrastructure/document_parsers.py
======================================
流式解析科研 **DOCX** / **LaTeX** 文档 → 术语-定义对 (用于 mem0 图写入)

依赖:
    python-docx    (可选, 仅用于获取文档属性)
    lxml
    pylatexenc
    tqdm
"""

from __future__ import annotations

import hashlib                # 计算 SHA-256
import json                   # 解析 LLM JSON 返回
import logging
import os
import re                     # 如需正则
import textwrap               # 控制终端输出宽度
import zipfile                # 解压 .docx
from dataclasses import dataclass, field
from pathlib import Path      # 路径处理
from typing import Dict, Generator, List, Any

from dotenv import load_dotenv          # 读取 .env
from lxml import etree                  # 流式 XML
from tqdm import tqdm                   # 进度条
from pylatexenc.latex2text import LatexNodes2Text  # LaTeX→text

# 本项目内部依赖
from deepseek_client import DeepSeekClient, DeepSeekAPIError

# -------------------- 常量与日志 --------------------
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
logger = logging.getLogger(__name__)

# -------------------- 工具函数 --------------------


def _sha256(data: str | bytes) -> str:
    """返回 *data* 的 SHA-256 十六进制摘要"""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def _chunk_text(text: str, max_chars: int = 8000, overlap: int = 250) -> List[str]:
    """
    将长文本切成重叠字符块, 防止切断定义
    """
    pieces: List[str] = []
    p = 0
    n = len(text)
    while p < n:
        end = min(p + max_chars, n)
        pieces.append(text[p:end])
        p = end - overlap
        if p < 0:
            p = 0
    return pieces


# -------------------- 主解析类 --------------------


@dataclass
class DocumentParser:
    """
    逐段流式解析文件 → term-definition 列表
    """

    llm: DeepSeekClient                          # DeepSeek 客户端
    max_chars: int = 8_000                       # 每块最多字符
    llm_model: str = field(default="deepseek-chat")  # 使用模型

    # —— 公共 API ————————————————————————

    def parse_file(self, file_path: str | Path) -> Dict[str, Any]:
        """
        流式解析 *file_path* 并返回:
            {
              "terms": [{"term":..,"definition":..}, ...],
              "metadata": {...}
            }
        """
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        # 选择流式迭代器
        ext = file_path.suffix.lower()
        if ext == ".docx":
            para_iter = self._iter_docx(file_path)
        elif ext in {".tex", ".latex"}:
            para_iter = self._iter_tex(file_path)
        else:
            raise ValueError(f"Unsupported extension: {ext}")

        # 收集术语（用 dict 去重）
        terms: Dict[str, str] = {}
        total_chars = 0
        chunk: List[str] = []

        for para in para_iter:
            total_chars += len(para) + 1
            chunk.append(para)

            # 达到 3 段或累积字符超限即发送 LLM
            if len(chunk) >= 3 or sum(len(p) for p in chunk) > self.max_chars:
                self._update_terms_from_chunk("\n".join(chunk), terms)
                chunk.clear()

        # 处理结尾残余
        if chunk:
            self._update_terms_from_chunk("\n".join(chunk), terms)

        return {
            "terms": [{"term": k, "definition": v} for k, v in terms.items()],
            "metadata": {
                "filename": file_path.name,
                "chars": total_chars,
                "sha256": _sha256(str(file_path) + str(total_chars)),
            },
        }

    # —— 私有：段落迭代器 ————————————————————

    def _iter_docx(self, path: Path) -> Generator[str, None, None]:
        """
        流式读取 .docx: 使用 lxml.iterparse 逐 <w:p> 段
        """
        with zipfile.ZipFile(path) as zf:
            with zf.open("word/document.xml") as xml:
                context = etree.iterparse(xml, events=("end",), tag="{%s}p" % NS["w"])
                for _, elem in context:
                    texts = [t.text for t in elem.iter("{%s}t" % NS["w"]) if t.text]
                    if texts:
                        yield "".join(texts).strip()
                    # 释放内存
                    elem.clear()
                    while elem.getprevious() is not None:
                        del elem.getparent()[0]

    def _iter_tex(self, path: Path) -> Generator[str, None, None]:
        """
        流式读取 .tex: 以空行作为段分隔
        """
        conv = LatexNodes2Text()
        buf: List[str] = []
        with path.open("r", encoding="utf-8", errors="ignore") as fp:
            for line in fp:
                if line.strip() == "":
                    if buf:
                        yield conv.latex_to_text(" ".join(buf))
                        buf.clear()
                else:
                    buf.append(line.rstrip())
        if buf:
            yield conv.latex_to_text(" ".join(buf))

    # —— 私有：LLM 调用 & 结果合并 ————————————

    def _update_terms_from_chunk(self, text: str, out: Dict[str, str]) -> None:
        """
        调 LLM 抽术语；若解析失败，尝试 fallback:
          1. 捕获 ```json ...``` 代码块再 json.loads
          2. 仍失败则记录 warning 并返回
        """
        if not text.strip():
            return

        raw = ""
        try:
            raw = self._call_llm(text)
            data = self._safe_load_json(raw)
            for item in data:
                term = item.get("term", "").strip()
                defi = item.get("definition", "").strip()
                if term and defi and (term not in out or len(defi) > len(out[term])):
                    out[term] = defi
        except DeepSeekAPIError as exc:
            logger.warning("LLM API error: %s", exc)
        except ValueError as exc:  # JSON 解析失败
            logger.warning("LLM extraction fail: %s • Raw: %s", exc, raw[:120])

    # ---------- 新增: 安全 JSON 加载 ----------
    @staticmethod
    def _safe_load_json(raw: str) -> List[Dict]:
        """
        尝试 json.loads(raw)；若失败则在 ```json``` 代码块中提取
        """
        import json, re
        try:
            obj = json.loads(raw)
            return obj if isinstance(obj, list) else []
        except json.JSONDecodeError:
            match = re.search(r"```json(.*?)```", raw, re.S)
            if match:
                return json.loads(match.group(1))
            raise


    def _call_llm(self, text: str) -> str:
        """
        请求 DeepSeek，并尽量让模型输出【纯 JSON】：
          • system 指示“仅输出 JSON 数组”
          • response_format={"type":"json_object"} 表达硬约束（DeepSeek 支持）
        返回 assistant content（str）
        """
        sys_msg = (
            "你是科研助手，只做术语抽取。\n"
            "输出严格的 JSON 数组，每项包含 term 和 definition 两个键。\n"
            "除 JSON 外不要输出任何多余文字。"
        )
        rsp = self.llm.chat_completion(
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": text},
            ],
            model=self.llm_model,
            temperature=0.1,
            max_tokens=1536,
            response_format={"type": "json_object"},  # ✅ DeepSeek 兼容
            stream=False,
        )
        return rsp["choices"][0]["message"]["content"]



# -------------------- CLI 测试入口 --------------------

if __name__ == "__main__":  # pragma: no cover
    """
    用法:
        python document_parsers.py [file]

    若省略文件参数，默认为 tests/sample_documents/sample.docx
    """

    import argparse
    from rich import print  # 彩色终端

    # 1) 加载环境变量
    load_dotenv()
    key = os.getenv("DEEPSEEK_API_KEY") or exit("缺少 DEEPSEEK_API_KEY")

    # 2) 解析命令行
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="待解析文件(.docx/.tex)")
    opts = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    default_path = root / "tests" / "sample_documents" / "sample.docx"
    target = Path(opts.file) if opts.file else default_path

    # 3) 执行解析
    dparser = DocumentParser(DeepSeekClient(api_key=key))
    result = dparser.parse_file(target)

    # 4) 打印前 10 条
    print("[bold green]前 10 条术语[/bold green]")
    for item in result["terms"][:10]:
        short_def = textwrap.shorten(item["definition"], 60)
        print(f"• {item['term']}: {short_def}")

    print("\n[bold blue]元数据[/bold blue]")
    print(json.dumps(result["metadata"], indent=2, ensure_ascii=False))
