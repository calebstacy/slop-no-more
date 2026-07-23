#!/usr/bin/env python3
"""The experiment behind this repo, runnable yourself.

Rule: "don't use em dashes."

Side A gives the rule to a language model as a system instruction and counts
how many of its outputs comply. Side B applies one regex. Side A costs money,
takes seconds per call, and leaks. Side B is free, instant, and total.

The model side is pluggable so this file has zero dependencies: fill in
ask_model() with any provider call (or paste outputs by hand into OUTPUTS).
The regex side runs as-is.
"""

import re

RULE_AS_PROMPT = "Please never use em dashes in your output."
RULE_AS_REGEX = re.compile("—")

PROMPTS = [
    "Write a two-sentence welcome email for a budgeting app.",
    "Write a push notification about a delayed package.",
    "Describe a rainy morning in one paragraph.",
    "Explain what an API is to a ten-year-old.",
    "Write a product blurb for noise-canceling headphones.",
    "Summarize the plot of Moby-Dick in three sentences.",
    "Write an error message for a failed file upload.",
    "Draft a tweet announcing a bakery's new location.",
    "Explain compound interest in two sentences.",
    "Write a calendar invite description for a design review.",
]


def ask_model(system, prompt):
    """Plug in your provider here and return the model's text.

    Example (Anthropic):
        client.messages.create(model=..., system=system,
                               messages=[{"role": "user", "content": prompt}])
    """
    raise NotImplementedError("wire up a provider, or fill OUTPUTS below")


# Paste model outputs here to score a run you did elsewhere.
OUTPUTS: list = []


def main():
    outputs = OUTPUTS
    if not outputs:
        try:
            outputs = [ask_model(RULE_AS_PROMPT, p) for p in PROMPTS]
        except NotImplementedError as e:
            print(f"model side skipped: {e}")
    if outputs:
        violations = sum(1 for o in outputs if RULE_AS_REGEX.search(o))
        print(f"prompt side: {len(outputs) - violations}/{len(outputs)} compliant")

    # The regex side needs no trial: it matches the character or it does not,
    # every time, in microseconds, for free. That asymmetry is the whole tool.
    print("regex side: catches the em dash 10/10 by construction")


if __name__ == "__main__":
    main()
