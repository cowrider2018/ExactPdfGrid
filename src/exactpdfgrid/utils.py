"""
Pluggable text-cleaning utilities.

The OCR/text-extraction core does NOT bake in any specific cleaning rule.
Each cleaner is a `Callable[[str], str]`; users compose them into a list
that the extraction pipeline applies in order via `clean_text_pipeline`.

Built-in cleaners
-----------------
- normalize_whitespace : the default — collapses internal whitespace.
- strip_square_brackets : opt-in — removes any "[...]" substring.
- strip_parentheses     : opt-in — removes any "(...)" substring.
- split_at_first_paren  : opt-in — keeps only the text before the first "(".
- strip_outer_whitespace: opt-in — trims leading/trailing whitespace.
"""

from __future__ import annotations
import re
from typing import Callable, Iterable

TextCleaner = Callable[[str], str]


def normalize_whitespace(s: str) -> str:
    """Collapse all internal whitespace runs to single spaces; trim ends."""
    return " ".join(s.split())


def strip_square_brackets(s: str) -> str:
    """Remove any "[...]" substring (non-greedy, single-line)."""
    return re.sub(r"\[.*?\]", "", s)


def strip_parentheses(s: str) -> str:
    """Remove any "(...)" substring (non-greedy, single-line)."""
    return re.sub(r"\(.*?\)", "", s)


def split_at_first_paren(s: str) -> str:
    """Keep only the substring before the first "(" character."""
    idx = s.find("(")
    return s if idx == -1 else s[:idx]


def strip_outer_whitespace(s: str) -> str:
    """Trim leading and trailing whitespace."""
    return s.strip()


def clean_text_pipeline(text: str, cleaners: Iterable[TextCleaner]) -> str:
    """
    Apply each cleaner to `text` in order, threading the output of one
    into the input of the next.
    """
    for fn in cleaners:
        text = fn(text)
    return text
