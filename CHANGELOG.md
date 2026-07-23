# Changelog

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
