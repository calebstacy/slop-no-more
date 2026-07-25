# Changelog

## Unreleased

- New move: `heading-afterbeat` (high) — the two-beat heading hinged on a comma
  where the second beat comments on the first instead of adding information
  ("Language systems, built on shipped product", "Four things, and the last one
  is the point"). Human catch, 2026-07-25. Brings the catalog to 24 families.
- The move's boundary is pinned by tests in both directions, because it keys on
  a shape legitimate headings also wear: a second beat carrying a real fact,
  three-beat lists, counted appositions, and body sentences all stay quiet.
- `examples/from-the-wild.md` retitled — the new move caught the repo's own doc.
- New move: `anaphoric-evaluation` (high) — the mirror of `cataphoric-evaluation`.
  A clause hung off the end of a sentence that rates the content it trails
  instead of adding to it ("which is the only test that counted", "and that's
  the point"). Human catch, 2026-07-25.
- New move: `unanchored-quantifier` (medium) — consecutive sentences opened by a
  bare Both/Neither/Either/None standing in for a noun the prose never states
  ("Both taught the same skill. Both were legible. Neither survived…"). Same
  specimen, same catch. Brings the catalog to 26 families.
- Both are calibrated against the specimen's hand repair: the sentence its
  author rewrote by ear scans clean, and a test asserts it stays that way.

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
