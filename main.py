"""
ExactPdfGrid – PDF table extraction pipeline
============================================

Usage
-----
    python main.py <input.pdf> [options]

Options
-------
  --dpi INT           Render resolution (default: 200)
  --out DIR           Output directory (default: output)
  --min-line INT      Minimum line length in pixels (default: 15)
  --ink-threshold INT Pixel value below which a pixel is considered ink (default: 200)
  --cluster-gap INT   Max pixel gap to merge nearby grid lines (default: 8)
  --border-thickness  Half-thickness used when probing for interior borders (default: 6)
  --border-density    Ink density fraction to confirm a border exists (default: 0.20)

Pipeline
--------
  Step 1  pdf_to_image   – PyMuPDF renders each page → BGR image
  Step 2  table_detection – OpenCV morphology finds H/V line segments
  Step 3  table_detection – Lines → cell bounding-box grid (handles merges)
  Step 4  ocr_processing  – RapidOCR reads text from each cell crop
  Step 5  xlsx_output     – Resolve logical grid positions
  Step 6  xlsx_output     – Write openpyxl workbook with merged cells
"""

from __future__ import annotations
import argparse
import sys
from pathlib import Path

import cv2

from pdf_to_image import pdf_to_images, save_page_images
from table_detection import detect_line_segments, build_cell_grid, draw_debug
import fitz
from ocr_processing import extract_cells_text
from xlsx_output import resolve_grid, write_xlsx_workbook


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="main.py",
        description="Extract tables from a PDF and export them to .xlsx",
    )
    p.add_argument("pdf", help="Path to the input PDF file")
    p.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    p.add_argument("--out", default="output", help="Output directory (default: output)")
    p.add_argument("--min-line", type=int, default=8,
                   help="Minimum line length in pixels (default: 8)")
    p.add_argument("--ink-threshold", type=int, default=240,
                   help="Pixel brightness below which ink is assumed (default: 240, 80% brightness)")
    p.add_argument("--cluster-gap", type=int, default=8,
                   help="Max gap to cluster nearby grid-line positions (default: 8)")
    p.add_argument("--border-thickness", type=int, default=6,
                   help="Half-thickness for border presence probe (default: 6)")
    p.add_argument("--border-density", type=float, default=0.20,
                   help="Ink density threshold to confirm interior border (default: 0.20)")
    return p.parse_args(argv)


# ---------------------------------------------------------------------------
# Per-page processing
# ---------------------------------------------------------------------------

def process_page(
    img,
    fitz_page: fitz.Page,
    page_index: int,
    args: argparse.Namespace,
) -> tuple[list, list[int], list[int]]:
    """Run Steps 2-4 on a single page image."""

    print(f"\n── Page {page_index + 1} ──────────────────────────────────────")

    # Step 1+2: detect line segments and run connectivity check
    accepted, rejected = detect_line_segments(
        img,
        min_line_length=args.min_line,
        ink_threshold=args.ink_threshold,
    )

    # Step 3: build cell grid (handles merged cells)
    cells, ys, xs = build_cell_grid(
        accepted,
        cluster_gap=args.cluster_gap,
    )

    # Always write a debug image
    debug_img = draw_debug(img, accepted, rejected, cells)
    debug_path = f"{args.out}/images/page_{page_index + 1:03d}_debug.png"
    cv2.imwrite(debug_path, debug_img)
    print(f"  Debug image → {debug_path}")

    if not cells:
        print("  No table cells found on this page – skipping text extraction.")
        return cells, ys, xs

    # Step 4: extract text via PyMuPDF (no OCR, uses PDF vector data)
    cells = extract_cells_text(
        fitz_page, cells,
        dpi=args.dpi,
    )

    return cells, ys, xs


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"ERROR: file not found → {pdf_path}", file=sys.stderr)
        sys.exit(1)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)
    (out_dir / "cells").mkdir(exist_ok=True)

    print(f"ExactPdfGrid  –  {pdf_path.name}")
    print(f"  DPI={args.dpi}  out={out_dir}")

    # ── Step 1: render PDF pages ────────────────────────────────────────────
    print("\n[Step 1] Rendering PDF pages…")
    fitz_doc = fitz.open(str(pdf_path))
    images = pdf_to_images(str(pdf_path), dpi=args.dpi)
    save_page_images(images, str(out_dir / "images"))

    sheet_data: list[tuple[str, list, list[int], list[int]]] = []

    # ── Steps 2-4: per-page detection + text extraction ────────────────────
    for page_index, img in enumerate(images):
        fitz_page = fitz_doc[page_index]
        cells, ys, xs = process_page(img, fitz_page, page_index, args)

        if not cells:
            continue

        # ── Step 5: resolve logical grid ───────────────────────────────────
        print(f"\n[Step 5] Resolving grid for page {page_index + 1}…")
        sorted_cells = resolve_grid(cells)
        sheet_data.append((f"Page{page_index + 1}", sorted_cells, ys, xs))

    if sheet_data:
        print("\n[Step 6] Writing workbook with multiple sheets…")
        stem = pdf_path.stem
        xlsx_path = str(out_dir / f"{stem}.xlsx")
        write_xlsx_workbook(
            sheet_data,
            out_path=xlsx_path,
            dpi=args.dpi,
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
