"""
Default text extractor backed by PyMuPDF's native text engine.

Uses the PDF vector data directly (no OCR). Fastest and most accurate
when the PDF contains actual text (not scanned images).
"""

from __future__ import annotations

import fitz
import numpy as np

from ..detection import CellRegion
from .base import TextExtractor


def _px_to_pt(px: float, dpi: int) -> float:
    """Convert a pixel coordinate (at `dpi`) back to PDF user-space points."""
    return px * 72.0 / dpi


class PyMuPDFExtractor(TextExtractor):
    """Clip-extract text from the fitz.Page that was rendered."""

    name = "pymupdf"

    def extract(
        self,
        *,
        fitz_page: fitz.Page,
        image: np.ndarray,
        cell: CellRegion,
        dpi: int,
        padding_px: int,
    ) -> str:
        p = padding_px
        rect = fitz.Rect(
            _px_to_pt(cell.x1 + p, dpi),
            _px_to_pt(cell.y1 + p, dpi),
            _px_to_pt(cell.x2 - p, dpi),
            _px_to_pt(cell.y2 - p, dpi),
        )
        return fitz_page.get_text("text", clip=rect).strip()
