"""Fixture tests: every move family fires on a known costume and stays quiet
on plain prose. Masking, escape hatches, verdicts, and the repo's own docs
(dogfood) are covered at the bottom."""

from pathlib import Path

import pytest

from slop_no_more.scanner import scan_text, scan_file, MOVES

REPO = Path(__file__).resolve().parent.parent

# move-name -> a sentence wearing a known costume  # slop-ignore
POSITIVE = {
    "cataphoric-evaluation": "It is important to note that the cache is stale.",
    "manufactured-antithesis": "This is not about speed, it's about trust.",
    "phantom-population": "Most teams have a thin answer for this.",
    "invented-adversary": "Skeptics might argue that the data is cherry-picked.",
    "endophoric-command": "Let that sink in.",
    "counterfeit-idiom": "It was a smell I could point at.",
    "hollow-pivot": "And it worked.",
    "dramatized-frame": "I spent a week interrogating Claude about tone.",
    "unanchored-we": "We built the pipeline in a weekend.",
    "borrowed-inference": "If the ear can be automated, it can be pointed at bigger things.",
    "false-collaboration": "Let's unpack this.",
    "gatekeeper-test": "Ask yourself whether the rule is enforceable.",
    "clean-dichotomy": "There are two kinds of style guides.",
    "empty-emphasis": "The real waste is the review time.",
    "phantom-bargain": "The model promises you a fluent draft.",
    "count-contrast-lockup": "Three jobs, one system.",
    "anonymous-authority": "Research shows that readers skim.",
    "hedge-cloud": "It may possibly indicate a trend that could matter.",
    "transition-turnstile": "Moreover, the cache is stale.",
    "template-roadmap": "This essay explores the nature of tone.",
    "coverage-sweep": "It covers everything from onboarding flows to error states today.",
    "sterile-balance": "The tool presents both benefits and risks.",
    "benefit-cascade": "It will enhance clarity and empower teams going forward.",
}

NEGATIVE = [
    "The cache is stale.",
    "I rewrote the error message and shipped it Tuesday.",
    "The button label is four words long.",
    "Nielsen's 1997 eye-tracking study found that readers skim.",
]

LEXICAL_POSITIVE = {
    "assistant-boilerplate": "As an AI language model, I cannot browse the web.",
    "trailing-offer": "I hope this helps!",
    "in-conclusion": "In conclusion, the gate held.",
    "diction-meme": "The team will delve into the details.",
    "the-gap": "That is the gap between what teams say and what ships.",
    "stock-idiom": "The linter does the heavy lifting.",
    "deep-dive": "A deep dive into error copy.",
    "hollow-opener": "In today's fast-paced world, copy matters.",
}


def moves_found(text):
    return {f["move"] for f in scan_text(text)["findings"]}


@pytest.mark.parametrize("move,specimen", sorted(POSITIVE.items()))
def test_move_fires_on_costume(move, specimen):
    assert move in moves_found(specimen), f"{move} missed: {specimen!r}"


@pytest.mark.parametrize("lex,specimen", sorted(LEXICAL_POSITIVE.items()))
def test_lexical_fires(lex, specimen):
    assert lex in moves_found(specimen), f"{lex} missed: {specimen!r}"


@pytest.mark.parametrize("text", NEGATIVE)
def test_plain_prose_is_quiet(text):
    report = scan_text(text)
    layer12 = [f for f in report["findings"] if f["layer"] in (1, 2)]
    assert not layer12, f"false positives on {text!r}: {layer12}"


def test_every_move_has_a_positive_fixture():
    assert set(POSITIVE) == {m["name"] for m in MOVES}


def test_quoted_specimens_are_masked():
    assert not moves_found('The reviewer wrote "let that sink in" on the draft.')


def test_backticks_are_masked():
    assert not moves_found("Grep for `most teams` in the corpus.")


def test_fenced_code_is_masked():
    text = "```\nMost teams have a thin answer.\nLet that sink in.\n```\n"
    assert not moves_found(text)


def test_blockquotes_are_masked():
    assert not moves_found("> Let that sink in.")


def test_ignore_token_skips_line():
    assert not moves_found("Most teams love this pattern. slop-ignore")


def test_launch_post_catch_2026_07_23():
    # the scanner passed this line in the project's own launch-post draft;
    # a human ear caught it; the costume joined the cataphoric family
    assert "cataphoric-evaluation" in moves_found(
        "Moves are the layer worth policing, because moves generate claims.")


def test_wild_catch_costumes_2026_07_23():
    # first wild specimen (a LinkedIn collaborative article) taught these
    assert "transition-turnstile" in moves_found(
        "Remote work saves money. Furthermore, it reduces commuting.")
    assert "template-roadmap" in moves_found(
        "Read on to explore the advantages of remote teamwork.")
    assert "cataphoric-evaluation" in moves_found(
        "Here are some tips to consider before you start.")
    assert "diction-meme" in moves_found(
        "Teams can leverage the diversity of their members.")


def test_source_suppresses_anonymous_authority():
    text = "Research shows that readers skim (Nielsen 1997)."
    assert "anonymous-authority" not in moves_found(text)


def test_clean_verdict_on_clean_text():
    text = (
        "The button label was four words long. I cut it to two after the "
        "usability session, where the tester read it aloud twice. Shipping "
        "took a day. The support tickets about that screen stopped within "
        "the week, and the localization team confirmed the shorter string "
        "fit every locale. Then I archived the old copy. The record of the "
        "decision lives in the changelog with the test notes attached. "
        "Nothing about the process was clever. It was maintenance."
    )
    assert scan_text(text)["verdict"] == "clean"


def test_slop_verdict_and_exit_signal_on_sloppy_text():
    text = " ".join(POSITIVE.values())
    report = scan_text(text)
    assert report["verdict"] in ("slop present", "heavy slop")
    assert report["high"] > 0


def test_fingerprint_has_move_rates():
    fp = scan_text("The cache is stale.")["fingerprint"]
    for m in MOVES:
        assert f"mv_{m['name']}_per_1k" in fp


def test_scan_file_roundtrip(tmp_path):
    p = tmp_path / "draft.md"
    p.write_text("Most teams have a thin answer for this.", encoding="utf-8")
    report = scan_file(p)
    assert report["high"] >= 1


# ---- dogfood: the repo's own prose passes its own gate ----

@pytest.mark.parametrize("doc", [
    "README.md", "SKILL.md", "examples/side-by-side.md",
    "examples/from-the-wild.md",
])
def test_dogfood_docs_scan_clean(doc):
    report = scan_file(REPO / doc)
    assert report["high"] == 0, [
        (f["move"], f["match"]) for f in report["findings"] if f["severity"] == "high"
    ]
