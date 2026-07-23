"""slop-no-more: deterministic, explainable, zero-model prose linting."""

from .scanner import scan_file, scan_text, MOVES, LEXICAL, L3_RULES

__version__ = "0.1.0"
__all__ = ["scan_file", "scan_text", "MOVES", "LEXICAL", "L3_RULES", "__version__"]
