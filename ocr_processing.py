"""
Step 4: Extract text from each detected cell using PyMuPDF's native text engine.

Cell bounding boxes are in pixel coordinates (from the rendered image).
We convert them back to PDF user-space points (1 pt = 1/72 inch) and ask
PyMuPDF to clip-extract exactly the text inside each cell rectangle.
No OCR is involved – text is read directly from the PDF vector data.
"""

from __future__ import annotations
import fitz  # PyMuPDF
from table_detection import CellRegion


def _px_to_pt(px: float, dpi: int) -> float:
    """Convert a pixel coordinate (at `dpi`) back to PDF user-space points."""
    return px * 72.0 / dpi


def extract_cells_text(
    page: fitz.Page,
    cells: list[CellRegion],
    dpi: int = 200,
    padding_px: int = 3,
) -> list[CellRegion]:
    """
    Fill in the `text` field of every CellRegion by clipping PyMuPDF's text
    extraction to each cell's bounding box.

    Parameters
    ----------
    page       : the fitz.Page that was rendered to produce the image
    cells      : cell list produced by table_detection.build_cell_grid
    dpi        : the DPI used when rendering (needed for px → pt conversion)
    padding_px : inset in pixels from the cell border to avoid capturing
                 border-line characters

    Returns
    -------
    The same `cells` list with `.text` populated.
    """
    def to_rect(cell: CellRegion) -> fitz.Rect:
        p = padding_px
        return fitz.Rect(
            _px_to_pt(cell.x1 + p, dpi),
            _px_to_pt(cell.y1 + p, dpi),
            _px_to_pt(cell.x2 - p, dpi),
            _px_to_pt(cell.y2 - p, dpi),
        )

    for cell in cells:
        rect = to_rect(cell)
        # "text" mode returns plain text with newlines between lines
        raw = page.get_text("text", clip=rect).strip()
        # Normalise internal whitespace
        cell.text = " ".join(raw.split())
        if cell.text:
            print(f"  [extract] r{cell.row}c{cell.col} → {cell.text!r}")

    filled = sum(1 for c in cells if c.text)
    print(f"  [extract] {filled}/{len(cells)} cells have text")
    return cells
