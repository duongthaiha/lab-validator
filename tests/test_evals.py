"""Guards on the eval set.

Evals are graded by a model reading prose, which means nothing here fails
loudly on its own: a test case that points at a deleted fixture, or a fixture
using a verdict code that no longer exists, still *runs*. It just quietly stops
measuring the thing it was written to measure, and the grade it produces looks
exactly like a real one. These are the checks that would otherwise be nobody's
job.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator import taxonomy  # noqa: E402

EVALS = ROOT / "evals" / "evals.json"
FIXTURE = ROOT / "evals" / "files" / "drifted-walk"


def load() -> dict:
    return json.loads(EVALS.read_text(encoding="utf-8"))


def cases() -> list[dict]:
    return load()["evals"]


def test_the_eval_set_parses():
    data = load()
    assert data["evals"], "an empty eval set silently reports nothing"


def test_the_eval_set_names_this_skill():
    """A harness picks the skill by this name; a stale one evaluates nothing."""
    frontmatter = (ROOT / "SKILL.md").read_text(encoding="utf-8").split("---", 2)[1]
    declared = re.search(r"^name:\s*(\S+)", frontmatter, re.M)
    assert declared and load()["skill_name"] == declared.group(1)


@pytest.mark.parametrize("field", ["prompt", "expected_output"])
def test_every_case_says_what_it_asks_and_what_success_is(field):
    for case in cases():
        assert case.get(field, "").strip(), f"eval {case['id']} has no {field}"


def test_case_identifiers_are_unique():
    """Results are filed per case; a collision overwrites one arm with another."""
    ids = [case["id"] for case in cases()]
    names = [case["name"] for case in cases()]
    assert len(set(ids)) == len(ids), ids
    assert len(set(names)) == len(names), names
    for name in names:
        assert re.fullmatch(r"[a-z0-9-]+", name), f"{name} is used as a directory name"


def test_every_input_file_a_case_names_exists():
    for case in cases():
        for relative in case.get("files", []):
            assert (ROOT / relative).exists(), f"eval {case['id']} points at missing {relative}"


def test_the_recorded_walk_fixture_is_loadable():
    run = json.loads((FIXTURE / "run.json").read_text(encoding="utf-8"))
    assert run["schema"] == "lab-validator/run-trace/v1"
    lines = [
        json.loads(line)
        for line in (FIXTURE / "trace.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert lines
    assert [entry["seq"] for entry in lines] == list(range(1, len(lines) + 1))


def test_the_fixture_only_uses_verdicts_that_exist():
    """A retired code turns a planted trap into an unreadable one."""
    lines = (FIXTURE / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    for entry in (json.loads(line) for line in lines if line.strip()):
        assert entry["verdict"] in taxonomy.VERDICTS, entry["verdict"]


def test_the_fixture_traces_only_segments_the_run_declares():
    run = json.loads((FIXTURE / "run.json").read_text(encoding="utf-8"))
    declared = {segment["id"] for segment in run["segments"]}
    lines = (FIXTURE / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    for entry in (json.loads(line) for line in lines if line.strip()):
        assert entry["segment"] in declared, entry["segment"]


def test_the_fixture_still_plants_every_trap_it_claims_to():
    """The fixture's whole value is the traps; losing one loses the eval quietly.

    Each of these probes a rule from `The judgement, in one page`. A trace edited
    down to only clean observations would still parse, still grade, and still
    tell you the skill was working.
    """
    lines = (FIXTURE / "trace.jsonl").read_text(encoding="utf-8").splitlines()
    entries = [json.loads(line) for line in lines if line.strip()]
    verdicts = [entry["verdict"] for entry in entries]

    assert verdicts.count("LAB000") >= 2, "no transients to wrongly report"
    assert "BLOCKED" in verdicts, "nothing to test 'blocked is a status, not a finding'"
    assert "LAB009" in verdicts, "no silently-succeeding step to catch"
    assert any(
        "gpt-35-turbo" in entry.get("note", "") for entry in entries
    ), "no name/identity mismatch to test ownership against"

    run = json.loads((FIXTURE / "run.json").read_text(encoding="utf-8"))
    unreached = [s for s in run["segments"] if s["status"] == "not_selected"]
    assert unreached, "nothing unwalked, so coverage cannot be got wrong"


def test_the_fixture_carries_nothing_that_looks_like_a_real_lab():
    """`runs/` is gitignored because real runs carry credentials. A fixture is a
    run folder that is *not* gitignored, so it is the one place that protection
    does not reach -- and it is committed, which makes a mistake permanent.
    """
    for path in FIXTURE.rglob("*"):
        if not path.is_file():
            continue
        body = path.read_text(encoding="utf-8")
        assert "@lab." not in body, f"{path.name} contains a Skillable token replacement"
        assert "mslearningcampus.com" not in body, f"{path.name} names the real platform host"
        for url in re.findall(r"https?://([^/\s\"]+)", body):
            assert url.endswith((".invalid", ".example")), f"{path.name} reaches {url}"
