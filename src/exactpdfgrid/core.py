"""
High-level pipeline orchestration.

`process_pdf` is the single public entry point used by both the CLI
(`exactpdfgrid.cli`) and the web server (`exactpdfgrid.web.server`).
With default configs it reproduces the original main.py behavior exactly.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

import cv2
import fitz

from .config import DetectionConfig, ExtractionConfig, OutputConfig
from .detection import build_cell_grid, detect_line_segments, draw_debug
from .detection_lineless import detect_gridlines_whitespace
from .extraction import extract_cells_text
from .output import resolve_grid, write_xlsx_workbook
from .pdf_render import pdf_to_images, save_page_images


def _process_page(
    img,
    fitz_page: fitz.Page,
    page_index: int,
    det: DetectionConfig,
    ext: ExtractionConfig,
    debug_image_path: Optional[Path],
) -> tuple[list, list[int], list[int]]:
    """Detect cells + extract text on a single page."""
    print(f"\n-- Page {page_index + 1} --------------------------------------------")

    if det.mode == "lineless":
        accepted, rejected = detect_gridlines_whitespace(
            img,
            ink_threshold=det.ink_threshold,
            min_gap_v=det.lineless_min_gap_v,
            max_gap_v=det.lineless_max_gap_v,
            min_gap_h=det.lineless_min_gap_h,
            max_gap_h=det.lineless_max_gap_h,
            ink_tolerance=det.lineless_ink_tolerance,
        )
    else:
        accepted, rejected = detect_line_segments(
            img,
            min_line_length=det.min_line_length,
            ink_threshold=det.ink_threshold,
            max_gap=det.max_gap,
            aspect_ratio=det.aspect_ratio,
            dilate_kernel=det.dilate_kernel,
            dilate_iterations=det.dilate_iterations,
            morph_open_iterations=det.morph_open_iterations,
        )

    cells, ys, xs = build_cell_grid(accepted, cluster_gap=det.cluster_gap)

    if debug_image_path is not None:
        debug_img = draw_debug(img, accepted, rejected, cells)
        debug_image_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(debug_image_path), debug_img)
        print(f"  Debug image -> {debug_image_path}")

    if not cells:
        print("  No table cells found on this page - skipping text extraction.")
        return cells, ys, xs

    cells = extract_cells_text(fitz_page, img, cells, dpi=det.dpi, cfg=ext)
    return cells, ys, xs


def process_pdf(
    pdf_path: str | Path,
    *,
    detection: Optional[DetectionConfig] = None,
    extraction: Optional[ExtractionConfig] = None,
    output: Optional[OutputConfig] = None,
    out_dir: str | Path = "output",
    write_debug_images: bool = True,
    save_page_pngs: bool = True,
) -> Optional[Path]:
    """
    Run the full pipeline on a PDF and write the resulting xlsx.

    Parameters
    ----------
    pdf_path : str | Path
        Source PDF.
    detection / extraction / output : *Config, optional
        Stage configs. None -> default (current behavior).
    out_dir : str | Path
        Output directory (will be created). Default "output".
    write_debug_images : bool
        If True, save per-page debug PNGs under `<out_dir>/images/`.
    save_page_pngs : bool
        If True, also save the rendered page PNGs alongside debug images.

    Returns
    -------
    Path of the generated .xlsx, or None if no cells were found anywhere.
    """
    det = detection or DetectionConfig()
    ext = extraction or ExtractionConfig()
    out_cfg = output or OutputConfig()

    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir = out_dir / "images"
    if write_debug_images or save_page_pngs:
        images_dir.mkdir(exist_ok=True)

    print(f"ExactPdfGrid  -  {pdf_path.name}")
    print(f"  DPI={det.dpi}  out={out_dir}")

    print("\n[Step 1] Rendering PDF pages...")
    fitz_doc = fitz.open(str(pdf_path))
    images = pdf_to_images(str(pdf_path), dpi=det.dpi)
    if save_page_pngs:
        save_page_images(images, str(images_dir))

    sheet_data: list[tuple[str, list, list[int], list[int]]] = []

    for page_index, img in enumerate(images):
        fitz_page = fitz_doc[page_index]
        debug_path = (
            images_dir / f"page_{page_index + 1:03d}_debug.png"
            if write_debug_images else None
        )
        cells, ys, xs = _process_page(img, fitz_page, page_index, det, ext, debug_path)
        if not cells:
            continue
        print(f"\n[Step 5] Resolving grid for page {page_index + 1}...")
        sorted_cells = resolve_grid(cells)
        sheet_data.append((f"Page{page_index + 1}", sorted_cells, ys, xs))

    fitz_doc.close()

    if not sheet_data:
        print("\nNo table cells detected in any page.")
        return None

    print("\n[Step 6] Writing workbook with multiple sheets...")
    xlsx_path = out_dir / f"{pdf_path.stem}.xlsx"
    write_xlsx_workbook(
        sheet_data,
        out_path=str(xlsx_path),
        dpi=det.dpi,
        apply_borders=out_cfg.apply_borders,
        apply_size_hints=out_cfg.apply_size_hints,
        min_col_width=out_cfg.min_col_width,
        min_row_height=out_cfg.min_row_height,
        px_per_char_calibration=out_cfg.px_per_char_calibration,
    )
    print("\nDone.")
    return xlsx_path
