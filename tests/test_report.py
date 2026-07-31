"""Tests for the per-section report.

Focus: the report is what the lab author reads, and it is written *while* the
walk is happening. So the properties that matter are the honest ones — that an
unfinished section never looks clean, that a withdrawn finding actually
disappears, and that image links resolve from where the file is written.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.report import (  # noqa: E402
    completability,
    render,
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
    assert "Withdrawn judgements" in after
    assert "second attempt succeeded" in after


def test_retracted_confirmation_stops_claiming_verification(tmp_path):
    """A wrong PASS must be withdrawable too.

    A confirmation asserts "this instruction was checked and matched reality".
    Getting that wrong is worse than a spurious finding, because a lab author
    reading it has no reason to look again. Retraction has to reach it.
    """
    run = make_run(tmp_path)
    rec = run.step(
        "s00",
        verdict="PASS",
        surface="analysis",
        note="the lab gives no time estimate",
    )
    assert "no time estimate" in render_segment(run, section(run, "s00"))

    run.retract(rec["seq"], "line 25 does state an estimate; I misread the corpus")
    after = render_segment(run, section(run, "s00"))
    assert "no time estimate" not in after
    assert "line 25 does state an estimate" in after


def test_mechanical_steps_cannot_be_retracted(tmp_path):
    """A click asserts nothing, so there is nothing to withdraw."""
    run = make_run(tmp_path)
    rec = run.step("s00", action="click:1,2", surface="vision")
    with pytest.raises(ValueError):
        run.retract(rec["seq"], "changed my mind")


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


# --- the headline question -------------------------------------------------
#
# "Can a learner complete this lab" is the reason anyone opens the report. It
# used to live in prose ("two structural defects gate the entire workshop") --
# true, well argued, and unreadable by anything but a human.


def test_a_blocked_section_means_the_lab_cannot_be_completed():
    verdict = completability([], [{"verdict": "BLOCKED", "seq": 3, "note": "no quota"}],
                             all_walked=True)
    assert verdict.verdict == "no"
    assert verdict.blockers[0]["note"] == "no quota"


def test_a_critical_finding_gates_the_lab():
    verdict = completability([{"verdict": "LAB001", "severity": "critical", "seq": 9}], [],
                             all_walked=True)
    assert verdict.verdict == "no"


def test_deferred_is_not_a_blocker():
    """DEFERRED records that the walker chose to come back later. That is a
    fact about the walk, not about the lab."""
    verdict = completability([], [{"verdict": "DEFERRED", "seq": 2, "note": "slow, retry"}],
                             all_walked=True)
    assert verdict.verdict == "yes"
    assert verdict.blockers == []


def test_major_findings_mean_partially():
    verdict = completability([{"verdict": "LAB003", "severity": "major", "seq": 1}], [],
                             all_walked=True)
    assert verdict.verdict == "partially"


def test_an_unfinished_walk_never_claims_yes():
    """Unreached content is unknown, not correct."""
    assert completability([], [], all_walked=False).verdict == "unknown"
    assert completability([], [], all_walked=True).verdict == "yes"


def test_blockers_are_reported_before_coverage(tmp_path):
    """A run that found the lab unusable has found the most important thing
    there is to find. It must not read as a run that failed to finish."""
    run = make_run(tmp_path)
    run.start_segment("s00")
    run.step("s00", verdict="BLOCKED", note="deployment quota is zero in every region")
    run.end_segment("s00", "blocked")
    text = render(run)
    assert "## Blockers" in text
    assert "deployment quota is zero" in text
    assert text.index("## Blockers") < text.index("## Coverage")
    assert text.index("Can a learner complete this lab?") < text.index("## Blockers")


def test_the_section_report_answers_completability(tmp_path):
    run = make_run(tmp_path)
    run.start_segment("s00")
    run.step("s00", verdict="BLOCKED", note="the portal never loaded")
    text = render_segment(run, section(run, "s00"))
    assert "Can a learner finish this section?" in text
    assert "**NO**" in text
    assert "## Blockers" in text


# --- routing by domain -----------------------------------------------------


def test_findings_are_routed_to_the_owner_who_can_fix_them(tmp_path):
    """An instruction defect is edited by the lab author; a setup defect is
    fixed by whoever owns the image. Sending one to the other gets it
    correctly rejected, and then it dies."""
    run = make_run(tmp_path)
    run.step("s00", verdict="LAB003", severity="major", domain="instruction",
             note="the blade is now called 'Deployments + endpoints'")
    run.step("s00", verdict="LAB009", severity="major", domain="setup",
             note="the shipped .env points at an operation URL")
    text = render_segment(run, section(run, "s00"))
    routing = text.split("### Who fixes what")[1].split("### 1.")[0]
    assert "lab author" in routing
    assert "lab profile / image / subscription owner" in routing
    assert routing.index("subscription owner") < routing.index("lab author"), (
        "setup defects go first -- they do not announce themselves"
    )


def test_an_unattributed_finding_says_so_rather_than_guessing(tmp_path):
    run = make_run(tmp_path)
    run.step("s00", verdict="LAB002", severity="major", note="no such resource group")
    text = render_segment(run, section(run, "s00"))
    assert "*At fault:* undetermined" in text
    assert "Unattributed" in text


def test_numbering_is_stable_across_domains(tmp_path):
    """Routing must not re-order the findings: a finding that changes number
    between runs cannot be tracked."""
    run = make_run(tmp_path)
    run.step("s00", verdict="LAB001", severity="critical", domain="instruction",
             note="first by severity")
    run.step("s00", verdict="LAB009", severity="minor", domain="setup", note="last by severity")
    text = render_segment(run, section(run, "s00"))
    assert text.index("first by severity") < text.index("last by severity")
    assert "**#1**" in text.split("### Who fixes what")[1]



# ---- coverage the section table cannot express ---------------------------
#
# Both of these publish an *absence*: routes we did not take, and checks we
# could not make. A report that omits them reads cleaner than the run was.


def test_the_report_admits_which_learner_controls_went_untested(tmp_path):
    from lab_validator.learnerpath import Ledger

    run = make_run(tmp_path)
    ledger = Ledger.load(run.dir)
    ledger.record_action("page")  # the bypass: read instructions without scrolling
    ledger.save(run.dir)

    out = render(run)

    assert "scroll_instructions" in out, (
        "the walk read instructions by a route the learner does not have, and the "
        "report did not say so"
    )


def test_a_covered_bypass_is_not_reported_as_a_hole(tmp_path):
    from lab_validator.learnerpath import Ledger

    run = make_run(tmp_path)
    ledger = Ledger.load(run.dir)
    ledger.record_action("page")
    ledger.record_action("read")  # the learner's own path through the pane
    ledger.save(run.dir)

    out = render(run)

    assert "scroll_instructions" not in out, (
        "the control channel was exercised, so claiming it is untested is a false alarm"
    )


def test_the_report_repeats_what_the_preflight_could_not_check(tmp_path):
    run = make_run(tmp_path)
    run.manifest["preflight"] = {
        "unchecked": ["model identity behind each deployment name"],
    }

    out = render(run)

    assert "model identity behind each deployment name" in out, (
        "a passing preflight must never be readable as 'the setup is correct'"
    )
