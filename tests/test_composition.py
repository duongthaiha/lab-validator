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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator import cli, walkloop  # noqa: E402
from lab_validator.corpus import Heading, Outline  # noqa: E402
from lab_validator.report import render  # noqa: E402
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

    Note what counts: a *recorded step* that scrolled, not a file on disk.
    Reading is proven by evidence in the trace, because an instruction pane the
    learner cannot scroll is a defect only a real scroll can find.
    """
    run.start_segment(segment.id)
    path = run.dir / walkloop.segment_filename(segment.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("read", encoding="utf-8")
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
