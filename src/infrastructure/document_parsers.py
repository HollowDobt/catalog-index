"""Utility to stream-parse **DOCX** / **LaTeX** files into structured terms."""

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
from typing import Dict, Generator, List, Any, Set

from dotenv import load_dotenv          # load .env for CLI
from lxml import etree                  # streaming XML
from tqdm import tqdm                   # progress bar
from pylatexenc.latex2text import LatexNodes2Text  # LaTeX→text

# internal deps
from deepseek_client import DeepSeekClient, DeepSeekAPIError
from mem0_client import Mem0Client

# -------------------- 常量与日志 --------------------
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
logger = logging.getLogger(__name__)

# -------------------- 工具函数 --------------------


def _sha256(data: str | bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# -------------------- Main parser --------------------


@dataclass
class DocumentParser:
    """Stream-parse documents into term-definition segments."""

    llm: DeepSeekClient
    max_chars: int = 8_000
    llm_model: str = field(default="deepseek-chat")

    # —— 公共 API ————————————————————————

    def parse_file(self, file_path: str | Path) -> Dict[str, Any]:
        """Parse *file_path* and return extracted segments and metadata."""
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

        # collect terms using a dict to deduplicate
        _terms: Dict[str, Dict[str, Any]] = {}
        _total_chars = 0
        _chunk: List[str] = []
        _start_para = 1
        _para_idx = 0

        for para in para_iter:
            _para_idx += 1
            _total_chars += len(para) + 1
            _chunk.append(para)

            # 达到 3 段或累积字符超限即发送 LLM
            if len(_chunk) >= 3 or sum(len(p) for p in _chunk) > self.max_chars:
                self._update_terms_from_chunk("\n".join(_chunk), _terms, _start_para, _para_idx)
                _chunk.clear()
                _start_para = _para_idx + 1

        # 处理结尾残余
        if _chunk:
            self._update_terms_from_chunk("\n".join(_chunk), _terms, _start_para, _para_idx)

        segments = []
        for term, info in _terms.items():
            segments.append(
                {
                    "term": term,
                    "synonyms": sorted(info["synonyms"]),
                    "definition": info["definition"],
                    "source": {"filename": file_path.name, "paragraphs": info["occurrences"]},
                }
            )

        return {
            "segments": segments,
            "metadata": {
                "filename": file_path.name,
                "chars": _total_chars,
                "sha256": _sha256(str(file_path) + str(_total_chars)),
            },
        }



    # —— 私有：段落迭代器 ————————————————————

    def _iter_docx(self, path: Path) -> Generator[str, None, None]:
        """Yield paragraph texts from a .docx file via streaming XML."""
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
        """Yield paragraphs from a .tex file separated by blank lines."""
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

    def _update_terms_from_chunk(
        self,
        text: str,
        out: Dict[str, Dict[str, Any]],
        para_start: int,
        para_end: int,
    ) -> None:
        """Update *out* with terms extracted from the text chunk via LLM."""
        if not text.strip():
            return

        raw = ""
        try:
            raw = self._call_llm(text)
            data = self._safe_load_json(raw)
            for item in data:
                term = item.get("term", "").strip()
                defi = item.get("definition", "").strip()
                syns = [s.strip() for s in item.get("synonyms", []) if isinstance(s, str) and s.strip()]
                if not term:
                    continue
                info = out.setdefault(term, {"definition": "", "synonyms": set(), "occurrences": []})
                if defi and len(defi) > len(info["definition"]):
                    info["definition"] = defi
                info["synonyms"].update(syns)
                info["occurrences"].append({"start": para_start, "end": para_end})
        except DeepSeekAPIError as exc:
            logger.warning("LLM API error: %s", exc)
        except ValueError as exc:  # JSON 解析失败
            logger.warning("LLM extraction fail: %s • Raw: %s", exc, raw[:120])

    # ---------- 新增: 安全 JSON 加载 ----------
    @staticmethod
    def _safe_load_json(raw: str) -> List[Dict]:
        """Safely load a JSON list from raw LLM output."""
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
        """Call the LLM to extract terms, expecting strictly JSON output."""
        sys_msg = (
            "你是科研助手，只做术语抽取。\n"
            "输出严格的 JSON 数组，每项包含 term, synonyms, definition 三个键。\n"
            "synonyms 应为字符串数组，可为空。\n"
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


class PaperParser(DocumentParser):
    """Parse papers and persist segments to mem0."""

    def __init__(self, llm: DeepSeekClient, mem0: Mem0Client, max_chars: int = 8_000, llm_model: str = "deepseek-chat") -> None:
        super().__init__(llm=llm, max_chars=max_chars, llm_model=llm_model)
        self.mem0 = mem0

    def parse_and_store(self, file_path: str | Path, *, user_id: str = "paper_parser") -> List[str]:
        """Parse the document and write segments to mem0."""
        result = self.parse_file(file_path)
        ids: List[str] = []
        for seg in result["segments"]:
            meta = {
                "term": seg["term"],
                "synonyms": seg["synonyms"],
                **seg["source"],
            }
            try:
                rsp = self.mem0.add_memory(seg["definition"], metadata=meta, user_id=user_id)
                if isinstance(rsp, dict) and "id" in rsp:
                    ids.append(rsp["id"])
            except Exception as exc:  # noqa: BLE001
                logger.warning("mem0 add failed: %s", exc)
        return ids



# -------------------- CLI 测试入口 --------------------

if __name__ == "__main__":  # pragma: no cover
    """CLI helper for manual testing."""

    import argparse
    from rich import print  # colorful output

    # 1) load environment
    load_dotenv()
    key = os.getenv("DEEPSEEK_API_KEY") or exit("Missing DEEPSEEK_API_KEY")

    # 2) parse command
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", help="File to parse (.docx/.tex)")
    opts = parser.parse_args()

    root = Path(__file__).resolve().parents[2]
    default_path = root / "tests" / "sample_documents" / "sample.docx"
    target = Path(opts.file) if opts.file else default_path

    # 3) run parser
    dparser = DocumentParser(DeepSeekClient(api_key=key))
    result = dparser.parse_file(target)

    # 4) show first 10 terms
    print("[bold green]First 10 terms[/bold green]")
    for item in result["segments"][:10]:
        short_def = textwrap.shorten(item["definition"], 60)
        print(f"• {item['term']}: {short_def} \u2192 {item['synonyms']}")

    print("\n[bold blue]Metadata[/bold blue]")
    print(json.dumps(result["metadata"], indent=2, ensure_ascii=False))
