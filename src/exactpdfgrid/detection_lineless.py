"""
Lineless table detection
========================
Alternative *line-extraction* stage for tables that have **no ruling lines** -
only text that is precisely aligned into columns and rows.

Where the black-line pipeline (``detection.detect_line_segments``) finds ink
that *is* a line, this module finds the **blank corridors** that run all the way
through the content and takes their centre line as a grid line.

Step 1  Binarize (reuse ``detection._binarize``) and find the content bounding box.
Step 2  Column projection - runs of fully-blank columns that pass the gap width
        test become vertical separators (centre line of the corridor).
Step 3  Row projection - same idea, horizontal separators.
Step 4  Emit full-span ``LineSegment`` objects (outer box edges + interior
        separators) so the shared ``build_cell_grid`` can rebuild the grid
        exactly as it does for the black-line pipeline.

The return type is identical to ``detect_line_segments`` -
``(accepted, rejected)`` - making this a drop-in replacement for the
line-extraction step. Everything downstream (``build_cell_grid``,
text extraction, xlsx output) is shared, unchanged.

Gap width knobs (the lineless counterpart to the black-line ``aspect_ratio``):
    min_gap_*  corridor thinner than this is treated as inter-character spacing
               and ignored.
    max_gap_*  corridor wider than this is treated as an empty margin / blank
               region and ignored (0 = no upper limit). Prevents a very wide
               blank area from being collapsed into a spurious centre-line.
"""

from __future__ import annotations

import numpy as np

from .detection import LineSegment, _binarize


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _blank_corridors(
    ink_profile: np.ndarray,
    lo: int,
    hi: int,
    ink_tolerance: int,
    min_gap: int,
    max_gap: int,
) -> list[int]:
    """
    Scan ``ink_profile[lo:hi+1]`` for runs of blank cells and return the centre
    coordinate of every run that qualifies as a separator.

    A cell is *blank* when its ink count is <= ``ink_tolerance``.
    A run qualifies when ``min_gap <= width`` and (``max_gap == 0`` or
    ``width <= max_gap``). Only interior runs (not touching ``lo``/``hi``) are
    returned; the outer box edges are added separately by the caller.
    """
    centres: list[int] = []
    run_start: int | None = None

    # Walk one past `hi` with a sentinel non-blank cell so a trailing run closes.
    for i in range(lo, hi + 2):
        blank = i <= hi and ink_profile[i] <= ink_tolerance
        if blank:
            if run_start is None:
                run_start = i
            continue
        # Not blank -> a run (if any) just ended at i-1.
        if run_start is not None:
            run_end = i - 1
            # Drop runs that touch the content edge (leading/trailing margin).
            touches_edge = run_start <= lo or run_end >= hi
            width = run_end - run_start + 1
            if (
                not touches_edge
                and width >= min_gap
                and (max_gap == 0 or width <= max_gap)
            ):
                centres.append((run_start + run_end) // 2)
            run_start = None
    return centres


# ---------------------------------------------------------------------------
# Public API - drop-in replacement for detect_line_segments
# ---------------------------------------------------------------------------

def detect_gridlines_whitespace(
    img: np.ndarray,
    *,
    ink_threshold: int = 240,
    min_gap_v: int = 6,
    max_gap_v: int = 0,
    min_gap_h: int = 4,
    max_gap_h: int = 0,
    ink_tolerance: int = 0,
) -> tuple[list[LineSegment], list[LineSegment]]:
    """
    Derive grid lines from blank whitespace corridors.

    Returns
    -------
    (accepted, rejected)
        Same shape as ``detect_line_segments``. ``rejected`` is always empty -
        there are no discarded ink segments in this mode.
    """
    binary = _binarize(img, ink_threshold)

    # Step 1 - content bounding box (rows/cols that contain any ink).
    col_ink = binary.sum(axis=0)           # ink per column
    row_ink = binary.sum(axis=1)           # ink per row
    ink_cols = np.flatnonzero(col_ink)
    ink_rows = np.flatnonzero(row_ink)
    if ink_cols.size == 0 or ink_rows.size == 0:
        print("  [Lineless] WARNING: page is blank - no content found.")
        return [], []

    x_left, x_right = int(ink_cols[0]), int(ink_cols[-1])
    y_top, y_bottom = int(ink_rows[0]), int(ink_rows[-1])

    # Step 2 - vertical separators from column corridors, measured only over
    # the content's vertical extent so a corridor must run through the table.
    col_ink_box = binary[y_top:y_bottom + 1, :].sum(axis=0)
    v_centres = _blank_corridors(
        col_ink_box, x_left, x_right, ink_tolerance, min_gap_v, max_gap_v
    )

    # Step 3 - horizontal separators from row corridors.
    row_ink_box = binary[:, x_left:x_right + 1].sum(axis=1)
    h_centres = _blank_corridors(
        row_ink_box, y_top, y_bottom, ink_tolerance, min_gap_h, max_gap_h
    )

    # Step 4 - assemble grid-line coordinates (outer edges + interior centres).
    xs = sorted({x_left, *v_centres, x_right})
    ys = sorted({y_top, *h_centres, y_bottom})

    # Emit full-span synthetic segments; build_cell_grid sees full coverage.
    v_segs = [LineSegment(x, y_top, x, y_bottom) for x in xs]
    h_segs = [LineSegment(x_left, y, x_right, y) for y in ys]
    accepted = h_segs + v_segs

    print(
        f"  [Lineless] {len(h_segs)} H + {len(v_segs)} V grid lines "
        f"({len(h_centres)} row + {len(v_centres)} col corridors)"
    )
    return accepted, []
