#!/usr/bin/env python3
"""slop-no-more scanner: three-layer AI-tell detection for prose.

Layer 1 (strings):      lexical tells. Diction memes, boilerplate, wrap-ups.
Layer 2 (moves):        rhetorical moves. Functional patterns that survive
                        paraphrase because the pattern family targets the move's
                        syntactic signature, not a fixed phrase.
Layer 3 (distribution): document-level statistics. Cadence variance, em-dash
                        density, triad density, metadiscourse ratio.

Every scan also emits a fingerprint: per-move rates per 1,000 words plus the
distribution metrics, so a corpus can be profiled and drift can be tracked
over time.

Usage:
  slop scan <path> [<path>...]        full report + verdict
  slop scan <path> --severity high    only high-severity findings
  slop scan <path> --json             machine-readable output
  slop scan <path> --fingerprint      fingerprint vector only (JSON)

A line containing `slop-ignore` (or the legacy `gate-ignore` / `unslop-ignore`)
is skipped. Blockquotes, fenced code, inline backticks, and "quoted spans" are
not linted: quoting a move to discuss it is not performing it.
Exit code = number of high-severity findings (capped at 100), so CI can gate.
"""

import json
import re
import statistics
import sys
from pathlib import Path

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
    "cadence_cv":        (0.40, 0.30, "below", "Sentence lengths are uniform, the single strongest structural tell. Vary on purpose: let one run, stop the next short."),
    "emdash_per_1k":     (3.0, 6.0, "above", "Em-dash density is machine-register. Convert most to commas or periods."),
    "triad_per_1k":      (5.0, 9.0, "above", "Rule-of-three density: too many triadic lists. Break the rhythm: two items, or four, or one."),
    "move_ratio_pct":    (6.0, 10.0, "above", "Metadiscourse inflation: too much text about the text. Cut the framing, keep the content."),
    "antithesis_per_1k": (2.0, 4.0, "above", "Contrast-frame density: the argument leans on staged corrections instead of positive claims."),
    "style_marker_per_1k": (12.0, 24.0, "above", "AI style-word density is high (per the excess-vocabulary literature; see references/moves.md). Replace decorative style words with domain nouns, verbs, and specific mechanisms."),
}

SEV_WEIGHT = {"high": 3.0, "medium": 1.5, "low": 0.5}
SEV_ORDER = {"high": 0, "medium": 1, "low": 2}

IGNORE_TOKENS = ("slop-ignore", "gate-ignore", "unslop-ignore")


def prepare_lines(text):
    """Return (lint_lines, prose_lines). Masks code/quotes; None = skip line."""
    # Mask inline code and double-quoted spans over the WHOLE text first, so a
    # quoted span that wraps across a line break is still skipped (quoting a
    # tell != using it). Newlines are preserved so line numbers stay true.
    def blank(m):
        return re.sub(r"[^\n]", " ", m.group(0))
    text = re.sub(r"`[^`\n]+`", blank, text)
    text = re.sub(r"\"[^\"]{0,300}?\"", blank, text, flags=re.S)
    text = re.sub(r"“[^”]{0,300}?”", blank, text, flags=re.S)

    lint, prose = [], []
    in_fence = False
    for raw in text.splitlines():
        line = raw
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            lint.append(None); prose.append(None)
            continue
        if in_fence or any(tok in line for tok in IGNORE_TOKENS):
            lint.append(None); prose.append(None)
            continue
        if stripped.startswith(">"):
            lint.append(None); prose.append(None)
            continue
        lint.append(line)
        # prose lines exclude structure: headers, tables, list markers kept as text
        if stripped.startswith("#") or stripped.startswith("|"):
            prose.append(None)
        else:
            prose.append(line)
    return lint, prose


def sentences_of(prose_lines):
    text = " ".join(l for l in prose_lines if l)
    text = re.sub(r"\s+", " ", text)
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z\"'“(])", text)
    sents = [p for p in parts if len(p.split()) >= 2]
    return sents


def scan_text(text, name="<text>"):
    """Scan a string. Returns the same report dict as scan_file."""
    lint_lines, prose_lines = prepare_lines(text)
    findings = []

    for lineno, line in enumerate(lint_lines, 1):
        if line is None:
            continue
        for lex_name, pat, sev, fix in LEXICAL:
            for m in re.finditer(pat, line):
                findings.append({
                    "layer": 1, "move": lex_name, "line": lineno,
                    "match": m.group(0), "severity": sev, "fix": fix,
                })
        for move in MOVES:
            if move.get("skip_if") and re.search(move["skip_if"], line, flags=re.IGNORECASE):
                continue
            for pat in move["patterns"]:
                for m in re.finditer(pat, line, flags=0 if pat.startswith("(?m)") else re.IGNORECASE):
                    findings.append({
                        "layer": 2, "move": move["name"], "line": lineno,
                        "match": m.group(0).strip(), "severity": move["severity"],
                        "fix": move["edit_rule"],
                    })

    # dedupe overlapping matches on same line+move
    seen = set()
    deduped = []
    for f in findings:
        key = (f["line"], f["move"], f["match"][:40])
        if key not in seen:
            seen.add(key)
            deduped.append(f)
    findings = deduped

    # ---- Layer 3 ----
    prose_text = " ".join(l for l in prose_lines if l)
    words = re.findall(r"[A-Za-z'’-]+", prose_text)
    n_words = max(len(words), 1)
    sents = sentences_of(prose_lines)
    metrics = {"words": len(words), "sentences": len(sents)}

    if len(sents) >= 8:
        lens = [len(s.split()) for s in sents]
        mean = statistics.mean(lens)
        sd = statistics.pstdev(lens)
        metrics["mean_sentence_len"] = round(mean, 1)
        metrics["cadence_cv"] = round(sd / mean, 3) if mean else 0.0
    metrics["emdash_per_1k"] = round(prose_text.count("—") * 1000 / n_words, 2)
    triads = re.findall(r",\s+[^,.;:\n]{2,50},\s+(?:and|or)\s+", prose_text)
    metrics["triad_per_1k"] = round(len(triads) * 1000 / n_words, 2)
    move_lines = {f["line"] for f in findings if f["layer"] == 2}
    if sents:
        metrics["move_ratio_pct"] = round(100.0 * len(move_lines) / max(len(sents), 1), 1)
    anti = sum(1 for f in findings if f["move"] == "manufactured-antithesis")
    metrics["antithesis_per_1k"] = round(anti * 1000 / n_words, 2)
    style_hits = STYLE_MARKER_RE.findall(prose_text)
    metrics["style_marker_count"] = len(style_hits)
    if len(words) >= 250 or len(style_hits) >= 4:
        metrics["style_marker_per_1k"] = round(len(style_hits) * 1000 / n_words, 2)

    # Rate metrics are meaningless on very short texts: one em dash in a
    # 40-word note is 25 per 1k. Below the floor, rates are still reported in
    # the fingerprint but never converted to findings (same design as the
    # 250-word style-marker guard and the 8-sentence cadence guard).
    RATE_FLOOR_WORDS = 120
    for metric, (med, high, direction, msg) in L3_RULES.items():
        if metric not in metrics:
            continue
        if metrics["words"] < RATE_FLOOR_WORDS and metric != "cadence_cv":
            continue
        v = metrics[metric]
        hit = None
        if direction == "below":
            if v < high: hit = "high"
            elif v < med: hit = "medium"
        else:
            if v > high: hit = "high"
            elif v > med: hit = "medium"
        if hit:
            findings.append({
                "layer": 3, "move": metric, "line": 0,
                "match": f"{metric}={v}", "severity": hit, "fix": msg,
            })

    # ---- fingerprint: per-move rates + metrics ----
    fp = dict(metrics)
    for move in MOVES:
        c = sum(1 for f in findings if f["move"] == move["name"])
        fp[f"mv_{move['name']}_per_1k"] = round(c * 1000 / n_words, 2)

    weight = sum(SEV_WEIGHT[f["severity"]] for f in findings)
    density = round(weight * 1000 / n_words, 2)
    high_n = sum(1 for f in findings if f["severity"] == "high")
    if density < 1.5 and high_n == 0:
        verdict = "clean"
    elif density < 4:
        verdict = "mostly clean"
    elif density < 10:
        verdict = "slop present"
    else:
        verdict = "heavy slop"

    findings.sort(key=lambda f: (SEV_ORDER[f["severity"]], f["layer"], f["line"]))
    return {
        "file": str(name), "verdict": verdict, "density": density,
        "high": high_n, "findings": findings, "fingerprint": fp,
    }


def scan_file(path):
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return scan_text(text, name=path)


def run(argv):
    args = [a for a in argv if not a.startswith("--")]
    flags = {a for a in argv if a.startswith("--")}
    sev_only = "high" if "--severity" in " ".join(argv) and "high" in argv else None
    if not args:
        print(__doc__)
        return 0

    paths = []
    for a in args:
        if a == "high":
            continue
        p = Path(a)
        if p.is_dir():
            for ext in (".md", ".markdown", ".mdx", ".txt", ".rst", ".html"):
                paths.extend(sorted(p.rglob(f"*{ext}")))
        else:
            paths.append(p)

    reports = [scan_file(p) for p in paths]

    if "--fingerprint" in flags:
        print(json.dumps({r["file"]: r["fingerprint"] for r in reports}, indent=2))
        return 0
    if "--json" in flags:
        print(json.dumps(reports, indent=2))
        return min(sum(r["high"] for r in reports), 100)

    total_high = 0
    for r in reports:
        total_high += r["high"]
        print(f"\n{'='*72}\n{r['file']}")
        print(f"verdict: {r['verdict'].upper()}   density: {r['density']} weighted hits / 1k words   high-severity: {r['high']}")
        shown = [f for f in r["findings"] if not sev_only or f["severity"] == sev_only]
        for f in shown:
            loc = f"L{f['line']}" if f["line"] else "doc"
            print(f"  [{f['severity']:<6}] {loc:>5}  ({f['move']})  “{f['match'][:70]}”")
            print(f"           fix: {f['fix']}")
        fp = r["fingerprint"]
        keys = ["words", "sentences", "mean_sentence_len", "cadence_cv",
                "emdash_per_1k", "triad_per_1k", "move_ratio_pct",
                "antithesis_per_1k", "style_marker_count", "style_marker_per_1k"]
        line = "  ".join(f"{k}={fp[k]}" for k in keys if k in fp)
        print(f"  fingerprint: {line}")
    return min(total_high, 100)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1:]))
