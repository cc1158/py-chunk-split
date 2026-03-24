from .base import BaseParser, Section
from .pdf_parser import PDFParser
from .docx_parser import DOCXParser
from .txt_parser import TXTParser
from .structure_detector import StructureDetector, create_detector

__all__ = [
    "BaseParser",
    "Section",
    "PDFParser",
    "DOCXParser",
    "TXTParser",
    "StructureDetector",
    "create_detector",
]
