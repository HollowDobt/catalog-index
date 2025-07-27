"""Utility to stream-parse **DOCX** / **LaTeX** files into structured terms."""

from __future__ import annotations

import hashlib  # compute SHA-256
import json  # decode LLM JSON
import logging
import os
import sys
import re  # regular expressions
import textwrap  # console output width
import zipfile  # unzip .docx
from dataclasses import dataclass, field
from pathlib import Path  # path utils
from typing import Dict, Generator, List, Any, Set, Protocol

from dotenv import load_dotenv  # load .env for CLI
from xml.etree import ElementTree as ET  # standard streaming XML
from tqdm import tqdm  # progress bar
from pylatexenc.latex2text import LatexNodes2Text  # LaTeX→text

# internal deps
from deepseek_client import DeepSeekClient, DeepSeekAPIError
from mem0_client import Mem0Client
import config


class LLMProtocol(Protocol):
    """Minimal chat completion interface required by the parser."""

    def chat_completion(self, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        ...

# constants and logging
NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
logger = logging.getLogger(__name__)

# helper utilities


def _sha256(data: str | bytes) -> str:
    """Return the SHA-256 hex digest of *data*."""
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# -------------------- Main parser --------------------


@dataclass
class DocumentParser:
    """Stream-parse documents into term-definition segments."""

    llm: LLMProtocol
    max_chars: int = 8_000
    # default model for parsing
    llm_model: str = field(default=config.PARSER_MODEL)

    # public API

    def parse_file(self, file_path: str | Path) -> Dict[str, Any]:
        """Parse *file_path* and return extracted segments and metadata."""
        file_path = Path(file_path).resolve()
        if not file_path.exists():
            raise FileNotFoundError(file_path)

        # choose iterator based on extension
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

        with tqdm(desc="parse", unit="para", disable=not sys.stderr.isatty()) as pbar, \
             tqdm(desc="deepseek", unit="call", disable=not sys.stderr.isatty()) as lbar:
            for para in para_iter:
                _para_idx += 1
                _total_chars += len(para) + 1
                _chunk.append(para)
                pbar.update(1)

                # send chunk to LLM every 3 paragraphs or when too long
                if len(_chunk) >= 3 or sum(len(p) for p in _chunk) > self.max_chars:
                    self._update_terms_from_chunk("\n".join(_chunk), _terms, _start_para, _para_idx, progress=lbar)
                    _chunk.clear()
                    _start_para = _para_idx + 1

            # handle final chunk
            if _chunk:
                self._update_terms_from_chunk("\n".join(_chunk), _terms, _start_para, _para_idx, progress=lbar)

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



    # internal: paragraph generators

    def _iter_docx(self, path: Path) -> Generator[str, None, None]:
        """Yield paragraph texts from a .docx file via streaming XML."""
        p_tag = f"{{{NS['w']}}}p"
        t_tag = f"{{{NS['w']}}}t"
        buffer: List[str] = []
        with zipfile.ZipFile(path) as zf:
            with zf.open("word/document.xml") as xml:
                for event, elem in ET.iterparse(xml, events=("start", "end")):
                    if event == "start" and elem.tag == p_tag:
                        buffer.clear()
                    elif event == "end" and elem.tag == t_tag:
                        if elem.text:
                            buffer.append(elem.text)
                    elif event == "end" and elem.tag == p_tag:
                        paragraph = "".join(buffer).strip()
                        if paragraph:
                            yield paragraph
                        elem.clear()

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

    # internal: call LLM and merge results

    def _update_terms_from_chunk(
        self,
        text: str,
        out: Dict[str, Dict[str, Any]],
        para_start: int,
        para_end: int,
        *,
        progress: tqdm | None = None,
    ) -> None:
        """Update *out* with terms extracted from the text chunk via LLM."""
        if not text.strip():
            return

        raw = ""
        try:
            raw = self._call_llm(text)
            if progress is not None:
                progress.update(1)
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
        except ValueError as exc:  # JSON decode error
            logger.warning("LLM extraction fail: %s • Raw: %s", exc, raw[:120])

    # safe JSON loading helper
    @staticmethod
    def _safe_load_json(raw: str) -> List[Dict]:
        """Safely load a JSON list from raw LLM output."""
        import json, re
        try:
            obj = json.loads(raw)
            if isinstance(obj, list):
                return obj
            if isinstance(obj, dict):
                # Common mis-format: single object or wrapper key
                if {"term", "definition"} <= obj.keys():
                    return [obj]
                for key in ("segments", "items", "data"):
                    if key in obj and isinstance(obj[key], list):
                        return obj[key]
            return []
        except json.JSONDecodeError:
            match = re.search(r"```json(.*?)```", raw, re.S)
            if not match:
                match = re.search(r"({.*}|\[.*\])", raw, re.S)
            if match:
                return json.loads(match.group(1))
            raise


    def _call_llm(self, text: str) -> str:
        """Call the LLM to extract terms, expecting strictly JSON output."""
        sys_msg = (
            "You are a research assistant. Extract terms only.\n"
            "Return a strict JSON array with keys term, synonyms and definition.\n"
            "synonyms should be a string array and may be empty.\n"
            "Return nothing except JSON."
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
        content = rsp.get("choices", [{}])[0].get("message", {}).get("content", "")
        if isinstance(content, dict):
            return json.dumps(content)
        return str(content)


class PaperParser(DocumentParser):
    """Parse papers and persist segments to mem0."""

    def __init__(self, llm: LLMProtocol, mem0: Mem0Client, max_chars: int = 8_000, llm_model: str = "deepseek-chat") -> None:
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



# -------------------- CLI test entry --------------------

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
