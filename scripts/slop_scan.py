#!/usr/bin/env python3
"""Skill-compatible shim: run the scanner without pip-installing the package.

Used by SKILL.md so a cloned copy of this repo works as a Claude skill as-is:
  python3 scripts/slop_scan.py <path> [--severity high] [--json] [--fingerprint]
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from slop_no_more.scanner import run  # noqa: E402

if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
