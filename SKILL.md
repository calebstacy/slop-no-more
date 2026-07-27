---
name: slop-no-more
description: >-
  Runs deterministic checks for configured English-language prose patterns and
  routes each match to an inspectable editorial repair. Use when drafting,
  editing or reviewing prose against an adopted style policy, especially when
  someone asks to de-slop a draft or remove familiar model-associated patterns.
  The scanner reports observable evidence; it does not identify authorship,
  measure writing quality or understand rhetorical function.
---

# slop-no-more

This skill turns an editorial policy into repeatable checks. The scanner owns
the observable question: *did a configured pattern occur?* A reviewer owns the
judgment: *is that occurrence a problem here, and what should replace it?*

The catalog groups known surface forms under editorial concerns called
**moves**. The functional definitions in
[references/moves.md](references/moves.md) explain those concerns. Read them as
review rubrics, not as capabilities the regex possesses. A match is not proof
that the sentence performs the named function.

Three commitments govern the workflow:

1. **Every claim goes to the strongest check it can honestly support.** A
   literal character, phrase or syntactic signature goes to code. Meaning,
   intent and tradeoffs stay with a reviewer.
2. **Some patterns can introduce unsupported premises.** An unattributed
   denial can imply a claimant; an unmeasured population phrase can imply data.
   Inspect the evidence before repeating or repairing the claim.
3. **A prompt is not a test.** Instructions can shape a draft. Only the
   post-draft scan establishes whether the configured observable checks passed.
   The scan does not itself enforce a repair; CI can reject the text, or an
   editor can change it.

## Mode 1: Build

Before drafting reader-facing prose, pin the inputs the writer or model would
otherwise have to invent:

- **Genre and job.** Name what the piece has to do for this reader.
- **Speaker and addressee.** Use the real relationship, not a generic market.
- **Claims and confidence.** Record the approved claims and the limits that cap
  their certainty.
- **Source material.** Start from approved facts, quotations and product
  details. A style constraint cannot supply missing evidence.
- **Applicable policy.** Select the rules that belong to this genre. Disable a
  rule deliberately when its surface form is legitimate here; do not ask the
  model to evade the scanner after the fact.

The catalog's instructions can be included in a drafting prompt. They may
improve compliance, but the output still has to be scanned independently.

## Mode 2: Review

Run the finished draft:

```bash
python3 scripts/slop_scan.py <path>
python3 scripts/slop_scan.py <path> --severity high
python3 scripts/slop_scan.py <path> --fail-on medium
python3 scripts/slop_scan.py <path> --disable manufactured-antithesis
python3 scripts/slop_scan.py <path> --json
python3 scripts/slop_scan.py <path> --fingerprint --fail-on never
```

With the package installed, `slop scan <path>` runs the same scanner.
Directory scans discover and accept only `.md`, `.markdown` and `.txt`. Extract
the prose from HTML, MDX or RST first; passing those formats returns input error
`3`. One scan accepts at most 1,000 files, 1 MiB per file and 20 MiB total
input; exceeding a limit is also input error `3`.
Directory discovery skips file symlinks; pass an intended file explicitly.

The gate contract is explicit:

- `--fail-on high` is the default.
- `--fail-on medium` fails on high or medium findings.
- `--fail-on never` reports without gating.
- `--severity high|medium|low` filters displayed findings only.
- `--disable RULE` is repeatable and removes that rule from the effective
  policy. The report fingerprints the disabled rules.
- `--json` and `--fingerprint` change output shape, not gate behavior.
- exit `0` means pass, `1` means configured findings failed the gate, `2`
  means invalid usage and `3` means an input error.

Then review each finding:

1. **Read the matched words in context.** Decide whether the configured
   concern applies. A surface signature can be a false positive.
2. **Use the attached repair as a route, not an automatic rewrite.** Attribute
   a denied claim, narrow an unsupported population, replace framing with the
   content or document a deliberate exception.
3. **Protect the substance.** The scanner does not compare meanings or verify
   facts. Check every edited claim against the source material.
4. **Rescan the edited passage.** Report the gate result and any remaining
   findings. Do not call the writing good, human or true because a scan passed.
5. **Record recurring boundary failures.** A new signature or exemption needs
   a positive specimen, a legitimate neighbor and regression tests before it
   becomes policy.

## Masking and deliberate exceptions

The scanner excludes:

- compatible fenced code blocks whose closer uses the opener's marker and at
  least its delimiter length;
- lines whose content begins with `>`;
- complete same-line inline-code spans with matching backtick delimiters;
- complete paired straight or curly double-quoted spans; and
- complete paired straight or curly single-quoted spans, with apostrophes
  inside words kept as prose.

Unclosed quote marks are ordinary prose. A line containing `slop-ignore` is
skipped. Prefer `--disable RULE` when the exception applies to a whole genre or
repository; use `slop-ignore` only for a deliberate local choice. Every
operative inline ignore is reported by source line and matched token in human
output, report JSON and fingerprint JSON.

Complete quoted spans mask everything inside them, including contractions.
Apostrophes in unquoted prose remain lintable and do not open a quote. Anchored
rules use logical Markdown and paragraph boundaries; physically soft-wrapping a
paragraph does not create a new start for those checks.

## The fingerprint

Each scan emits counts and rates, the scanner version, a fingerprint schema
version, a deterministic ruleset identifier and the effective disabled-rule
list. Compare fingerprints only when scanner version, schema, ruleset,
configuration and genre are compatible.

The fingerprint can show that configured pattern rates changed. It does not
identify a writer, measure voice, explain the cause of drift or establish that
one text is better. Density bands are occurrence summaries. In short copy, read
the findings themselves; per-1,000-word rates amplify single occurrences.
If structural Markdown remains after masking but no prose words do, density and
per-move rates are `n/a` in text output and `null` in JSON. Structural findings
still affect the verdict and gate.

## Reporting

Start with the configured gate result. Follow it with the most consequential
matched evidence and its repair. Include:

- `PASS` or `FAIL` and the `--fail-on` threshold;
- findings by severity with line numbers and matched text;
- any disabled rules or ignored lines;
- the scanner version, fingerprint schema and ruleset identifier when comparing
  runs; and
- a plain limitation: a pass means the selected observable checks passed.

Never convert the result into an authorship verdict, quality score or claim
that the revision preserved every fact. Those questions require different
evidence.
