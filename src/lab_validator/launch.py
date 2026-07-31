"""Get from a lab URL to a running lab client, with the human doing only the sign-in.

This is the step the engine never had. Until now a run began with the operator
having already signed in *and* already clicked Launch, and
``LabClient.find`` simply reported *"Launch the lab first, then retry."* That
made the entry point a human ritual rather than a contract.

Three jobs, in order, and each has a different relationship to automation:

1. **Sign in — the human's job, permanently.** The identity challenge is
   hardware-bound (Windows Hello / FIDO passkey) and deliberately
   un-automatable. That is a good boundary, not a limitation: the human proves
   identity, the machine does the work. So this is a *first-class blocking
   gate* with a generous budget and a heartbeat, not a failure path.
2. **Resolve the URL to one enrolment.** Pure, and lives in
   :mod:`lab_validator.discovery`. Ambiguity stops the run rather than picking
   a winner.
3. **Click Launch and wait for the lab client.** Automatable, but the least
   proven part of the whole engine, so every failure falls back to asking the
   human rather than ending the run.

Two standing constraints are enforced here as code rather than as lore:

* **Never force-restart the controller browser.** The TMS session cookie is
  memory-only and the lab-client URL returns *Access Denied* when loaded
  directly, so a restart costs a human sign-in and ends the run. Nothing in
  this module closes or relaunches a browser.
* **Never click a hidden Launch.** The control is gated by a client-side
  countdown and is sometimes ``display:none``. Reaching past that with a
  scripted click bypasses the exact gate the product uses to say "not ready",
  and buys a lab client in an undefined state. Wait instead, and say so.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

__all__ = [
    "SignInTimeout",
    "LaunchOutcome",
    "signed_out",
    "wait_for",
    "ensure_signed_in",
    "find_launch",
    "click_launch",
    "await_lab_client",
    "LAUNCH_LABELS",
]

#: The sign-in wall redirects here; the marker is the path, not page text,
#: because the text is localised and the path is not.
LOGIN_PATH = "/User/Login"

#: Controls that start a lab, in preference order. Skillable's wording has
#: drifted across editions ("Launch" -> "Launch Lab"), and a resumed lab offers
#: "Resume" instead, which is the same action from the learner's point of view.
LAUNCH_LABELS = ("Launch Lab", "Launch", "Start Lab", "Start", "Resume")

#: How long to wait for a human who may have walked away. Generous on purpose:
#: a run that gives up after 60s and discards an hour of setup is worse than
#: one that waits.
SIGNIN_BUDGET_S = 900.0
HEARTBEAT_S = 30.0
POLL_S = 3.0


class SignInTimeout(RuntimeError):
    """Nobody completed the sign-in within the budget."""


@dataclass(frozen=True)
class LaunchOutcome:
    """What happened when we tried to start the lab.

    ``needs_human`` is not an error. It is the documented fallback, and it is
    the difference between a run that pauses for one click and a run that dies.
    """

    started: bool
    needs_human: bool
    reason: str

    @property
    def ok(self) -> bool:
        return self.started


def signed_out(url: str, has_login_control: bool) -> bool:
    """Is this page the sign-in wall?

    Two independent signals because either alone is wrong. The URL alone misses
    a page that renders a login prompt in place; the control alone false-fires
    on a catalogue page that merely offers a "Sign In" link in its header while
    the user is already signed in elsewhere on the page.
    """
    if LOGIN_PATH.lower() in url.lower():
        return True
    return has_login_control


async def wait_for(
    probe,
    *,
    budget_s: float,
    poll_s: float = POLL_S,
    heartbeat_s: float = HEARTBEAT_S,
    on_heartbeat=None,
    sleep=None,
    clock=None,
):
    """Poll ``probe()`` until it returns something truthy, or the budget runs out.

    Factored out with injectable ``sleep`` and ``clock`` because the waiting
    *policy* -- budget, cadence, and proving liveness while it waits -- is the
    part worth testing, and it is untestable if it is welded to a real browser
    and a real wall clock.

    Returns the truthy value, or ``None`` on timeout. Timeout is a return value
    rather than an exception because every caller here has a fallback that is
    better than dying.
    """
    clock = clock or time.monotonic
    if sleep is None:
        import asyncio

        sleep = asyncio.sleep
    started = clock()
    last_beat = started
    while True:
        result = await probe()
        if result:
            return result
        now = clock()
        if now - started >= budget_s:
            return None
        if on_heartbeat is not None and now - last_beat >= heartbeat_s:
            last_beat = now
            on_heartbeat(now - started)
        await sleep(poll_s)


async def ensure_signed_in(
    probe,
    *,
    budget_s: float = SIGNIN_BUDGET_S,
    say=print,
    sleep=None,
    clock=None,
) -> float:
    """Block until a human has signed in. Never attempt the challenge.

    ``probe()`` is an async callable returning ``True`` once the session is
    usable. Printing one unmistakable instruction and then waiting is the whole
    design: an agent that retries a passkey prompt achieves nothing except
    locking the account.

    Returns the seconds waited, so the caller can record how much of the lab
    clock the gate consumed -- a lab instance is on a countdown, and time spent
    waiting for a human is time the learner would not have spent.
    """
    clock = clock or time.monotonic
    started = clock()
    if await probe():
        return 0.0

    say("")
    say("  SIGN IN REQUIRED")
    say("  The browser window is open and focused. Sign in there by hand.")
    say("  This step is yours by design: the challenge is hardware-bound and")
    say("  cannot be automated. Everything after it is automatic.")
    say(f"  Waiting up to {budget_s / 60:.0f} minutes.")
    say("")

    ok = await wait_for(
        probe,
        budget_s=budget_s,
        on_heartbeat=lambda waited: say(f"  ... still waiting to be signed in ({waited:.0f}s)"),
        sleep=sleep,
        clock=clock,
    )
    if not ok:
        raise SignInTimeout(
            f"not signed in after {budget_s / 60:.0f} minutes. Sign in, then re-run -- "
            "the browser was left running on purpose, because restarting it would "
            "discard the session and cost another sign-in."
        )
    waited = clock() - started
    say(f"  signed in after {waited:.0f}s")
    return waited


# ---- the browser-touching half ------------------------------------------
#
# Kept below the pure functions on purpose: everything above is testable
# without a browser, and the policy decisions live up there.


async def find_launch(page, *, say=print):
    """The first launch control a *learner* could actually click.

    Returns ``(locator, reason)``; ``locator`` is ``None`` when nothing is
    clickable yet. Hidden controls are found but deliberately not returned as
    clickable, and the reason says so, because a hidden Launch is the product
    telling us the lab is not ready. ``--dump`` exists precisely because this
    control can be present and ``display:none``.
    """
    hidden = 0
    for label in LAUNCH_LABELS:
        candidate = page.get_by_role("button", name=label, exact=False).or_(
            page.get_by_role("link", name=label, exact=False)
        )
        count = await candidate.count()
        for i in range(count):
            one = candidate.nth(i)
            clickable = False
            try:
                clickable = await one.is_visible() and await one.is_enabled()
            except Exception as exc:  # noqa: BLE001
                # A node detached between count() and the check. That is the
                # page re-rendering, not a defect, and the next poll re-reads it.
                say(f"  (launch candidate {label!r} vanished mid-check: {type(exc).__name__})")
            if clickable:
                return one, f"visible {label!r} control"
            hidden += 1
    if hidden:
        return None, (
            f"{hidden} launch control(s) present but not clickable -- the lab client "
            "gates Launch behind a countdown, so this usually means 'not ready yet'"
        )
    return None, "no launch control on this page"


async def click_launch(page, *, budget_s: float = 180.0, say=print) -> LaunchOutcome:
    """Wait for Launch to become clickable, then click it once.

    Never clicks a hidden control and never reaches past the countdown with a
    scripted event: that would bypass the exact gate the product uses to say
    "not ready" and buy a lab client in an undefined state.
    """

    async def probe():
        control, reason = await find_launch(page, say=say)
        if control is None:
            probe.reason = reason
            return None
        return control

    probe.reason = "not checked"
    control = await wait_for(
        probe,
        budget_s=budget_s,
        on_heartbeat=lambda w: say(f"  ... waiting for Launch ({w:.0f}s): {probe.reason}"),
    )
    if control is None:
        return LaunchOutcome(False, True, probe.reason)
    try:
        await control.click(timeout=15000)
    except Exception as exc:  # noqa: BLE001 - the fallback is better than the traceback
        return LaunchOutcome(False, True, f"Launch was found but the click failed: {exc}")
    return LaunchOutcome(True, False, "clicked Launch")


async def await_lab_client(context, *, budget_s: float = 300.0, known=(), say=print,
                           sleep=None, clock=None):
    """Wait for the lab-client tab to exist *and* answer.

    A tab whose URL matches is not enough. The client is a frameset and
    ``window.api.v1`` is exposed only in the child frames, so a tab that has
    navigated but not finished building its frames looks ready and then fails
    on the first call. Waiting for the API to answer is the difference between
    a clean start and a first step that dies for reasons nobody can reproduce.

    ``known`` is the set of lab-client URLs open *before* Launch was clicked,
    so the tab Launch just opened can be told apart from one left over from an
    earlier lab. Selection itself is ``LabClient.find``'s job, including its
    refusal to choose between two candidates.
    """
    from .browser import BrowserError
    from .labclient import LabClient

    ambiguous: list[str] = []

    async def probe():
        try:
            lab = LabClient.find(context, known=known)
        except BrowserError as exc:
            # Several answered: that is a decision for a human, and polling
            # will never resolve it. Remember it so the caller can say so.
            if "lab client tabs are open" in str(exc):
                ambiguous.append(str(exc))
            return None
        try:
            await lab.minutes_remaining()
        except Exception:  # noqa: BLE001 - frames still building
            return None
        return lab

    lab = await wait_for(
        probe,
        budget_s=budget_s,
        sleep=sleep,
        clock=clock,
        on_heartbeat=lambda w: say(f"  ... waiting for the lab client to answer ({w:.0f}s)"),
    )
    if lab is None:
        if ambiguous:
            raise SignInTimeout(ambiguous[-1])
        raise SignInTimeout(
            "the lab client never answered. It may still be provisioning -- the lab "
            "tab was left open on purpose, so re-running will pick it up."
        )
    return lab
