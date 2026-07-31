"""Tests for the verdict taxonomy.

Focus: the taxonomy is the *public interface* of the whole capability. It
previously lived in three places that disagreed -- ``runlog`` accepted
``LAB009``, ``report`` had no name for it, and no document defined it -- so 40
findings rendered as a bare code with no name. These tests exist so that
particular failure cannot recur silently: adding a code without documenting it
fails here rather than degrading a report nobody re-reads.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator import runlog, taxonomy  # noqa: E402
from lab_validator.report import CODE_NAMES as REPORT_CODE_NAMES  # noqa: E402
from lab_validator.runlog import Run, Segment  # noqa: E402


def make_run(tmp_path: Path) -> Run:
    return Run.create(
        tmp_path,
        "Demo Workshop",
        lab={"id": 1},
        instance="inst-1",
        agent="test",
        segments=[Segment(id="s00", title="Setup")],
    )


def test_every_finding_code_is_fully_documented() -> None:
    """The guard. A finding code with no name renders as a bare code; with no
    definition nobody can tell whether it was applied correctly."""
    assert taxonomy.undocumented_codes(taxonomy.FINDING_VERDICTS) == set()


def test_every_verdict_has_a_name_including_non_findings() -> None:
    """``report`` falls back to the raw code, so a missing name is silent."""
    missing = [c for c in taxonomy.VERDICTS if c not in taxonomy.CODE_NAMES]
    assert missing == []


def test_lab009_is_named() -> None:
    """The specific regression: LAB009 was accepted by the writer and nameless
    in the reader, and 40 findings rendered as ``LAB009 -- LAB009``."""
    assert "LAB009" in taxonomy.FINDING_VERDICTS
    assert taxonomy.name_of("LAB009") == "Defective sample code"
    assert taxonomy.name_of("LAB009") != "LAB009"


def test_writer_and_reader_share_one_taxonomy() -> None:
    """The drift that caused the bug was two private copies. Assert identity,
    not equality: equal-but-separate dicts drift apart again."""
    assert runlog.VERDICTS is taxonomy.VERDICTS
    assert runlog.FINDING_VERDICTS is taxonomy.FINDING_VERDICTS
    assert REPORT_CODE_NAMES is taxonomy.CODE_NAMES


def test_finding_set_is_derived_not_hardcoded() -> None:
    assert taxonomy.FINDING_VERDICTS == frozenset(
        v.code for v in taxonomy._VERDICTS if v.is_finding
    )
    assert "PASS" not in taxonomy.FINDING_VERDICTS
    assert "LAB000" not in taxonomy.FINDING_VERDICTS, "a transient is not a defect"
    assert "BLOCKED" not in taxonomy.FINDING_VERDICTS, "blocked is a status, not a finding"


def test_undocumented_codes_actually_detects_a_gap() -> None:
    """A guard that cannot fail is not a guard."""
    assert taxonomy.undocumented_codes({"LAB999"}) == {"LAB999"}


def test_a_finding_defaults_to_undetermined_domain(tmp_path: Path) -> None:
    """Never guess which side is at fault. An unattributed finding is honest;
    a wrongly attributed one is rejected by its owner and then dies."""
    run = make_run(tmp_path)
    rec = run.step("s00", verdict="LAB002", severity="major", note="no such resource")
    assert rec["domain"] == "undetermined"


def test_a_finding_can_state_its_domain(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    rec = run.step("s00", verdict="LAB009", severity="major", note="wrong .env", domain="setup")
    assert rec["domain"] == "setup"


def test_non_findings_carry_no_domain(tmp_path: Path) -> None:
    """A screenshot has no side at fault."""
    run = make_run(tmp_path)
    rec = run.step("s00", action="click:1,2")
    assert "domain" not in rec


def test_an_unknown_domain_is_refused(tmp_path: Path) -> None:
    run = make_run(tmp_path)
    with pytest.raises(ValueError, match="unknown domain"):
        run.step("s00", verdict="LAB001", domain="whose-fault-anyway")


def test_domains_are_the_three_we_reason_about() -> None:
    assert taxonomy.DOMAINS == ("instruction", "setup", "undetermined")


@pytest.mark.parametrize("code", sorted(taxonomy.FINDING_VERDICTS))
def test_every_finding_declares_where_the_fault_usually_lies(code: str) -> None:
    """``either`` is allowed and honest -- it means the code genuinely falls
    both ways, so the domain must always be established per finding."""
    assert taxonomy.BY_CODE[code].typical_domain in (*taxonomy.DOMAINS, "either")
