"""
Text-extractor engine registry.

Use `get_extractor(name_or_instance)` to resolve a string name (e.g. "pymupdf")
into a TextExtractor instance. Passing an instance returns it unchanged so
users can plug in custom subclasses.

Adding a new engine
-------------------
1. Subclass TextExtractor in a new module under exactpdfgrid.engines.
2. Register it below in `_REGISTRY` keyed by its string name.
"""

from __future__ import annotations
from typing import Union

from .base import TextExtractor
from .pymupdf import PyMuPDFExtractor


def _make_rapidocr() -> TextExtractor:
    # Lazy import: only triggered when the user actually selects "rapidocr".
    from .rapidocr import RapidOCRExtractor
    return RapidOCRExtractor()


_BUILTIN_FACTORIES = {
    "pymupdf": PyMuPDFExtractor,
    "rapidocr": _make_rapidocr,
}


def get_extractor(name_or_instance: Union[str, TextExtractor]) -> TextExtractor:
    """Resolve a string engine name into an instance; pass instances through."""
    if isinstance(name_or_instance, TextExtractor):
        return name_or_instance
    if not isinstance(name_or_instance, str):
        raise TypeError(
            f"engine must be a str or TextExtractor instance, got {type(name_or_instance)!r}"
        )
    key = name_or_instance.lower()
    if key not in _BUILTIN_FACTORIES:
        known = ", ".join(sorted(_BUILTIN_FACTORIES))
        raise ValueError(f"Unknown engine {name_or_instance!r}. Known engines: {known}")
    factory = _BUILTIN_FACTORIES[key]
    return factory()


__all__ = ["TextExtractor", "PyMuPDFExtractor", "get_extractor"]
