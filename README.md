# slop-no-more

Deterministic, explainable, zero-model prose linting with CI exit codes.

Don't ask a model to catch what a regex can catch.

## The experiment this repo is built on

I had a style rule: don't use em dashes. I gave it to a language model as a
polite instruction and ran ten test strings. The model complied on seven.
Then I wrote the same rule as one line of regex and ran the same ten strings.
It caught all ten, in microseconds and for free, and it will catch the next
ten thousand at the same rate. The instruction costs tokens every single call and
still leaks. The regex is dirt cheap and total.

That asymmetry is the whole tool. AI-tell detection is mostly a deterministic
problem wearing a probabilistic costume. The fluent-but-fake patterns in
machine prose are finite and matchable. So this scanner names them and
matches them. No model, no API key, no network, no dependencies. The same
input produces the same findings every time, and each finding tells you
exactly which pattern fired. The exit code makes it a build gate.

Run the experiment yourself: [examples/prompt_vs_regex.py](examples/prompt_vs_regex.py).

## See it on real models

The same 300-word announcement prompt, run against `gpt-5.5` and
`claude-sonnet-5` through their raw APIs, comparing three pipelines: the
bare model, instructions only (the constraint block in the prompt, which is
the pipeline prompt packs sell), and the skill's draft-scan-repair loop.
Bare drafts scored 38.83 and 49.18 weighted density, both HEAVY SLOP.
Instructions alone transformed the substance and barely moved the number
(36.21 and 42.86): both models violated constraints they had just been
handed, inside the same response. The loop finished both at 0.00, CLEAN.
Captured outputs, findings, and the full protocol:
[examples/side-by-side.md](examples/side-by-side.md).

## What makes this one different

When I surveyed the field in July 2026 I found four families of tools:
instruction packs, which put rules in a prompt and cannot enforce them;
rewriters and humanizers, which change your text without showing findings;
ML detectors, which output an authorship verdict nobody can explain; and
word-list linters, which catch banned strings and miss the rhetoric. I could
not find one open-source tool that combines move-level analysis, deterministic
scanning, repair rules, and CI enforcement. This is that tool.

The unit of detection is the **move**: what a clause is doing, not what words
it contains. "Here's why this matters" and "the part worth sitting with" share
no vocabulary and are the same move (cataphoric evaluation: praising a point
before making it). Strings are unbounded; moves are few. AI slop is roughly a
dozen moves wearing ten thousand costumes, so the rules live at the move
level, where paraphrase can't escape. The catalog with definitions, lineage
(Hyland 2005; Swales 1990), and research anchors is in
[references/moves.md](references/moves.md).

Moves matter for a second reason: **they generate claims.** A "not X, but Y"
template invents someone who claimed X. A "most teams get this wrong" template
invents a survey. This slop doesn't just sound machine-made; it quietly
changes what your text asserts. That is why every finding ships with a repair
rule instead of a synonym suggestion.

## Three layers

| Layer | What it catches | Examples |
|---|---|---|
| 1. Strings | Lexical tells | "delve", "In conclusion", "I hope this helps", stock idioms at machine frequency |
| 2. Moves | Rhetorical patterns | manufactured antithesis, phantom populations, cataphoric evaluation, invented adversaries, hedge clouds, 23 families total |
| 3. Distribution | Document statistics | sentence-cadence uniformity, em-dash density, triad density, metadiscourse ratio, style-marker density |

Every scan also emits a fingerprint: per-move rates per 1,000 words plus the
distribution metrics. Scan a corpus and you have a behavioral profile of a
writer or a model; scan over time and you can watch drift.

## Quickstart

```bash
pip install git+https://github.com/REPLACE-OWNER/slop-no-more
slop scan draft.md
```

Or with no install at all (stdlib only):

```bash
python3 scripts/slop_scan.py draft.md
```

Output on [examples/sample-slop.md](examples/sample-slop.md), trimmed:

```text
examples/sample-slop.md
verdict: HEAVY SLOP   density: 452.05 weighted hits / 1k words   high-severity: 9
  [high  ]  L3  (manufactured-antithesis)  "not about wording, it's about"
           fix: Name who actually asserted X (with a source), or delete the denial and state Y as a plain positive claim.
  [high  ]  L3  (phantom-population)  "Most teams"
           fix: Cite the source and number, downgrade to a first-person observation ('the teams I have seen'), or delete the claim.
  [high  ]  L5  (cataphoric-evaluation)  "The key insight"
           fix: Delete the evaluation and lead with the content. If the point matters, the sentence that states it must carry that weight itself.
  [high  ]  L5  (anonymous-authority)  "Research shows"
           fix: Name the source and claim precisely, or remove the authority wrapper and state the claim at the confidence level you can defend.
  [medium]  L5  (benefit-cascade)  "foster engagement while empowering them to streamline"
           fix: Replace the benefit stack with the mechanism: who does what differently, and what changes because of it.
  ...9 more findings
  fingerprint: words=73  sentences=9  cadence_cv=0.571  emdash_per_1k=0.0  move_ratio_pct=22.2
```

Flags: `--severity high` (strongest signals only), `--json` (machine-readable),
`--fingerprint` (the vector only). Verdict bands run CLEAN, MOSTLY CLEAN, SLOP
PRESENT, HEAVY SLOP, from a severity-weighted density per 1,000 words.

## CI enforcement

The exit code is the number of high-severity findings, capped at 100. That
makes the scanner itself the gate:

```yaml
- run: pip install git+https://github.com/REPLACE-OWNER/slop-no-more
- run: slop scan docs/ README.md
```

Full workflow: [examples/github-action.yml](examples/github-action.yml).

## Honest edges

Quoted spans, inline code, fenced blocks and blockquotes are never linted:
quoting a move to discuss it is not performing it. A line containing
`slop-ignore` is skipped, so deliberate rhetorical choices stay possible and
the gate stays trustworthy. And the scanner only catches known costumes of
each move; the functional definitions in the catalog are the rubric a human
applies to novel ones, and every human catch becomes a new pattern. The
deterministic layer grows; it never guesses.

One calibration point from the tool's first live outing: an essay a human
reader had flagged as painful scored 53.9 weighted density, and the draft
that later passed the same reader's ear scored 0.0. The instrument and the
ear agreed on rank order at first try.

## As a Claude Code skill

The repo doubles as a skill: clone it into your skills directory and
[SKILL.md](SKILL.md) wires the scanner into a drafting workflow with two
modes: build, which pins genre stance, speaker, claim and move instructions
before generating; and gate, which scans, applies the edit rule attached to
each finding, regenerates what was load-bearing, then rescans.

## Dogfood

This README scans CLEAN with its own scanner, and CI enforces that on every
commit. The catalog's rules were extracted from live drafting sessions where
a human reader caught each move in real prose; the specimens in
[references/moves.md](references/moves.md) are the actual catches, dated.

## License

MIT. No telemetry, no network calls, no models. It is a Python file that
reads your text and tells you the truth about it.
