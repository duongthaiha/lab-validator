"""Tests for the per-section report.

Focus: the report is what the lab author reads, and it is written *while* the
walk is happening. So the properties that matter are the honest ones — that an
unfinished section never looks clean, that a withdrawn finding actually
disappears, and that image links resolve from where the file is written.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.report import (  # noqa: E402
    render_segment,
    segment_filename,
    write_segment,
)
from lab_validator.runlog import Run, Segment  # noqa: E402


def make_run(tmp_path: Path) -> Run:
    return Run.create(
        tmp_path,
        "Demo Workshop",
        lab={"id": 1},
        instance="inst-1",
        agent="test",
        segments=[
            Segment(id="s00", title="Setup", module="Required Lab Setup"),
            Segment(id="s01", title="Lab 01"),
        ],
    )


def section(run: Run, segment_id: str) -> Segment:
    return next(s for s in run.segments() if s.id == segment_id)


def test_unfinished_section_does_not_read_as_clean(tmp_path):
    """An in-progress section with no findings must not say "no defects".

    Silence during a walk means "not looked at yet", and a lab author reading
    "no defects recorded" would take the opposite meaning.
    """
    run = make_run(tmp_path)
    run.start_segment("s00")
    text = render_segment(run, section(run, "s00"))
    assert "No defects recorded" not in text
    assert "not finished" in text


def test_finished_section_with_no_findings_says_so(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    run.end_segment("s00", "done")
    text = render_segment(run, section(run, "s00"))
    assert "No defects recorded" in text


def test_only_this_sections_findings_appear(tmp_path):
    run = make_run(tmp_path)
    run.step("s00", verdict="LAB008", severity="major", note="setup step missing")
    run.step("s01", verdict="LAB001", severity="critical", note="model retired")
    text = render_segment(run, section(run, "s00"))
    assert "setup step missing" in text
    assert "model retired" not in text


def test_retracted_finding_disappears(tmp_path):
    """Rendering from the trace each time is what makes withdrawal work.

    A report accumulated as the walk went would need an erratum instead.
    """
    run = make_run(tmp_path)
    rec = run.step("s00", verdict="LAB001", severity="major", note="wrongly blamed the model")
    before = render_segment(run, section(run, "s00"))
    assert "wrongly blamed the model" in before

    run.retract(rec["seq"], "second attempt succeeded; it was a transient")
    after = render_segment(run, section(run, "s00"))
    assert "### 1." not in after
    assert "Withdrawn findings" in after
    assert "second attempt succeeded" in after


def test_image_links_resolve_from_the_sections_folder(tmp_path):
    """The report sits one level below the run root, so links need to climb."""
    run = make_run(tmp_path)
    run.step("s00", verdict="LAB003", severity="minor", note="label changed",
             images=["images/0001-s00-shot.jpg"])
    path = write_segment(run, section(run, "s00"))

    assert path == run.dir / segment_filename("s00")
    text = path.read_text(encoding="utf-8")
    assert "(../images/0001-s00-shot.jpg)" in text
    target = (path.parent / "../images/0001-s00-shot.jpg").resolve()
    assert target == (run.dir / "images" / "0001-s00-shot.jpg").resolve()


def test_mechanical_notes_are_not_counted_as_verifications(tmp_path):
    """Driving a step emits its own notes; they are not confirmations.

    ``settled after 7s`` and ``42 chars`` are trace bookkeeping. Listing them
    under "Verified correct" would credit the run with checks nobody made.
    """
    run = make_run(tmp_path)
    run.step("s00", verdict="PASS", surface="probe", note="settled after 7s")
    run.step("s00", verdict="PASS", surface="vm", note="42 chars")
    run.step("s00", verdict="PASS", surface="analysis",
             note="Deploy button is labelled 'Deploy model' exactly as written")
    text = render_segment(run, section(run, "s00"))
    body = text.split("## Verified correct")[1]
    assert "Deploy button is labelled" in body
    assert "settled after 7s" not in body
    assert "42 chars" not in body


def test_verified_correct_is_honest_when_nothing_was_judged(tmp_path):
    run = make_run(tmp_path)
    run.step("s00", verdict="PASS", surface="probe", note="settled after 3s")
    text = render_segment(run, section(run, "s00"))
    assert "_No explicit confirmations recorded in this section._" in text


def test_heartbeats_are_counted_not_listed(tmp_path):
    """Heartbeats prove liveness during a long wait; they are not steps."""
    run = make_run(tmp_path)
    run.step("s00", verdict="PASS", note="started the scan")
    run.heartbeat("s00", operation="scan", elapsed_s=30.0)
    run.heartbeat("s00", operation="scan", elapsed_s=60.0)
    text = render_segment(run, section(run, "s00"))
    assert "2 heartbeat(s)" in text
    assert "1 recorded step(s)" in text


def test_writing_is_idempotent(tmp_path):
    run = make_run(tmp_path)
    run.step("s00", verdict="PASS", note="checked")
    first = write_segment(run, section(run, "s00")).read_text(encoding="utf-8")
    second = write_segment(run, section(run, "s00")).read_text(encoding="utf-8")
    assert first == second
