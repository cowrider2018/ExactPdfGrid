"""
Optional RapidOCR backend.

Crops each cell out of the rendered page image and runs RapidOCR's models
on the crop. Useful for scanned PDFs where PyMuPDF's native text
extraction returns nothing.

Backends
--------
The unified ``rapidocr`` (>= 3.0) package supports multiple inference
runtimes via its ``EngineType`` enum. We expose two:

* ``"openvino"``   — OpenVINO Runtime (default; faster on Intel CPU/GPU,
                     requires the ``openvino`` Python package).
* ``"onnx"``       — ONNX Runtime (cross-platform fallback, requires
                     the ``onnxruntime`` Python package).

Install
-------
    pip install 'exactpdfgrid[ocr]'        # rapidocr + openvino (default)
    pip install 'exactpdfgrid[ocr-onnx]'   # rapidocr + onnxruntime (fallback)
    pip install 'exactpdfgrid[ocr-all]'    # both backends installed

The RapidOCR package is imported lazily so importing `exactpdfgrid` (or
even `exactpdfgrid.engines`) never triggers the model download.
"""

from __future__ import annotations

import importlib
import warnings

import fitz
import numpy as np

from ..detection import CellRegion
from .base import TextExtractor


_BACKEND_TO_RUNTIME_PKG = {
    "openvino": "openvino",
    "onnx": "onnxruntime",
}
_BACKEND_TO_EXTRA = {
    "openvino": "ocr",
    "onnx": "ocr-onnx",
}


def _runtime_available(backend: str) -> bool:
    """Return True if the runtime package backing `backend` can be imported."""
    pkg = _BACKEND_TO_RUNTIME_PKG[backend]
    try:
        importlib.import_module(pkg)
        return True
    except ImportError:
        return False


def _build_engine(backend: str, **rapidocr_kwargs):
    """Construct a unified rapidocr ``RapidOCR`` engine pinned to `backend`."""
    from rapidocr import RapidOCR
    from rapidocr.utils.typings import EngineType

    engine_type = EngineType.OPENVINO if backend == "openvino" else EngineType.ONNXRUNTIME
    params = {
        "Det.engine_type": engine_type,
        "Cls.engine_type": engine_type,
        "Rec.engine_type": engine_type,
    }
    params.update(rapidocr_kwargs)
    return RapidOCR(params=params)


class RapidOCRExtractor(TextExtractor):
    """OCR-based extractor backed by unified rapidocr (>=3.0)."""

    name = "rapidocr"

    def __init__(self, *, backend: str = "auto", **rapidocr_kwargs):
        """
        Parameters
        ----------
        backend : {"auto", "openvino", "onnx"}
            Which runtime to use under unified rapidocr.

            * ``"auto"`` (default): try OpenVINO first; if its runtime
              package is missing, fall back to ONNX Runtime and emit a
              ``RuntimeWarning``.
            * ``"openvino"``: force OpenVINO; raise ``ImportError`` if the
              ``openvino`` package is missing.
            * ``"onnx"``: force ONNX Runtime; raise ``ImportError`` if the
              ``onnxruntime`` package is missing.
        **rapidocr_kwargs
            Extra entries merged into the ``params`` dict forwarded to
            ``RapidOCR(...)``. Use the dotted keys accepted by rapidocr 3.x
            (e.g. ``{"Global.text_score": 0.5}``).

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

        if backend in {"openvino", "onnx"}:
            self._engine = self._require(backend, **rapidocr_kwargs)
            self.backend_in_use = backend
        else:  # auto
            if _runtime_available("openvino"):
                self._engine = _build_engine("openvino", **rapidocr_kwargs)
                self.backend_in_use = "openvino"
            elif _runtime_available("onnx"):
                warnings.warn(
                    "openvino runtime not found; falling back to onnxruntime. "
                    "Install 'exactpdfgrid[ocr]' for OpenVINO acceleration, or "
                    "pick the 'rapidocr-onnx' engine explicitly to silence this warning.",
                    RuntimeWarning,
                    stacklevel=2,
                )
                self._engine = _build_engine("onnx", **rapidocr_kwargs)
                self.backend_in_use = "onnx"
            else:
                raise ImportError(
                    "The RapidOCR backend requires the unified 'rapidocr' package "
                    "plus a runtime ('openvino' or 'onnxruntime'). Install with:\n"
                    "    pip install 'exactpdfgrid[ocr]'        # OpenVINO (recommended)\n"
                    "    pip install 'exactpdfgrid[ocr-onnx]'   # ONNX Runtime"
                )

    @staticmethod
    def _require(backend: str, **rapidocr_kwargs):
        if not _runtime_available(backend):
            pkg = _BACKEND_TO_RUNTIME_PKG[backend]
            extra = _BACKEND_TO_EXTRA[backend]
            raise ImportError(
                f"The RapidOCR '{backend}' backend requires the '{pkg}' package. "
                f"Install with: pip install 'exactpdfgrid[{extra}]'"
            )
        return _build_engine(backend, **rapidocr_kwargs)

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

        result = self._engine(crop)
        # rapidocr 3.x returns RapidOCROutput with `.txts` as a tuple[str, ...]
        # (or None when nothing is detected); join recognized strings top-to-bottom.
        txts = getattr(result, "txts", None)
        if not txts:
            return ""
        return " ".join(t for t in txts if t)
