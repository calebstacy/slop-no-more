"""Fixture tests: every move family fires on a known costume and stays quiet
on plain prose. Masking, escape hatches, verdicts, and the repo's own docs
(dogfood) are covered at the bottom."""

from pathlib import Path

import pytest

import slop_no_more.scanner as scanner
from slop_no_more.scanner import (
    IGNORE_TOKENS,
    L3_RULES,
    MAX_FILE_BYTES,
    MOVES,
    RULESET_ID,
    SCANNER_VERSION,
    _ruleset_payload,
    run,
    scan_file,
    scan_text,
)
from slop_no_more.cli import main as cli_main

REPO = Path(__file__).resolve().parent.parent

# move-name -> a sentence wearing a known costume  # slop-ignore
POSITIVE = {
    "cataphoric-evaluation": "It is important to note that the cache is stale.",
    "anaphoric-evaluation": "It failed with novices, which is the only test that counted.",
    "unanchored-quantifier": "Both taught the same skill. Both were legible.",
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
    "heading-afterbeat": "# Language systems, built on shipped product.",
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


# The afterbeat move keys on a shape that legitimate headings also wear, so its
# boundary is pinned in both directions rather than left to the general fixtures.
AFTERBEAT_FIRES = [
    "# Language, measured.",                                # single participle tag
    "# The rail, redrawn.",                                 # irregular -wn participle
    "# A five-job content model, decided before there was an interface.",
    "# Teaching and poetry, then product design.",          # sequel tag
    "# Four things, and the last one is the point.",        # meta-claim tag
    "# Four rules, and the strings that came out of them.", # counted heading + tag
    "# The practice, in order",                             # prepositional label tag
]

AFTERBEAT_QUIET = [
    # -en is not a participle suffix: op|en, oft|en, ev|en, t|en
    "Published research, open dependencies",
    # body sentences run past heading length even when a participle follows the comma
    "Hypotheses that survive contact with shipped behaviour, run with research and data partners.",
    "Completion, return, and retention, measured against the curriculum it replaced.",
    # a real restriction in the second beat is information, not cadence
    "Social, but only in relation to VR",
    # three beats is a list, not the two-beat lockup
    "It shipped, it was tested, and it went onstage.",
    "Standards, schemas, and checks.",
    # owned by other moves; this one must not double-fire
    "Considered, not shipped.",
    "Four places, one through-line.",
    "Meta, 2024",
]


@pytest.mark.parametrize("text", AFTERBEAT_FIRES)
def test_afterbeat_fires(text):
    assert "heading-afterbeat" in moves_found(text), f"missed: {text!r}"


@pytest.mark.parametrize("text", AFTERBEAT_QUIET)
def test_afterbeat_stays_quiet(text):
    assert "heading-afterbeat" not in moves_found(text), f"false positive: {text!r}"


def test_afterbeat_only_scans_explicit_markdown_headings():
    body = (
        "Technical writing describes real, documented interfaces, then "
        "explains what each one guarantees."
    )
    assert "heading-afterbeat" not in moves_found(body)
    assert "heading-afterbeat" in moves_found(
        "# Technical interfaces, then guarantees."
    )


# The specimen that produced both moves, and the rewrite its author wrote by ear.
# The instrument has to agree with the ear in both directions or it is not calibrated.
SPECIMEN = (
    "Both taught the same skill. Both were legible. Neither survived contact "
    "with somebody who had never held a controller, which is the only test that counted."
)
SPECIMEN_REPAIRED = (
    "Both approaches taught the same skill and were legible, but neither survived "
    "contact with someone who was new to a VR controller."
)


def test_specimen_fires_both_moves():
    found = moves_found(SPECIMEN)
    assert "anaphoric-evaluation" in found
    assert "unanchored-quantifier" in found


def test_hand_repair_of_specimen_is_clean():
    report = scan_text(SPECIMEN_REPAIRED)
    layer12 = [f for f in report["findings"] if f["layer"] in (1, 2)]
    assert not layer12, f"the hand repair should scan clean: {layer12}"


ANAPHORIC_QUIET = [
    # a relative clause that adds content is not an evaluation of the clause it trails
    "It failed with novices, which is documented in the appendix.",
    "The gate held, which is why we shipped on Tuesday.",
    "I cut the clause, which the reviewer had flagged.",
    # the same claim stated rather than appended
    "The only test that counted was the one with novices.",
]

QUANTIFIER_QUIET = [
    SPECIMEN_REPAIRED,
    "Both prototypes shipped in March.",
    "Neither of the two builds passed. The third did.",
    # the quantifier carries its own noun, so nothing is unanchored
    "Neither the naive prompt nor the published guide is a straw man here. "
    "Both are close to what a team would actually ship.",
    "Both of the runs finished. Both of them agreed.",
]


@pytest.mark.parametrize("text", ANAPHORIC_QUIET)
def test_anaphoric_stays_quiet(text):
    assert "anaphoric-evaluation" not in moves_found(text), f"false positive: {text!r}"


@pytest.mark.parametrize("text", QUANTIFIER_QUIET)
def test_quantifier_stays_quiet(text):
    assert "unanchored-quantifier" not in moves_found(text), f"false positive: {text!r}"


def test_quoted_specimens_are_masked():
    assert not moves_found('The reviewer wrote "let that sink in" on the draft.')


def test_backticks_are_masked():
    assert not moves_found("Grep for `most teams` in the corpus.")


def test_matching_multi_backtick_inline_code_is_masked():
    text = "The literal is ``Most teams use this.`` in the example."
    report = scan_text(text)
    assert "phantom-population" not in {
        finding["move"] for finding in report["findings"]
    }
    assert report["fingerprint"]["words"] == 6


def test_fenced_code_is_masked():
    text = "```\nMost teams have a thin answer.\nLet that sink in.\n```\n"
    assert not moves_found(text)


def test_fence_closer_must_match_opener_marker_and_length():
    text = (
        "```text\n"
        "plain code\n"
        "~~~\n"
        "Most teams use this.\n"
        "```\n"
    )
    report = scan_text(text)
    assert not report["findings"]
    assert report["fingerprint"]["words"] == 0


def test_fence_closer_may_be_longer_and_indented_three_spaces():
    text = (
        "  ~~~\n"
        "Most teams use this.\n"
        "   ~~~~\n"
        "The cache is stale.\n"
    )
    report = scan_text(text)
    assert "phantom-population" not in {
        finding["move"] for finding in report["findings"]
    }
    assert report["fingerprint"]["words"] == 4


def test_blockquotes_are_masked():
    assert not moves_found("> Let that sink in.")


def test_only_explicit_blockquote_lines_are_masked():
    text = "> The quoted paragraph begins here\nMost teams use this."
    assert "phantom-population" in moves_found(text)


def test_ignore_token_skips_line():
    report = scan_text("Most teams love this pattern. slop-ignore")
    assert not report["findings"]
    assert report["ignored_lines"] == [
        {"line": 1, "tokens": ["slop-ignore"]}
    ]
    assert report["fingerprint"]["ignored_line_count"] == 1
    assert report["fingerprint"]["ignored_lines"] == report["ignored_lines"]


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


def test_hard_wrapping_cannot_evade_patterns_and_keeps_source_lines():
    report = scan_text(
        "It is important to\nnote that the cache is stale.\n"
        "I hope\nthis helps."
    )
    by_move = {finding["move"]: finding for finding in report["findings"]}
    assert by_move["cataphoric-evaluation"]["line"] == 1
    assert by_move["cataphoric-evaluation"]["end_line"] == 2
    assert by_move["trailing-offer"]["line"] == 3
    assert by_move["trailing-offer"]["end_line"] == 4


@pytest.mark.parametrize(
    "text",
    [
        "i hope THIS helps.",
        "I HOPE This Helps.",
        "in CONCLUSION, the gate held.",
    ],
)
def test_lexical_rules_match_canonical_case_variants(text):
    assert moves_found(text)


def test_sentence_move_percentage_is_formatting_invariant():
    unwrapped = (
        "Most teams have a thin answer. The cache is stale. "
        "Let that sink in. I shipped the patch."
    )
    wrapped = (
        "Most teams\nhave a thin answer. The cache\nis stale. "
        "Let that\nsink in. I shipped\nthe patch."
    )
    first = scan_text(unwrapped)["fingerprint"]
    second = scan_text(wrapped)["fingerprint"]
    assert first["sentences_with_moves_pct"] == 50.0
    assert second["sentences_with_moves_pct"] == 50.0
    assert "move_ratio_pct" not in first


def test_short_copy_medium_finding_is_not_heavy_slop():
    report = scan_text("Moreover, the cache was stale.")
    assert report["severity_counts"]["medium"] == 1
    assert report["verdict"] == "mostly clean"


@pytest.mark.parametrize(
    "text",
    [
        'The reviewer wrote "let that sink in" in a very long '
        + '"'
        + ("quoted passage " * 40)
        + 'most teams have a thin answer."',
        "The reviewer wrote “let that sink in across\n"
        + ("many wrapped words " * 30)
        + "most teams have a thin answer.”",
        "The reviewer wrote ‘let that sink in’ on the draft.",
        "The reviewer wrote 'let that sink in' on the draft.",
    ],
)
def test_supported_quoted_spans_are_masked_without_length_cap(text):
    assert not moves_found(text)


def test_apostrophes_are_not_treated_as_quote_delimiters():
    assert "cataphoric-evaluation" in moves_found(
        "The writer's note says it is important to note that the cache is stale."
    )


def test_citation_suppression_is_claim_local():
    report = scan_text(
        "Research shows readers skim (Nielsen 1997). "
        "Research shows writers scan."
    )
    findings = [
        finding
        for finding in report["findings"]
        if finding["move"] == "anonymous-authority"
    ]
    assert len(findings) == 1
    assert findings[0]["match"].lower() == "research shows"


def test_citation_suppression_keeps_abbreviated_source_in_claim():
    assert "anonymous-authority" not in moves_found(
        "Research shows readers skim (Nielsen et al. 1997)."
    )


def test_soft_wrapped_citation_suppresses_the_continuous_claim():
    report = scan_text(
        "Research shows that readers skim\n(Nielsen et al. 1997)."
    )
    assert "anonymous-authority" not in {
        finding["move"] for finding in report["findings"]
    }


def test_same_text_twice_on_one_line_is_two_occurrences():
    findings = [
        finding
        for finding in scan_text(
            "Let that sink in. Let that sink in."
        )["findings"]
        if finding["move"] == "endophoric-command"
    ]
    assert len(findings) == 2
    assert findings[0]["column"] != findings[1]["column"]


def test_many_repeated_occurrences_remain_distinct():
    repeat_count = 5000
    findings = [
        finding
        for finding in scan_text(
            " ".join(["Let that sink in."] * repeat_count)
        )["findings"]
        if finding["move"] == "endophoric-command"
    ]
    assert len(findings) == repeat_count


def test_word_count_excludes_punctuation_only_hyphens():
    fingerprint = scan_text("--- Alpha - beta --")["fingerprint"]
    assert fingerprint["words"] == 2


@pytest.mark.parametrize(
    "text",
    [
        "'don't let that sink in'",
        "‘don’t let that sink in’",
    ],
)
def test_single_quoted_spans_with_contractions_are_fully_masked(text):
    assert not moves_found(text)


@pytest.mark.parametrize(
    "heading",
    [
        "# Language, measured.",
        " # Language, measured.",
        "  ## Language, measured.",
        "   ### Language, measured.",
    ],
)
def test_valid_atx_headings_are_structural_and_scanned(heading):
    report = scan_text(heading)
    assert "heading-afterbeat" in {
        finding["move"] for finding in report["findings"]
    }
    assert report["fingerprint"]["words"] == 0
    assert report["density"] is None


@pytest.mark.parametrize(
    "not_heading",
    [
        "#NoSpace Language, measured.",
        "    # Language, measured.",
        "####### Language, measured.",
    ],
)
def test_invalid_atx_forms_are_not_treated_as_headings(not_heading):
    report = scan_text(not_heading)
    assert "heading-afterbeat" not in {
        finding["move"] for finding in report["findings"]
    }
    assert report["fingerprint"]["words"] > 0


def test_hash_starting_prose_remains_in_distribution_metrics():
    report = scan_text("#NoSpace is still ordinary prose.")
    assert report["fingerprint"]["words"] == 5
    assert report["fingerprint"]["sentences"] == 1


def test_soft_wrap_does_not_create_an_anchored_command():
    report = scan_text(
        "XX It is important to\nnote that the cache is stale."
    )
    found = {finding["move"] for finding in report["findings"]}
    assert "cataphoric-evaluation" in found
    assert "endophoric-command" not in found


def test_soft_wrap_does_not_create_a_transition_opening():
    report = scan_text(
        "We changed the cache and\nMoreover, updated the tests."
    )
    assert "transition-turnstile" not in {
        finding["move"] for finding in report["findings"]
    }


def test_list_item_body_is_a_logical_anchored_block():
    findings = scan_text("- Moreover, the cache is stale.")["findings"]
    transition = next(
        finding
        for finding in findings
        if finding["move"] == "transition-turnstile"
    )
    assert transition["line"] == 1
    assert transition["column"] == 3


def test_twenty_item_markdown_list_keeps_sentence_rate_below_gate():
    suffixes = (
        "",
        " after review",
        " after the weekly review",
        " after the editor checked the cited source",
        " after the editor checked the source and logged the date",
        " once the owner compared the draft with the signed decision record",
        " when the reviewer found the matching issue in the archived release notes",
    )
    items = [
        "- It will enhance clarity and empower teams through careful review today."
    ]
    items.extend(
        f"- Item {index} records one concrete change{suffixes[(index - 2) % len(suffixes)]}."
        for index in range(2, 21)
    )
    report = scan_text("\n".join(items))
    fingerprint = report["fingerprint"]
    assert fingerprint["words"] > 120
    assert fingerprint["sentences"] == 20
    assert fingerprint["sentences_with_moves_pct"] == 5.0
    assert not [
        finding
        for finding in report["findings"]
        if finding["move"] == "sentences_with_moves_pct"
    ]
    assert report["high"] == 0, [
        (finding["move"], finding["match"])
        for finding in report["findings"]
        if finding["severity"] == "high"
    ]


def test_lowercase_sentence_start_is_counted():
    report = scan_text("The cache failed. it recovered slowly.")
    assert report["fingerprint"]["sentences"] == 2


def test_initialism_inside_sentence_does_not_split_sentence():
    report = scan_text(
        "I served in the U.S. Army. Then I wrote the guide."
    )
    assert report["fingerprint"]["sentences"] == 2


def test_structural_only_findings_have_no_fabricated_rate_denominator():
    for text, move in (
        ("# Language, measured.", "heading-afterbeat"),
        ("| Most teams use this. |", "phantom-population"),
    ):
        report = scan_text(text)
        assert move in {
            finding["move"] for finding in report["findings"]
        }
        assert report["fingerprint"]["words"] == 0
        assert report["fingerprint"][f"mv_{move}_per_1k"] is None
        assert report["density"] is None


def test_disable_rule_is_validated_and_changes_effective_policy():
    enabled = scan_text("Let that sink in.")
    disabled = scan_text(
        "Let that sink in.", disabled_rules=["endophoric-command"]
    )
    assert "endophoric-command" in moves_found("Let that sink in.")
    assert not disabled["findings"]
    assert enabled["fingerprint"]["ruleset_id"] == RULESET_ID
    assert enabled["fingerprint"]["scanner_version"] == SCANNER_VERSION
    assert disabled["fingerprint"]["ruleset_id"] == RULESET_ID
    assert (
        enabled["fingerprint"]["policy_id"]
        != disabled["fingerprint"]["policy_id"]
    )
    assert disabled["fingerprint"]["disabled_rules"] == [
        "endophoric-command"
    ]
    with pytest.raises(ValueError, match="unknown rule"):
        scan_text("Plain text.", disabled_rules=["does-not-exist"])


def test_clean_always_means_zero_findings_on_long_copy():
    text = ("The cache is stale. " * 2000) + "Moreover, the log is stale."
    report = scan_text(text, disabled_rules=L3_RULES)
    assert report["density"] < 1.5
    assert report["severity_counts"]["medium"] == 1
    assert report["verdict"] == "mostly clean"


def test_every_distribution_rule_is_skipped_below_rate_floor():
    report = scan_text(
        "Cats run. Dogs run. Birds fly. Fish swim. "
        "Bats fly. Bees buzz. Ants work. Owls hunt."
    )
    assert not [
        finding for finding in report["findings"] if finding["layer"] == 3
    ]


def test_ruleset_payload_covers_repairs_ignores_and_engine_policy():
    payload = _ruleset_payload()
    ignore_policy = payload["engine"]["ignore_policy"]
    assert ignore_policy["tokens"] == IGNORE_TOKENS
    assert ignore_policy["reporting"] == "line number and matched token"
    assert payload["engine"]["short_verdict_policy"]["floor_words"] == 120
    assert all(rule["fix"] for rule in payload["lexical"])
    assert all(move["definition"] for move in payload["moves"])
    assert all(move["edit_rule"] for move in payload["moves"])


def test_package_and_scanner_versions_stay_in_sync():
    pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{SCANNER_VERSION}"' in pyproject


def test_cli_usage_unknown_option_and_input_errors_are_distinct(
    tmp_path, capsys
):
    assert run([]) == 2
    assert run(["--does-not-exist", "draft.md"]) == 2
    assert run([str(tmp_path / "missing.md")]) == 3
    unsupported = tmp_path / "draft.html"
    unsupported.write_text("<p>Most teams</p>", encoding="utf-8")
    assert run([str(unsupported)]) == 3
    captured = capsys.readouterr()
    assert "usage:" in captured.err
    assert "input error:" in captured.err


def test_installed_cli_rejects_unknown_subcommands(capsys):
    assert cli_main(["lint", "draft.md"]) == 2
    assert "unknown command" in capsys.readouterr().err


def test_cli_gate_contract_and_output_modes(tmp_path, capsys):
    high = tmp_path / "high.md"
    high.write_text("Let that sink in.", encoding="utf-8")
    medium = tmp_path / "medium.md"
    medium.write_text("Moreover, the cache is stale.", encoding="utf-8")

    assert run([str(high), "--fingerprint"]) == 1
    fingerprint_output = capsys.readouterr().out
    assert '"mode": "fingerprint"' in fingerprint_output
    assert '"gate_failed": true' in fingerprint_output

    assert run([str(high), "--fingerprint", "--fail-on", "never"]) == 0
    assert '"gate_failed": false' in capsys.readouterr().out

    assert run([str(medium), "--json"]) == 0
    assert '"gate_failed": false' in capsys.readouterr().out
    assert run([str(medium), "--json", "--fail-on", "medium"]) == 1
    assert '"gate_failed": true' in capsys.readouterr().out


def test_cli_reports_inline_ignore_exceptions_in_every_output_mode(
    tmp_path, capsys
):
    path = tmp_path / "ignored.md"
    path.write_text(
        "Most teams use this. slop-ignore", encoding="utf-8"
    )

    assert run([str(path)]) == 0
    human_output = capsys.readouterr().out
    assert "ignored lines: L1 (slop-ignore)" in human_output
    assert f"scanner: {SCANNER_VERSION}" in human_output

    assert run([str(path), "--json"]) == 0
    json_output = capsys.readouterr().out
    assert '"ignored_lines": [' in json_output
    assert '"line": 1' in json_output
    assert '"slop-ignore"' in json_output

    assert run([str(path), "--fingerprint"]) == 0
    fingerprint_output = capsys.readouterr().out
    assert '"ignored_line_count": 1' in fingerprint_output
    assert '"ignored_lines": [' in fingerprint_output


def test_cli_disable_is_repeatable_and_unknown_rule_is_usage_error(
    tmp_path, capsys
):
    path = tmp_path / "draft.md"
    path.write_text(
        "Let that sink in. Moreover, the cache is stale.", encoding="utf-8"
    )
    assert (
        run(
            [
                str(path),
                "--disable",
                "endophoric-command",
                "--disable",
                "transition-turnstile",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "gate: PASS" in output
    assert run([str(path), "--disable", "made-up-rule"]) == 2
    assert "unknown rule" in capsys.readouterr().err


def test_directory_discovery_only_scans_supported_prose_files(
    tmp_path, capsys
):
    (tmp_path / "draft.md").write_text("The cache is stale.", encoding="utf-8")
    (tmp_path / "page.html").write_text(
        "Let that sink in.", encoding="utf-8"
    )
    assert run([str(tmp_path), "--json"]) == 0
    output = capsys.readouterr().out
    assert "draft.md" in output
    assert "page.html" not in output


def test_directory_discovery_does_not_follow_file_symlinks(
    tmp_path, monkeypatch, capsys
):
    scan_root = tmp_path / "scan"
    scan_root.mkdir()
    local = scan_root / "local.md"
    local.write_text("The cache is stale.", encoding="utf-8")
    link = scan_root / "linked.md"
    link.write_text("Let that sink in.", encoding="utf-8")
    monkeypatch.setattr(
        Path, "is_symlink", lambda path: path.name == "linked.md"
    )

    assert run([str(scan_root), "--json"]) == 0
    output = capsys.readouterr().out
    assert "local.md" in output
    assert "linked.md" not in output


def test_file_size_limit_accepts_boundary_and_rejects_one_byte_over(
    tmp_path, capsys
):
    boundary = tmp_path / "boundary.txt"
    boundary.write_bytes(b"a" * MAX_FILE_BYTES)
    assert scan_file(boundary)["fingerprint"]["words"] == 1
    too_large = tmp_path / "too-large.txt"
    too_large.write_bytes(b"a" * (MAX_FILE_BYTES + 1))
    with pytest.raises(OSError, match="exceeds"):
        scan_file(too_large)
    assert run([str(too_large)]) == 3
    assert f"{MAX_FILE_BYTES} byte limit" in capsys.readouterr().err


def test_directory_scan_rejects_too_many_input_files(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.setattr(scanner, "MAX_INPUT_FILES", 2)
    for index in range(3):
        (tmp_path / f"{index}.txt").write_text(
            "The cache is stale.", encoding="utf-8"
        )
    assert run([str(tmp_path)]) == 3
    assert "2 file limit" in capsys.readouterr().err


def test_scan_rejects_aggregate_input_bytes(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(scanner, "MAX_TOTAL_BYTES", 5)
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_bytes(b"abc")
    second.write_bytes(b"def")
    assert run([str(first), str(second)]) == 3
    assert "5 aggregate byte limit" in capsys.readouterr().err


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
