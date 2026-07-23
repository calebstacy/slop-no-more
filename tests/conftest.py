"""Let the suite run from a bare clone (no pip install) by exposing src/."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
