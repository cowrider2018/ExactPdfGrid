"""Abstract base class for cell-text extractors."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover
    import fitz
    from ..detection import CellRegion


class TextExtractor(ABC):
    """
    Engine-agnostic interface for extracting text from a single cell.

    Implementations may use either the PDF's vector text (fast, exact) or
    OCR on the rendered image (works on scanned PDFs). The orchestrator
    passes both `fitz_page` and `image`; each subclass uses whichever it
    needs.
    """

    name: str = "abstract"

    @abstractmethod
    def extract(
        self,
        *,
        fitz_page: "fitz.Page",
        image: np.ndarray,
        cell: "CellRegion",
        dpi: int,
        padding_px: int,
    ) -> str:
        """Return the raw text for one cell (before clean_text_pipeline)."""
        raise NotImplementedError
