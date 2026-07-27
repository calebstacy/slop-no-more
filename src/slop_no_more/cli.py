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
  slop scan <path> --fail-on medium   gate on medium and high findings
  slop scan <path> --fail-on never    output only; never fail the gate
  slop scan <path> --disable RULE     disable a registered rule
  slop --version

Exit codes: 0 pass, 1 gate failure, 2 usage error, 3 input/read error.
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
        return run(argv[1:], prog="slop scan")
    print(f"slop: unknown command: {argv[0]}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
