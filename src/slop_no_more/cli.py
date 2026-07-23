"""Console entry point: `slop scan <paths> [flags]`."""

import sys

from . import __version__
from .scanner import run


USAGE = """slop-no-more {v}

Usage:
  slop scan <path> [<path>...]        full report + verdict
  slop scan <path> --severity high    only high-severity findings
  slop scan <path> --json             machine-readable output
  slop scan <path> --fingerprint      fingerprint vector only (JSON)
  slop --version

Exit code = number of high-severity findings (capped at 100), so CI can gate.
""".format(v=__version__)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    if argv[0] in ("--version", "-V", "version"):
        print(f"slop-no-more {__version__}")
        return 0
    if argv[0] == "scan":
        argv = argv[1:]
    return run(argv)


if __name__ == "__main__":
    sys.exit(main())
