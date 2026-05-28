"""ExactPdfGrid - extract bordered tables from PDFs and export to .xlsx."""

from .config import DetectionConfig, ExtractionConfig, OutputConfig
from .core import process_pdf
from .detection import CellRegion, LineSegment
from .engines import TextExtractor, get_extractor
from .utils import (
    TextCleaner,
    clean_text_pipeline,
    normalize_whitespace,
    split_at_first_paren,
    strip_outer_whitespace,
    strip_parentheses,
    strip_square_brackets,
)

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "DetectionConfig",
    "ExtractionConfig",
    "OutputConfig",
    "process_pdf",
    "CellRegion",
    "LineSegment",
    "TextExtractor",
    "get_extractor",
    "TextCleaner",
    "clean_text_pipeline",
    "normalize_whitespace",
    "split_at_first_paren",
    "strip_outer_whitespace",
    "strip_parentheses",
    "strip_square_brackets",
]
