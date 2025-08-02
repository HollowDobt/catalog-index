"""
==================================
|src/infrastructure|pdf_parser.py|
==================================

# PDF Parser Class
"""

import os
import pymupdf

from dataclasses import dataclass
from typing import List, Dict, Any


class PDFPathError(RuntimeError):
    """
    Path does not exist error
    """

class PDFUnpackingError(RuntimeError):
    """
    The expected number of packets is inconsistent with the actual number
    """

class PDFImgParseError(RuntimeError):
    """
    Unable to parse image
    """


@dataclass
class PDFParser:
    """
    PDFParser parses PDF documents and extracts text blocks, image blocks, and table blocks.
    
    :return: A list containing the entire text block, each element of which is a dictionary:
        "page": page number, "type": content type, "bbox": [x0, y0, x1, y1], "content": content}.
        content is a text string, image bytes, or a list of table data.
    """
    
    file_path: str
    doc: pymupdf.Document | None = None
    

    def __post_init__(self):
        """
        Post-initialization transaction hook function.
        Import the PDF path file downloaded by the user.
        """
        try:
            self.doc = pymupdf.open(self.file_path)
        except Exception as exc:
            raise PDFPathError(f"Failed to open PDF file: {exc}")
        
        
    def parse(self):
        """
        Parse all pages of a PDF file and extract text blocks, image blocks, and table blocks
        """
        all_blocks = []
        assert self.doc , "doc initialite required"
        for page_index in range(len(self.doc)):
            page = self.doc[page_index]
            page_number = page_index + 1
            
            # 1, Detect all tables on the current page and extract their content and borders
            tables = page.find_tables()
            table_blocks = []           # Table block content record
            table_regions = []          # Table block location record
            
            if tables and getattr(tables, "tables", tables):
                for table in tables:
                    bbox = table.bbox
                    table_regions.append(bbox)
                    
                    table_blocks.append({
                        "page": page_number,
                        "type": "table",
                        "bbox": list(bbox),
                        "content": table.extract()
                    })
                    
            # 2, Extract text blocks (skip text within table areas)
            page_dict = page.get_text("dict", sort=True)
            dict_blocks = page_dict.get("blocks", [])
            
            img_xref_map = {
                idx: info[0] for idx, info in enumerate(page.get_images(full=True))
            }
            
            text_blocks: list[dict] = []
            image_blocks: list[dict] = []

            for blk in dict_blocks:
                btype = blk.get("type")
                x0, y0, x1, y1 = blk["bbox"]

                if btype == 0: 
                    text = ""
                    for line in blk.get("lines", []):
                        for span in line.get("spans", []):
                            text += span.get("text", "")
                        text += "\n"
                    text = text.strip()
                    if not text:
                        continue
                    
                    if any(x0 >= bx0 and y0 >= by0 and x1 <= bx1 and y1 <= by1
                        for bx0, by0, bx1, by1 in table_regions):
                        continue
                    
                    text_blocks.append({
                        "page": page_number,
                        "type": "text",
                        "bbox": [x0, y0, x1, y1],
                        "content": text
                    })
                
                elif btype == 1:
                    xref = blk.get("xref", 0)
                    if not xref:
                        continue
                    try:
                        img_dict = self.doc.extract_image(xref)
                    except Exception:
                        continue
                    
                    image_blocks.append({
                        "page": page_number,
                        "type": "image",
                        "bbox": [x0, y0, x1, y1],
                        "content": img_dict.get("image", b""),
                    })
            
            page_blocks = text_blocks + image_blocks + table_blocks
            page_blocks.sort(key=lambda b : (b["bbox"][1], b["bbox"][0]))
            all_blocks.extend(page_blocks)
        
        return all_blocks
    
    
    def parse_and_merge(self):
        """
        Call self.parse() to get the original list of blocks, 
        then merge consecutive 'text' blocks into a new 'paragraph' block in order 
        and insert it at the same position (preserving the original order).
        """
        raw_blocks = self.parse()
        merged_blocks = []
        
        buffer = []
        
        def _flush():
            """
            Merge the stored text blocks into paragraphs and push them into merged_blocks.
            """
            if not buffer:
                return
            paragraph = " ".join(b["content"].strip() for b in buffer).strip()
            x0 = min(b["bbox"][0] for b in buffer)
            y0 = min(b["bbox"][1] for b in buffer)
            x1 = max(b["bbox"][2] for b in buffer)
            y1 = max(b["bbox"][3] for b in buffer)
            merged_blocks.append({
                "page": buffer[0]["page"],
                "type": "paragraph",
                "bbox": [x0, y0, x1, y1],
                "content": paragraph,
            })
            buffer.clear()
        
        for blk in raw_blocks:
            if blk["type"] == "text":
                buffer.append(blk)
            else:
                _flush()
                merged_blocks.append(blk)
        _flush()
        
        return merged_blocks
    
    
    def __del__(self):
        """
        Closes the PDF document when the object is destroyed.
        """
        try:
            self.doc.close()
        except Exception:
            pass