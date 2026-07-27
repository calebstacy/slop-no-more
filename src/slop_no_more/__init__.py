"""slop-no-more: deterministic, explainable, zero-model prose linting."""

from .scanner import (
    L3_RULES,
    LEXICAL,
    MOVES,
    SCANNER_VERSION,
    scan_file,
    scan_text,
)

__version__ = SCANNER_VERSION
__all__ = [
    "scan_file",
    "scan_text",
    "MOVES",
    "LEXICAL",
    "L3_RULES",
    "SCANNER_VERSION",
    "__version__",
]
