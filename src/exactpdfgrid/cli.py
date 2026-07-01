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
                   help="Text extractor engine: pymupdf (default), "
                        "rapidocr (auto: OpenVINO with ONNX fallback), "
                        "rapidocr-vino (force OpenVINO), "
                        "or rapidocr-onnx (force ONNX Runtime)")
    p.add_argument("--mode", choices=["lines", "lineless"], default="lines",
                   help="Table detection strategy: lines (black ruling lines, "
                        "default) or lineless (derive grid lines from blank "
                        "whitespace corridors of aligned text)")
    p.add_argument("--lineless-min-gap-v", type=int, default=6,
                   help="Lineless: min blank column corridor width in px "
                        "(default: 6)")
    p.add_argument("--lineless-max-gap-v", type=int, default=0,
                   help="Lineless: max blank column corridor width in px; "
                        "0 = no limit (default: 0)")
    p.add_argument("--lineless-min-gap-h", type=int, default=4,
                   help="Lineless: min blank row corridor height in px "
                        "(default: 4)")
    p.add_argument("--lineless-max-gap-h", type=int, default=0,
                   help="Lineless: max blank row corridor height in px; "
                        "0 = no limit (default: 0)")
    p.add_argument("--lineless-ink-tolerance", type=int, default=0,
                   help="Lineless: ink pixels tolerated inside a blank "
                        "corridor (default: 0)")
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
        mode=args.mode,
        lineless_min_gap_v=args.lineless_min_gap_v,
        lineless_max_gap_v=args.lineless_max_gap_v,
        lineless_min_gap_h=args.lineless_min_gap_h,
        lineless_max_gap_h=args.lineless_max_gap_h,
        lineless_ink_tolerance=args.lineless_ink_tolerance,
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
