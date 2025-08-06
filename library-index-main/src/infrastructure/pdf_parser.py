"""
=======================================
|src/infrastructure|pdf_parser_beta.py|
=======================================

# PDF Parser Class
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
import logging

# Import Docling library related modules
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.datamodel.base_models import InputFormat
from docling_core.types.doc.base import ImageRefMode
from docling_core.types.doc.document import PictureItem
import pymupdf4llm


# Configuring Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PDFConverterConfig:
    """
    PDF Converter Configuration Class
    """
    image_scale: float = 2.0
    generate_page_images: bool = True
    image_ref_mode: ImageRefMode = ImageRefMode.EMBEDDED
    preserve_alt_text: bool = True
    
    def __post_init__(self):
        """
Verify the validity of configuration parameters.

params
------
No parameters

return
------
No return value. A ValueError exception is thrown if the parameters are invalid.
        """
        if self.image_scale <= 0:
            raise ValueError("Error: value **image_scale** must > 0")


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
    error_message: Optional[str] = None
    
    @property
    def has_images(self) -> bool:
        """
Checks whether the conversion result contains an image.

params
------
No parameters

return
------
Returns a Boolean value. True indicates the image is included, False indicates the image is not included.
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
Extracts a data URI from markdown content.

params
------
No parameters

return
------
No return value; the data_uri attribute is automatically set.
        """
        if self.markdown_content:
            match = re.match(r'!\[.*?\]\((.*?)\)', self.markdown_content)
            if match:
                self.data_uri = match.group(1)


class PDFToMarkdownConverter:
    """
    Convert PDF to Markdown string using Docling
    """
    
    def __init__(self, config: Optional[PDFConverterConfig] = None):
        """
        Initializes the PDF to Markdown converter.

params
------
config: Converter configuration object. If None, the default configuration is used.

return
------
No return value.
        """
        self.config = config or PDFConverterConfig()
        self.converter = self._create_converter()
    
    def _create_converter(self) -> DocumentConverter:
        """
Creates a Docling document converter instance.

params
------
No parameters

return
------
Returns the configured DocumentConverter instance.        """
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
        Extract image information from a Docling document.

params
------
doc: The document object after parsing Docling.

return
------
Returns a list of ImageInfo objects containing image information.
        """
        images = []
        
        for item, *level in doc.iterate_items():
            if isinstance(item, PictureItem):
                try:
                    img_md = item.export_to_markdown(
                        doc, 
                        image_mode=self.config.image_ref_mode
                    )
                    images.append(ImageInfo(markdown_content=img_md.strip()))
                except Exception as exc:
                    logger.warning(f"Failed to extract image: {exc}")
                    continue
        
        logger.info(f"Number of images successfully extracted: {len(images)}")
        return images
    
    def _replace_images(self, md_text: str, images: List[ImageInfo]) -> str:
        """
        Replaces image references in Markdown text.

params
------
md_text: Original Markdown text string
images: List of image information containing the image data to be replaced

return
------
Returns the Markdown text string after replacing the image references.
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
                logger.warning("The number of pictures does not match, keep the original reference")
                return match.group(0)
        
        return re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image, md_text)
    
    def convert(self, pdf_path: str) -> ConversionResult:
        """
        Converts a PDF file to Markdown format.

params
------
pdf_path: String path to the PDF file.

return
------
Returns a ConversionResult object containing the conversion result and status information.
        """
        file_path = Path(pdf_path)
        
        # Verify Documents
        if not file_path.exists():
            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
                error_message=f"File does not exist: {pdf_path}"
            )
        
        if file_path.suffix.lower() != '.pdf':
            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
                error_message=f"Not a PDF file: {pdf_path}"
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
            
            logger.info(f"Conversion completed, including the number of pictures: {len(images)}")
            
            return ConversionResult(
                markdown_text=md_text,
                image_count=len(images),
                file_path=file_path,
                success=True
            )
            
        except Exception as exc:
            error_msg = f"Conversion failed: {str(exc)}"
            logger.error(error_msg)
            
            return ConversionResult(
                markdown_text="",
                image_count=0,
                file_path=file_path,
                success=False,
                error_message=error_msg
            )