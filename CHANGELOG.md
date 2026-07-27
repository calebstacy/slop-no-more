# Changelog

## 0.2.0 (2026-07-27)

Soundness release: the public contract now matches what the deterministic
instrument can establish.

- Repositioned the project as a configurable English prose-pattern linter, not
  an authorship detector, quality measure or semantic judge.
- Made the gate threshold explicit with `--fail-on high|medium|never`.
  Exit codes now mean pass (`0`), configured gate failure (`1`), invalid usage
  (`2`) or input failure (`3`).
- Added repeatable `--disable RULE` policy exceptions.
- Added scanner version, fingerprint schema and ruleset identifiers plus the
  effective disabled rules, so comparisons can reject incompatible runs.
- Renamed `move_ratio_pct` to `sentences_with_moves_pct`; the metric now counts
  prose sentences containing a Layer-2 occurrence instead of matched lines.
- Made verdict bands count-based below 120 words, so a single medium finding in
  short copy no longer becomes `HEAVY SLOP` through per-1,000-word scaling.
- Expanded quote masking to complete paired straight and curly single- or
  double-quoted spans of any length. Contractions inside a complete quoted span
  are masked with it; apostrophes in unquoted prose remain lintable.
- Anchored rules now use logical Markdown and paragraph boundaries, so physical
  soft wraps do not create new starts or change findings.
- Structural-only documents with zero prose words report density and per-move
  rates as `n/a` in text and `null` in JSON while structural findings continue
  to affect verdicts and gates.
- Fenced-code masking now requires a compatible closing marker and delimiter
  length, and same-line inline code supports matching multi-backtick spans.
- Inline ignore exceptions now appear by source line and matched token in
  human, report-JSON and fingerprint-JSON output.
- Added explicit errors for unknown options, unreadable inputs, unsupported
  file types and directories with no supported prose files. Directory
  discovery accepts `.md`, `.markdown` and `.txt`; HTML, MDX and RST require
  extraction first. Inputs are capped at 1,000 files, 1 MiB per file and
  20 MiB total, and directory discovery skips file symlinks.
- Pinned the reusable GitHub Actions recipe to release `v0.2.0` and pinned
  third-party actions to reviewed commits.
- Reworked the demos as bounded specimens. The prompt comparison now requires
  recorded outputs for model-side claims, and the public field note no longer
  republishes a long source passage or claims semantic preservation.
- Revised the research notes to separate relevant scholarship from the
  project's unvalidated regexes, severities and density bands.
- Added `heading-afterbeat` (high), `anaphoric-evaluation` (high) and
  `unanchored-quantifier` (medium), bringing the catalog to 26 families. Each
  rule includes positive and legitimate-neighbor regression specimens.

## 0.1.0 (2026-07-23)

First public release.

- Three-layer scanner: lexical tells, 23 rhetorical-move families, and
  document-level distribution metrics.
- Findings carry severities and repair rules; exit code equals high-severity
  count for CI gating.
- Fingerprint vector: per-move rates per 1,000 words plus distribution
  metrics.
- Masking for quotes, inline code, fences, and blockquotes; `slop-ignore`
  escape hatch.
- Rate-metric floor: distribution rates (em-dash, triad, metadiscourse,
  antithesis) are reported but never judged below 120 words, so one em dash
  in a short note cannot read as heavy density.
- Side-by-side demo (`examples/side-by-side.md`): the same prompt on
  gpt-5.5 and claude-sonnet-5, bare vs constrained vs gated, captured
  outputs and real scan numbers. Both models violated fresh constraints in
  the same response; the gate closed both to CLEAN.
- Ships as a pip CLI (`slop scan`), a stdlib-only script, and a Claude Code
  skill (SKILL.md + references/moves.md).
