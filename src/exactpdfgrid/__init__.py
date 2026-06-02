"""ExactPdfGrid - extract bordered tables from PDFs and export to .xlsx."""

from __future__ import annotations
import sys
import types
from pathlib import Path
from typing import Optional, Union

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

__version__ = "0.1.1"


# Engine string aliases (UPPER_CASE so they don't shadow the real `pymupdf`
# package on `from exactpdfgrid import *`). Either of:
#     exactpdfgrid("a.pdf", "rapidocr", "out/")
#     exactpdfgrid("a.pdf", RAPIDOCR,    "out/")
# resolves through engines.get_extractor.
PYMUPDF: str = "pymupdf"
RAPIDOCR: str = "rapidocr"            # auto: OpenVINO first, ONNX fallback
RAPIDOCR_VINO: str = "rapidocr-vino"  # force OpenVINO runtime
RAPIDOCR_ONNX: str = "rapidocr-onnx"  # force ONNX runtime


def run(
    pdf_path: Union[str, Path],
    engine: Union[str, TextExtractor] = "pymupdf",
    out_dir: Union[str, Path] = "output",
    *,
    detection: Optional[DetectionConfig] = None,
    extraction: Optional[ExtractionConfig] = None,
    output: Optional[OutputConfig] = None,
    **kwargs,
) -> Optional[Path]:
    """
    Shorthand wrapper around :func:`process_pdf`.

    Positional form mirrors what most users want at the call site:

        exactpdfgrid("input.pdf", "rapidocr", "outputpath")

    `extra kwargs` (e.g. ``write_debug_images=False``) are forwarded to
    :func:`process_pdf` verbatim.

    If both a positional ``engine`` and an explicit ``extraction`` config are
    supplied, the positional ``engine`` wins — it is the shorthand lever.
    """
    if extraction is None:
        extraction = ExtractionConfig(engine=engine)
    elif engine != "pymupdf":
        extraction = ExtractionConfig(
            engine=engine,
            padding_px=extraction.padding_px,
            clean_pipeline=extraction.clean_pipeline,
        )
    return process_pdf(
        pdf_path,
        detection=detection,
        extraction=extraction,
        output=output,
        out_dir=out_dir,
        **kwargs,
    )


class _CallableModule(types.ModuleType):
    """Module subclass that forwards `package(...)` calls to :func:`run`."""

    def __call__(self, *args, **kwargs):
        return run(*args, **kwargs)


sys.modules[__name__].__class__ = _CallableModule


__all__ = [
    "__version__",
    "DetectionConfig",
    "ExtractionConfig",
    "OutputConfig",
    "process_pdf",
    "run",
    "PYMUPDF",
    "RAPIDOCR",
    "RAPIDOCR_VINO",
    "RAPIDOCR_ONNX",
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
