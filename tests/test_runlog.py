"""Tests for the run log.

Focus: a run folder is *evidence*. It has to stay readable after the code that
wrote it has moved on, so the tests that matter here are the ones about reading
older manifests and about recording progress when the lab is gone.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.runlog import Run, Segment  # noqa: E402


def test_segment_reads_legacy_line_keys():
    """``start_line``/``end_line`` were renamed once they were found to hold
    heading ordinals. Runs written before that must still load."""
    seg = Segment.from_dict(
        {"id": "s00", "title": "Setup", "start_line": 4, "end_line": 16, "status": "done"}
    )
    assert seg.start_heading == 4
    assert seg.end_heading == 16
    assert seg.status == "done"


def test_segment_ignores_keys_it_does_not_know():
    """Forward compatibility, the other direction: a newer writer's extra field
    must not make an older reader crash."""
    seg = Segment.from_dict({"id": "s00", "title": "Setup", "invented_later": True})
    assert seg.id == "s00"


def test_new_keys_take_precedence_over_legacy():
    seg = Segment.from_dict(
        {"id": "s00", "title": "S", "start_line": 1, "start_heading": 9, "end_line": 2}
    )
    assert seg.start_heading == 9


def make_run(tmp_path: Path) -> Run:
    return Run.create(
        tmp_path,
        "Demo Workshop",
        lab={"id": 1},
        instance="inst-1",
        agent="test",
        segments=[Segment(id="s00", title="Setup"), Segment(id="s01", title="Lab 01")],
    )


def test_run_round_trips_a_legacy_manifest(tmp_path):
    run = make_run(tmp_path)
    # Rewrite the manifest the way an older version would have.
    for seg in run.manifest["segments"]:
        seg["start_line"] = 4
        seg["end_line"] = 16
    run._save()

    reopened = Run.open(run.dir)
    segments = reopened.segments()
    assert [s.id for s in segments] == ["s00", "s01"]
    assert all(s.start_heading == 4 for s in segments)


def test_segment_transitions_record_without_a_lab_clock(tmp_path):
    """The clock is optional. A checkpoint must land even when the lab has
    disappeared -- that is exactly when an honest record matters."""
    run = make_run(tmp_path)
    run.start_segment("s00", None)
    run.end_segment("s00", "done", None)

    reopened = Run.open(run.dir)
    seg = reopened.segment("s00")
    assert seg["status"] == "done"
    assert "lab_minutes_at_end" not in seg


def test_retracted_findings_do_not_stand(tmp_path):
    run = make_run(tmp_path)
    rec = run.step("s00", verdict="LAB004", severity="major", note="claimed defect")
    assert len(run.findings()) == 1

    run.retract(rec["seq"], "evidence was a scrolled terminal, not the whole file")
    assert run.findings() == []
    assert rec["seq"] in run.retracted()


def test_trace_is_append_only(tmp_path):
    run = make_run(tmp_path)
    run.step("s00", note="one")
    run.step("s00", note="two")
    lines = [
        json.loads(line)
        for line in (run.dir / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert [r["seq"] for r in lines] == [1, 2]
