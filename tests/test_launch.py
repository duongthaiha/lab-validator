"""Tests for the sign-in gate and the launch policy.

The waiting *policy* is the part worth testing and the part that is untestable
if it is welded to a real browser and a real wall clock -- so ``wait_for`` takes
an injectable clock and sleep, and these tests drive it with a fake one. The
behaviour under test is what happens when a human walks away: a run that gives
up after 60 seconds and discards an hour of setup is worse than one that waits.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.launch import (  # noqa: E402
    LAUNCH_LABELS,
    LaunchOutcome,
    SignInTimeout,
    ensure_signed_in,
    signed_out,
    wait_for,
)


class FakeClock:
    """A clock that only moves when something sleeps, so a 15-minute budget
    takes no wall time to exercise."""

    def __init__(self):
        self.now = 0.0
        self.slept = []

    def __call__(self) -> float:
        return self.now

    async def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def after(n: int):
    """A probe that reports success on the nth call."""
    calls = {"n": 0}

    async def probe():
        calls["n"] += 1
        return calls["n"] >= n

    probe.calls = calls
    return probe


# --- signed_out ------------------------------------------------------------


def test_the_login_path_means_signed_out():
    assert signed_out("https://mslearningcampus.com/User/Login?returnUrl=%2F", False)


def test_a_login_control_means_signed_out_even_on_another_path():
    """Some pages render the prompt in place rather than redirecting."""
    assert signed_out("https://mslearningcampus.com/Pages/ms-learningcampus", True)


def test_a_signed_in_page_is_not_reported_as_signed_out():
    assert not signed_out("https://mslearningcampus.com/ClassEnrollment/5928204", False)


# --- wait_for --------------------------------------------------------------


async def test_wait_for_returns_as_soon_as_the_probe_succeeds():
    clock = FakeClock()
    assert await wait_for(after(3), budget_s=600, poll_s=3,
                          sleep=clock.sleep, clock=clock)
    assert clock.now == pytest.approx(6.0)


async def test_wait_for_gives_up_at_the_budget_rather_than_forever():
    clock = FakeClock()

    async def never():
        return False

    assert await wait_for(never, budget_s=30, poll_s=3, sleep=clock.sleep, clock=clock) is None
    assert clock.now >= 30


async def test_a_timeout_is_a_return_value_not_an_exception():
    """Every caller has a fallback that is better than dying, so the timeout
    has to be something they can act on."""
    clock = FakeClock()

    async def never():
        return False

    assert await wait_for(never, budget_s=10, poll_s=5, sleep=clock.sleep, clock=clock) is None


async def test_waiting_proves_it_is_still_alive():
    """An unattended multi-hour run that goes silent is indistinguishable from
    one that hung."""
    clock = FakeClock()
    beats = []

    async def never():
        return False

    await wait_for(never, budget_s=100, poll_s=10, heartbeat_s=30,
                   on_heartbeat=beats.append, sleep=clock.sleep, clock=clock)
    assert len(beats) >= 3
    assert beats[0] >= 30


# --- ensure_signed_in ------------------------------------------------------


async def test_an_already_signed_in_session_says_nothing_and_waits_not_at_all():
    said = []
    clock = FakeClock()
    assert await ensure_signed_in(after(1), say=said.append,
                                  sleep=clock.sleep, clock=clock) == 0.0
    assert said == [], "no instruction is needed when there is nothing to do"


async def test_the_instruction_is_unmistakable_and_states_it_is_deliberate():
    """A human who thinks the tool is broken will restart the browser, and a
    restart discards the session and ends the run."""
    said = []
    clock = FakeClock()
    await ensure_signed_in(after(2), say=said.append, sleep=clock.sleep, clock=clock)
    blob = "\n".join(said).lower()
    assert "sign in required" in blob
    assert "by hand" in blob
    assert "cannot be automated" in blob


async def test_a_human_who_steps_away_does_not_lose_the_run():
    """Ten minutes of absence must not cost the setup."""
    clock = FakeClock()
    said = []
    waited = await ensure_signed_in(after(200), budget_s=900, say=said.append,
                                    sleep=clock.sleep, clock=clock)
    assert waited >= 500
    assert any("still waiting" in s for s in said)


async def test_giving_up_explains_why_the_browser_was_left_running():
    clock = FakeClock()

    async def never():
        return False

    with pytest.raises(SignInTimeout, match="left running on purpose"):
        await ensure_signed_in(never, budget_s=60, say=lambda _: None,
                               sleep=clock.sleep, clock=clock)


# --- launch policy ---------------------------------------------------------


def test_resume_counts_as_a_launch():
    """A lab already started offers Resume; from the learner's point of view
    that is the same action."""
    assert "Resume" in LAUNCH_LABELS


def test_launch_wording_drift_is_anticipated():
    assert "Launch" in LAUNCH_LABELS and "Launch Lab" in LAUNCH_LABELS


def test_needing_a_human_is_not_a_failure():
    """The documented fallback is the difference between a run that pauses for
    one click and a run that dies."""
    outcome = LaunchOutcome(False, True, "countdown-gated")
    assert not outcome.ok
    assert outcome.needs_human
