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
- Ships as a pip CLI (`slop scan`), a stdlib-only script, and a Claude Code
  skill (SKILL.md + references/moves.md).
