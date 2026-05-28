"""
Engine-agnostic text extraction orchestrator.

Iterates over the detected cells, asks the configured TextExtractor for
raw text per cell, runs the configured clean_text_pipeline on each result,
and writes the cleaned text into CellRegion.text.
"""

from __future__ import annotations
from typing import Optional

import fitz
import numpy as np

from .config import ExtractionConfig
from .detection import CellRegion
from .engines import get_extractor
from .utils import clean_text_pipeline


def extract_cells_text(
    fitz_page: fitz.Page,
    image: np.ndarray,
    cells: list[CellRegion],
    dpi: int = 200,
    cfg: Optional[ExtractionConfig] = None,
) -> list[CellRegion]:
    """
    Fill in `.text` on every CellRegion using the configured extractor and
    cleaning pipeline.

    Parameters
    ----------
    fitz_page : fitz.Page
        The page the cells were detected on (needed by PyMuPDFExtractor).
    image : np.ndarray
        The rendered BGR image of the same page (needed by OCR engines).
    cells : list[CellRegion]
        Cell list from build_cell_grid.
    dpi : int
        DPI used when rendering the image.
    cfg : ExtractionConfig, optional
        Engine selection, padding, and cleaning pipeline. Defaults to a
        fresh ExtractionConfig() — PyMuPDF + normalize_whitespace.

    Returns
    -------
    The same `cells` list with `.text` populated.
    """
    if cfg is None:
        cfg = ExtractionConfig()

    extractor = get_extractor(cfg.engine)

    for cell in cells:
        raw = extractor.extract(
            fitz_page=fitz_page,
            image=image,
            cell=cell,
            dpi=dpi,
            padding_px=cfg.padding_px,
        )
        cell.text = clean_text_pipeline(raw, cfg.clean_pipeline)
        if cell.text:
            print(f"  [extract:{extractor.name}] r{cell.row}c{cell.col} -> {cell.text!r}")

    filled = sum(1 for c in cells if c.text)
    print(f"  [extract:{extractor.name}] {filled}/{len(cells)} cells have text")
    return cells
