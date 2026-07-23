# slop-no-more

A writing gate that catches the patterns making text sound like AI, the way
a spell-checker catches typos: the same rules every time, a fix attached to
every catch.

Stop asking AI to do the parts that don't require intelligence.

AI drafts a large share of the text people publish now, and the fastest
checks still get skipped because they feel like they need another AI.
They don't. The failure patterns are finite and matchable, and a
deterministic check beats a probabilistic promise every time it runs.

## What it is

A scanner that reads prose and flags the patterns that make text read as
AI-written: the giveaway words, and underneath them the rhetorical moves.
It is built for the people who own the words: content designers, UX
writers, editors and anyone shipping prose an AI helped draft.

The word-level tells are the easy part, and plenty of tools catch them.
The moves are the deeper layer: what a sentence is doing, regardless of
how it is phrased. Take "here's why this matters" and "the part worth
sitting with." They share no vocabulary, and they are the same move,
praising a point the text has not made yet. A banned-word list can't see
that; a move pattern can. AI slop is roughly a dozen moves wearing ten
thousand costumes, so this tool detects at the move level, where
paraphrase can't escape.

The move concept is borrowed, with credit, from applied linguistics. John
Swales' move analysis (1990) treats a stretch of discourse as a unit
defined by the job it does. Ken Hyland's metadiscourse research (2005)
maps the language a text spends on itself, the signposting and stance
work that surrounds the content. That is the lens this scanner operates:
slop is largely metadiscourse doing content's job. The full research
anchors, including 2025 corpus studies of how LLM prose actually behaves,
live in [references/moves.md](references/moves.md).

Three layers run on every scan:

| Layer | What it catches | Examples |
|---|---|---|
| 1. Strings | Lexical tells | "delve", "In conclusion", "I hope this helps", stock idioms at machine frequency |
| 2. Moves | Rhetorical patterns | manufactured antithesis, phantom populations, cataphoric evaluation, invented adversaries, hedge clouds, 23 families total |
| 3. Distribution | Document statistics | sentence-cadence uniformity, em-dash density, triad density, metadiscourse ratio, style-marker density |

Every finding names the pattern that fired and carries a repair rule that
says what the sentence should become. The exit code equals the number of
high-severity findings, so the scanner works as a build gate. And every
scan emits a fingerprint, per-move rates per 1,000 words, so a corpus can
be profiled and drift can be watched over time.

It runs on nothing but Python's standard library. No model, no API key, no
network, no pip dependencies. Cloning the repo is the entire installation.

## Why it matters

The experiment this repo is built on: take one real style rule, "don't use
em dashes." Handed to a language model as a polite instruction and run
over ten test strings, compliance came back at seven. The same rule as one
line of regex caught ten of ten, in microseconds, for free, and it will
catch the next ten thousand at the same rate. Rules that live in prompts
leak; rules that live in code hold. ([Run it yourself.](examples/prompt_vs_regex.py))

The same holds at full scale, on the models people actually use. The
[side-by-side demo](examples/side-by-side.md) sent one prompt through
three pipelines on `gpt-5.5` and `claude-sonnet-5`: the bare model, the
model with strict writing instructions, and this tool's draft-scan-repair
loop. Bare drafts scored 38.83 and 49.18 weighted density, both HEAVY
SLOP. Instructions alone transformed the substance and barely moved the
number (36.21 and 42.86): both models broke rules they had just been
handed, inside the same response. The loop finished both at 0.00, CLEAN.

And [one specimen nobody prompted](examples/from-the-wild.md): a page of
AI-written text from the live web, machine-authored by the publishing
platform's own disclosure, scanned as found at HEAVY SLOP and repaired to
CLEAN at 72 percent shorter with every fact intact. The vanished words
were carrying rhythm, and the facts all survived.

A survey of the field for this project (July 2026) found four tool
families: instruction packs, which put rules in a prompt and cannot
enforce them; rewriters, which change your text without showing findings;
ML detectors, which output an authorship verdict nobody can explain; and
word-list linters, which catch banned strings and miss the rhetoric. No
open-source tool combining move-level analysis, deterministic scanning,
repair rules, and CI enforcement turned up. This is that tool.

## Install

### On claude.ai (no terminal needed)

Custom skills are supported on paid claude.ai plans, and Claude can run
this scanner inside its own code sandbox.

1. Download this repo as a ZIP (the green Code button, then Download ZIP).
2. In claude.ai, open Settings, then Capabilities, then upload the ZIP as
   a skill.
3. Ask Claude: "Scan this draft with slop-no-more and apply the edit
   rules."

### On ChatGPT or any AI chat that can run Python (no terminal needed)

1. Download [`src/slop_no_more/scanner.py`](src/slop_no_more/scanner.py),
   one self-contained file.
2. Attach it to a chat along with your draft.
3. Ask: "Run this scanner on my draft, show the findings, and apply each
   finding's edit rule."

Without code execution, a model can only promise to follow the rules,
which is the exact pipeline the demos show failing. The scanner is the
point; get it run.

### In Claude Code

```bash
git clone https://github.com/calebstacy/slop-no-more ~/.claude/skills/slop-no-more
```

The [SKILL.md](SKILL.md) wires the scanner into a drafting workflow with
two modes: build, which pins genre stance, speaker, claim and move
instructions before generating; and gate, which scans, applies the edit
rule attached to each finding, regenerates what was load-bearing, then
rescans.

### On the command line, and in CI

For the engineers: deterministic, explainable, zero-model, and the exit
code is the gate. Don't ask a model to catch what a regex can catch.

```bash
pip install git+https://github.com/calebstacy/slop-no-more
slop scan draft.md
```

Or with no install at all:

```bash
python3 scripts/slop_scan.py draft.md
```

The exit code gates CI directly:

```yaml
- run: pip install git+https://github.com/calebstacy/slop-no-more
- run: slop scan docs/ README.md
```

Full workflow: [examples/github-action.yml](examples/github-action.yml).

## What a scan looks like

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

Flags: `--severity high` (strongest signals only), `--json`
(machine-readable), `--fingerprint` (the vector only). Verdict bands run
CLEAN, MOSTLY CLEAN, SLOP PRESENT, HEAVY SLOP, from a severity-weighted
density per 1,000 words.

## Honest edges

Quoted spans, inline code, fenced blocks and blockquotes are never linted:
quoting a move to discuss it is not performing it. A line containing
`slop-ignore` is skipped, so deliberate rhetorical choices stay possible
and the gate stays trustworthy. Distribution rates are reported but never
judged below 120 words, where one em dash would otherwise read as heavy
density.

The scanner only catches known costumes of each move. The functional
definitions in [references/moves.md](references/moves.md) are the rubric a
human applies to novel ones, and every human catch becomes a new pattern
with a test; the catalog's research lineage (Hyland 2005; Swales 1990) and
its full growth discipline live in that file. One calibration point from
its first live outing: an essay a human reader had flagged as painful
scored 53.9 weighted density, and the draft that later passed the same
reader's ear scored 0.0. The instrument and the ear agreed on rank order
at first try.

## Dogfood

This README scans CLEAN with its own scanner, as do SKILL.md, the move
catalog and both demo documents. CI enforces that on every commit.

## License

MIT. No telemetry, no network calls, no models. It is a Python file that
reads your text and tells you the truth about it.
