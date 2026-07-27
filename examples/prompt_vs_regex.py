#!/usr/bin/env python3
"""A reproducible boundary between instruction and verification.

Rule under review: do not use an em dash.

This script does not call a model or claim a model pass rate. Give it a JSON
file containing recorded model outputs to measure one run:

    python examples/prompt_vs_regex.py outputs.json

Without that file, it reports that the prompt side was not measured and runs
ten declared unit fixtures for the regex. Passing fixtures show that the
observable check behaves as specified. They do not show that the check
understands prose, improves writing or enforces its own repair.
"""

import argparse
import json
import re
from pathlib import Path


RULE_AS_PROMPT = "Do not use em dashes in your output."
RULE_AS_REGEX = re.compile("\N{EM DASH}")

PROMPTS = [
    "Write a two-sentence welcome email for a budgeting app.",
    "Write a push notification about a delayed package.",
    "Describe a rainy morning in one paragraph.",
    "Explain what an API is to a ten-year-old.",
    "Write a product blurb for noise-canceling headphones.",
    "Summarize the plot of Moby-Dick in three sentences.",
    "Write an error message for a failed file upload.",
    "Draft a post announcing a bakery's new location.",
    "Explain compound interest in two sentences.",
    "Write a calendar invite description for a design review.",
]

# Each tuple is (text, should_match). These test the declared character rule,
# including neighboring punctuation the rule must not confuse with an em dash.
REGEX_FIXTURES = [
    ("Alpha—beta", True),
    ("An em dash — with spaces", True),
    ("Two—em—dashes", True),
    ("—leading", True),
    ("trailing—", True),
    ("Alpha-beta", False),
    ("Alpha – beta", False),
    ("Alpha -- beta", False),
    ("No dash here.", False),
    ("The code point is U+2014.", False),
]


def load_outputs(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("outputs JSON must be a list of strings")
    return data


def score_outputs(outputs):
    violations = sum(bool(RULE_AS_REGEX.search(output)) for output in outputs)
    compliant = len(outputs) - violations
    print(
        f"recorded prompt run: {compliant}/{len(outputs)} outputs complied "
        f"with the observable em-dash rule"
    )


def check_regex_fixtures():
    results = [
        bool(RULE_AS_REGEX.search(text)) == expected
        for text, expected in REGEX_FIXTURES
    ]
    passed = sum(results)
    print(f"regex unit fixtures: {passed}/{len(results)} expected classifications")
    return passed == len(results)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "outputs",
        nargs="?",
        help="optional JSON file containing recorded model outputs",
    )
    args = parser.parse_args(argv)

    print(f"prompt instruction: {RULE_AS_PROMPT}")
    if args.outputs:
        score_outputs(load_outputs(args.outputs))
    else:
        print("recorded prompt run: not measured (no outputs file supplied)")

    if not check_regex_fixtures():
        raise SystemExit(1)
    print("scope: detection only; a separate actor must reject or repair a match")


if __name__ == "__main__":
    main()
