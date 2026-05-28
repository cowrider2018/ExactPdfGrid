"""
Optional RapidOCR backend.

Crops each cell out of the rendered page image and runs RapidOCR's
ONNX-runtime models on the crop. Useful for scanned PDFs where
PyMuPDF's native text extraction returns nothing.

Install
-------
    pip install 'exactpdfgrid[ocr]'

The RapidOCR package is imported lazily so importing `exactpdfgrid` (or
even `exactpdfgrid.engines`) never triggers the model download.
"""

from __future__ import annotations

import fitz
import numpy as np

from ..detection import CellRegion
from .base import TextExtractor


class RapidOCRExtractor(TextExtractor):
    """OCR-based extractor using rapidocr-onnxruntime."""

    name = "rapidocr"

    def __init__(self, **rapidocr_kwargs):
        """
        Parameters
        ----------
        **rapidocr_kwargs
            Forwarded verbatim to the underlying `RapidOCR(...)` constructor.
            Examples: `det_model_path`, `rec_model_path`, `use_angle_cls`, etc.
        """
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "The RapidOCR backend requires the 'ocr' extra. "
                "Install with: pip install 'exactpdfgrid[ocr]'"
            ) from e
        self._engine = RapidOCR(**rapidocr_kwargs)

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
        h, w = image.shape[:2]
        y1 = max(0, cell.y1 + p)
        y2 = min(h, cell.y2 - p)
        x1 = max(0, cell.x1 + p)
        x2 = min(w, cell.x2 - p)
        if y2 <= y1 or x2 <= x1:
            return ""
        crop = image[y1:y2, x1:x2]

        result, _ = self._engine(crop)
        if not result:
            return ""
        # rapidocr returns [[box, text, score], ...]; join recognized strings top-to-bottom.
        return " ".join(item[1] for item in result if len(item) >= 2 and item[1])
