"""
Configuration dataclasses.

Each config groups the hyperparameters for one pipeline stage.
Every default reproduces today's behavior exactly; users may override any
field to retune the detection, extraction, or output stages.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Union

from .utils import TextCleaner, normalize_whitespace

if TYPE_CHECKING:
    from .engines.base import TextExtractor


@dataclass(frozen=True)
class DetectionConfig:
    """All knobs governing line detection and cell-grid construction."""

    dpi: int = 200
    min_line_length: int = 8
    ink_threshold: int = 240
    max_gap: int = 6
    aspect_ratio: float = 40.0
    cluster_gap: int = 8
    dilate_kernel: tuple[int, int] = (3, 3)
    dilate_iterations: int = 1
    morph_open_iterations: int = 1
    border_thickness: int = 6
    border_density: float = 0.20

    # -- Lineless mode -------------------------------------------------------
    # Table detection strategy: "lines" (black ruling lines, the default) or
    # "lineless" (derive grid lines from blank whitespace corridors).
    mode: str = "lines"
    # Blank corridor width knobs (px). min_* filters inter-character spacing;
    # max_* (0 = no limit) filters over-wide empty margins / blank regions -
    # the lineless counterpart to the black-line `aspect_ratio` knob.
    lineless_min_gap_v: int = 6
    lineless_max_gap_v: int = 0
    lineless_min_gap_h: int = 4
    lineless_max_gap_h: int = 0
    lineless_ink_tolerance: int = 0


@dataclass
class ExtractionConfig:
    """
    Settings for text extraction.

    `engine` may be either a string name (resolved by engines.get_extractor)
    or a pre-built TextExtractor instance.
    """

    engine: Union[str, "TextExtractor"] = "pymupdf"
    padding_px: int = 3
    clean_pipeline: list[TextCleaner] = field(
        default_factory=lambda: [normalize_whitespace]
    )


@dataclass(frozen=True)
class OutputConfig:
    """All knobs governing the .xlsx writing stage."""

    apply_borders: bool = True
    apply_size_hints: bool = True
    min_col_width: float = 4.0
    min_row_height: float = 12.0
    px_per_char_calibration: float = 96 / 8.43
