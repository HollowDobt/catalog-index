"""
# src/infrastructure/parsers/pdf_to_md.py

A parser for converting PDF files to Markdown files

PDF 文件转化为 Markdown 文件的解析器
"""


import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import logging

from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import PictureItem
import pymupdf4llm

from config import CONFIG


logger = logging.getLogger(__name__)


@dataclass
class PDFConverterConfig:
    """
    PDF Converter Configuration Class
    """

    image_scale: float = CONFIG["PDF_CONVERTER_IMAGE_SCALE"]
    generate_page_images: bool = CONFIG["PDF_CONVERTER_IMAGE_GENERATOR"]
    image_ref_mode: ImageRefMode = ImageRefMode.EMBEDDED
    preserve_alt_text: bool = True

    def __post_init__(self):
        """
        Verify configuration parameters
        """
        if self.image_scale <= 0:
            logger.warning(f"*image_scale* must be greater than zero. Use default: 2.0")
            self.image_scale = 2.0


@dataclass
class ConversionResult:
    """
    Conversion result data class

    # Used to store conversion results
    """

    markdown_text: str
    image_count: int
    file_path: Path
    success: bool = True

    @property
    def has_images(self) -> bool:
        """
        Check whether the result includes any images.

        return
        ------
        True if at least one image is present
        """
        return self.image_count > 0


@dataclass
class ImageInfo:
    """
    Image information data class
    """

    markdown_content: str
    alt_text: str = ""
    data_uri: str = ""

    def __post_init__(self):
        """
        Extracting data URIs from markdown content
        """
        if self.markdown_content:
            match = re.match(r"!\[.*?\]\((.*?)\)", self.markdown_content)
            if match:
                self.data_uri = match.group(1)


class PDFToMarkdownConverter:
    """
    Convert PDF to Markdown string using Docling
    """

    def __init__(self, config: Optional[PDFConverterConfig] = None):
        """
        Initialize the converter

        params
        ------
        config: Converter configuration, if None, use the default configuration
        """
        self.config = config or PDFConverterConfig()
        self.converter = self._create_converter()
        logger.info("PDF converter initialization completed")

    def _create_converter(self) -> DocumentConverter:
        """
        Create the document converter instance.

        return
        ------
        Configured DocumentConverter object
        """
        pipeline_opts = PdfPipelineOptions()
        pipeline_opts.images_scale = self.config.image_scale
        pipeline_opts.generate_page_images = self.config.generate_page_images

        return DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_opts)
            }
        )

    def _extract_images(self, doc) -> List[ImageInfo]:
        """
        Extract image information from documents

        params
        ------
        doc: Docling document

        return
        ------
        Picture information list
        """
        images = []

        for item, *level in doc.iterate_items():
            if isinstance(item, PictureItem):
                try:
                    img_md = item.export_to_markdown(
                        doc, image_mode=self.config.image_ref_mode
                    )
                    images.append(ImageInfo(markdown_content=img_md.strip()))
                    logger.info("Extract one image successfully. Continue next")
                except Exception as exc:
                    logger.warning(f"Failed to extract image: {exc}")
                    continue

        logger.info(f"Image extraction process completed. Number: {len(images)}")
        return images

    def _replace_images(self, md_text: str, images: List[ImageInfo]) -> str:
        """
        Replace image references in Markdown text

        params
        ------
        md_text: Original Markdown text
        images: Picture information list

        return
        ------
        Markdown text after replacement
        """
        image_iter = iter(images)

        def replace_image(match: re.Match) -> str:
            original_alt_text = match.group(1)

            try:
                image_info = next(image_iter)
                if self.config.preserve_alt_text and original_alt_text:
                    return f"![{original_alt_text}]({image_info.data_uri})"
                else:
                    return image_info.markdown_content
            except StopIteration:
                logger.warning(
                    "The number of pictures does not match, keep the original reference"
                )
                return match.group(0)

        return re.sub(r"!\[(.*?)\]\((.*?)\)", replace_image, md_text)

    def convert(self, pdf_path: str) -> ConversionResult:
        """
        Convert PDF files to Markdown format

        params
        ------
        pdf_path: PDF file path

        return
        ------
        Conversion result object
        """
        file_path = Path(pdf_path)

        # Verify Documents
        if not file_path.exists():
            logger.warning(f"The input PDF file path is incorrect: {file_path}. Use dafault: ''")
            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
            )

        if file_path.suffix.lower() != ".pdf":
            logger.warning(f"File suffix error: {file_path}. Expected: pdf. Use default: ''")
            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
            )

        try:
            logger.info(f"Start converting PDF: {pdf_path}")

            # 1 Parsing PDF using Docling
            result = self.converter.convert(file_path)
            doc = result.document

            # 2 Generate Markdown using PyMuPDF4LLM
            md_text = pymupdf4llm.to_markdown(str(file_path))

            # 3. Extract images
            images = self._extract_images(doc)

            # 4. Replace image reference
            if images:
                md_text = self._replace_images(md_text, images)

            logger.info(
                f"Conversion completed, including the number of pictures: {len(images)}"
            )

            return ConversionResult(
                markdown_text=md_text,
                image_count=len(images),
                file_path=file_path,
                success=True,
            )

        except Exception as exc:
            logger.error(f"Conversion failed: {exc}")

            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
            )
