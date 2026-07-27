# slop-no-more

A deterministic linter for configured prose patterns: the same inspectable
checks every time, with an editorial repair attached to every match.

Stop asking AI to do the checks that do not require intelligence.

## What it is

`slop-no-more` gives a writing team executable policy for English-language
prose. It looks for lexical strings, syntactic signatures and document-level
distributions the team has chosen to review. A match is evidence that a
configured pattern is present. It is not proof of who wrote the text, whether
the writing is good or whether a clause is performing a particular rhetorical
function.

That distinction is the point. A reviewer still decides which policy to adopt.
Once the decision exists, the scanner makes it difficult to ignore by
accident.

Three layers run on every scan:

| Layer | What is measured | Examples |
|---|---|---|
| 1. Strings | Literal lexical patterns | `delve`, `In conclusion`, stock boilerplate |
| 2. Signatures | Known surface forms associated with editorial concerns | unsupported antithesis, unsourced population claims, evaluative framing, roadmap openings |
| 3. Distribution | Document statistics | sentence-cadence variation, em-dash density, triad density, sentences containing configured signatures |

The catalog currently groups the signatures into 26 editorial families. Those
family names describe the concern behind each rule; the regex can only detect
the surface forms it encodes. Paraphrase can escape a pattern. A legitimate
sentence can wear the same surface form. Every finding therefore includes the
matched text and a repair rule a reviewer can inspect.

The vocabulary comes from move analysis and metadiscourse research, both of
which study what stretches of discourse do beyond carrying subject matter.
That scholarship gives the catalog useful questions. It does not validate this
project's particular regexes, severities or thresholds. See
[the research notes and rule catalog](references/moves.md).

The scanner uses Python's standard library alone: no model, API key, network
call or runtime dependency.

## What it can honestly guarantee

Given the same text, scanner version and configuration, `slop-no-more` applies
the same checks and returns the same findings. It can tell you:

- which configured patterns matched;
- where they matched;
- which repair the adopted policy recommends;
- whether the configured CI threshold passed; and
- how the reported measurements changed between comparable texts.

It cannot tell you:

- whether a human or a model wrote the text;
- whether the text is good, true or persuasive;
- whether every match performs the rhetorical function named by its family;
- whether a clean scan preserves facts or meaning; or
- how well the catalog performs outside the examples and tests in this repo.

No precision, recall or authorship-detection claim is made here.

## Why put the check in code?

Prompts and code solve different parts of the job. A prompt can shape a draft.
A deterministic check can verify an observable constraint after the draft
exists. For a rule such as `do not use an em dash`, the check is a yes-or-no
character test. Spending another model call to answer it adds cost and
uncertainty without adding judgment.

[The small prompt-versus-regex scaffold](examples/prompt_vs_regex.py) keeps the
comparison honest. Supply your own recorded model outputs to measure prompt
compliance; the bundled unit fixtures only demonstrate that the regex classifies
its declared cases consistently. Detection is not enforcement: the check can
fail a gate or route a match to repair, but another actor still has to change
the prose.

[The side-by-side case study](examples/side-by-side.md) records one generation
per pipeline on two models. In those captured runs, instructions changed the
drafts but did not eliminate all configured patterns; scan-guided repairs did.
One generation per cell is a specimen, not a benchmark or a model pass-rate
estimate.

[The field note](examples/from-the-wild.md) records how one disclosed,
AI-assisted public page exposed missing signatures in the catalog. It is a
catalog-growth example, not an authorship test or evidence that the scanner
measures information content.

## Install

### On claude.ai (no terminal needed)

Custom skills are available in Claude when code execution is enabled. The
scanner runs inside that code environment.

1. Download this repo as a ZIP.
2. In Claude, open Customize, then Skills. Choose **Create skill**, then
   **Upload a skill**, and upload the ZIP.
3. Ask Claude: `Run slop-no-more on this draft. Show me each match before
   applying its repair rule.`

### On ChatGPT or another chat with Python execution

1. Download [`src/slop_no_more/scanner.py`](src/slop_no_more/scanner.py).
2. Attach it with the draft.
3. Ask the chat to run the scanner, show the findings and apply only the
   repairs you approve.

Without code execution, a model can discuss the policy but cannot run the
deterministic check.

### In Claude Code

```bash
git clone https://github.com/calebstacy/slop-no-more ~/.claude/skills/slop-no-more
```

[SKILL.md](SKILL.md) wires the scanner into a drafting workflow with two modes:
build, which supplies editorial constraints before generation, and review,
which scans a finished draft and routes matches to repairs.

### On the command line

```bash
pip install git+https://github.com/calebstacy/slop-no-more
slop scan draft.md
```

Or with no install:

```bash
python3 scripts/slop_scan.py draft.md
```

## Use it as a CI policy

The gate threshold is explicit:

```bash
slop scan docs/ README.md --fail-on high    # default: high findings fail
slop scan docs/ README.md --fail-on medium  # high or medium findings fail
slop scan docs/ README.md --fail-on never   # report only
slop scan docs/ --disable heading-afterbeat # repeat for deliberate exclusions
```

Exit codes are a stable machine contract:

| Code | Meaning |
|---|---|
| `0` | The configured gate passed |
| `1` | The configured gate failed |
| `2` | The command or option was invalid |
| `3` | An input could not be read or was unsupported |

`--severity high|medium|low` filters what is displayed; it does not change the
gate. `--json` and `--fingerprint` change the output shape; they do not disable
the gate. `--disable RULE` is repeatable and records the effective rule set in
the fingerprint. Use `--fail-on never` when collecting measurements without
gating.

Directory scans discover and accept only `.md`, `.markdown` and `.txt` files.
HTML, MDX and RST require prose extraction first; passing them explicitly
returns input error `3` instead of treating raw markup as prose. One scan is
limited to 1,000 files, 1 MiB per file and 20 MiB total input; exceeding a
limit also returns input error `3`.
Directory discovery skips file symlinks; pass an intended file explicitly.

The [GitHub Actions example](examples/github-action.yml) shows the full
workflow. Pin both this scanner and third-party actions to reviewed commits in
production; a moving default branch is not a reproducible policy.

## What a scan looks like

Output on [examples/sample-slop.md](examples/sample-slop.md), trimmed:

```text
examples/sample-slop.md
verdict: HEAVY SLOP   density: 390.41 weighted hits / 1k words
high: 7   medium: 5   gate: FAIL (fail-on: high)
  [high  ]  L3  (manufactured-antithesis)  "not about wording, it's about"
           fix: Name who asserted X, or delete the denial and state Y as a positive claim.
  [high  ]  L3  (phantom-population)  "Most teams"
           fix: Cite the source and number, narrow to observed cases, or delete the claim.
  [medium]  L5  (benefit-cascade)  "foster engagement while empowering them"
           fix: Replace the benefit stack with the mechanism.
  ...more findings
  fingerprint: words=73  sentences=9  sentences_with_moves_pct=77.8 ...
  policy: policy-[content hash] (ruleset: snm-[content hash])
```

The labels `CLEAN`, `MOSTLY CLEAN`, `SLOP PRESENT` and `HEAVY SLOP` summarize
configured occurrences. They are not grades of writing quality or authorship
verdicts. At 120 words or more, the label uses weighted occurrences per 1,000
words. Below 120 words, it uses finding counts: no findings is `CLEAN`; one or
two non-high findings is `MOSTLY CLEAN`; a high finding or three to five total
findings is `SLOP PRESENT`; and three high or six total findings is `HEAVY
SLOP`. Document-rate rules are not judged below that floor.

Every report also emits a fingerprint with the scanner version, schema version,
ruleset identifier, counts and rates. Compare fingerprints only when the
scanner version, schema, ruleset,
configuration and genre are compatible. A change can show drift in configured
patterns; it does not explain why the drift happened.

## Honest edges

Checks anchored to the start or end of prose use logical Markdown and paragraph
boundaries, not physical file lines. Soft-wrapping one paragraph across several
lines does not create new starts for anchored rules.

The scanner excludes compatible fenced code, lines whose content begins with
`>`, matching same-line inline-code spans and complete paired straight or curly
quotation spans. It handles double-quoted and single-quoted spans. A
contraction inside a complete quoted span is masked with the rest of that span.
Apostrophes in unquoted prose remain ordinary, lintable characters rather than
quote delimiters. A line containing `slop-ignore` is skipped, and every
operative ignore is reported by line number and matched token in text, report
JSON and fingerprint JSON. Unclosed quote marks are still ordinary prose.

When a document contains structural Markdown but zero prose words after
masking, density and per-move rates are `n/a` in text output and `null` in JSON.
Structural findings still count toward the verdict and configured gate.

The scanner catches known surface forms, not novel paraphrases or rhetorical
functions. The functional definitions in [references/moves.md](references/moves.md)
are editorial rubrics for a human reviewer. When a repeated false positive or
false negative exposes a bad boundary, the rule needs a specimen and a
regression test before the catalog changes.

The current severities and density bands are policy defaults, not validated
psychometric thresholds. Teams should review them against their own genres and
failure costs before making them release criteria.

## Dogfood

Tests exercise the scanner's declared patterns and boundaries. CI also scans
the public documentation with the same executable rules. A passing dogfood
scan means those configured checks passed at the selected threshold, not that
the documents are beyond editorial review.

## License

MIT. No telemetry, network calls or models. It is a small, inspectable program
that reads text and reports the configured evidence it can actually observe.
