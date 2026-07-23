---
name: slop-no-more
description: >-
  Detects and repairs rhetorical moves that make prose read as AI-written and
  quietly mutate the argument: cataphoric evaluation ("here's why it matters"),
  manufactured antithesis ("not X, but Y"), phantom populations ("most teams"),
  invented adversaries, endophoric commands ("read that again"), anonymous
  authority, hedge clouds, rigid transitions, roadmap openings, coverage sweeps,
  sterile balance, benefit cascades and kin. Three layers: lexical strings,
  functional moves and document statistics (cadence variance, em-dash density,
  AI style-marker density, metadiscourse ratio). Ships a deterministic scanner
  (scripts/slop_scan.py) whose findings carry edit rules and a fingerprint
  vector. Use when writing, drafting, editing, reviewing or auditing prose for
  a reader, especially when the user says something sounds like AI, reads as
  slop, needs de-slopping or should sound like a specific human.
---

# slop-no-more

The unit of enforcement here is the **move**. A move is what a clause is
doing ("an evaluative clause whose referent is upcoming content"), and the
full catalog with definitions, edit rules and lineage lives in
[references/moves.md](references/moves.md). Read it before your first edit;
it is the ground truth this file only summarizes.

Two facts drive the whole design:

1. **Moves generate claims.** A denial template invents a claimant; a "most
   teams" template invents a survey. Slop at this layer changes what the piece
   asserts. So the gate rejects and regenerates instead of patching wording.
2. **Instructions alone do not hold.** A generator can hold a rule in full
   attention and violate it in the same paragraph (this was demonstrated live,
   repeatedly, during this skill's design). Instructions raise the pass rate;
   only the test enforces. Never report prose as clean because you tried to
   write it clean; report it clean because the scanner said so.

## Mode 1: Build (upstream)

Most slop is a specification problem: an unspecified prompt gets the median of
the training data, and the median is a persuasion artifact, an authoritative
diagnostician addressing an imagined audience, building to a quotable line.
Before drafting anything for a reader, pin:

- **Genre stance: thinking or persuading?** Default for essays is *thinking*:
  a person turning an idea over, uncertainty held openly, attention distributed
  unevenly. The model's default is persuading; left unpinned, it will recast
  the idea as a pitch and invent the audience to pitch to.
- **A speaker and an addressee.** One real person with a stake, writing at a
  specific someone. Never "teams," never a market.
- **The claim**, in one sentence, with its certainty level. If a claim ledger
  exists for the piece, every assertion traces to it; the ledger's confidence
  level caps the prose's confidence level.
- **Raw material first.** When the piece is in a specific person's voice, build
  quote-first from their recorded words. Human-sounding text is not achieved by
  subtraction from machine prose; it is achieved by starting from human
  material. The machine assembles; it does not author.
- **The move instructions** from the catalog, one line each, e.g. "never
  evaluate a point you have not yet made," "every antithesis names its
  claimant," "no quantifier over an unmeasured population."

## Mode 2: Gate (downstream)

For any draft, yours or existing prose brought in for audit:

```bash
python3 scripts/slop_scan.py <path>                 # report + verdict + fingerprint
python3 scripts/slop_scan.py <path> --severity high # strongest signals only
python3 scripts/slop_scan.py <path> --json          # machine-readable; exit code = high count
python3 scripts/slop_scan.py <path> --fingerprint   # the vector only
```

(With the package installed, `slop scan <path>` is the same tool.)

Then:

1. **Apply the edit rule attached to each finding.** A synonym swap is never
   the repair. The rules say what the sentence becomes: attribute the
   antithesis or convert it to a positive
   claim; replace the phantom population with a source or first-person scope;
   delete the cataphoric evaluation and lead with the content.
2. **Regenerate the affected passage** when a high-severity move is
   load-bearing (the paragraph's evidence *was* the move). Patching around a
   removed move leaves a hole where an argument should be.
3. **Rescan.** The gate is passed when the scanner passes.
4. **Novel costumes.** The scanner catches known disguises of each move. When
   prose feels off but scans clean, read it against the functional definitions
   in the catalog; anything you find gets added to the pattern family, so the
   deterministic layer grows.

Findings inside quotes, backticks and blockquotes are skipped: quoting a
move to discuss it is not performing it. A line containing `slop-ignore` is
skipped; use it for deliberate choices so the gate stays trustworthy.

## The over-correction trap

The mirror-image register (staccato fragments, forced lowercase, manufactured
casualness, fake typos) is its own tell, clocked just as fast. Evenness is
the tell whichever length it settles on: all-short sentences are as mechanical
as all-medium ones. The fix for a flagged move is the plain sentence a person
would write, never a costume of not-AI.

## The fingerprint

Every scan emits per-move rates per 1,000 words plus the distribution metrics
(cadence variance, em-dash density, triad density, metadiscourse ratio). Run
it over a corpus and you have a move fingerprint: a profile of how a writer,
a team, or a model actually behaves at the move level, and a baseline to
catch drift against. It pairs well with voice-fingerprinting tools, and the
division of labor is clean: a voice fingerprint tells you whether text sounds
like you; slop-no-more tells you whether it reads machine-made.

## Reporting

Lead with the verdict and the single highest-impact repair. Then findings by
severity with line numbers and their edit rules. Close with the fingerprint
line. A clean scan means the known layers are clean; say exactly that. The
final read against the catalog definitions is still a human's call.
