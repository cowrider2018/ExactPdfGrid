"""
Table detection pipeline
========================
Step 1  Find candidate line segments via morphological open + contour bounding rect.
Step 2  Connectivity check - reject any segment that has a gap larger than max_gap
        pixels along its own centre line in the binary mask.
Step 3  Form rectangular cells - for every combination of H/V segments find fully
        enclosed quadrilaterals (top/bottom H + left/right V).
Step 4  Return cell bounding boxes (pixel coords) for xlsx output.

Debug colours (BGR):
    Blue   (255,   0,   0) - accepted connected segments (Step 1+2)
    Green  (  0, 200,   0) - rejected segments (Step 2, failed connectivity)
    Red    (  0,   0, 255) - detected cell rectangles (Step 3)
"""

from __future__ import annotations
from dataclasses import dataclass
import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LineSegment:
    """A detected line segment in image-pixel coordinates."""
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def is_horizontal(self) -> bool:
        return abs(self.y2 - self.y1) <= abs(self.x2 - self.x1)

    @property
    def length(self) -> float:
        return ((self.x2 - self.x1) ** 2 + (self.y2 - self.y1) ** 2) ** 0.5


@dataclass
class CellRegion:
    """One detected table cell."""
    row: int
    col: int
    x1: int
    y1: int
    x2: int
    y2: int
    row_span: int = 1
    col_span: int = 1
    text: str = ""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _binarize(img: np.ndarray, threshold: int = 200) -> np.ndarray:
    """Dark ink -> 255, white background -> 0."""
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    return binary


def _morpho_mask(binary: np.ndarray, direction: str, min_length: int) -> np.ndarray:
    """Keep only pixels that belong to lines longer than min_length."""
    binary = cv2.dilate(
        binary,
        cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)),
        iterations=1,
    )
    ksize = (min_length, 1) if direction == "h" else (1, min_length)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, ksize)
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)


def _contours_to_raw_segments(
    mask: np.ndarray,
    horiz: bool,
    min_length: int,
    aspect_ratio: float = 40.0,
) -> list[LineSegment]:
    """
    Convert each connected contour to a centre-line segment.
    Blobs that fail the aspect-ratio test (cw/ch or ch/cw < aspect_ratio)
    are discarded here, before the segment is collapsed to a line.
    """
    segs: list[LineSegment] = []
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in cnts:
        x, y, cw, ch = cv2.boundingRect(cnt)
        if horiz:
            if cw < min_length:
                continue
            if ch > 0 and cw / ch < aspect_ratio:
                continue
            cy = y + ch // 2
            segs.append(LineSegment(x, cy, x + cw, cy))
        else:
            if ch < min_length:
                continue
            if cw > 0 and ch / cw < aspect_ratio:
                continue
            cx = x + cw // 2
            segs.append(LineSegment(cx, y, cx, y + ch))
    return segs


def _is_connected(seg: LineSegment, mask: np.ndarray, max_gap: int) -> bool:
    """
    Step 2 - connectivity check.
    Returns True only if no run of empty pixels along the centre line exceeds max_gap.
    """
    if seg.is_horizontal:
        row = int(np.clip(seg.y1, 0, mask.shape[0] - 1))
        strip = mask[row, max(0, seg.x1):min(mask.shape[1], seg.x2)]
    else:
        col = int(np.clip(seg.x1, 0, mask.shape[1] - 1))
        strip = mask[max(0, seg.y1):min(mask.shape[0], seg.y2), col]

    if len(strip) == 0:
        return False
    gap = 0
    for pixel in strip:
        if pixel == 0:
            gap += 1
            if gap > max_gap:
                return False
        else:
            gap = 0
    return True


def _cluster(values: list[int], gap: int = 8) -> list[int]:
    """Merge nearby integer coordinates into single representative values."""
    if not values:
        return []
    arr = sorted(set(values))
    clusters: list[list[int]] = [[arr[0]]]
    for v in arr[1:]:
        if v - clusters[-1][-1] <= gap:
            clusters[-1].append(v)
        else:
            clusters.append([v])
    return [int(np.median(c)) for c in clusters]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_line_segments(
    img: np.ndarray,
    min_line_length: int = 40,
    ink_threshold: int = 200,
    max_gap: int = 6,
) -> tuple[list[LineSegment], list[LineSegment]]:
    """
    Step 1 + Step 2.

    1. Extract candidate segments via morphological open + contour bounding rect.
    2. Reject segments that have large gaps along their centre line.

    Returns
    -------
    (accepted, rejected)
    """
    binary = _binarize(img, ink_threshold)

    h_mask = _morpho_mask(binary, "h", min_line_length)
    v_mask = _morpho_mask(binary, "v", min_line_length)

    raw_h = _contours_to_raw_segments(h_mask, horiz=True,  min_length=min_line_length)
    raw_v = _contours_to_raw_segments(v_mask, horiz=False, min_length=min_line_length)

    accepted: list[LineSegment] = []
    rejected: list[LineSegment] = []

    for seg in raw_h:
        (accepted if _is_connected(seg, h_mask, max_gap) else rejected).append(seg)

    for seg in raw_v:
        (accepted if _is_connected(seg, v_mask, max_gap) else rejected).append(seg)

    h_acc = sorted([s for s in accepted if     s.is_horizontal], key=lambda s: (s.y1, s.x1))
    v_acc = sorted([s for s in accepted if not s.is_horizontal], key=lambda s: (s.x1, s.y1))
    accepted = h_acc + v_acc

    print(
        f"  [Step1+2] {len(h_acc)} H + {len(v_acc)} V accepted; "
        f"{len(rejected)} rejected"
    )
    return accepted, rejected


def _snap(value: int, candidates: list[int], gap: int) -> int | None:
    """Return the candidate closest to value if within gap, else None."""
    best = min(candidates, key=lambda c: abs(c - value))
    return best if abs(best - value) <= gap else None


def build_cell_grid(
    accepted: list[LineSegment],
    cluster_gap: int = 8,
) -> tuple[list[CellRegion], list[int], list[int]]:
    """
    Step 3 – purely mathematical cell detection.

    Rules (zero tolerance after snapping):
    • A H segment belongs to row-boundary yi  if its snapped y  == ys[yi].
      It covers column boundary range [xi_start, xi_end] only if its snapped
      x1 == xs[xi_start]  AND  snapped x2 == xs[xi_end]  (exact endpoints).
    • A V segment belongs to col-boundary xi  if its snapped x  == xs[xi].
      It covers row boundary range [yi_start, yi_end] only if its snapped
      y1 == ys[yi_start]  AND  snapped y2 == ys[yi_end]  (exact endpoints).
    • A cell (ri→row_end, ci→col_end) is valid iff top/bottom H edges and
      left/right V edges are fully covered with no gaps.

    Returns
    -------
    (cells, ys, xs)
    """
    h_segs = [s for s in accepted if     s.is_horizontal]
    v_segs = [s for s in accepted if not s.is_horizontal]

    ys = _cluster([s.y1 for s in h_segs], cluster_gap)
    xs = _cluster([s.x1 for s in v_segs], cluster_gap)

    if len(ys) < 2 or len(xs) < 2:
        print("  [Step3] WARNING: not enough grid lines.")
        return [], ys, xs

    n_rows = len(ys) - 1
    n_cols = len(xs) - 1
    snap = cluster_gap  # snap tolerance (pixels) – only used to assign to grid

    # h_cover[yi][ci] = True  ⟺  a H segment at boundary ys[yi] spans across
    #   the full column slot xs[ci]..xs[ci+1]  (seg.x1 <= xs[ci] and seg.x2 >= xs[ci+1])
    h_cover: list[list[bool]] = [[False] * n_cols for _ in range(len(ys))]

    for seg in h_segs:
        yi_snap = _snap(seg.y1, ys, snap)
        if yi_snap is None:
            continue
        yi = ys.index(yi_snap)
        # Mark every column slot the segment fully spans
        for ci in range(n_cols):
            if seg.x1 <= xs[ci] and seg.x2 >= xs[ci + 1]:
                h_cover[yi][ci] = True

    # v_cover[xi][ri] = True  ⟺  a V segment at boundary xs[xi] spans across
    #   the full row slot ys[ri]..ys[ri+1]  (seg.y1 <= ys[ri] and seg.y2 >= ys[ri+1])
    v_cover: list[list[bool]] = [[False] * n_rows for _ in range(len(xs))]

    for seg in v_segs:
        xi_snap = _snap(seg.x1, xs, snap)
        if xi_snap is None:
            continue
        xi = xs.index(xi_snap)
        for ri in range(n_rows):
            if seg.y1 <= ys[ri] and seg.y2 >= ys[ri + 1]:
                v_cover[xi][ri] = True

    # Find cells: for each (ri, ci) find smallest enclosing rectangle whose
    # four borders are fully covered.
    covered = [[False] * n_cols for _ in range(n_rows)]
    cells: list[CellRegion] = []

    for ri in range(n_rows):
        for ci in range(n_cols):
            if covered[ri][ci]:
                continue
            found = False
            for row_end in range(ri + 1, n_rows + 1):
                # bottom border: h_cover[row_end][ci] must be True before scanning further
                if not h_cover[row_end][ci]:
                    continue
                for col_end in range(ci + 1, n_cols + 1):
                    # right border: v_cover[col_end][ri] must be True
                    if not v_cover[col_end][ri]:
                        continue

                    # All four borders must be continuously present (exact, no tol)
                    top_ok    = all(h_cover[ri][c]       for c in range(ci, col_end))
                    bottom_ok = all(h_cover[row_end][c]  for c in range(ci, col_end))
                    left_ok   = all(v_cover[ci][r]       for r in range(ri, row_end))
                    right_ok  = all(v_cover[col_end][r]  for r in range(ri, row_end))

                    if not (top_ok and bottom_ok and left_ok and right_ok):
                        continue

                    for r in range(ri, row_end):
                        for c in range(ci, col_end):
                            covered[r][c] = True
                    cells.append(CellRegion(
                        row=ri, col=ci,
                        x1=xs[ci],      y1=ys[ri],
                        x2=xs[col_end], y2=ys[row_end],
                        row_span=row_end - ri,
                        col_span=col_end - ci,
                    ))
                    found = True
                    break
                if found:
                    break
            if not found:
                covered[ri][ci] = True

    merged = sum(1 for c in cells if c.row_span > 1 or c.col_span > 1)
    print(f"  [Step3] grid {n_rows}x{n_cols}, {len(cells)} cells ({merged} merged)")
    return cells, ys, xs


def draw_debug(
    img: np.ndarray,
    accepted: list[LineSegment],
    rejected: list[LineSegment],
    cells: list[CellRegion],
) -> np.ndarray:
    """
    Draw debug annotation:
      Green – rejected (disconnected) segments
      Blue  – accepted (connected) segments
      Red   – detected cell rectangles
    """
    out = img.copy()

    for s in rejected:
        cv2.line(out, (s.x1, s.y1), (s.x2, s.y2), (0, 200, 0), 1)

    for s in accepted:
        cv2.line(out, (s.x1, s.y1), (s.x2, s.y2), (255, 0, 0), 2)

    for cell in cells:
        cv2.rectangle(
            out,
            (cell.x1 + 2, cell.y1 + 2),
            (cell.x2 - 2, cell.y2 - 2),
            (0, 0, 255), 1,
        )
        label = f"r{cell.row}c{cell.col}"
        if cell.row_span > 1 or cell.col_span > 1:
            label += f"[{cell.row_span}x{cell.col_span}]"
        cv2.putText(
            out, label,
            (cell.x1 + 4, cell.y1 + 14),
            cv2.FONT_HERSHEY_SIMPLEX, 0.3,
            (0, 0, 200), 1,
        )

    return out
