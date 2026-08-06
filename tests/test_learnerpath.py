"""Tests for the learner-path rule.

The rule is enforceable precisely because it is narrow, so most of these tests
are about what it does *not* call a bypass. A rule that flagged everything would
be ignored within a week, and a rule that flagged nothing would be decoration.

The load-bearing test is the last group: that the ledger turns a bypass into a
sentence the report can print. The module exists to make a true statement
sayable — "this section passed, but the pane's own navigation was never
exercised" — not to stop anything happening.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from lab_validator import labclient, learnerpath
from lab_validator.learnerpath import (
    ACTION_CAPABILITY,
    CAPABILITIES,
    Ledger,
    classify,
    is_bypass,
)

# --- what is and is not a bypass -------------------------------------------


def test_paging_the_instruction_pane_by_api_is_a_bypass():
    """The case the rule was written for: a learner scrolls, we page."""
    assert is_bypass("goto_page")


@pytest.mark.parametrize("capability", ["click", "type", "key", "wheel", "move"])
def test_vm_input_is_not_a_bypass(capability):
    """There is no control being skipped -- this *is* how keystrokes travel."""
    assert not is_bypass(capability)


@pytest.mark.parametrize("capability", ["show_instructions", "type_credential_natively",
                                        "dismiss_dialog", "focus_vm"])
def test_acting_through_a_visible_control_is_the_learners_path(capability):
    assert not is_bypass(capability)


@pytest.mark.parametrize("capability", ["instructions_text", "credentials",
                                        "screen", "minutes_remaining", "page_index"])
def test_observation_is_never_a_bypass(capability):
    """Looking at a pane without scrolling claims nothing about the scroll."""
    assert not is_bypass(capability)


def test_bookkeeping_carries_no_coverage_claim():
    assert classify("minutes_remaining").surface == "bookkeeping"
    assert not is_bypass("minutes_remaining")


def test_an_unclassified_capability_is_an_error_not_a_silent_pass():
    """Defaulting to 'fine' is how a report comes to overstate itself."""
    with pytest.raises(KeyError, match="not classified"):
        is_bypass("some_new_thing")


# --- the registry has to keep up with the engine ----------------------------


def test_every_classified_capability_actually_exists_on_the_client():
    """Otherwise the rule describes an engine that is no longer there."""
    missing = [name for name in CAPABILITIES if not hasattr(labclient.LabClient, name)]
    assert missing == [], f"classified but gone from LabClient: {missing}"


def test_every_state_changing_client_method_is_classified():
    """A new capability must declare what using it costs the coverage claim.

    Not every public method -- only the ones that touch the lab or the VM. The
    list is derived from the client rather than hand-maintained, so adding a
    method fails this test until somebody has thought about it.
    """
    interesting = {
        name for name in dir(labclient.LabClient)
        if not name.startswith("_")
        and callable(getattr(labclient.LabClient, name, None))
        and name not in {
            # Plumbing and helpers, not capabilities: they route other calls or
            # compute values without reaching the lab. `find`/`candidates`
            # inspect the browser's own tab list, which is bookkeeping about
            # *which* lab we are in, never an action inside one.
            "find", "candidates", "call", "console", "instructions",
            "find_credential", "credential_value", "normalise_key",
        }
    }
    unclassified = sorted(interesting - set(CAPABILITIES))
    assert unclassified == [], (
        f"unclassified capabilities: {unclassified}. Classify each in "
        "learnerpath.CAPABILITIES -- the coverage claim depends on it."
    )


def test_the_registry_rejects_a_surface_it_does_not_know():
    with pytest.raises(ValueError, match="unknown surface"):
        learnerpath.Capability(name="x", surface="elsewhere", channel="api", acts=True)


def test_the_registry_rejects_a_channel_it_does_not_know():
    with pytest.raises(ValueError, match="unknown channel"):
        learnerpath.Capability(name="x", surface="labui", channel="telepathy", acts=True)


# --- the ledger: turning a bypass into a sentence ---------------------------


def test_a_clean_walk_says_so_without_hedging():
    ledger = Ledger()
    for capability in ("click", "type", "show_instructions", "screen"):
        ledger.record(capability)
    assert ledger.clean
    assert "would have been hit" in ledger.to_markdown()
    assert ledger.untested_surfaces() == []


def test_a_bypass_becomes_a_stated_coverage_limit():
    ledger = Ledger()
    ledger.record("goto_page")
    ledger.record("goto_page")
    assert not ledger.clean

    report = ledger.to_markdown()
    assert "2 action(s) routed around" in report
    assert "not tested" in report
    assert "goto_page" in report
    # It must not read as a defect in the lab -- it is a defect in the run.
    assert "coverage limit, not a defect in the lab" in report


def test_a_bypass_still_counts_as_used():
    ledger = Ledger()
    ledger.record("goto_page")
    assert ledger.used["goto_page"] == 1
    assert ledger.bypassed["goto_page"] == 1


def test_exercising_the_nominated_control_closes_the_hole():
    """A bypass costs nothing if the control it skipped was tested anyway."""
    ledger = Ledger()
    ledger.record("goto_page")
    ledger.record("scroll_instructions")
    assert ledger.bypassed, "the bypass is still recorded"
    assert ledger.untested_surfaces() == [], "but it is no longer a hole"


def test_a_different_control_on_the_same_surface_does_not_close_the_hole():
    """Clicking the Instructions tab does not exercise the pane's pager.

    The pairing has to be per-capability. Per-surface would let any click
    anywhere in the lab chrome vouch for every control in it, which is how a
    coverage claim becomes worthless while remaining technically defensible.
    """
    ledger = Ledger()
    ledger.record("goto_page")
    ledger.record("show_instructions")
    assert ledger.untested_surfaces() == [
        "goto_page — pages the instruction pane without touching its navigation "
        "(use `scroll_instructions` to close this)"
    ]


def test_a_bypass_nothing_can_close_says_so():
    """Better than implying a fix exists when the engine has no path to it."""
    ledger = Ledger()
    ledger.used["mystery"] = 1
    ledger.bypassed["mystery"] = 1
    CAPABILITIES["mystery"] = learnerpath.Capability(
        name="mystery", surface="labui", channel="api", acts=True, note="unpaired"
    )
    try:
        assert "nothing in the engine tests this yet" in ledger.untested_surfaces()[0]
    finally:
        del CAPABILITIES["mystery"]


def test_an_empty_ledger_does_not_claim_a_clean_walk():
    """Nothing recorded is not the same as nothing bypassed."""
    assert "Nothing was recorded" in Ledger().to_markdown()


def test_recording_an_unknown_capability_fails_loudly():
    with pytest.raises(KeyError):
        Ledger().record("teleport")


# --- the step-verb table has to match the step engine ----------------------


def _step_verbs() -> set[str]:
    """Every verb `lab_step.py`'s action loop handles, read from the engine.

    Derived rather than listed, so adding a verb to the engine and forgetting to
    classify it fails here instead of silently costing coverage. This used to
    scrape the source of an if/elif chain; the chain is now a dict, so it reads
    the dict -- the thing that actually decides, not a description of it.
    """
    spec = importlib.util.spec_from_file_location(
        "lab_step_verbs", Path(__file__).resolve().parents[1] / "scripts" / "lab_step.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return set(module.ACTIONS)


def test_every_step_verb_declares_a_capability():
    verbs = _step_verbs()
    assert verbs, "the verb scrape found nothing, so this test proves nothing"
    undeclared = sorted(verbs - set(ACTION_CAPABILITY))
    assert undeclared == [], (
        f"verbs with no capability: {undeclared}. Add them to "
        "learnerpath.ACTION_CAPABILITY."
    )


def test_no_declared_verb_has_disappeared_from_the_engine():
    stale = sorted(set(ACTION_CAPABILITY) - _step_verbs())
    assert stale == [], f"declared but no longer handled: {stale}"


def test_every_declared_capability_is_one_that_exists():
    unknown = sorted(
        {c for c in ACTION_CAPABILITY.values() if c is not None} - set(CAPABILITIES)
    )
    assert unknown == []


def test_an_undeclared_verb_is_rejected_rather_than_ignored():
    with pytest.raises(KeyError, match="does not declare a capability"):
        Ledger().record_action("teleport")


def test_verbs_that_touch_nothing_record_nothing():
    ledger = Ledger()
    ledger.record_action("wait")
    ledger.record_action("until")
    assert ledger.used == {}


def test_paging_through_the_step_engine_shows_up_as_a_bypass():
    ledger = Ledger()
    ledger.record_action("page")
    assert ledger.bypassed == {"goto_page": 1}


def test_reading_the_pane_by_hand_closes_that_hole():
    ledger = Ledger()
    ledger.record_action("page")
    ledger.record_action("read")
    assert ledger.untested_surfaces() == []


# --- persistence across steps ----------------------------------------------


def test_the_ledger_survives_between_steps(tmp_path):
    """A walk is many processes; the coverage claim is about all of them."""
    first = Ledger()
    first.record_action("page")
    first.save(tmp_path)

    second = Ledger.load(tmp_path)
    assert second.bypassed == {"goto_page": 1}
    second.record_action("read")
    second.save(tmp_path)

    assert Ledger.load(tmp_path).untested_surfaces() == []


def test_a_missing_ledger_starts_empty_rather_than_failing(tmp_path):
    assert Ledger.load(tmp_path).used == {}


def test_a_corrupt_ledger_starts_empty_rather_than_ending_the_run(tmp_path):
    """Bookkeeping that can refuse to load fails when the run is already sick."""
    (tmp_path / Ledger.FILE).write_text("{not json", encoding="utf-8")
    assert Ledger.load(tmp_path).used == {}


def test_the_ledger_holds_no_secrets(tmp_path):
    ledger = Ledger()
    ledger.record_action("cred")
    ledger.save(tmp_path)
    written = json.loads((tmp_path / Ledger.FILE).read_text(encoding="utf-8"))
    assert written == {"used": {"type": 1}, "bypassed": {}}