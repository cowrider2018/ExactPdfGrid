"""
Optional RapidOCR backend.

Crops each cell out of the rendered page image and runs RapidOCR's models
on the crop. Useful for scanned PDFs where PyMuPDF's native text
extraction returns nothing.

Backends
--------
Two upstream packages expose the same `RapidOCR` class:

* ``rapidocr_openvino``   — OpenVINO Runtime (default; faster on Intel CPU/GPU)
* ``rapidocr_onnxruntime`` — ONNX Runtime (cross-platform fallback)

Install
-------
    pip install 'exactpdfgrid[ocr]'        # OpenVINO (default acceleration)
    pip install 'exactpdfgrid[ocr-onnx]'   # ONNX Runtime opt-out

The RapidOCR package is imported lazily so importing `exactpdfgrid` (or
even `exactpdfgrid.engines`) never triggers the model download.
"""

from __future__ import annotations

import warnings

import fitz
import numpy as np

from ..detection import CellRegion
from .base import TextExtractor


def _import_openvino():
    from rapidocr_openvino import RapidOCR  # type: ignore
    return RapidOCR


def _import_onnx():
    from rapidocr_onnxruntime import RapidOCR  # type: ignore
    return RapidOCR


class RapidOCRExtractor(TextExtractor):
    """OCR-based extractor backed by either rapidocr-openvino or rapidocr-onnxruntime."""

    name = "rapidocr"

    def __init__(self, *, backend: str = "auto", **rapidocr_kwargs):
        """
        Parameters
        ----------
        backend : {"auto", "openvino", "onnx"}
            Which RapidOCR runtime to load.

            * ``"auto"`` (default): try OpenVINO first; if not installed, fall
              back to ONNX Runtime and emit a ``RuntimeWarning``.
            * ``"openvino"``: force OpenVINO; raise ``ImportError`` if missing.
            * ``"onnx"``: force ONNX Runtime; raise ``ImportError`` if missing.
        **rapidocr_kwargs
            Forwarded verbatim to the underlying `RapidOCR(...)` constructor.
            Examples: `det_model_path`, `rec_model_path`, `use_angle_cls`, etc.

        Attributes
        ----------
        backend_in_use : str
            ``"openvino"`` or ``"onnx"`` — the runtime that was actually loaded.
        """
        backend = backend.lower()
        if backend not in {"auto", "openvino", "onnx"}:
            raise ValueError(
                f"backend must be one of 'auto', 'openvino', 'onnx'; got {backend!r}"
            )

        if backend == "openvino":
            RapidOCR = self._require("openvino")
            self.backend_in_use = "openvino"
        elif backend == "onnx":
            RapidOCR = self._require("onnx")
            self.backend_in_use = "onnx"
        else:  # auto
            try:
                RapidOCR = _import_openvino()
                self.backend_in_use = "openvino"
            except ImportError:
                try:
                    RapidOCR = _import_onnx()
                except ImportError as e:
                    raise ImportError(
                        "The RapidOCR backend requires either 'rapidocr-openvino' "
                        "or 'rapidocr-onnxruntime'. Install with:\n"
                        "    pip install 'exactpdfgrid[ocr]'        # OpenVINO (recommended)\n"
                        "    pip install 'exactpdfgrid[ocr-onnx]'   # ONNX Runtime"
                    ) from e
                warnings.warn(
                    "rapidocr-openvino not found; falling back to rapidocr-onnxruntime. "
                    "Install 'exactpdfgrid[ocr]' for OpenVINO acceleration, or pick the "
                    "'rapidocr-onnx' engine explicitly to silence this warning.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self.backend_in_use = "onnx"

        self._engine = RapidOCR(**rapidocr_kwargs)

    @staticmethod
    def _require(backend: str):
        importer = _import_openvino if backend == "openvino" else _import_onnx
        pkg, extra = (
            ("rapidocr-openvino", "ocr")
            if backend == "openvino"
            else ("rapidocr-onnxruntime", "ocr-onnx")
        )
        try:
            return importer()
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                f"The RapidOCR '{backend}' backend requires the '{pkg}' package. "
                f"Install with: pip install 'exactpdfgrid[{extra}]'"
            ) from e

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
