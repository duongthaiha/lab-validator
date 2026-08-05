"""Tests for choosing what to walk.

The feature under test is a convenience, and the tests are almost all about the
danger it creates rather than the convenience it delivers. Selecting three of
twenty-three sections is easy; the hard part is that the resulting report must
not read like the other twenty were checked and found fine.

So: a few tests that selection works, and rather more that it refuses, that it
never erases evidence, and that everything downstream counts it honestly.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator import scope  # noqa: E402
from lab_validator.corpus import Heading, Outline  # noqa: E402
from lab_validator.labclient import Credential  # noqa: E402
from lab_validator.report import STATUS_WORD, render  # noqa: E402
from lab_validator.runlog import NOT_SELECTED, Run  # noqa: E402
from lab_validator.vault import Vault  # noqa: E402
from lab_validator.walkloop import describe, next_move  # noqa: E402

CAPTURED_VALUE = "SuperSecret-9c2f4a11-live-and-long"


def make_outline(n: int = 4) -> Outline:
    heads: list[Heading] = []
    order = 0
    for i in range(n):
        heads.append(Heading(order=order, level=1, id=f"lab-{i:02d}", text=f"Lab {i:02d}"))
        order += 1
        heads.append(Heading(order=order, level=3, id=f"l{i}-t0", text="1. Do the thing"))
        order += 1
    return Outline(title="Demo Workshop", headings=heads)


def make_run(tmp_path: Path, n: int = 4) -> tuple[Run, Outline]:
    outline = make_outline(n)
    run = Run.create(
        tmp_path / "runs", "Demo Workshop", instance="i-1", agent="test",
        segments=outline.segments(),
    )
    return run, outline


# ---- parsing: it resolves, or it refuses --------------------------------


def test_all_selects_every_section(tmp_path):
    run, _ = make_run(tmp_path)
    selection = scope.parse("all", run)
    assert len(selection.chosen) == 4
    assert selection.excluded == ()
    assert selection.is_everything


def test_an_unambiguous_prefix_is_enough(tmp_path):
    run, _ = make_run(tmp_path)
    assert scope.parse("s01", run).chosen == ("s01-lab-01",)


def test_a_range_is_inclusive_and_in_lab_order(tmp_path):
    run, _ = make_run(tmp_path)
    assert scope.parse("s01..s03", run).chosen == (
        "s01-lab-01", "s02-lab-02", "s03-lab-03",
    )


def test_a_backwards_range_is_refused_rather_than_reordered(tmp_path):
    """Reversing it for them would silently accept a typo as an instruction."""
    run, _ = make_run(tmp_path)
    with pytest.raises(scope.ScopeError, match="backwards"):
        scope.parse("s03..s01", run)


def test_an_unknown_section_names_the_real_ones(tmp_path):
    """A selection that quietly matched nothing would walk nothing and report
    clean -- the failure shape this whole project exists to catch."""
    run, _ = make_run(tmp_path)
    with pytest.raises(scope.ScopeError) as exc:
        scope.parse("s09", run)
    assert "s00-lab-00" in str(exc.value)


def test_an_ambiguous_prefix_is_refused_not_guessed(tmp_path):
    run, _ = make_run(tmp_path)
    with pytest.raises(scope.ScopeError, match="ambiguous"):
        scope.parse("s", run)


def test_a_hyphen_range_is_told_how_to_write_a_range(tmp_path):
    """Section ids contain hyphens, so ``s01-s03`` cannot mean a range. That is
    defensible and unguessable, so the refusal has to teach it."""
    run, _ = make_run(tmp_path)
    with pytest.raises(scope.ScopeError, match=r"s01\.\.s03"):
        scope.parse("s01-s03", run)


def test_an_empty_expression_is_refused(tmp_path):
    run, _ = make_run(tmp_path)
    for expr in ("", "   ", ",,"):
        with pytest.raises(scope.ScopeError):
            scope.parse(expr, run)


def test_a_half_written_range_is_refused(tmp_path):
    run, _ = make_run(tmp_path)
    with pytest.raises(scope.ScopeError, match="missing an end"):
        scope.parse("s01..", run)


def test_the_expression_and_who_chose_are_both_recorded(tmp_path):
    """'A human picked these' and 'nobody was asked' must stay distinguishable
    in the manifest, or a default will later read as an approval."""
    run, _ = make_run(tmp_path)
    scope.apply(run, scope.parse("s01", run, how="prompt"))
    record = run.manifest["selections"][-1]
    assert record["how"] == "prompt"
    assert record["expression"] == "s01"


# ---- applying: it excludes, and it refuses to un-walk --------------------


def test_unchosen_sections_are_marked_not_selected_not_skipped(tmp_path):
    """``skipped`` already means 'the walker passed over this mid-walk'."""
    run, _ = make_run(tmp_path)
    scope.apply(run, scope.parse("s01", run))
    statuses = {s.id: s.status for s in run.segments()}
    assert statuses["s01-lab-01"] == "pending"
    assert statuses["s00-lab-00"] == NOT_SELECTED
    assert "skipped" not in statuses.values()


def test_a_walked_section_is_never_unwalked_by_a_narrower_scope(tmp_path):
    """The observation is the evidence. Re-scoping may widen a run; it may not
    delete what a previous pass actually saw."""
    run, _ = make_run(tmp_path)
    run.end_segment("s00-lab-00", "done")
    run.end_segment("s02-lab-02", "blocked")

    applied = scope.apply(run, scope.parse("s01", run))

    statuses = {s.id: s.status for s in run.segments()}
    assert statuses["s00-lab-00"] == "done"
    assert statuses["s02-lab-02"] == "blocked"
    assert sorted(applied.refused) == [("s00-lab-00", "done"), ("s02-lab-02", "blocked")]


def test_what_it_refused_is_written_into_the_run(tmp_path):
    run, _ = make_run(tmp_path)
    run.end_segment("s00-lab-00", "done")
    scope.apply(run, scope.parse("s01", run))
    assert run.manifest["selections"][-1]["refused"] == [
        {"id": "s00-lab-00", "status": "done"}
    ]


def test_rescoping_wider_reopens_a_section(tmp_path):
    run, _ = make_run(tmp_path)
    scope.apply(run, scope.parse("s01", run))
    applied = scope.apply(run, scope.parse("all", run))
    assert "s00-lab-00" in applied.reopened
    assert all(s.status == "pending" for s in run.segments())


def test_selections_accumulate_as_a_history(tmp_path):
    """Each decision is evidence about the run, not a setting to overwrite."""
    run, _ = make_run(tmp_path)
    scope.apply(run, scope.parse("s01", run))
    scope.apply(run, scope.parse("s01,s02", run))
    assert len(run.manifest["selections"]) == 2
    assert run.manifest["selections"][0]["expression"] == "s01"


def test_the_summary_describes_the_result_not_the_request(tmp_path):
    """Asking to exclude a walked section does not exclude it, so reporting the
    request would print a count that does not match the folder."""
    run, _ = make_run(tmp_path)
    run.end_segment("s00-lab-00", "done")
    said = scope.apply(run, scope.parse("s01", run)).summary()
    assert "2 not selected" in said
    assert "1 kept as already walked" in said


# ---- the loop honours it -------------------------------------------------


def test_the_loop_never_opens_a_section_nobody_selected(tmp_path):
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s02", run))
    for _ in range(4):
        move = next_move(run, outline)
        if move.action != "open":
            break
        assert move.segment_id == "s02-lab-02"
        run.end_segment(move.segment_id, "done")
    assert move.action == "stop"


def test_the_last_sentence_of_a_scoped_walk_says_what_it_did_not_do(tmp_path):
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s02", run))
    run.end_segment("s02-lab-02", "done")

    why = next_move(run, outline).why

    assert "3 of 4 sections were not selected" in why
    assert "unknown rather than correct" in why


def test_an_unscoped_walk_keeps_its_plain_ending(tmp_path):
    """The scoped wording must not leak into a run that walked everything."""
    run, outline = make_run(tmp_path)
    for seg in run.segments():
        run.end_segment(seg.id, "done")
    why = next_move(run, outline).why
    assert why.startswith("all 4 sections have been walked or accounted for")
    assert "not selected" not in why


def test_unjudged_tasks_are_attributed_to_the_sections_that_were_walked(tmp_path):
    """Word order carries a claim here. Put the not-selected clause first and
    'N task(s) across M of them' comes to mean the sections nobody opened."""
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s02", run))
    run.end_segment("s02-lab-02", "done")

    why = next_move(run, outline).why

    assert "of the sections that were walked" in why
    assert why.index("sections that were walked") < why.index("were not selected")


def test_the_console_does_not_count_unselected_sections_as_accounted_for(tmp_path):
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s02", run))
    run.end_segment("s02-lab-02", "done")

    said = describe(run, outline)

    assert said.startswith("1/1 sections accounted for")
    assert "3 not selected" in said


# ---- the report states its own scope -------------------------------------


def scoped_report(tmp_path) -> str:
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s02", run))
    run.start_segment("s02-lab-02")
    run.step("s02-lab-02", verdict="PASS", action="perform", note="Did the thing.")
    run.end_segment("s02-lab-02", "done")
    return render(run, outline)


def test_a_scoped_report_says_it_is_scoped_next_to_the_verdict(tmp_path):
    body = scoped_report(tmp_path)
    assert "**Scoped run.**" in body
    assert "3 of 4 sections were not selected" in body


def test_a_scoped_report_can_never_claim_the_lab_is_completable(tmp_path):
    """The single most important assertion in this file. A run that walked one
    section of four must not answer the question the whole report asks."""
    body = scoped_report(tmp_path)
    assert "**YES**" not in body


def test_coverage_is_measured_against_what_was_selected(tmp_path):
    body = scoped_report(tmp_path)
    assert "1 of 1 selected sections completed (100%)" in body
    assert "**3 of 4 sections were not selected for this run.**" in body


def test_not_selected_reads_differently_from_skipped_and_never_reached(tmp_path):
    """Three kinds of ignorance with three different causes. Merging any two
    loses the only useful thing either one says.

    Built so all three are true at once, because that is the only arrangement
    that can prove they render as separate claims rather than one sentence
    doing double duty.
    """
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s01,s02,s03", run))       # s04 not selected
    run.end_segment("s01-lab-01", "done")
    run.end_segment("s02-lab-02", "skipped")
    # s03 is left pending: selected, and the walk ran out of road before it.
    body = render(run, outline)

    assert "**1 section was not selected for this run.**" in body
    assert "out of scope, not correct" in body, (
        "the warning must say what an absent section means, or a reader fills "
        "the silence in with 'it was fine'"
    )
    assert "**1 section was never reached.**" in body
    assert "they are unknown, not correct" in body

    assert STATUS_WORD[NOT_SELECTED] != STATUS_WORD["skipped"]
    assert STATUS_WORD[NOT_SELECTED] not in ("", None)
    assert body.index("never reached") < body.index("out of scope"), (
        "two blocks, not one -- if they merge, this ordering collapses"
    )


def test_a_scoped_run_that_ran_out_of_road_says_both_things(tmp_path):
    """A budget failure inside a scoped run is the case most likely to be
    read as 'the scope explains it'. It does not: nobody chose to skip s03."""
    run, outline = make_run(tmp_path)
    scope.apply(run, scope.parse("s01,s02,s03", run))
    run.end_segment("s01-lab-01", "done")
    body = render(run, outline)

    assert "**1 of 4 sections were not selected for this run.**" in body
    assert "**2 sections were never reached.**" in body
    assert "1 of 3 selected sections completed" in body, (
        "coverage counts against the selection, so an interrupted scoped run "
        "still shows the road it did not finish"
    )


def test_an_unscoped_report_is_unchanged(tmp_path):
    run, outline = make_run(tmp_path)
    for seg in run.segments():
        run.end_segment(seg.id, "done")
    body = render(run, outline)
    assert "4 of 4 sections completed (100%)" in body
    assert "not selected" not in body


# ---- the review ----------------------------------------------------------


def with_vault(tmp_path) -> tuple[Run, Outline, Vault]:
    run, outline = make_run(tmp_path)
    vault = Vault.capture(
        [
            Credential(scope="Azure", label="Password", value=CAPTURED_VALUE),
            Credential(scope="Azure", label="Username", value="learner@example.com"),
        ],
        run.redactor,
    )
    return run, outline, vault


def test_the_review_never_writes_a_credential_value(tmp_path):
    """This is a text artefact somebody will paste into a bug. The safe design
    is for the value never to be written, not for it to be masked afterwards --
    masking only covers what the redactor was told about.

    Asserts against the *unscrubbed* render as well as the file. The file goes
    through the redactor, which would hide a leak here and leave this test
    passing for a reason that has nothing to do with what it claims to check.
    """
    run, outline, vault = with_vault(tmp_path)
    path = scope.write_review(run, outline, vault)

    assert CAPTURED_VALUE not in scope.review(run, outline, vault)
    body = path.read_text(encoding="utf-8")
    assert CAPTURED_VALUE not in body
    assert "Password" in body, "the label must still be there, or it is not a review"


def test_the_review_lists_every_section_with_its_task_count(tmp_path):
    run, outline, vault = with_vault(tmp_path)
    body = scope.review(run, outline, vault)
    for seg in run.segments():
        assert seg.id in body
    assert "| 1 |" in body


def test_the_review_says_when_it_cannot_count_tasks(tmp_path):
    """A '?' and a '0' must not look the same. One means 'this section has no
    numbered tasks', the other means 'we could not find the section'."""
    run, _ = make_run(tmp_path)
    body = scope.review(run, None, None)
    assert "No instruction outline available" in body
    assert "| ? |" in body


def test_the_review_states_what_a_scoped_run_cannot_answer(tmp_path):
    run, outline, vault = with_vault(tmp_path)
    assert "can a learner complete this lab?" in scope.review(run, outline, vault)


# ---- deciding who chose --------------------------------------------------


def test_a_flag_is_applied_without_asking(tmp_path, capsys):
    run, outline = make_run(tmp_path)
    applied = scope.select(run, "s01", outline=outline, interactive=False)
    assert applied.selection.how == "flag"
    assert applied.not_selected_now


def test_no_flag_and_no_terminal_walks_everything_and_says_so(tmp_path, capsys):
    """The behaviour this command had before selection existed. Safe, and
    recorded as a default rather than as somebody's decision."""
    run, outline = make_run(tmp_path)
    applied = scope.select(run, None, outline=outline, interactive=False)
    assert applied.selection.how == "default"
    assert applied.not_selected_now == ()
    assert "ALL sections are selected" in capsys.readouterr().out


def test_a_terminal_is_asked_and_its_answer_is_recorded_as_a_choice(tmp_path):
    run, outline = make_run(tmp_path)
    applied = scope.select(
        run, None, outline=outline, interactive=True, reader=lambda _: "s01"
    )
    assert applied.selection.how == "prompt"
    assert applied.selection.chosen == ("s01-lab-01",)


def test_pressing_enter_is_silence_not_a_choice_of_everything(tmp_path, capsys):
    """A bare Enter is the least deliberate keystroke available, and it used to
    commit the most expensive outcome this tool has -- every section of a live
    lab -- filed as though a human had chosen it. Observed live: the prompt took
    an empty stdin and selected all 23 sections of a 96-hour lab."""
    run, outline = make_run(tmp_path)

    with pytest.raises(scope.ScopeError) as exc:
        scope.select(
            run, None, outline=outline, interactive=True, reader=lambda _: ""
        )

    assert "nobody answered" in str(exc.value)
    assert "--sections all" in str(exc.value), "a refusal has to name the way back"
    assert "Say 'all' if you mean all" in capsys.readouterr().out


def test_a_reader_that_never_answers_does_not_spin_forever(tmp_path):
    """`input()` raises at a real EOF, but a piped or stubbed reader can return
    "" on every call. An unbounded re-ask would hang holding a live lab open."""
    calls = []

    def silent(_):
        calls.append(1)
        return ""

    run, outline = make_run(tmp_path)
    with pytest.raises(scope.ScopeError):
        scope.select(run, None, outline=outline, interactive=True, reader=silent)

    assert len(calls) <= scope.BLANK_ANSWER_LIMIT


def test_end_of_input_at_the_prompt_is_refused_not_defaulted(tmp_path):
    """A terminal was detected but nobody is behind it -- an agent harness, a
    pipe, a CI job. That is not a mandate to walk the whole lab."""
    run, outline = make_run(tmp_path)

    def eof(_):
        raise EOFError

    with pytest.raises(scope.ScopeError) as exc:
        scope.select(run, None, outline=outline, interactive=True, reader=eof)

    assert "nobody answered" in str(exc.value)


def test_a_typo_then_a_real_answer_still_lands(tmp_path):
    """Refusing silence must not make the prompt brittle about typos: only
    consecutive blanks count, so a mistake followed by an answer works."""
    run, outline = make_run(tmp_path)
    answers = iter(["", "s99", "", "s01"])

    applied = scope.select(
        run, None, outline=outline, interactive=True, reader=lambda _: next(answers)
    )

    assert applied.selection.chosen == ("s01-lab-01",)


def test_a_bad_answer_is_re_asked_rather_than_fatal(tmp_path, capsys):
    """Losing a captured run to a typo would be an absurd price."""
    run, outline = make_run(tmp_path)
    answers = iter(["s99", "s01"])

    applied = scope.select(
        run, None, outline=outline, interactive=True, reader=lambda _: next(answers)
    )

    assert applied.selection.chosen == ("s01-lab-01",)
    assert "unknown segment" in capsys.readouterr().out


# ---- can a human type what the review just showed them? -------------------
#
# Section ids are not knowable before the lab is launched and segmented, which
# is minutes after the command was typed. So the review's numbers are the only
# handle a person has at the prompt, and every one of them has to work.


def review_rows(run, outline) -> list[tuple[str, str]]:
    """(number, id) for each section row of the review table."""
    rows = []
    for line in scope.review(run, outline, None).split("\n"):
        cells = [c.strip() for c in line.split("|")]
        if len(cells) >= 4 and cells[2].startswith("`s"):
            rows.append((cells[1], cells[2].strip("`")))
    return rows


def test_every_number_the_review_prints_selects_the_row_it_printed_it_on(tmp_path):
    """The defect this replaces was not a refusal but a wrong answer: the table
    numbered rows from 1 while ids number from s00, so the reader of row 5
    (`s04-deploy-models`) typed `s05` and silently walked a different section.

    A property over the whole table rather than a fixed string, because the
    fixed-string version of this test is exactly what passed while the bug
    was live.
    """
    run, outline = make_run(tmp_path, n=12)
    rows = review_rows(run, outline)
    assert len(rows) == 12, "the review must list every section"

    for number, segment_id in rows:
        assert scope.parse(number, run).chosen == (segment_id,), (
            f"the review printed {number!r} beside {segment_id}, so typing "
            f"{number!r} must select that section and no other"
        )


def test_a_bare_number_is_the_number_inside_the_id(tmp_path):
    run, _ = make_run(tmp_path, n=6)
    assert scope.parse("4", run).chosen == ("s04-lab-04",)
    assert scope.parse("04", run).chosen == ("s04-lab-04",)
    assert scope.parse("0", run).chosen == ("s00-lab-00",)


def test_numbers_can_be_listed_and_ranged(tmp_path):
    run, _ = make_run(tmp_path, n=6)
    assert scope.parse("1,4", run).chosen == ("s01-lab-01", "s04-lab-04")
    assert scope.parse("1-3", run).chosen == ("s01-lab-01", "s02-lab-02", "s03-lab-03")
    assert scope.parse("1..3", run).chosen == scope.parse("1-3", run).chosen


def test_a_hyphen_ranges_numbers_but_never_ids(tmp_path):
    """The ambiguity that forced `..` is an id problem, not a range problem:
    ids contain hyphens, bare numbers cannot. Keeping `-` banned for numbers
    would be a rule with no reason behind it -- and `1-3` is what somebody
    reading a numbered list types."""
    run, _ = make_run(tmp_path, n=6)
    assert len(scope.parse("1-3", run).chosen) == 3

    with pytest.raises(scope.ScopeError) as caught:
        scope.parse("s01-s03", run)
    assert "s01..s03" in str(caught.value), "ids still get the '..' hint"


def test_a_number_past_the_end_is_refused_not_clamped(tmp_path):
    run, _ = make_run(tmp_path, n=4)
    with pytest.raises(scope.ScopeError) as caught:
        scope.parse("9", run)
    assert "s09" in str(caught.value), (
        "the refusal should name what it looked for, not the raw digit"
    )


def test_the_prompt_offers_the_numbers_not_only_ids(tmp_path):
    """The help line is the entire interface for somebody who has never run
    this before. Offering only `s01,s04` teaches a syntax they cannot know."""
    assert "'4'" in scope.PROMPT_HELP
    run, outline = make_run(tmp_path)
    assert "# column" in scope.HOW_TO_CHOOSE
    assert "`4`" in scope.review(run, outline, None)