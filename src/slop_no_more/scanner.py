#!/usr/bin/env python3
"""slop-no-more: deterministic checks for configured English prose patterns.

Layer 1 (strings):      lexical tells. Diction memes, boilerplate, wrap-ups.
Layer 2 (moves):        configured rhetorical-pattern families. Regexes match
                        known surface forms; human review decides whether the
                        named rhetorical function applies in context.
Layer 3 (distribution): document-level statistics. Cadence variance, em-dash
                        density, triad density, sentence-with-move rate.

Every scan also emits a fingerprint: per-move rates per 1,000 words plus the
distribution metrics, so a corpus can be compared under a versioned ruleset.

Usage:
  slop scan <path> [<path>...]        full report + verdict
  slop scan <path> --severity high    only high-severity findings
  slop scan <path> --json             machine-readable output
  slop scan <path> --fingerprint      fingerprint vector only (JSON)
  slop scan <path> --fail-on medium   gate on medium and high findings
  slop scan <path> --fail-on never    output only; never fail the gate
  slop scan <path> --disable RULE     disable a registered rule

A line containing `slop-ignore` (or the legacy `gate-ignore` / `unslop-ignore`)
is skipped. Lines whose content begins with `>`, compatible fenced code,
same-line matching backtick spans, and supported paired quote spans are not
linted: quoting a move to discuss it is not performing it.
Exit codes: 0 pass, 1 gate failure, 2 usage error, 3 input/read error.
"""

import argparse
import hashlib
import json
import re
import statistics
import sys
from dataclasses import dataclass
from pathlib import Path

SCANNER_VERSION = "0.2.0"

# --------------------------------------------------------------------------
# Layer 2: the move catalog.
# Each move: functional definition, pattern family (the costumes we know),
# severity, and the edit rule applied on failure.
# Patterns catch known costumes of the move; the functional definition in
# references/moves.md is the ground truth a reviewer applies to novel costumes.
# --------------------------------------------------------------------------

SOURCE_PRESENT_RE = (
    r"\((?:[^)]{0,80}\d{4}[a-z]?[^)]{0,80})\)"
    r"|\[[0-9,\s-]{1,24}\]"
    r"|https?://|doi\.org|DOI\b|PMID\b|arXiv:"
)

MOVES = [
    {
        "name": "cataphoric-evaluation",
        "definition": "An evaluative clause whose referent is upcoming content: the text praises what it is about to say instead of saying it.",
        "severity": "high",
        "edit_rule": "Delete the evaluation and lead with the content. If the point matters, the sentence that states it must carry that weight itself.",
        "patterns": [
            r"\b(?:is|are|it'?s)\s+worth\s+(?:not|nam|mention|remember|repeat|paus|say|ask|emphasi|stress|dwell|sit)\w*",
            r"\bworth\s+(?:noting|naming|policing|watching|sitting\s+with|dwelling\s+on|unpacking|calling\s+out|pausing\s+on)\b",
            r"\bthe\s+part\s+worth\b",
            r"\b(?:here'?s|here\s+is)\s+(?:the\s+thing|the\s+part|why|what|where|how)\b",
            r"\bthe\s+(?:part|piece|thing|bit)\s+(?:that\s+matters|that\s+counts|worth|to\s+sit\s+with)\b",
            r"\bthe\s+(?:key|real|important|crucial|deeper|bigger|interesting)\s+(?:insight|point|question|takeaway|mechanism|lesson|story|part|piece)\b",
            r"\b(?:was|is)\s+the\s+(?:satisfying|surprising|funny|funniest|strange|strangest|scary|scariest|best|worst|wild|wildest)\s+part\b",
            r"(?m)^(?:Importantly|Crucially|Critically|Notably|Significantly)\b",
            r"\bit\s+(?:is|'s)\s+(?:important|crucial|critical|essential)\s+to\s+(?:note|remember|understand|recognize|realize)\b",
            r"\bwhat\s+matters\s+(?:here|most|more)\s+is\b",
            r"\bwhat\s+(?:this|that)\s+(?:really\s+)?(?:means|tells\s+us)\s+is\b",
            r"\b(?:that|this|the)\s+(?:last|next|first|second|real|important|key|hard|quiet|dangerous)?\s*(?:part|piece|thing|bit|point)\s+matters\b",
            r"\b(?:the\s+)?(?:clearest|simplest|easiest|hardest|trickiest|most\s+useful|most\s+important)\s+(?:one|part|piece|thing|point)\s+is\b",
            r"\b(?:this|that)\s+is\s+where\s+\w[^.?!\n]{0,70}?\s+(?:gets?|becomes?|turns?|starts?|begins?)\b",
            r"\b(?:that|this)\s+is\s+why\s+(?:I|we|you|the\s+\w+)\b",
            r"\bdeserves?\s+(?:naming|attention|a\s+closer\s+look|to\s+be\s+taken\s+seriously)\b",
            r"\b(?:so\s+)?here\s+is\s+the\s+\w+\s+you\s+actually\b",
            # wild catch, 2026-07-23, LinkedIn collaborative article
            r"\bhere\s+are\s+(?:some|a\s+few)\s+\w+\s+to\s+(?:consider|keep\s+in\s+mind)\b",
        ],
    },
    {
        "name": "anaphoric-evaluation",
        "definition": "The mirror of cataphoric-evaluation: a clause hung off the end of a sentence that rates the content it trails ('which is the only test that counted', 'and that is the point') rather than adding to it. The sentence finishes, then tells the reader the sentence mattered.",
        "severity": "high",
        "edit_rule": "Delete the trailing clause. If the fact it gestures at is real, state it: name the test, say who failed it, give the number. Significance is what the sentence demonstrates, not a rating appended to it.",
        "patterns": [
            # "…, which is the only test that counted." / "…, which was the real measure that mattered."
            r",\s+which\s+(?:is|was)\s+(?:the\s+)?(?:only\s+|whole\s+|real\s+|actual\s+)?\w{3,14}\s+that\s+(?:count|matter)\w*",
            # "…, which is the point." / "…, which was exactly the problem."
            r",\s+which\s+(?:is|was)\s+(?:exactly\s+)?(?:the\s+)?(?:whole\s+)?(?:point|problem|issue|catch)\b",
            # "…, which is what mattered."
            r",\s+which\s+(?:is|was)\s+what\s+(?:count|matter)\w*",
            # "…, and that's the point." / "— and that is what counted."
            r"[,—–]\s+and\s+that(?:'s|’s|\s+is|\s+was)\s+(?:the\s+)?(?:whole\s+)?(?:point|thing|catch)\b",
            r"[,—–]\s+and\s+that(?:'s|’s|\s+is|\s+was)\s+what\s+(?:count|matter)\w*",
            # "…, which is the part that matters."
            r",\s+which\s+(?:is|was)\s+the\s+(?:part|piece|bit)\s+that\s+(?:count|matter)\w*",
        ],
    },
    {
        "name": "manufactured-antithesis",
        "definition": "A denial of a claim with no attributable claimant, staged so the correction can carry the assertion (not-X-but-Y and kin).",
        "severity": "high",
        "edit_rule": "Name who actually asserted X (with a source), or delete the denial and state Y as a plain positive claim.",
        "patterns": [
            r"\bnot\s+(?:just|only|merely|simply)\s+\w[^.?!\n]{0,80}?\bbut\b",
            r"\b(?:is|are|was|were)\s+not\s+(?:a|an|the)\s+[\w' ]{1,30}?\s*[—–,-]+\s*(?:it|they|that)\s+(?:is|are|'s|'re|\s)",
            r"\b(?:is|are)\s+not\s+\w+[^.?!\n]{0,20}[.?!]\s+(?:It|They|That|This)\s+(?:is|are)\b",
            r"\b(?:isn'?t|not)\s+about\s+\w[^.?!\n]{0,60}?\b(?:it'?s|but)\s+about\b",
            r"\bless\s+about\s+\w[^.?!\n]{0,50}?\bthan\s+(?:about\s+)?\b",
            r"(?m)^(?:It'?s|This\s+is|That\s+is)\s+not\s+(?:that\s+)?\w+",
            r"\b[Ii]t'?s\s+not\s+(?:a|an|the)?\s?[\w' ]{1,30}?\s*[—–,-]+\s*it\s+(?:is|'s)\b",
            r"[—–]\s*not\s+(?:a|an|the)\s+\w[^.?!\n]{0,50}?,\s*but\b",
            r",\s+not\s+\w+\s*[—–.;]",
        ],
    },
    {
        "name": "phantom-population",
        "definition": "A quantified claim over a population nobody measured, asserted because the rhetorical template requires a group that fails or agrees.",
        "severity": "high",
        "edit_rule": "Cite the source and number, downgrade to a first-person observation ('the teams I have seen'), or delete the claim.",
        "patterns": [
            r"\b[Mm]ost\s+(?:teams|people|companies|writers|developers|engineers|users|organizations|orgs|founders|leaders|managers|readers)\b",
            r"\b(?:everyone|everybody)\s+(?:knows|agrees|is\s+talking|has\s+seen)\b",
            r"\bnobody\s+(?:talks\s+about|tells\s+you|wants\s+to\s+admit|is\s+prepared)\b",
            r"\bwe'?ve\s+all\s+(?:seen|been|felt|done)\b",
            r"\b[Mm]any\s+(?:teams|people|companies|writers|developers|users|organizations|founders|leaders)\b",
            r"\bsorted?\s+into\s+two\s+camps\b",
            r"\bthe\s+(?:first|second|other)\s+camp\s+is\s+(?:bigger|larger|louder|smaller|right|wrong|winning)\b",
        ],
    },
    {
        "name": "invented-adversary",
        "definition": "A rebuttal of an accusation or belief no one voiced, conjured so the text can perform fairness or correction.",
        "severity": "high",
        "edit_rule": "Quote the real person who holds the position, or delete the rebuttal. You cannot correct a belief you invented.",
        "patterns": [
            r"\b(?:is|are)\s+not\s+the\s+(?:villain|enemy|problem|culprit|point)\s+here\b",
            r"\b(?:is|are)\s+not\s+the\s+(?:villain|enemy|culprit)\b",
            r"\bnot\s+to\s+blame\b",
            r"\bnobody\s+is\s+(?:saying|arguing|claiming)\b",
            r"\b(?:critics|skeptics|detractors|some)\s+(?:might|will|would|may)\s+(?:say|argue|object|claim)\s+that\b",
            r"\byou\s+might\s+(?:think|assume|be\s+tempted\s+to\s+(?:think|assume|conclude))\b",
            r"\bthe\s+\w+s\s+in\s+the\s+room\s+(?:have|has|are|will|would|might)\b",
        ],
    },
    {
        "name": "endophoric-command",
        "definition": "An imperative ordering the reader to re-attend to the text itself, claiming significance the prose has not earned.",
        "severity": "high",
        "edit_rule": "Delete the command. If the material deserves a second read, rewrite it so one read lands it.",
        "patterns": [
            r"\b[Rr]ead\s+(?:that|this|it|the\s+[\w ]{1,25})\s+again\b",
            r"\b[Ll]et\s+that\s+sink\s+in\b",
            r"\b[Ss]it\s+with\s+that\b",
            r"\b[Tt]hink\s+about\s+(?:that|it)\s+for\s+a\s+(?:second|moment|minute)\b",
            r"(?m)^(?:Note|Notice|Consider|Remember)\s+(?:that|how|what|this)\b",
        ],
    },
    {
        "name": "counterfeit-idiom",
        "definition": "A figurative or colloquial phrase that imitates spoken idiom but is not one anyone says: invented folksiness signaling 'human voice' instead of carrying meaning.",
        "severity": "high",
        "edit_rule": "Say it plainly. If a real idiom exists and fits, use it; otherwise the plain phrase was the human one all along.",
        "patterns": [
            # open class, primarily caught by a human ear; every catch lands
            # here as a literal costume so it can never ship twice
            r"\bsmell\s+(?:I|you|we)\s+could\s+point\s+at\b",
            r"\bem\s+dashes\s+by\s+the\s+pound\b",
            r"\bcomes?\s+back\s+wearing\s+synonyms\b",
            r"\b(?:make|makes|made)\s+the\s+smell\s+pointable\b",
            r"\blittle\s+constitution\b",
            r"\bkindness\s+to\s+the\s+reader\b",
        ],
    },
    {
        "name": "hollow-pivot",
        "definition": "A clause styled as a decisive conclusion that only restates or negates the previous clause: pure rhythm posing as a decision.",
        "severity": "high",
        "edit_rule": "State the actual decision or consequence the pivot was gesturing at. If there is none, delete the clause.",
        "patterns": [
            r"\bso\s+(?:we|I)\s+stopped\s+asking\b",
            r"(?m)^So\s+(?:we|I)\s+(?:did|stopped|quit)\.\s*$",
            r"(?m)^And\s+it\s+worked\.\s*$",
            r"(?m)^It\s+(?:did|was)\.\s*$",
        ],
    },
    {
        "name": "dramatized-frame",
        "definition": "Verbs and time-scales punched up beyond the facts (interrogated for asked, an afternoon for months), falsifying the writer's actual relationship to the events.",
        "severity": "high",
        "edit_rule": "Restore the literal verb and the real timeline. Drama that the facts did not supply is fiction.",
        "patterns": [
            # ear-first move; costumes accumulate per catch
            r"\binterrogat(?:e|ed|ing)\w*\s+(?:Claude|ChatGPT|the\s+model|the\s+AI)\b",
        ],
    },
    {
        "name": "unanchored-we",
        "definition": "A first-person-plural actor in single-author prose whose members are never named, blurring who actually did what.",
        "severity": "medium",
        "edit_rule": "Name the actors: I decided, the model built, the team shipped. Keep 'we' only for a group the reader can identify.",
        "patterns": [
            r"\b[Ww]e\s+(?:built|wrote|made|designed|decided|created|shipped|defined)\b",
        ],
    },
    {
        "name": "unanchored-quantifier",
        "definition": "Consecutive sentences opened by a bare quantifier (Both, Neither, Either, None) standing in for a noun the prose never states, chopping one claim into parallel fragments so the repetition can supply structure the sentence does not.",
        "severity": "medium",
        "edit_rule": "Name the antecedent once and join the fragments into the single sentence they already are: 'Both approaches taught the same skill and were legible, but neither survived contact with a first-time user.'",
        "patterns": [
            # the run is the detectable signal: a regex cannot see whether an antecedent exists,
            # but two sentences in a row opening on the same bare quantifier is the cadence, and
            # the repair (name the noun, join the clauses) fixes the missing referent too.
            # "Bare" is the whole move: a quantifier followed straight by a determiner or
            # possessive has its noun attached and is ordinary English — "Neither the naive
            # prompt nor the published guide is a straw man. Both are close to…" is not this
            # move, and cost a false fire before the lookahead was added.
            r"(?m)(?:^|[.!?]\s+)(?:Both|Neither|Either|None)\s+(?!the\b|a\b|an\b|of\b|my\b|our\b|your\b|his\b|her\b|their\b|its\b|this\b|that\b|these\b|those\b)"
            r"[^.!?\n]{2,100}[.!?]\s+(?:Both|Neither|Either|None)\s+"
            r"(?!the\b|a\b|an\b|of\b|my\b|our\b|your\b|his\b|her\b|their\b|its\b|this\b|that\b|these\b|those\b)",
        ],
    },
    {
        "name": "borrowed-inference",
        "definition": "An inferential connective (so, which means, if X then Y) asserting a logical relation the text never establishes: logic's syntax used as transition music.",
        "severity": "high",
        "edit_rule": "Either supply the actual reasoning that connects the claims, or drop the connective and state the second claim as what it is (a plan, a hope, a separate fact).",
        "patterns": [
            # ear-first; the pseudo-syllogism shape is the one reliable costume
            r"\bif\s+(?:the\s+)?\w[^,.?!]{0,50}can\s+be\s+\w+(?:ed|en),?\s+(?:then\s+)?it\s+can\s+be\b",
            r"(?m)^And\s+if\s+\w[^.?!]{0,60},\s*(?:it|that|we|you)\s+can\b",
        ],
    },
    {
        "name": "false-collaboration",
        "definition": "First-person-plural stagecraft that casts the reader as a participant in work the writer is doing alone.",
        "severity": "medium",
        "edit_rule": "Do the thing instead of announcing it together: state the finding, make the argument.",
        "patterns": [
            r"\b[Ll]et'?s\s+(?:unpack|dig\s+in|dive|break\s+(?:this|it|that)\s+down|be\s+honest|be\s+clear|be\s+real|take\s+a\s+(?:closer\s+)?look|talk\s+about|explore)\b",
            r"\bwe\s+need\s+to\s+talk\s+about\b",
            r"\b[Ll]et'?s\s+start\s+with\b",
        ],
    },
    {
        "name": "gatekeeper-test",
        "definition": "The text hands the reader a diagnostic question to ask others, casting writer and reader as evaluators of an absent population.",
        "severity": "medium",
        "edit_rule": "Answer the question yourself, in the text, with your own evidence, or cut the consulting frame entirely.",
        "patterns": [
            r"\bask\s+(?:one|a\s+single)\s+(?:thing|question)\b",
            r"\bask\s+yourself\s+(?:one\s+thing|this|whether)\b",
            r"\bthe\s+(?:one|only)\s+question\s+(?:that|worth|to\s+ask)\b",
        ],
    },
    {
        "name": "clean-dichotomy",
        "definition": "Asserting that a drawn distinction is sharp ('the line cuts cleanly') as a claim about the world, when only the sentence is clean.",
        "severity": "medium",
        "edit_rule": "Show the edge cases or drop the cleanliness claim; a real line earns its sharpness with examples at the boundary.",
        "patterns": [
            r"\bcuts?\s+cleanly\b",
            r"\bthe\s+line\s+worth\s+drawing\b",
            r"\bfalls?\s+into\s+(?:two|three)\s+(?:neat\s+)?(?:camps|buckets|categories)\b",
            r"\bthere\s+are\s+(?:exactly\s+)?two\s+kinds\s+of\b",
        ],
    },
    {
        "name": "empty-emphasis",
        "definition": "An intensity claim about the writer's own argument ('this is the scariest part', 'the trap', 'the real waste') doing work evidence should do.",
        "severity": "medium",
        "edit_rule": "Replace the intensity word with the fact that justifies it; if no fact justifies it, delete the sentence.",
        "patterns": [
            r"\b(?:this|that|it)\s+is\s+(?:partly\s+)?a\s+trap\b",
            r"\bthe\s+(?:real|true|actual)\s+(?:waste|cost|danger|problem|failure|question)\s+is\b",
            r"\b(?:the\s+scariest|the\s+most\s+dangerous|the\s+deadliest)\s+(?:part|class|kind)\b",
            r"\bfeels\s+responsible\.\s",
            r"\b(?:this|that)\s+is\s+the\s+(?:whole\s+)?(?:bet|threshold|point|claim|lesson)\b",
            r"\b(?:this|that)\s+is\s+(?:technical|human|useful|important)\s+work\b",
        ],
    },
    {
        "name": "phantom-bargain",
        "definition": "A mechanism recast as a deal, promise, or contract between the reader and an abstraction, borrowing the authority of an agreement no one made.",
        "severity": "high",
        "edit_rule": "Replace the bargain with the mechanism: what is produced, by what process, with what guarantees actually documented. CS contract terminology for real, documented interfaces is legitimate; the personified bargain with the reader is not.",
        "patterns": [
            r"\bthe\s+(?:contract|deal|bargain)\s+you\s+actually\s+(?:hold|have|get|signed|made)\b",
            r"\b(?:model|machine|AI|it|system)\s+promises\s+you\b",
            r"\b\w+'?s\s+deal\s+is\s+that\b",
            r"\bhere\s+is\s+the\s+(?:contract|deal|bargain)\b",
        ],
    },
    {
        "name": "count-contrast-lockup",
        "definition": "A verbless apposition of counted noun phrases, 'N xs, one y' or its inversion, used as a heading, kicker, or closer so the count rhythm can assert a synthesis the prose has not established.",
        "severity": "high",
        "edit_rule": "Replace with a heading that names what the list is, or a sentence stating the unifying mechanism. Partitives ('nine drafts, one past the gate') and flat data inventories of 3+ counts are legitimate.",
        "patterns": [
            # convergence: "three jobs, one system" / "two channels, two methods, one vocabulary"
            r"\b(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen|\d[\d,]*)\s+\w+(?:\s+\w+){0,2}(?:,\s*(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|dozen|\d[\d,]*)\s+\w+(?:\s+\w+){0,2})*,\s*one\s+(?!of\b|in\b|on\b|at\b|by\b|per\b|past\b|from\b|with\b|for\b|to\b|that\b|which\b|already\b|still\b)\w+",
            # inversion: "one argument, four parts" — bare pairing, suppressed when a third count follows (data inventory)
            r"\bone\s+(?!of\b|in\b|on\b|at\b|by\b|per\b|past\b|from\b|with\b|for\b|to\b|that\b|which\b)\w+(?:\s+\w+){0,2},\s*(?:two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen|\d[\d,]*)\s+\w+(?:\s+\w+){0,2}\b(?!\s*(?:,|\s+and)\s*(?:one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|dozen|\d))",
        ],
    },
    {
        "name": "heading-afterbeat",
        "definition": "A heading or kicker built as two beats hinged on a comma, where the beat after the comma comments on the first instead of adding information: a participle tag ('Language, measured'), a sequel tag ('Teaching and poetry, then product design'), or a meta-claim about the list the heading introduces ('Four things, and the last one is the point'). The comma supplies cadence, and the cadence is mistaken for a point.",
        "severity": "high",
        "edit_rule": "Delete the beat after the comma and let the heading name its own subject. If the second beat carries a fact the first does not, it belongs in the body as a sentence, not hung off a heading as a tag.",
        "patterns": [
            # participle tag: "Language, measured." / "Language systems, built on shipped
            # product." / "A five-job content model, decided before there was an interface."
            # One comma only, and the whole line stays heading-length — the char bounds are the
            # word-count guard, since a body sentence that happens to have a participle after a
            # comma ("Hypotheses that survive contact with shipped behaviour, run with research
            # and data partners.") runs past them and is left alone.
            # 'not X' is left to manufactured-antithesis so the two moves do not both fire.
            # NB: the regular-participle class is -ed/-ing/-wn with a 3+ char stem, never a bare
            # -en: "op|en", "oft|en", "ev|en" and "t|en" are not participles, and -en cost a false
            # fire on "Published research, open dependencies". Irregulars are listed explicitly.
            r"(?m)^ {0,3}#{1,6}[ \t]+[A-Z][^,\n]{2,48},\s+(?!not\b)(?:[a-z]{3,}(?:ed|ing|wn)|built|made|kept|shown|sent|met|gone|lost|done|taken|given|written|broken|chosen|driven|proven|known|held|left|told|found|brought|caught|taught|seen|spent|split|dealt)\b[^,\n]{0,34}\.?$",
            # sequel tag: "Teaching and poetry, then product design."
            r"(?m)^ {0,3}#{1,6}[ \t]+[A-Z][^,\n]{2,48},\s+then\s+[^,\n]{2,44}\.?$",
            # counted heading with an appended tag: "Four rules, and the strings that came out of
            # them." / "Four things, and the last one is the point."
            r"(?m)^ {0,3}#{1,6}[ \t]+(?:One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve|\d+)\s+[a-z]+,\s+and\s+the\s+[^,\n]{2,48}\.?$",
            # meta-claim tag in an explicit Markdown heading:
            # "…, and the last one is the point."
            r"(?m)^ {0,3}#{1,6}[ \t]+[^,\n]{2,64},\s+and\s+the\s+(?:last|first|second|third|next|only|real|best|worst|hardest|simplest|biggest)\s+one\s+(?:is|was|matters|counts|wins|does|did)\b[^,\n]*$",
            # bare ordinal meta-tag in an explicit Markdown heading:
            # "Four things, the last one matters."
            r"(?m)^ {0,3}#{1,6}[ \t]+[^,\n]{2,64},\s+the\s+(?:last|first|next|only|hardest|biggest)\s+one\s+(?:is\s+the\s+\w+|matters|counts)\b[^,\n]*$",
            # prepositional label tag: "The practice, in order" / "The before, on its own terms"
            r"(?m)^ {0,3}#{1,6}[ \t]+[A-Z][^,\n]{2,34},\s+(?:in|on|at|by|for|with|from|under|after|before|through)\s+[a-z][^,\n]{2,26}$",
        ],
    },
    {
        "name": "anonymous-authority",
        "definition": "A source-shaped claim that invokes research, evidence, experts, or consensus without naming the source.",
        "severity": "high",
        "edit_rule": "Name the source and claim precisely, or remove the authority wrapper and state the claim at the confidence level you can defend.",
        "skip_if": SOURCE_PRESENT_RE,
        "patterns": [
            r"\b(?:research|studies|evidence|data|the\s+literature)\s+(?:shows?|suggests?|indicates?|demonstrates?|confirms?|reveals?|points\s+to|supports?)\b",
            r"\b(?:experts|scholars|researchers|analysts)\s+(?:agree|say|argue|suggest|believe|emphasize|warn)\b",
            r"\bit\s+is\s+(?:widely|generally|commonly)\s+(?:accepted|recognized|understood|known|believed)\b",
            r"\ba\s+growing\s+body\s+of\s+(?:research|evidence|literature)\b",
        ],
    },
    {
        "name": "hedge-cloud",
        "definition": "A stack of modal and hedging terms that diffuses responsibility for a claim instead of calibrating uncertainty.",
        "severity": "medium",
        "edit_rule": "Keep one calibrated uncertainty term and say what makes the claim uncertain: sample size, source quality, timing, or scope.",
        "patterns": [
            r"\b(?:may|might|could|possibly|potentially|arguably|generally|often|typically|tend(?:s)?\s+to|seems?|appears?|likely|suggests?)\b[^.?!\n]{0,90}\b(?:may|might|could|possibly|potentially|arguably|generally|often|typically|tend(?:s)?\s+to|seems?|appears?|likely|suggests?)\b",
        ],
    },
    {
        "name": "transition-turnstile",
        "definition": "A sentence or paragraph begins with a formal transition that supplies motion without a real relation between claims.",
        "severity": "medium",
        "edit_rule": "Name the actual relation between the sentences, or delete the transition and let the content make the turn.",
        "patterns": [
            r"(?m)^\s*(?:Moreover|Furthermore|Additionally|In\s+addition|Overall|Ultimately|Notably|Importantly|Crucially),\s+(?=\w)",
            # same move mid-paragraph: sentence-initial after a full stop
            # (wild catch, 2026-07-23, LinkedIn collaborative article)
            r"[.!?]\s+(?:Moreover|Furthermore|Additionally|In\s+addition|Overall|Ultimately),\s+(?=\w)",
        ],
    },
    {
        "name": "template-roadmap",
        "definition": "The text announces the generic task it will perform instead of beginning the task with a substantive claim.",
        "severity": "medium",
        "edit_rule": "Cut the roadmap and start with the first claim, example, or question that actually belongs to this piece.",
        "patterns": [
            r"\b(?:this|the)\s+(?:essay|article|post|piece|guide|section)\s+(?:explores?|examines?|delves?\s+into|dives?\s+into|unpacks|highlights|discusses|aims?\s+to|will\s+(?:explore|examine|discuss|highlight|show))\b",
            r"\bin\s+this\s+(?:essay|article|post|piece|guide|section),?\s+(?:we|I|the\s+reader)\s+(?:will|can)\b",
            r"\bthis\s+piece\s+is\s+about\s+(?:how|why|what)\b",
            # wild catch, 2026-07-23, LinkedIn collaborative article
            r"\b[Rr]ead\s+on\s+to\s+(?:explore|learn|discover|find\s+out|see)\b",
        ],
    },
    {
        "name": "coverage-sweep",
        "definition": "A breadth montage that gestures across a range instead of selecting the specific cases the argument needs.",
        "severity": "medium",
        "edit_rule": "Replace the sweep with the two or three cases that matter, and say why those cases were chosen.",
        "patterns": [
            r"\b(?:everything|anything)\s+from\s+[^.?!\n]{2,60}\s+to\s+[^.?!\n]{2,60}\b",
            r"\b(?:ranging|spanning)\s+from\s+[^.?!\n]{2,60}\s+to\s+[^.?!\n]{2,60}\b",
            r"\bacross\s+(?:a\s+wide\s+range|multiple|various|diverse)\s+(?:of\s+)?[\w-]+",
            r"(?<!across\s)\b(?:a\s+wide|a\s+broad|an\s+array)\s+(?:range|array|set)\s+of\b",
        ],
    },
    {
        "name": "sterile-balance",
        "definition": "A symmetrical concession frame that performs neutrality without adjudicating which side is true, stronger, or relevant.",
        "severity": "medium",
        "edit_rule": "State the actual tradeoff with evidence and weight. If the balance is just manners, delete it.",
        "patterns": [
            r"\bwhile\s+(?:there\s+are|it\s+has|it\s+offers|it\s+can|this\s+may|some\s+may)[^.?!\n]{0,90},\s+(?:it\s+(?:also|is\s+also|remains)|there\s+is\s+also|we\s+must\s+also|one\s+must\s+also)\b",
            r"(?<!it also )\b(?:offers?|presents?|creates?|brings?)\s+both\s+(?:opportunities|promise|benefits|advantages)\s+and\s+(?:challenges|risks|concerns|limitations)\b",
            r"\bboth\s+(?:promise|opportunity|benefits|advantages)\s+and\s+(?:peril|risk|challenges|limitations)\b",
            r"\bnot\s+without\s+its\s+(?:challenges|risks|limitations)\b",
        ],
    },
    {
        "name": "benefit-cascade",
        "definition": "A chain of generic uplift verbs that converts desired outcomes into evidence of mechanism.",
        "severity": "medium",
        "edit_rule": "Replace the benefit stack with the mechanism: who does what differently, and what changes because of it.",
        "patterns": [
            r"\b(?:enhance|enhances|enhancing|foster|fosters|promote|promotes|drive|drives|enable|enables|empower|empowers|facilitate|facilitates|support|supports|optimize|optimizes|streamline|streamlines)\s+\w[^.?!\n]{0,100}\b(?:enhance|foster|promote|drive|enable|empower|facilitate|support|optimize|streamline)\w*\b",
        ],
    },
]

# --------------------------------------------------------------------------
# Layer 1: lexical tells (condensed, density-weighted).
# --------------------------------------------------------------------------

LEXICAL = [
    ("assistant-boilerplate", r"\bas\s+an\s+AI(?:\s+language)?\s+model\b|\bI\s+(?:cannot|can'?t)\s+browse\b", "high",
     "Delete it. This is machinery showing through the fiction."),
    ("trailing-offer", r"\bWould\s+you\s+like\s+me\s+to\b|\bLet\s+me\s+know\s+if\s+(?:you|this)\b|\bI\s+hope\s+this\s+helps\b", "high",
     "Delete. A written piece does not offer follow-up service."),
    ("in-conclusion", r"(?m)^\s*(?:In\s+conclusion|To\s+sum\s+up|In\s+summary)\b", "high",
     "Cut the recap. End on the last real point."),
    ("diction-meme", r"\bdelve\b|\btapestry\b|\btestament\s+to\b|\bgame-?chang\w+\b|\bseamless(?:ly)?\b|\bsupercharge\b|\belevate\s+your\b|\bunlock\s+(?:the\s+)?(?:potential|power)\b|\bleverag(?:e|es|ed|ing)\b", "medium",
     "Use the plain verb or noun you would say out loud."),
    # reified "the gap" — a named human catch, 2026-07-02: recurs constantly in AI prose
    ("the-gap", r"\bthat'?s\s+the\s+gap\b|\bthat\s+gap\s+is\b|\bthe\s+gap\s+between\s+what\b|\bmind\s+the\s+gap\b", "high",
     "Name the two concrete things and the difference between them, or cut the gap talk."),
    # attested idioms at machine frequency: real phrases no writer uses this often
    ("stock-idiom", r"\b(?:gave|give|giving)\s+(?:it|them|this|that)\s+teeth\b|\bwith\s+(?:real\s+)?teeth\b|\bdo(?:es|ing)?\s+the\s+heavy\s+lifting\b|\bearn(?:s|ed)?\s+its\s+keep\b|\btable\s+stakes\b|\bsecret\s+sauce\b", "high",
     "State literally what it does. The idiom is real; the frequency is the machine's."),
    ("deep-dive", r"\bdeep\s+dive\b|\bdive\s+deep\b|\bdive\s+in(?:to)?\b", "medium",
     "Say 'look at' / 'read' / 'study', whichever is literally true."),
    ("hollow-opener", r"\bIn\s+today'?s\s+(?:fast-paced|digital|modern|ever-changing)\b|\bIn\s+the\s+world\s+of\b|\bIn\s+the\s+age\s+of\b", "medium",
     "Start with the actual subject of the piece."),
]
# The em dash is deliberately NOT a per-instance finding: presence is human,
# rate is the tell. It is scored only as Layer 3 density (emdash_per_1k).

STYLE_MARKER_RE = re.compile(
    r"\b(?:across|additionally|comprehensive|crucial|enhanc(?:e|es|ed|ing)|"
    r"exhibited|insights?|notably|particularly|within|delv(?:e|es|ed|ing)|"
    r"showcas(?:e|es|ed|ing)|underscor(?:e|es|ed|ing)|potential|intricate|"
    r"commendable|meticulous|pivotal|robust|realm|landscape|"
    r"navigat(?:e|es|ed|ing)|resonat(?:e|es|ed|ing)|seamless(?:ly)?|"
    r"tapestr(?:y|ies))\b",
    re.IGNORECASE,
)

# --------------------------------------------------------------------------
# Layer 3 thresholds
# --------------------------------------------------------------------------

L3_RULES = {
    # metric: (medium_threshold, high_threshold, direction, message)
    "cadence_cv":        (0.40, 0.30, "below", "Sentence-length variation falls below the configured range. Review the cadence and vary it where the subject calls for a change."),
    "emdash_per_1k":     (3.0, 6.0, "above", "Em-dash rate exceeds the configured range. Review each dash and keep it only where it clarifies the sentence."),
    "triad_per_1k":      (5.0, 9.0, "above", "Triadic-list rate exceeds the configured range. Review whether each three-part list reflects the content or repeats a cadence."),
    "sentences_with_moves_pct": (6.0, 10.0, "above", "Configured rhetorical moves appear in a high share of sentences. Review the matched sentences and keep only the framing the argument needs."),
    "antithesis_per_1k": (2.0, 4.0, "above", "Configured contrast-frame rate exceeds the target. Review whether each correction has an attributable claim to correct."),
    "style_marker_per_1k": (12.0, 24.0, "above", "Configured style-marker rate exceeds the target. Review the matches and prefer domain nouns, literal verbs, and specific mechanisms where they carry the meaning more directly."),
}

SEV_WEIGHT = {"high": 3.0, "medium": 1.5, "low": 0.5}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}

IGNORE_TOKENS = ("slop-ignore", "gate-ignore", "unslop-ignore")


# --------------------------------------------------------------------------
# v0.2 runtime
#
# The catalog above remains data. This runtime normalizes ordinary prose wraps
# before applying it, maps every match back to source coordinates, and gives
# the CLI an explicit policy/gating contract.
# --------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = frozenset({".md", ".markdown", ".txt"})
MAX_FILE_BYTES = 1 * 1024 * 1024
MAX_INPUT_FILES = 1000
MAX_TOTAL_BYTES = 20 * 1024 * 1024
FINGERPRINT_SCHEMA_VERSION = 2
RATE_FLOOR_WORDS = 120
FAIL_LEVELS = ("high", "medium", "never")
WORD_RE = re.compile(r"[^\W_]+(?:['’\u2011-][^\W_]+)*", re.UNICODE)
ATX_HEADING_RE = re.compile(r" {0,3}#{1,6}(?:[ \t]+|$)")
LIST_ITEM_RE = re.compile(
    r" {0,3}(?:[-+*][ \t]+|\d{1,9}[.)][ \t]+)"
)
FENCE_OPEN_RE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)$")
FENCE_CLOSE_RE = re.compile(r" {0,3}(`{3,}|~{3,})[ \t]*$")
HARD_BOUNDARY = "\n.\n"
SENTENCE_CLOSERS = "\"'”’)]}"
NONTERMINAL_ABBREVIATIONS = frozenset(
    {
        "al.",
        "dr.",
        "e.g.",
        "etc.",
        "fig.",
        "i.e.",
        "jr.",
        "mr.",
        "mrs.",
        "ms.",
        "no.",
        "prof.",
        "sr.",
        "st.",
        "vs.",
    }
)
MASK_PATTERN_SPECS = (
    (r"(?<!`)(`+)(?!`)[^\r\n]*?(?<!`)\1(?!`)", 0),
    (r'"(?:\\.|[^"\\])*"', re.DOTALL),
    (r"“[^”]*”", re.DOTALL),
    (r"‘(?:[^’]|(?<=\w)’(?=\w))*?’(?!\w)", re.DOTALL),
    (
        r"(?<!\w)'(?:\\.|[^'\\]|(?<=\w)'(?=\w))*?'(?!\w)",
        re.DOTALL,
    ),
)


def _ruleset_payload():
    return {
        "engine": {
            "fingerprint_schema": FINGERPRINT_SCHEMA_VERSION,
            "word_pattern": WORD_RE.pattern,
            "sentence_boundary_policy": {
                "terminal_marks": ".!?",
                "hard_boundary": HARD_BOUNDARY,
                "nonterminal_abbreviations": sorted(
                    NONTERMINAL_ABBREVIATIONS
                ),
                "initialisms_are_nonterminal": True,
                "lowercase_sentence_starts": True,
            },
            "atx_heading_pattern": ATX_HEADING_RE.pattern,
            "list_item_pattern": LIST_ITEM_RE.pattern,
            "fence_policy": {
                "open_pattern": FENCE_OPEN_RE.pattern,
                "close_pattern": FENCE_CLOSE_RE.pattern,
                "closer_matches_marker": True,
                "closer_minimum_opener_length": True,
            },
            "rate_floor_words": RATE_FLOOR_WORDS,
            "max_file_bytes": MAX_FILE_BYTES,
            "max_input_files": MAX_INPUT_FILES,
            "max_total_bytes": MAX_TOTAL_BYTES,
            "case_insensitive": True,
            "sentence_move_metric": "sentences_with_moves_pct",
            "anchored_boundary_policy": "logical Markdown blocks",
            "zero_prose_rate_policy": "null",
            "mask_patterns": [
                {"pattern": pattern, "flags": flags}
                for pattern, flags in MASK_PATTERN_SPECS
            ],
            "ignore_policy": {
                "tokens": IGNORE_TOKENS,
                "match": "literal substring on one source line",
                "scope": "skip the matched source line",
                "reporting": "line number and matched token",
            },
            "supported_extensions": sorted(SUPPORTED_EXTENSIONS),
            "directory_symlink_policy": "skip",
            "severity_weights": SEV_WEIGHT,
            "severity_order": SEV_ORDER,
            "fail_levels": FAIL_LEVELS,
            "short_verdict_policy": {
                "floor_words": RATE_FLOOR_WORDS,
                "mostly_clean": "1-2 findings and no high",
                "slop_present": "1-2 findings with high, or 3-5 total",
                "heavy_slop": "3+ high, or 6+ total",
            },
            "hard_boundary": HARD_BOUNDARY,
        },
        "lexical": [
            {
                "name": name,
                "pattern": pattern,
                "severity": severity,
                "fix": fix,
            }
            for name, pattern, severity, fix in LEXICAL
        ],
        "moves": [
            {
                "name": move["name"],
                "definition": move["definition"],
                "patterns": move["patterns"],
                "severity": move["severity"],
                "edit_rule": move["edit_rule"],
                "skip_if": move.get("skip_if"),
            }
            for move in MOVES
        ],
        "distribution": L3_RULES,
    }


RULESET_ID = "snm-" + hashlib.sha256(
    json.dumps(
        _ruleset_payload(), sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
).hexdigest()[:16]

RULE_NAMES = frozenset(
    [name for name, _pattern, _severity, _fix in LEXICAL]
    + [move["name"] for move in MOVES]
    + list(L3_RULES)
)


@dataclass(frozen=True)
class PreparedBuffer:
    text: str
    source_offsets: tuple
    source_lines: tuple
    source_columns: tuple


@dataclass(frozen=True)
class PreparedDocument:
    lint: PreparedBuffer
    prose: PreparedBuffer
    lint_lines: tuple
    ignored_lines: tuple


def _blank_match(chars, match):
    """Mask a complete paired span while preserving newline positions."""
    for index in range(match.start(), match.end()):
        if chars[index] not in "\r\n":
            chars[index] = " "


def _mask_nonprose_spans(text):
    """Mask complete inline-code and quoted spans without a length cap."""
    chars = list(text)
    for pattern_source, flags in MASK_PATTERN_SPECS:
        pattern = re.compile(pattern_source, flags)
        for match in pattern.finditer(text):
            _blank_match(chars, match)
    return "".join(chars)


def _make_buffer(parts):
    text_parts = []
    offsets = []
    lines = []
    columns = []
    for value, value_offsets, value_lines, value_columns in parts:
        text_parts.append(value)
        offsets.extend(value_offsets)
        lines.extend(value_lines)
        columns.extend(value_columns)
    return PreparedBuffer(
        "".join(text_parts), tuple(offsets), tuple(lines), tuple(columns)
    )


def prepare_document(text):
    """Build normalized lint/prose buffers and offset maps to the source."""
    masked = _mask_nonprose_spans(text)
    original_lines = text.splitlines(keepends=True)
    masked_lines = masked.splitlines(keepends=True)

    lint_parts = []
    prose_parts = []
    line_buffers = []
    ignored_lines = []
    fence_marker = None
    fence_length = 0
    source_offset = 0
    lint_soft_open = False
    prose_soft_open = False

    def append_synthetic(parts, value, line_number, column):
        parts.append(
            (
                value,
                (-1,) * len(value),
                (line_number,) * len(value),
                (column,) * len(value),
            )
        )

    def append_boundary(parts, line_number, column):
        append_synthetic(parts, HARD_BOUNDARY, line_number, column)

    for line_number, (original_raw, masked_raw) in enumerate(
        zip(original_lines, masked_lines), 1
    ):
        content_len = len(masked_raw.rstrip("\r\n"))
        original_content = original_raw[:content_len]
        masked_content = masked_raw[:content_len]
        stripped = original_content.strip()
        if fence_marker is not None:
            close_match = FENCE_CLOSE_RE.fullmatch(original_content)
            if (
                close_match is not None
                and close_match.group(1)[0] == fence_marker
                and len(close_match.group(1)) >= fence_length
            ):
                fence_marker = None
                fence_length = 0
            allowed = False
        else:
            open_match = FENCE_OPEN_RE.fullmatch(original_content)
            if (
                open_match is not None
                and not (
                    open_match.group(1)[0] == "`"
                    and "`" in open_match.group(2)
                )
            ):
                fence_marker = open_match.group(1)[0]
                fence_length = len(open_match.group(1))
                allowed = False
            else:
                ignore_matches = tuple(
                    token
                    for token in IGNORE_TOKENS
                    if token in original_content
                )
                if ignore_matches and not stripped.startswith(">"):
                    ignored_lines.append(
                        {
                            "line": line_number,
                            "tokens": list(ignore_matches),
                        }
                    )
                allowed = (
                    not ignore_matches
                    and not stripped.startswith(">")
                )

        offsets = tuple(range(source_offset, source_offset + content_len))
        lines = (line_number,) * content_len
        columns = tuple(range(1, content_len + 1))
        is_heading = ATX_HEADING_RE.match(original_content) is not None
        is_table = stripped.startswith("|")
        list_match = LIST_ITEM_RE.match(original_content)
        structural = is_heading or is_table

        if allowed and stripped:
            full_part = (masked_content, offsets, lines, columns)
            line_buffers.append(_make_buffer([full_part]))

            if structural:
                if lint_parts:
                    append_boundary(
                        lint_parts, line_number, content_len + 1
                    )
                lint_parts.append(full_part)
                append_boundary(lint_parts, line_number, content_len + 1)
                lint_soft_open = False

                append_boundary(
                    prose_parts, line_number, content_len + 1
                )
                prose_soft_open = False
            elif list_match:
                body_start = list_match.end()
                body_part = (
                    masked_content[body_start:],
                    offsets[body_start:],
                    lines[body_start:],
                    columns[body_start:],
                )
                if lint_parts:
                    append_boundary(
                        lint_parts, line_number, content_len + 1
                    )
                lint_parts.append(body_part)
                lint_soft_open = True

                if prose_parts:
                    append_boundary(
                        prose_parts, line_number, content_len + 1
                    )
                prose_parts.append(body_part)
                prose_soft_open = True
            else:
                if lint_soft_open:
                    append_synthetic(
                        lint_parts, " ", line_number, content_len + 1
                    )
                lint_parts.append(full_part)
                lint_soft_open = True

                if prose_soft_open:
                    append_synthetic(
                        prose_parts, " ", line_number, content_len + 1
                    )
                prose_parts.append(full_part)
                prose_soft_open = True
        else:
            append_boundary(lint_parts, line_number, content_len + 1)
            append_boundary(prose_parts, line_number, content_len + 1)
            lint_soft_open = False
            prose_soft_open = False

        source_offset += len(original_raw)

    return PreparedDocument(
        lint=_make_buffer(lint_parts),
        prose=_make_buffer(prose_parts),
        lint_lines=tuple(line_buffers),
        ignored_lines=tuple(ignored_lines),
    )


def prepare_lines(text):
    """Return the legacy line views, backed by the v0.2 masking rules."""
    prepared = prepare_document(text)
    source_lines = text.splitlines()
    lint = [None] * len(source_lines)
    prose = [None] * len(source_lines)
    for line_buffer in prepared.lint_lines:
        if not line_buffer.source_lines:
            continue
        index = line_buffer.source_lines[0] - 1
        lint[index] = line_buffer.text
        source_line = source_lines[index]
        stripped = source_line.strip()
        if not (
            ATX_HEADING_RE.match(source_line)
            or stripped.startswith("|")
        ):
            prose[index] = line_buffer.text
    return lint, prose


def _period_is_nonterminal(text, period_index):
    token_match = re.search(r"([A-Za-z.]+)$", text[:period_index + 1])
    if token_match is None:
        return False
    token = token_match.group(1)
    lowered = token.lower()
    if lowered in NONTERMINAL_ABBREVIATIONS:
        return True
    if re.fullmatch(r"(?:[A-Za-z]\.){2,}", token):
        return True
    return re.fullmatch(r"[A-Za-z]\.", token) is not None


def _boundary_ranges(text, include_semicolon=False):
    """Yield logical hard boundaries and conservative sentence boundaries."""
    terminal_marks = ".!?" + (";" if include_semicolon else "")
    index = 0
    while index < len(text):
        if text.startswith(HARD_BOUNDARY, index):
            end = index + len(HARD_BOUNDARY)
            while text.startswith(HARD_BOUNDARY, end):
                end += len(HARD_BOUNDARY)
            yield index, end
            index = end
            continue

        mark = text[index]
        if mark not in terminal_marks:
            index += 1
            continue
        if mark == "." and _period_is_nonterminal(text, index):
            index += 1
            continue

        after_closers = index + 1
        while (
            after_closers < len(text)
            and text[after_closers] in SENTENCE_CLOSERS
        ):
            after_closers += 1
        if (
            after_closers >= len(text)
            or not text[after_closers].isspace()
            or text.startswith(HARD_BOUNDARY, after_closers)
        ):
            index += 1
            continue

        end = after_closers
        while end < len(text) and text[end].isspace():
            if text.startswith(HARD_BOUNDARY, end):
                break
            end += 1
        if end > after_closers:
            yield after_closers, end
            index = end
            continue
        index += 1


def _sentence_spans(buffer):
    """Return (start, end, text) spans for sentences in a prepared buffer."""
    boundaries = list(_boundary_ranges(buffer.text))
    spans = []
    start = 0
    for boundary_start, boundary_end in boundaries:
        raw = buffer.text[start:boundary_start]
        candidate = raw.strip()
        if len(WORD_RE.findall(candidate)) >= 2:
            leading = len(raw) - len(raw.lstrip())
            trailing = len(raw.rstrip())
            spans.append((start + leading, start + trailing, candidate))
        start = boundary_end
    raw = buffer.text[start:]
    candidate = raw.strip()
    if len(WORD_RE.findall(candidate)) >= 2:
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        spans.append((start + leading, start + trailing, candidate))
    return spans


def sentences_of(prose_lines):
    """Return normalized sentence strings for legacy API callers."""
    prepared = prepare_document("\n".join(line for line in prose_lines if line))
    return [
        sentence
        for _start, _end, sentence in _sentence_spans(prepared.prose)
    ]


def _source_location(buffer, start, end):
    positions = [
        index
        for index in range(start, end)
        if 0 <= index < len(buffer.source_offsets)
        and buffer.source_offsets[index] >= 0
    ]
    if not positions:
        return None
    first = positions[0]
    last = positions[-1]
    return {
        "_source_start": buffer.source_offsets[first],
        "_source_end": buffer.source_offsets[last] + 1,
        "line": buffer.source_lines[first],
        "column": buffer.source_columns[first],
        "end_line": buffer.source_lines[last],
        "end_column": buffer.source_columns[last] + 1,
    }


def _claim_has_source(buffer_text, start, end, source_pattern):
    """Suppress an authority wrapper only when its own sentence has a source."""
    left = 0
    right = len(buffer_text)
    for boundary_start, boundary_end in _boundary_ranges(
        buffer_text, include_semicolon=True
    ):
        if boundary_end <= start:
            left = boundary_end
            continue
        if boundary_start >= end:
            right = boundary_start
            break
    return (
        re.search(
            source_pattern, buffer_text[left:right], flags=re.IGNORECASE
        )
        is not None
    )


def _iter_matches(buffer, pattern):
    return re.finditer(
        pattern, buffer.text, flags=re.IGNORECASE | re.MULTILINE
    )


def _normalize_disabled(disabled_rules):
    disabled = frozenset(disabled_rules or ())
    unknown = sorted(disabled - RULE_NAMES)
    if unknown:
        raise ValueError("unknown rule(s): " + ", ".join(unknown))
    return disabled


def _policy_id(disabled_rules):
    material = RULESET_ID + "\0" + "\0".join(sorted(disabled_rules))
    return "policy-" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def _add_finding(findings, buffer, match, layer, move, severity, fix):
    location = _source_location(buffer, match.start(), match.end())
    if location is None:
        return
    findings.append(
        {
            "layer": layer,
            "move": move,
            "match": match.group(0).strip(),
            "severity": severity,
            "fix": fix,
            **location,
        }
    )


def _dedupe_findings(findings):
    """Merge overlapping regex costumes for one source occurrence."""
    ordered = sorted(
        findings,
        key=lambda finding: (
            finding["move"],
            finding["_source_start"],
            finding["_source_end"],
        ),
    )
    deduped = []
    cluster_move = None
    cluster_end = -1
    cluster_best = None
    cluster_best_width = -1

    for finding in ordered:
        starts_new_cluster = (
            finding["move"] != cluster_move
            or finding["_source_start"] >= cluster_end
        )
        if starts_new_cluster:
            if cluster_best is not None:
                deduped.append(cluster_best)
            cluster_move = finding["move"]
            cluster_end = finding["_source_end"]
            cluster_best = finding
            cluster_best_width = (
                finding["_source_end"] - finding["_source_start"]
            )
            continue

        cluster_end = max(cluster_end, finding["_source_end"])
        finding_width = finding["_source_end"] - finding["_source_start"]
        if finding_width > cluster_best_width:
            cluster_best = finding
            cluster_best_width = finding_width

    if cluster_best is not None:
        deduped.append(cluster_best)
    return deduped


def _verdict_for(findings, density, word_count):
    high_count = sum(
        finding["severity"] == "high" for finding in findings
    )
    finding_count = len(findings)
    if finding_count == 0:
        return "clean"
    # A per-1k rate is unstable on short copy. Keep the measured density, but
    # assign its label from occurrence counts until the rate has a base.
    if word_count < RATE_FLOOR_WORDS:
        if high_count >= 3 or finding_count >= 6:
            return "heavy slop"
        if high_count >= 1 or finding_count >= 3:
            return "slop present"
        return "mostly clean"
    if density < 4:
        return "mostly clean"
    if density < 10:
        return "slop present"
    return "heavy slop"


def scan_text(text, name="<text>", disabled_rules=None):
    """Scan a string and return a deterministic report dictionary."""
    disabled = _normalize_disabled(disabled_rules)
    prepared = prepare_document(text)
    findings = []

    # Physical line breaks inside a Markdown paragraph are soft wrapping, not
    # rhetorical boundaries. The prepared lint buffer preserves only logical
    # paragraph and structural boundaries, so anchored rules cannot fire on an
    # arbitrary wrap and citations remain attached to the claim they source.
    for buffer in (prepared.lint,):
        for lex_name, pattern, severity, fix in LEXICAL:
            if lex_name in disabled:
                continue
            for match in _iter_matches(buffer, pattern):
                _add_finding(
                    findings, buffer, match, 1, lex_name, severity, fix
                )
        for move in MOVES:
            if move["name"] in disabled:
                continue
            for pattern in move["patterns"]:
                for match in _iter_matches(buffer, pattern):
                    if move.get("skip_if") and _claim_has_source(
                        buffer.text,
                        match.start(),
                        match.end(),
                        move["skip_if"],
                    ):
                        continue
                    _add_finding(
                        findings,
                        buffer,
                        match,
                        2,
                        move["name"],
                        move["severity"],
                        move["edit_rule"],
                    )

    findings = _dedupe_findings(findings)

    # ---- Layer 3 ----
    prose_text = prepared.prose.text
    words = WORD_RE.findall(prose_text)
    word_count = len(words)
    rate_denominator = max(word_count, 1)
    sentence_spans = _sentence_spans(prepared.prose)
    sentences = [
        sentence for _start, _end, sentence in sentence_spans
    ]
    metrics = {"words": word_count, "sentences": len(sentences)}

    if len(sentences) >= 8:
        lengths = [len(WORD_RE.findall(sentence)) for sentence in sentences]
        mean = statistics.mean(lengths)
        deviation = statistics.pstdev(lengths)
        metrics["mean_sentence_len"] = round(mean, 1)
        metrics["cadence_cv"] = (
            round(deviation / mean, 3) if mean else 0.0
        )
    metrics["emdash_per_1k"] = round(
        prose_text.count("—") * 1000 / rate_denominator, 2
    )
    triads = re.findall(
        r",\s+[^,.;:\n]{2,50},\s+(?:and|or)\s+", prose_text
    )
    metrics["triad_per_1k"] = round(
        len(triads) * 1000 / rate_denominator, 2
    )

    source_sentence = {}
    for sentence_index, (start, end, _sentence) in enumerate(sentence_spans):
        for buffer_index in range(start, end):
            source_offset = prepared.prose.source_offsets[buffer_index]
            if source_offset >= 0:
                source_sentence[source_offset] = sentence_index
    sentences_with_moves = set()
    for finding in findings:
        if finding["layer"] != 2:
            continue
        for source_offset in range(
            finding["_source_start"], finding["_source_end"]
        ):
            sentence_index = source_sentence.get(source_offset)
            if sentence_index is not None:
                sentences_with_moves.add(sentence_index)
    if sentences:
        metrics["sentences_with_moves_pct"] = round(
            100.0 * len(sentences_with_moves) / len(sentences), 1
        )

    antithesis_count = sum(
        finding["move"] == "manufactured-antithesis"
        for finding in findings
    )
    metrics["antithesis_per_1k"] = round(
        antithesis_count * 1000 / rate_denominator, 2
    )
    style_hits = STYLE_MARKER_RE.findall(prose_text)
    metrics["style_marker_count"] = len(style_hits)
    if len(words) >= 250 or len(style_hits) >= 4:
        metrics["style_marker_per_1k"] = round(
            len(style_hits) * 1000 / rate_denominator, 2
        )

    for metric, (medium, high, direction, message) in L3_RULES.items():
        if metric in disabled or metric not in metrics:
            continue
        if metrics["words"] < RATE_FLOOR_WORDS:
            continue
        value = metrics[metric]
        hit = None
        if direction == "below":
            if value < high:
                hit = "high"
            elif value < medium:
                hit = "medium"
        else:
            if value > high:
                hit = "high"
            elif value > medium:
                hit = "medium"
        if hit:
            findings.append(
                {
                    "layer": 3,
                    "move": metric,
                    "line": 0,
                    "column": 0,
                    "end_line": 0,
                    "end_column": 0,
                    "match": f"{metric}={value}",
                    "severity": hit,
                    "fix": message,
                    "_source_start": -1,
                    "_source_end": -1,
                }
            )

    fingerprint = {
        "scanner_version": SCANNER_VERSION,
        "fingerprint_schema": FINGERPRINT_SCHEMA_VERSION,
        "ruleset_id": RULESET_ID,
        "policy_id": _policy_id(disabled),
        "disabled_rules": sorted(disabled),
        "ignored_line_count": len(prepared.ignored_lines),
        "ignored_lines": list(prepared.ignored_lines),
        **metrics,
    }
    for move in MOVES:
        count = sum(
            finding["move"] == move["name"] for finding in findings
        )
        fingerprint[f"mv_{move['name']}_per_1k"] = (
            round(count * 1000 / word_count, 2)
            if word_count
            else None
        )

    weight = sum(SEV_WEIGHT[finding["severity"]] for finding in findings)
    density = (
        round(weight * 1000 / word_count, 2)
        if word_count
        else None
    )
    severity_counts = {
        severity: sum(
            finding["severity"] == severity for finding in findings
        )
        for severity in ("high", "medium", "low")
    }
    verdict = _verdict_for(findings, density, len(words))
    findings.sort(
        key=lambda finding: (
            SEV_ORDER[finding["severity"]],
            finding["layer"],
            finding["line"],
            finding["column"],
        )
    )
    for finding in findings:
        finding.pop("_source_start", None)
        finding.pop("_source_end", None)
    return {
        "file": str(name),
        "verdict": verdict,
        "density": density,
        "high": severity_counts["high"],
        "severity_counts": severity_counts,
        "findings": findings,
        "ignored_lines": list(prepared.ignored_lines),
        "fingerprint": fingerprint,
    }


def scan_file(path, disabled_rules=None):
    path = Path(path)
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise OSError(
            f"file exceeds {MAX_FILE_BYTES} byte limit ({size} bytes): {path}"
        )
    text = path.read_text(encoding="utf-8", errors="replace")
    return scan_text(text, name=path, disabled_rules=disabled_rules)


class _UsageError(Exception):
    pass


class _ScanArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise _UsageError(message)


def _scan_parser(prog="slop scan"):
    parser = _ScanArgumentParser(prog=prog)
    parser.add_argument("paths", nargs="+", help="Markdown or plain-text path")
    parser.add_argument(
        "--severity",
        choices=("high", "medium", "low"),
        help="show only this severity; does not change the gate",
    )
    output = parser.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="JSON report")
    output.add_argument(
        "--fingerprint",
        action="store_true",
        help="fingerprint vectors as JSON",
    )
    parser.add_argument(
        "--fail-on",
        choices=FAIL_LEVELS,
        default="high",
        help="gate threshold; never is an explicit output-only scan",
    )
    parser.add_argument(
        "--disable",
        action="append",
        default=[],
        metavar="RULE",
        help="disable a registered rule; repeat to disable more",
    )
    return parser


def _collect_paths(raw_paths):
    paths = []
    seen = set()

    def add_path(path):
        key = path.resolve()
        if key in seen:
            return
        seen.add(key)
        paths.append(path)
        if len(paths) > MAX_INPUT_FILES:
            raise OSError(
                f"input exceeds {MAX_INPUT_FILES} file limit"
            )

    for raw_path in raw_paths:
        path = Path(raw_path)
        if not path.exists():
            raise OSError(f"path does not exist: {path}")
        if path.is_dir():
            discovered = []
            for candidate in path.rglob("*"):
                if (
                    candidate.is_file()
                    and not candidate.is_symlink()
                    and candidate.suffix.lower() in SUPPORTED_EXTENSIONS
                ):
                    discovered.append(candidate)
                    if len(discovered) > MAX_INPUT_FILES:
                        raise OSError(
                            f"input exceeds {MAX_INPUT_FILES} file limit"
                        )
            if not discovered:
                raise OSError(
                    "directory has no supported prose files "
                    f"({', '.join(sorted(SUPPORTED_EXTENSIONS))}): {path}"
                )
            for candidate in sorted(discovered):
                add_path(candidate)
        elif path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise OSError(
                f"unsupported file type {path.suffix or '<none>'}: {path}; "
                f"supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
            )
        else:
            add_path(path)

    total_bytes = 0
    for path in paths:
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            raise OSError(
                f"file exceeds {MAX_FILE_BYTES} byte limit "
                f"({size} bytes): {path}"
            )
        total_bytes += size
        if total_bytes > MAX_TOTAL_BYTES:
            raise OSError(
                f"input exceeds {MAX_TOTAL_BYTES} aggregate byte limit "
                f"({total_bytes} bytes)"
            )
    return paths


def _gate_count(reports, fail_on):
    if fail_on == "never":
        return 0
    severities = {"high"} if fail_on == "high" else {"high", "medium"}
    return sum(
        1
        for report in reports
        for finding in report["findings"]
        if finding["severity"] in severities
    )


def run(argv, prog="slop scan"):
    parser = _scan_parser(prog)
    try:
        options = parser.parse_args(argv)
    except _UsageError:
        return 2
    except SystemExit as exc:
        return int(exc.code)

    try:
        disabled = _normalize_disabled(options.disable)
    except ValueError as exc:
        parser.print_usage(sys.stderr)
        print(f"{prog}: error: {exc}", file=sys.stderr)
        return 2

    try:
        paths = _collect_paths(options.paths)
        reports = [
            scan_file(path, disabled_rules=disabled) for path in paths
        ]
    except (OSError, UnicodeError) as exc:
        print(f"{prog}: input error: {exc}", file=sys.stderr)
        return 3

    gate_count = _gate_count(reports, options.fail_on)
    gate_failed = gate_count > 0
    metadata = {
        "mode": "fingerprint" if options.fingerprint else "report",
        "fail_on": options.fail_on,
        "gate_failed": gate_failed,
        "gate_findings": gate_count,
        "ruleset_id": RULESET_ID,
        "policy_id": _policy_id(disabled),
        "disabled_rules": sorted(disabled),
    }

    if options.fingerprint:
        print(
            json.dumps(
                {
                    **metadata,
                    "files": {
                        report["file"]: report["fingerprint"]
                        for report in reports
                    },
                },
                indent=2,
            )
        )
        return 1 if gate_failed else 0
    if options.json:
        print(json.dumps({**metadata, "reports": reports}, indent=2))
        return 1 if gate_failed else 0

    gate_label = "FAIL" if gate_failed else "PASS"
    for report in reports:
        print(f"\n{'=' * 72}\n{report['file']}")
        counts = report["severity_counts"]
        density_label = (
            "n/a"
            if report["density"] is None
            else str(report["density"])
        )
        print(
            f"verdict: {report['verdict'].upper()}   "
            f"density: {density_label} weighted hits / 1k words   "
            f"high: {counts['high']}   medium: {counts['medium']}   "
            f"gate: {gate_label} (fail-on: {options.fail_on})"
        )
        if report["ignored_lines"]:
            ignored = ", ".join(
                f"L{entry['line']} ({'/'.join(entry['tokens'])})"
                for entry in report["ignored_lines"]
            )
            print(f"  ignored lines: {ignored}")
        shown = [
            finding
            for finding in report["findings"]
            if not options.severity
            or finding["severity"] == options.severity
        ]
        for finding in shown:
            if finding["line"]:
                location = f"L{finding['line']}"
                if finding["end_line"] != finding["line"]:
                    location += f"-{finding['end_line']}"
            else:
                location = "doc"
            print(
                f"  [{finding['severity']:<6}] {location:>9}  "
                f"({finding['move']})  “{finding['match'][:70]}”"
            )
            print(f"               fix: {finding['fix']}")
        fingerprint = report["fingerprint"]
        keys = [
            "words",
            "sentences",
            "mean_sentence_len",
            "cadence_cv",
            "emdash_per_1k",
            "triad_per_1k",
            "sentences_with_moves_pct",
            "antithesis_per_1k",
            "style_marker_count",
            "style_marker_per_1k",
        ]
        line = "  ".join(
            f"{key}={fingerprint[key]}"
            for key in keys
            if key in fingerprint
        )
        print(f"  fingerprint: {line}")
        print(
            f"  policy: {fingerprint['policy_id']} "
            f"(ruleset: {fingerprint['ruleset_id']})"
        )
    return 1 if gate_failed else 0


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
