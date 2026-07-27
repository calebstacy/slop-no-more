# Field note: one disclosed AI-assisted page

The controlled side-by-side uses a prompt written for this repo. This field
note records a different job: use a public specimen to find gaps in the
catalog.

## Provenance and scope

On 2026-07-23, a
[LinkedIn collaborative article about remote teamwork](https://www.linkedin.com/advice/0/what-benefits-challenges-remote-teamwork-skills-teamwork)
displayed LinkedIn's disclosure that the page was powered by AI and the
LinkedIn community. The scanner was run on the page's framing prose, excluding
the named community contributions.

The full 659-word source passage is not republished here. That keeps the
example within the job it can support: a field note about the scanner's rule
boundaries, not a mirror of someone else's page. The small excerpts below are
the evidence relevant to those boundaries:

- `Read on to explore`
- `Furthermore`
- `Additionally`
- `here are some tips to consider`
- `leverage`

The disclosure establishes AI assistance at the page level. It does not make
the scanner an authorship detector, and the scan does not establish how much of
any sentence came from a model.

## What the scan found

The historical run reported configured instances of roadmap framing, formal
transitions, cataphoric framing, stock diction, repeated triads and low cadence
variation. The density band was `HEAVY SLOP`.

That label summarizes configured occurrence density. It is not a quality grade
or independent proof of authorship.

## What the specimen changed

The first run exposed four signatures the scanner did not yet cover:

- `Furthermore` and `Additionally` inside a paragraph, where the old transition
  pattern only matched line starts;
- `Read on to explore` as a roadmap opening;
- `here are some tips to consider` as evaluative framing; and
- `leverage` in the lexical layer.

Each observed form was added with a positive fixture and a legitimate neighbor.
That is the useful growth loop: a human identifies a repeated editorial concern,
the code captures the observable signature, and regression tests hold the
boundary.

## What the repair did not prove

An editorial rewrite reduced the passage from 659 words to 183 and produced no
findings under the ruleset used that day. The rewrite removed the configured
forms and preserved the editor's intended outline.

The scanner did **not** verify that every fact, recommendation or implication
survived. It does not compare meaning or measure information content. A factual
or semantic-preservation claim would require a separate source check.

This example therefore supports one narrow conclusion: a real specimen can
improve the boundaries of a deterministic policy linter. It does not validate
the catalog's thresholds or turn a clean scan into an editorial verdict.
