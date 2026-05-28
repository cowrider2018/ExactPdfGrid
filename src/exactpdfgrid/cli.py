"""
Command-line entry point.

Installed as the `exactpdfgrid` console script (see pyproject.toml).
"""

from __future__ import annotations
import argparse
import sys

from .config import DetectionConfig, ExtractionConfig, OutputConfig
from .core import process_pdf


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="exactpdfgrid",
        description="Extract tables from a PDF and export them to .xlsx",
    )
    p.add_argument("pdf", help="Path to the input PDF file")
    p.add_argument("--dpi", type=int, default=200, help="Render DPI (default: 200)")
    p.add_argument("--out", default="output", help="Output directory (default: output)")
    p.add_argument("--min-line", type=int, default=8,
                   help="Minimum line length in pixels (default: 8)")
    p.add_argument("--ink-threshold", type=int, default=240,
                   help="Pixel brightness below which ink is assumed (default: 240)")
    p.add_argument("--cluster-gap", type=int, default=8,
                   help="Max gap to cluster nearby grid-line positions (default: 8)")
    p.add_argument("--aspect-ratio", type=float, default=40.0,
                   help="Aspect ratio threshold for line detection blobs (default: 40.0)")
    p.add_argument("--border-thickness", type=int, default=6,
                   help="Half-thickness for border presence probe (default: 6)")
    p.add_argument("--border-density", type=float, default=0.20,
                   help="Ink density threshold to confirm interior border (default: 0.20)")
    p.add_argument("--engine", default="pymupdf",
                   help="Text extractor engine: pymupdf (default) or rapidocr")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    det = DetectionConfig(
        dpi=args.dpi,
        min_line_length=args.min_line,
        ink_threshold=args.ink_threshold,
        cluster_gap=args.cluster_gap,
        aspect_ratio=args.aspect_ratio,
        border_thickness=args.border_thickness,
        border_density=args.border_density,
    )
    ext = ExtractionConfig(engine=args.engine)
    out_cfg = OutputConfig()

    try:
        process_pdf(
            args.pdf,
            detection=det,
            extraction=ext,
            output=out_cfg,
            out_dir=args.out,
        )
    except FileNotFoundError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
