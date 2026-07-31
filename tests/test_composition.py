"""Does the packaged capability actually compose?

Every part of the walk is unit-tested in isolation, and that is exactly the
condition under which a seam can be broken while every test stays green: the
loop reads a field the recorder never writes, the report counts something the
loop names differently, and nothing notices until a real run has burned an hour
of a live lab that cannot be re-run cheaply.

So this file exercises the actual chain -- what ``walk`` writes, what ``next``
decides, what ``step`` records, what ``run --report`` renders -- through the
real APIs, with no browser. It asserts about the *joins* rather than the parts.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator import cli, scope, walkloop  # noqa: E402
from lab_validator.corpus import Heading, Outline  # noqa: E402
from lab_validator.report import render, write_segment  # noqa: E402
from lab_validator.runlog import Run, Segment  # noqa: E402

BODY = """# Sign in
### 1. Open the portal
Go to portal.azure.com.
### 2. Deploy the model
Deploy `gpt-4o`.
"""


def _walked_run(tmp_path):
    """Exactly the shape ``walk`` leaves behind: a run, a corpus, and the
    parsed outline saved *into the run* rather than only beside it."""
    md = tmp_path / "outline.md"
    md.write_text(BODY, encoding="utf-8")
    outline = Outline(title="Demo Lab", headings=[
        Heading(order=0, level=1, id="sign-in", text="Sign in"),
        Heading(order=1, level=3, id="1-open-the-portal", text="1. Open the portal"),
        Heading(order=2, level=3, id="2-deploy-the-model", text="2. Deploy the model"),
    ])
    segment = Segment(id="s01", title="Sign in", anchor="sign-in")
    run = Run.create(
        tmp_path / "runs", "Demo Lab", lab={"id": 1}, instance="i", agent="test",
        corpus=md, segments=[segment],
    )
    outline.save(run.dir / "outline.json")
    return run, segment


def _opened(run, segment):
    """Start the section and read it the way the loop insists on.

    Note what counts: a *recorded step* that scrolled. Reading is proven by
    evidence in the trace, because an instruction pane the learner cannot
    scroll is a defect only a real scroll can find. Nothing here writes
    ``sections/<id>.md`` -- that path is the section *report*, and conflating
    "I read it" with "I reported it" is how a section advances unreported.
    """
    run.start_segment(segment.id)
    run.step(segment.id, verdict="PASS", action="read",
             capability="scroll_instructions", note="Scrolled the pane to the end.")


def test_the_loop_reads_what_the_walk_wrote(tmp_path):
    """The first join: `next` must find the outline `walk` saved, without
    being handed it."""
    run, _ = _walked_run(tmp_path)

    outline, why = cli._outline_for(run)

    assert why == "", why
    assert [h.id for h in outline.tasks(outline.sections()[0])] == [
        "1-open-the-portal", "2-deploy-the-model",
    ]


def test_a_fresh_run_is_told_to_open_the_first_section(tmp_path):
    run, _ = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)

    move = walkloop.next_move(run, outline)

    assert move.action == "open"
    assert move.segment_id == "s01"


def test_a_step_recorded_by_the_documented_call_counts_as_coverage(tmp_path):
    """The join that matters most, and the one most likely to rot silently.

    `step` writes `instructionRef`; the loop counts coverage by matching it
    against task anchors. If either side renames or re-cases that field the
    loop keeps asking for tasks that were already judged, forever, with no
    error -- so this asserts the two halves still agree.
    """
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _opened(run, segment)

    run.step("s01", verdict="PASS", instruction_ref="1-open-the-portal",
             action="click", note="The portal opened.")

    judged, unjudged = walkloop.task_coverage(run, segment, outline)
    assert judged == ["1-open-the-portal"]
    assert unjudged == ["2-deploy-the-model"], (
        "one task judged, one outstanding -- if this is empty the loop would "
        "advance past work nobody did"
    )


def test_the_loop_will_not_advance_while_a_task_is_unjudged(tmp_path):
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _opened(run, segment)
    run.step("s01", verdict="PASS", instruction_ref="1-open-the-portal", action="click")

    move = walkloop.next_move(run, outline)

    assert move.action in {"perform", "assess"}
    assert "2-deploy-the-model" in move.tasks


def test_a_finding_recorded_during_the_walk_reaches_the_report(tmp_path):
    """The last join. A finding that the loop accepted but the report drops is
    a defect the run paid for and then threw away."""
    run, segment = _walked_run(tmp_path)
    _opened(run, segment)
    run.step("s01", verdict="PASS", instruction_ref="1-open-the-portal")
    run.step("s01", verdict="LAB001", instruction_ref="2-deploy-the-model",
             domain="instruction", severity="major",
             note="The portal offers no gpt-4o; the model list ends at gpt-4.1.")
    run.end_segment("s01", "done")

    text = render(run)

    assert "LAB001" in text
    assert "gpt-4o" in text, "the evidence, not just the code"
    assert "instruction" in text.lower(), "the report must say who fixes it"


def test_the_report_admits_a_task_nobody_judged(tmp_path):
    """A section can be marked done with a task outstanding -- an operator can
    always overrule the loop. The report must not then read clean."""
    run, segment = _walked_run(tmp_path)
    _opened(run, segment)
    run.step("s01", verdict="PASS", instruction_ref="1-open-the-portal")
    run.end_segment("s01", "done")

    outline, _ = cli._outline_for(run)
    _, unjudged = walkloop.task_coverage(run, segment, outline)

    assert unjudged == ["2-deploy-the-model"], (
        "the run folder still knows, even though the section says done -- "
        "which is what lets the report tell the truth about coverage"
    )


# --- is the section report current, or merely present? ---------------------


def _both_tasks_judged(run, segment):
    _opened(run, segment)
    run.step(segment.id, verdict="PASS", instruction_ref="1-open-the-portal")
    run.step(segment.id, verdict="PASS", instruction_ref="2-deploy-the-model")


def test_a_section_with_every_task_judged_is_asked_to_report(tmp_path):
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _both_tasks_judged(run, segment)

    move = walkloop.next_move(run, outline)

    assert move.action == "report", (
        "an unreported section must not advance -- an interrupted run would "
        "then have walked it and delivered nothing about it"
    )


def test_a_current_report_lets_the_section_advance(tmp_path):
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _both_tasks_judged(run, segment)

    write_segment(run, segment, outline)

    assert walkloop.next_move(run, outline).action == "advance"


def test_a_finding_recorded_after_the_report_reopens_it(tmp_path):
    """The failure this catches is silent and permanent: the report on disk
    reads clean while the trace beside it holds a defect nobody rendered."""
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _both_tasks_judged(run, segment)
    write_segment(run, segment, outline)

    run.step(segment.id, verdict="LAB001", instruction_ref="2-deploy-the-model",
             domain="instruction", note="Re-checked: the model list ends at gpt-4.1.")

    move = walkloop.next_move(run, outline)
    assert move.action == "report", "the report predates a finding and must be rewritten"


def test_a_run_from_an_older_version_is_still_readable(tmp_path):
    """Run folders are evidence and outlive the code that wrote them. A run
    with no `reported_through` recorded must not be forced to re-report; that
    would rewrite sealed evidence to satisfy a newer bookkeeping field."""
    run, segment = _walked_run(tmp_path)
    outline, _ = cli._outline_for(run)
    _both_tasks_judged(run, segment)
    path = run.dir / walkloop.segment_filename(segment.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# s01\nWritten by an older version.\n", encoding="utf-8")

    assert run.segment("s01").get("reported_through") is None
    assert walkloop.next_move(run, outline).action == "advance"


# --- does a selection survive the whole chain? -----------------------------


def _two_section_run(tmp_path):
    """Two sections, so that scoping to one leaves something unwalked."""
    md = tmp_path / "outline.md"
    md.write_text(BODY + "\n# Clean up\n### 1. Delete the group\nDelete it.\n",
                  encoding="utf-8")
    outline = Outline(title="Demo Lab", headings=[
        Heading(order=0, level=1, id="sign-in", text="Sign in"),
        Heading(order=1, level=3, id="1-open-the-portal", text="1. Open the portal"),
        Heading(order=2, level=3, id="2-deploy-the-model", text="2. Deploy the model"),
        Heading(order=3, level=1, id="clean-up", text="Clean up"),
        Heading(order=4, level=3, id="1-delete-the-group", text="1. Delete the group"),
    ])
    run = Run.create(
        tmp_path / "runs", "Demo Lab", lab={"id": 1}, instance="i", agent="test",
        corpus=md, segments=outline.segments(),
    )
    outline.save(run.dir / "outline.json")
    return run, outline


def test_a_selection_survives_from_scope_through_next_to_the_report(tmp_path):
    """The join this feature lives or dies on. Selection is written by one
    module, obeyed by a second and counted by a third, and each of them is
    unit-tested against its own idea of what an excluded section looks like."""
    run, outline = _two_section_run(tmp_path)
    chosen = run.segments()[0].id
    other = run.segments()[1].id

    scope.select(run, chosen, outline=outline, interactive=False)

    reopened = Run.open(run.dir)
    move = walkloop.next_move(reopened, outline)
    assert move.action == "open" and move.segment_id == chosen

    reopened.end_segment(chosen, "done")
    assert walkloop.next_move(reopened, outline).action == "stop"

    body = render(Run.open(run.dir), outline)
    assert "1 of 2 sections were not selected for this run." in body
    assert "**YES**" not in body, (
        "one of two sections walked cannot answer whether the lab is completable"
    )
    assert other in {s.id for s in Run.open(run.dir).segments()
                     if s.status == "not_selected"}


def test_the_run_folder_alone_carries_the_selection(tmp_path):
    """A multi-hour walk gets interrupted. If the scope lived in memory or in a
    flag, resuming would quietly widen it back to everything."""
    run, outline = _two_section_run(tmp_path)
    scope.select(run, run.segments()[0].id, outline=outline, interactive=False)

    resumed = Run.open(run.dir)

    assert [s.status for s in resumed.segments()] == ["pending", "not_selected"]
    assert resumed.manifest["selections"][-1]["how"] == "flag"

# --- pointing --run at the folder of folders -------------------------------


def test_a_runs_root_passed_as_a_run_is_refused_by_name(tmp_path, capsys):
    """`--run` and `--runs` sit next to each other and mean opposite things, so
    this is the mistake people actually make. It used to exit with a traceback,
    which reads as a crash rather than as a typo."""
    run, _ = _two_section_run(tmp_path)
    root = run.dir.parent

    code = cli.cmd_scope(argparse.Namespace(run=str(root), runs=None, sections=None))

    assert code == 2
    err = capsys.readouterr().err
    assert "looks like a runs root" in err
    assert run.dir.name in err, "naming the candidate is the whole point of refusing"


def test_the_same_refusal_serves_next(tmp_path, capsys):
    """Two commands, one mistake. Different wording for the same error would
    read as two different problems."""
    run, _ = _two_section_run(tmp_path)

    code = cli.cmd_next(argparse.Namespace(run=str(run.dir.parent), runs=None))

    assert code == 2
    assert "looks like a runs root" in capsys.readouterr().err


def test_a_real_run_folder_still_opens(tmp_path):
    """The refusal must not fire on the path that works."""
    run, _ = _two_section_run(tmp_path)
    assert cli.cmd_scope(
        argparse.Namespace(run=str(run.dir), runs=None, sections=None)
    ) == 0

# --- the prompt must not freeze the loop that owns the browser -------------


def test_the_selection_prompt_does_not_block_the_event_loop():
    """`walk` asks which sections to walk while holding a live Playwright
    connection to the launched lab. A person reading a 23-row review takes
    minutes, and a coroutine that blocks services no websocket for all of it.

    Every other test injects a reader, so none of them has ever held the loop.
    """
    ticks = 0

    async def scenario():
        nonlocal ticks

        async def heartbeat():
            nonlocal ticks
            while True:
                await asyncio.sleep(0.01)
                ticks += 1

        beat = asyncio.ensure_future(heartbeat())
        try:
            answer = await cli._select_off_the_loop(_slow_input)
        finally:
            beat.cancel()
        return answer

    assert asyncio.run(scenario()) == "s01"
    assert ticks > 5, (
        f"the loop ran {ticks} times while the prompt waited -- it was frozen, "
        "and a real browser connection would have gone unserviced"
    )


def _slow_input():
    time.sleep(0.3)
    return "s01"


def test_a_failure_at_the_prompt_reaches_the_caller():
    """A helper that swallowed the error would leave `walk` reporting success
    for a selection nobody made."""

    def boom():
        raise RuntimeError("stdin exploded")

    async def scenario():
        return await cli._select_off_the_loop(boom)

    with pytest.raises(RuntimeError, match="stdin exploded"):
        asyncio.run(scenario())