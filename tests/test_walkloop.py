"""Tests for the walk loop.

The loop exists to catch the failure mode of a hand-driven walk: a task quietly
skipped inside a section that then reports clean. So most of these tests are
about *refusing to advance*, which is the only behaviour that can catch it.

There is no browser anywhere in this file, and that is the design working. The
loop reads the run folder and nothing else, so a whole multi-hour walk can be
driven in milliseconds — and, more importantly, a killed walk resumes by asking
the same question again.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.corpus import Heading, Outline  # noqa: E402
from lab_validator.report import segment_filename  # noqa: E402
from lab_validator.runlog import Run, Segment  # noqa: E402
from lab_validator.walkloop import (  # noqa: E402
    RESERVE_MINUTES,
    Move,
    coverage_kind,
    describe,
    next_move,
    task_coverage,
    unjudged_tasks,
)

# ---- fixtures -------------------------------------------------------------
#
# Two sections and, in one of them, two numbered tasks. Small on purpose: every
# assertion below is about a transition, and a bigger corpus would only make the
# arithmetic harder to check by eye.


def make_run(tmp_path: Path) -> Run:
    return Run.create(
        tmp_path,
        "Demo Workshop",
        lab={"id": 1},
        instance="inst-1",
        agent="test",
        segments=[
            Segment(id="s00", title="Setup", anchor="setup"),
            Segment(id="s01", title="Lab 01", anchor="lab-01"),
        ],
    )


def make_outline() -> Outline:
    """An outline whose section 'setup' has two numbered tasks.

    Sections are ``h1`` and tasks are ``h3`` whose text starts with a number —
    that is the corpus's own definition, and the fixture has to honour it or the
    tests would be checking a shape the real parser never produces.
    """
    heads = [
        Heading(order=0, level=1, id="setup", text="Setup"),
        Heading(order=1, level=3, id="task-1", text="1. Create the project"),
        Heading(order=2, level=3, id="task-2", text="2. Deploy a model"),
        Heading(order=3, level=1, id="lab-01", text="Lab 01"),
        Heading(order=4, level=2, id="lab-01-intro", text="Overview"),
    ]
    return Outline(title="Demo Workshop", headings=heads)


def scrolled(run: Run, segment_id: str) -> None:
    """Record the learner-path read that every section needs before work."""
    run.step(segment_id, action="read:600", verdict="PASS", surface="labui")


def judge(run: Run, segment_id: str, ref: str, verdict: str = "PASS") -> None:
    # DEFERRED carries a mandatory justification, enforced by the run log itself.
    note = "not attempted: the section's blocker prevents it" if verdict == "DEFERRED" else None
    run.step(segment_id, verdict=verdict, instruction_ref=f"#{ref}", note=note)


def write_section_report(run: Run, segment_id: str) -> None:
    path = run.dir / segment_filename(segment_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# section", encoding="utf-8")


# ---- the happy path, one transition at a time -----------------------------


def test_a_fresh_run_opens_the_first_section(tmp_path):
    run = make_run(tmp_path)
    move = next_move(run, make_outline())
    assert move.action == "open"
    assert move.segment_id == "s00"


def test_an_open_section_must_be_read_before_it_is_worked(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")

    move = next_move(run, make_outline())

    assert move.action == "read", (
        "reading the pane by API is a bypass; the loop must ask for the learner's "
        "own scroll before it accepts any work in the section"
    )


def test_once_read_the_loop_asks_for_the_unjudged_tasks(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, make_outline())

    assert move.action == "perform"
    assert move.tasks == ["task-1", "task-2"]


def test_the_loop_names_only_the_tasks_still_missing_a_verdict(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")

    move = next_move(run, make_outline())

    assert move.tasks == ["task-2"], "a task already judged must not be asked for again"


def test_a_fully_judged_section_is_reported_before_it_advances(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")
    judge(run, "s00", "task-2")

    move = next_move(run, make_outline())

    assert move.action == "report", (
        "the section report is written as the walk happens, so that an interrupted "
        "run still delivers the sections it finished"
    )


def test_a_reported_section_advances(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")
    judge(run, "s00", "task-2")
    write_section_report(run, "s00")

    assert next_move(run, make_outline()).action == "advance"


def test_the_walk_ends_when_every_section_is_accounted_for(tmp_path):
    run = make_run(tmp_path)
    for seg in ("s00", "s01"):
        run.start_segment(seg)
        run.end_segment(seg, status="done")

    move = next_move(run, make_outline())

    assert move.action == "stop"
    assert move.is_terminal


# ---- refusing to advance: the reason this module exists -------------------


def test_a_section_with_an_unjudged_task_never_reaches_report(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")
    write_section_report(run, "s00")  # a caller trying to skip ahead

    move = next_move(run, make_outline())

    assert move.action == "perform", (
        "writing the report early must not buy an advance — the silently skipped "
        "task inside an apparently clean section is the exact defect being prevented"
    )
    assert move.tasks == ["task-2"]


def test_work_recorded_under_the_wrong_section_does_not_count(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s01", "task-1")  # right task reference, wrong section

    assert unjudged_tasks(run, run.segments()[0], make_outline()) == ["task-1", "task-2"]


def test_a_retracted_verdict_leaves_its_task_unjudged_again(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    step = run.step("s00", verdict="LAB001", instruction_ref="#task-1")
    judge(run, "s00", "task-2")

    run.retract(step["seq"], reason="misread the instruction")

    move = next_move(run, make_outline())
    assert move.tasks == ["task-1"], (
        "withdrawing a judgement must reopen the task; a retracted finding that "
        "still counts as coverage is worse than never having made it"
    )


def test_a_step_with_no_instruction_reference_judges_nothing(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    run.step("s00", verdict="PASS", note="looks fine to me")

    assert unjudged_tasks(run, run.segments()[0], make_outline()) == ["task-1", "task-2"]


# ---- blocked is a status, not an ending -----------------------------------


def test_a_blocked_section_keeps_reading_instead_of_stopping(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1", verdict="BLOCKED")

    move = next_move(run, make_outline())

    assert move.action == "assess", (
        "a blocker is the first finding in a section, not the last; the remaining "
        "tasks still have claims that the text alone can settle"
    )
    assert move.tasks == ["task-2"]
    assert move.detail["blocked"] is True


def test_a_blocked_section_still_has_to_finish_before_it_advances(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1", verdict="BLOCKED")
    judge(run, "s00", "task-2", verdict="DEFERRED")

    assert next_move(run, make_outline()).action == "report"


# ---- the clock ------------------------------------------------------------


def test_the_loop_stops_while_there_is_still_time_to_write_up(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, make_outline(), minutes_remaining=RESERVE_MINUTES)

    assert move.action == "stop"
    assert move.detail["reason"] == "clock"


def test_the_clock_outranks_work_that_is_ready_to_do(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")

    assert next_move(run, make_outline(), minutes_remaining=5).action == "stop", (
        "stopping mid-section leaves it unreported, which is worse than stopping"
    )


def test_plenty_of_clock_changes_nothing(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    assert next_move(run, make_outline(), minutes_remaining=600).action == "perform"


# ---- resumability ---------------------------------------------------------


def test_the_next_move_survives_losing_the_process(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")
    before = next_move(run, make_outline())

    del run
    reopened = Run.open(tmp_path / next(p.name for p in tmp_path.iterdir() if p.is_dir()))
    after = next_move(reopened, make_outline())

    assert (after.action, after.tasks) == (before.action, before.tasks), (
        "the loop keeps its position in the run folder, so resuming a killed walk "
        "is the same call as continuing a live one"
    )


def test_the_loop_terminates_when_driven_to_exhaustion(tmp_path):
    """Drive the whole state machine and prove it cannot spin.

    A loop that can return the same move forever would hang an unattended run
    with no error and no output, which is the least debuggable failure there is.
    """
    run = make_run(tmp_path)
    outline = make_outline()
    seen: list[str] = []

    for _ in range(50):
        move = next_move(run, outline)
        seen.append(str(move))
        if move.is_terminal:
            break
        if move.action == "open":
            run.start_segment(move.segment_id)
        elif move.action == "read":
            scrolled(run, move.segment_id)
        elif move.action in ("perform", "assess"):
            for ref in move.tasks:
                judge(run, move.segment_id, ref)
        elif move.action == "report":
            write_section_report(run, move.segment_id)
        elif move.action == "advance":
            run.end_segment(move.segment_id, status="done")
    else:
        pytest.fail("the loop did not terminate in 50 moves:\n" + "\n".join(seen))

    assert [s.status for s in run.segments()] == ["done", "done"]


# ---- sections the outline knows nothing about -----------------------------


def test_a_section_with_no_numbered_tasks_can_still_complete(tmp_path):
    """Not every section has tasks, and a loop that demands them would deadlock.

    This is the case that would have hung the reference run: prose-only sections
    like an introduction or a summary exist in every workshop.
    """
    run = make_run(tmp_path)
    run.start_segment("s01")  # 'lab-01' has no task headings under it
    scrolled(run, "s01")

    assert next_move(run, make_outline()).action == "report"


def test_without_an_outline_the_loop_cannot_invent_task_coverage(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, None)

    assert move.action == "report", (
        "with no corpus there are no known tasks, so the loop must not pretend to "
        "check for them — it may not invent an expectation"
    )
    assert task_coverage(run, run.segments()[0], None) == ([], [])


# ---- the move itself ------------------------------------------------------


def test_an_unknown_move_is_refused_at_construction(tmp_path):
    with pytest.raises(ValueError):
        Move("wander")


def test_every_move_explains_itself(tmp_path):
    run = make_run(tmp_path)
    outline = make_outline()
    for setup in (
        lambda: None,
        lambda: run.start_segment("s00"),
        lambda: scrolled(run, "s00"),
        lambda: judge(run, "s00", "task-1"),
        lambda: judge(run, "s00", "task-2"),
    ):
        setup()
        move = next_move(run, outline)
        assert move.why, (
            f"move {move.action!r} carries no reason; when a walk stops, the reason "
            "is the most useful thing in the folder"
        )


def test_the_status_line_names_sections_with_unjudged_tasks(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")

    assert "1 task(s) unjudged" in describe(run, make_outline())


def test_the_status_line_names_the_unjudged_task_itself(tmp_path):
    # A count alone leaves the harness to work out *which* anchor is missing by
    # reading the corpus by hand, and a mistyped anchor from that exercise is
    # recorded without complaint. Naming it removes the guess.
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")

    assert "task-2" in describe(run, make_outline())


# ---- "no tasks" and "could not find the tasks" are different answers ------
#
# Both produce an empty task list, so a loop that only counts tasks reports
# them identically: clean. The corpus parser already warns about exactly this
# shape -- an unresolvable anchor "looks like 'nothing to check' instead of
# 'could not resolve'". That misreading is the whole point of these tests.


def test_a_section_whose_anchor_does_not_resolve_is_not_called_complete(tmp_path):
    run = Run.create(
        tmp_path, "Demo", lab={"id": 1}, instance="i", agent="t",
        segments=[Segment(id="s00", title="Setup", anchor="a-heading-that-moved")],
    )
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, make_outline())

    assert move.detail["taskCoverage"] == "unresolved"
    assert "COULD NOT BE ENUMERATED" in move.why, (
        "an anchor that no longer resolves must not be reported the same as a "
        "section that genuinely has no tasks -- one is silence, the other is a fact"
    )


def test_a_section_that_genuinely_has_no_tasks_says_so_differently(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s01")  # 'lab-01' resolves, and has no numbered tasks
    scrolled(run, "s01")

    move = next_move(run, make_outline())

    assert move.detail["taskCoverage"] == "no-tasks"
    assert "COULD NOT BE ENUMERATED" not in move.why


def test_walking_with_no_corpus_at_all_counts_as_unresolved(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    assert next_move(run, None).detail["taskCoverage"] == "unresolved", (
        "with no corpus the loop knows of no tasks; it must not report that as "
        "having checked there were none"
    )


def test_the_status_line_flags_a_section_whose_tasks_could_not_be_found(tmp_path):
    run = Run.create(
        tmp_path, "Demo", lab={"id": 1}, instance="i", agent="t",
        segments=[Segment(id="s00", title="Setup", anchor="gone")],
    )
    run.start_segment("s00")

    assert "TASKS NOT ENUMERABLE" in describe(run, make_outline())


def test_coverage_kind_names_all_three_states(tmp_path):
    outline = make_outline()
    assert coverage_kind(Segment(id="a", title="A", anchor="setup"), outline) == "enumerated"
    assert coverage_kind(Segment(id="b", title="B", anchor="lab-01"), outline) == "no-tasks"
    assert coverage_kind(Segment(id="c", title="C", anchor="gone"), outline) == "unresolved"
    assert coverage_kind(Segment(id="d", title="D"), outline) == "unresolved"


# ---- the livelock the reference run would have caused ---------------------


def test_a_section_reference_is_not_accepted_as_task_coverage(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    run.step("s00", verdict="PASS", instruction_ref="#setup")  # the section, not a task

    move = next_move(run, make_outline())

    assert move.tasks == ["task-1", "task-2"], (
        "accepting a section reference would let one step vouch for every task "
        "under it, which is the hole this module exists to close"
    )


def test_the_loop_says_why_it_keeps_asking_for_the_same_tasks(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    run.step("s00", verdict="PASS", instruction_ref="#setup")

    move = next_move(run, make_outline())

    assert move.detail["misScopedRefs"] is True
    assert "--ref" in move.why, (
        "a loop that asks for the same thing forever with no explanation is the "
        "least debuggable failure there is; it must name the fix"
    )


def test_correctly_scoped_work_raises_no_alarm(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")
    judge(run, "s00", "task-1")

    assert next_move(run, make_outline()).detail["misScopedRefs"] is False


def test_a_completed_run_still_names_tasks_nobody_judged(tmp_path):
    """The last sentence of a run must not read cleaner than the run was.

    A section can reach 'done' under an older bookkeeping convention or via a
    caller that closed it early. Reporting "all sections walked" without saying
    which tasks have no verdict is the misreading this module exists to prevent.
    """
    run = make_run(tmp_path)
    for seg in ("s00", "s01"):
        run.start_segment(seg)
        run.end_segment(seg, status="done")

    move = next_move(run, make_outline())

    assert move.action == "stop"
    assert move.detail["unjudgedTasks"] == {"s00": ["task-1", "task-2"]}
    assert "unknown, not correct" in move.why


def test_a_genuinely_complete_run_is_not_hedged(tmp_path):
    run = make_run(tmp_path)
    for seg in ("s00", "s01"):
        run.start_segment(seg)
        scrolled(run, seg)
    judge(run, "s00", "task-1")
    judge(run, "s00", "task-2")
    for seg in ("s00", "s01"):
        run.end_segment(seg, status="done")

    move = next_move(run, make_outline())

    assert move.detail["unjudgedTasks"] == {}
    assert "unknown, not correct" not in move.why, (
        "a caveat printed on a clean run is noise, and noise is how real caveats "
        "stop being read"
    )


# ---- credential-aware instruction following ------------------------------
#
# Operating by hand, a human reads "sign in with the username from the
# Resources tab" and goes and fetches it. An autonomous walk has to be told,
# and the move that asks for the task is the only place that can tell it.


def outline_with_credential_task() -> Outline:
    return Outline(title="Demo", headings=[
        Heading(order=0, level=1, id="setup", text="Setup"),
        Heading(
            order=1, level=3, id="task-1", text="1. Sign in",
            body="Sign in using the username shown on the Resources tab.",
        ),
        Heading(order=2, level=1, id="lab-01", text="Lab 01"),
    ])


def test_the_move_names_the_credential_the_next_task_wants(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, outline_with_credential_task(), labels={"username": ("cred-1",)})

    assert move.detail["asks"]["task-1"] == ["username -> cred-1"]
    assert move.detail["unsatisfiedAsks"] == []


def test_an_ask_the_lab_never_issued_is_reported_not_swallowed(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, outline_with_credential_task(), labels={"password": ("cred-9",)})

    assert move.detail["unsatisfiedAsks"] == ["username"]
    assert "did not issue" in move.why, (
        "the instruction asks for something the lab never handed out; that is a "
        "setup finding, and a loop that silently skipped it would hide it"
    )


def test_the_move_never_carries_a_credential_value(tmp_path):
    """Moves get printed to consoles and written into manifests.

    Built from a *real* vault holding a *real* value, because the version of
    this test that passes a hand-written label map proves nothing: the secret
    never enters the system, so its absence downstream is guaranteed by the
    fixture rather than by the code. The value has to be in the vault for the
    label index's exclusion of it to mean anything.
    """
    from lab_validator.labclient import Credential
    from lab_validator.vault import Vault

    secret = "S3cr3t-Value-Never-Printed"  # noqa: S105 - a fixture, deliberately fake
    vault = Vault.capture([Credential(scope="VM", label="Username", value=secret)])
    assert secret in {c.value for c in vault.credentials}, "the fixture must hold it"

    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, outline_with_credential_task(), labels=vault.label_index())

    assert move.detail["asks"]["task-1"] == ["username -> VM/Username"]
    assert secret not in repr(move.detail)
    assert secret not in move.why


def test_without_a_vault_the_asks_are_unsatisfied_not_absent(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, outline_with_credential_task())

    assert move.detail["unsatisfiedAsks"] == ["username"], (
        "no captured credentials means nothing can be supplied, which is not the "
        "same as the instruction asking for nothing"
    )


def test_prose_that_asks_for_nothing_produces_no_asks(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    scrolled(run, "s00")

    move = next_move(run, make_outline(), labels={"username": ("cred-1",)})

    assert move.detail["asks"] == {}
    assert "did not issue" not in move.why
