"""Tests for the `--ref` guard on `step`.

The defect these exist for cost a live walk its coverage claim. An anchor that
matches no heading was accepted in silence: the verdict was written, the note
reached the section report, and the only sign anything was wrong was `next`
saying a task was unjudged in a section whose tasks had all, apparently, been
judged. A judgement that vouches for nothing is worse than no judgement, because
it looks like work.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.runlog import Run, Segment  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _lab_step():
    if "lab_step" in sys.modules:
        return sys.modules["lab_step"]
    spec = importlib.util.spec_from_file_location("lab_step", ROOT / "scripts" / "lab_step.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lab_step"] = module
    spec.loader.exec_module(module)
    return module


def make_run(tmp_path: Path, *, with_outline: bool = True) -> Run:
    run = Run.create(
        tmp_path,
        "Demo Workshop",
        lab={"id": 1},
        instance="inst-1",
        agent="test",
        segments=[Segment(id="s00", title="Setup", anchor="setup")],
    )
    if with_outline:
        heads = [
            {"order": 0, "level": 1, "id": "setup", "text": "Setup", "body": ""},
            {
                "order": 1, "level": 3,
                "id": "1-open-the-microsoft-foundry---overview-page",
                "text": "1. Open the Microsoft Foundry - Overview page",
                "body": "",
            },
        ]
        (run.dir / "outline.json").write_text(
            json.dumps({
                "title": "Demo Workshop",
                "headings": heads,
                "toc": [],
                "links": [],
                "ids": [h["id"] for h in heads],
            }),
            encoding="utf-8",
        )
    return run


def test_a_resolvable_ref_passes(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path)
    assert module.check_ref(run, "1-open-the-microsoft-foundry---overview-page") is None


def test_a_leading_hash_is_tolerated(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path)
    assert module.check_ref(run, "#1-open-the-microsoft-foundry---overview-page") is None


def test_no_ref_is_not_an_error(tmp_path):
    # Most steps carry no reference at all; the guard must be invisible to them.
    module = _lab_step()
    run = make_run(tmp_path)
    assert module.check_ref(run, None) is None
    assert module.check_ref(run, "") is None


def test_an_unresolvable_ref_is_rejected(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path)
    problem = module.check_ref(run, "1-open-the-microsoft-foundry-overview-page")
    assert problem
    assert "matches no heading" in problem


def test_the_rejection_names_the_anchor_that_was_meant(tmp_path):
    # Without this the harness is told only that it was wrong, and the next
    # guess is as likely to be wrong as the first.
    module = _lab_step()
    run = make_run(tmp_path)
    problem = module.check_ref(run, "1-open-the-microsoft-foundry-overview-page")
    assert "1-open-the-microsoft-foundry---overview-page" in problem


def test_the_rejection_says_nothing_was_recorded(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path)
    problem = module.check_ref(run, "totally-unrelated-anchor")
    assert "Nothing was recorded" in problem


def test_a_run_without_a_corpus_does_not_block_the_walk(tmp_path):
    # Absence of evidence is not evidence of a bad reference. A run folder that
    # has no outline yet must not have every judgement refused.
    module = _lab_step()
    run = make_run(tmp_path, with_outline=False)
    assert module.check_ref(run, "anything-at-all") is None


def test_a_corrupt_corpus_does_not_block_the_walk(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path, with_outline=False)
    (run.dir / "outline.json").write_text("{not json", encoding="utf-8")
    assert module.check_ref(run, "anything-at-all") is None


def test_both_recording_paths_check_the_reference():
    # `step` records through two routes -- with a browser attached and without
    # -- and a guard on only one of them is a guard on neither, because the
    # offline route is the one that judges instruction text.
    source = (ROOT / "scripts" / "lab_step.py").read_text(encoding="utf-8")
    assert source.count("check_ref(run, args.ref)") == 2


def test_deviation_recording_preserves_the_existing_judgement_fields(tmp_path):
    module = _lab_step()
    run = make_run(tmp_path)
    args = SimpleNamespace(
        note="The alternate route completed the deployment.",
        deviation="Used Models + endpoints because Overview had no deployment link.",
        verdict="LAB004",
        severity="minor",
        ref="1-open-the-microsoft-foundry---overview-page",
        domain="instruction",
    )

    findings = module.record_judgement(run, "s00", args)

    record = list(run.steps())[-1]
    assert findings == 1
    assert record["deviation"] == args.deviation
    assert record["note"] == args.note
    assert record["instructionRef"] == args.ref
    assert record["verdict"] == "LAB004"
    assert record["severity"] == "minor"
    assert record["domain"] == "instruction"


def test_both_step_paths_share_the_deviation_recorder():
    source = (ROOT / "scripts" / "lab_step.py").read_text(encoding="utf-8")
    assert source.count("record_judgement(run,") == 2
