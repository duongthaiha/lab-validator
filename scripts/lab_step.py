"""Walk a lab step by step, recording every action as trace evidence.

This replaces ``lab_drive.py``'s flag bag. Actions are given as a repeated,
**order-preserving** ``--do`` list, because the old design could not express a
sequence at all: ``argparse`` keeps only the last ``--click``, and the verbs ran
in a fixed order regardless of how they were written. Anything needing
"click here, then type, then click there" was simply inexpressible.

    python scripts/lab_step.py --segment s00-... --label open-portal \
        --do click:960,540 --do wait:800 --do type:portal.azure.com \
        --do key:Enter --do until:portal --do shot

Every verb becomes a trace record, so the evidence trail is a side effect of
driving rather than something to remember to write.

Long-running work uses ``until:<probe>``, which polls with heartbeats instead of
guessing a fixed sleep. On budget exhaustion it records ``LAB007`` -- "this step
never finishes" is a real finding about the lab, not a harness failure to hide.

Orientation
-----------
Role:     operator-facing shim over `runlog`: the ordered actions; every verb becomes evidence.
Entry:    `main`, `run_actions`, `ACTIONS`, `Step`
Talks to: browser, console, corpus, imaging, labclient, learnerpath, paths, report, runlog, vault
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
)
from lab_validator.console import (  # noqa: E402
    ConsoleWatch,
    DebugLog,
)
from lab_validator.corpus import Outline  # noqa: E402
from lab_validator.imaging import (  # noqa: E402
    QUIET_THRESHOLD,
    save_evidence,
    save_view,
    stability,
)
from lab_validator.labclient import (  # noqa: E402
    LabClient,
    LabClosed,
    closed_reason,
)
from lab_validator.learnerpath import Ledger
from lab_validator.paths import OUTLINE, RUNS  # noqa: E402
from lab_validator.report import write_segment  # noqa: E402
from lab_validator.runlog import DOMAINS, FINDING_VERDICTS, Run, RunNotFound  # noqa: E402
from lab_validator.vault import SIGNIN_FIELDS, Vault, VaultError  # noqa: E402


def refresh_section_report(run: Run, segment_id: str) -> Path | None:
    """Rewrite this section's own report so it is current after every step.

    Written continuously rather than at the end because a run that dies at
    section 9 of 23 should still leave nine finished reports behind. Rendering
    is a pure function of the trace, so rewriting is cheap and idempotent, and
    a withdrawn finding disappears from the report instead of needing an
    erratum appended to it.
    """
    segment = next((s for s in run.segments() if s.id == segment_id), None)
    if segment is None:
        return None
    outline = None
    if OUTLINE.exists():
        try:
            outline = Outline.load(OUTLINE)
        except Exception:  # noqa: BLE001 - the task headings are a nicety, not the report
            outline = None
    try:
        return write_segment(run, segment, outline)
    except OSError as exc:
        print(f"  (section report not written: {exc})", file=sys.stderr)
        return None


HELP = """\
Actions (repeat --do; they run in the order given):
  click:X,Y          click the VM at VM-pixel coordinates
  dblclick:X,Y       double-click
  move:X,Y           move the pointer without clicking
  scroll:X,Y[,DELTA]  wheel the VM at those coordinates (default 400). This
                     scrolls *inside the VM*; use read for the instruction pane.
  focus              click the centre of the VM to give it keyboard focus
  type:TEXT          send text to the VM (settle time scales with length)
  cred:SCOPE/LABEL   send a Resources-tab credential without printing it
  signin:ROLE[/FIELD]  sign in by role, never by credential name: ROLE is vm or
                     portal, FIELD is password (default), username, or tap for a
                     Temporary Access Pass where the lab issues one. The lab
                     issues several passwords and more than one is called
                     "Password"; naming the login picks the right one. signin:vm
                     must come before signin:portal — the portal sign-in types
                     into a VM nothing has unlocked yet.
  key:A+B            press keys, e.g. key:Enter  key:Control+s  key:Alt+ArrowLeft
                     Playwright key names, not Windows ones: Control/Alt/Shift/
                     Meta, and ArrowLeft/ArrowRight/ArrowUp/ArrowDown. "alt+Left"
                     is rejected outright rather than guessed at.
  wait:MS            fixed pause
  until:PROBE[:SEC]  poll until PROBE matches, default budget 300s
  shot[:LABEL]       capture the VM screen as evidence
  dialog             dismiss a lab dialog and report its text
  page:N             go to instruction page N — fast, exact, and a BYPASS: it
                     never touches the pane's own navigation, so a pane that
                     will not scroll still reads as a clean section
  read[:PX]          scroll the instruction pane the way a learner does, and
                     report a finding if it does not move (default 600px)

Probes for until: any literal text to find on screen is not supported (there is
no OCR here); probes are lab-client conditions:
  connected          environment status is connected
  quiet:MS           screen stops changing for MS (default 4000)
"""


class Stop(Exception):
    """Raised to abandon the remaining actions in a step."""


async def capture(
    lab: LabClient, run: Run, segment: str, label: str,
    watch: ConsoleWatch | None = None, log: DebugLog | None = None,
) -> Path:
    """Capture the VM screen as evidence, plus a reader-sized copy.

    Evidence frames must stay legible enough to read a portal label or a
    traceback; the agent's reader has a much smaller size limit than that
    requires. Writing both keeps each fit for purpose.

    This is also where the console is measured, because it is the one place
    every image the walk writes passes through -- so the whole run gets watched
    without a single extra screenshot being taken.
    """
    png = await lab.screen_bytes()
    out = save_evidence(png, run.next_image(segment, label))
    save_view(png, out)
    if watch is not None:
        # The *saved* frame, not the raw one. A watch that resumes reads its
        # baseline back from disk, where the frame is a JPEG; comparing that
        # against a lossless PNG measures the difference between two encoders
        # rather than the difference between two moments. Live, that scored
        # every interval at ~0.02 against a 0.01 floor -- so everything "moved",
        # nothing was ever reported as ineffective, and the whole diagnostic
        # would have sat there looking healthy and saying nothing.
        interval = watch.saw(out.read_bytes(), label=out.stem)
        if interval is not None and log is not None:
            log.write(
                "interval",
                delta=round(interval.delta, 6),
                actions=list(interval.actions),
                label=interval.label,
                floor=round(interval.floor, 6),
                moved=interval.moved,
                image=out.name,
                segment=segment,
            )
    return out


async def _refuse_if_closed(lab: LabClient, run: Run, segment: str) -> None:
    """Stop a long poll the moment the thing it is waiting on has gone.

    Checked once per heartbeat rather than once per iteration: the cost of a
    miss is bounded at fifteen seconds, and the cost of asking is a page read.

    Without this a probe runs its whole budget against a closed lab and then
    files `LAB007 ... did not complete within Ns` -- a **major** finding about a
    lab that had already ended. Observed live in the reverse direction (a false
    `LAB003` about a dead instruction pane), which is the same defect: a
    measurement taken after the subject went away, published as a fact about
    the subject.
    """
    reason = await closed_reason(lab.page)
    if reason is None:
        return
    run.log(f"lab closed mid-step: {reason!r}")
    raise LabClosed(
        f"The lab client says: {reason!r}. It closed while this step was "
        "waiting, so the wait proves nothing about the lab. Sections already "
        "walked keep their reports; the rest are unknown, not correct. "
        "Launch the lab again to continue."
    )


async def probe_quiet(lab: LabClient, run: Run, segment: str, arg: str, budget: float) -> bool:
    """Wait until the VM screen stops changing.

    Screen-stability is the one completion signal that works for everything --
    installers, restores, notebook cells, long portal deployments -- without
    needing to know what "done" looks like for each.
    """
    settle_ms = int(arg or 4000)
    started = time.monotonic()
    last, last_change = None, time.monotonic()
    beat = 0.0
    worst = 0.0
    while time.monotonic() - started < budget:
        try:
            frame = await lab.screen_bytes()
        except Exception as exc:  # transient console hiccup, keep polling
            run.log(f"probe quiet: screen failed ({type(exc).__name__})")
            frame = None
        now = time.monotonic()
        if frame is not None:
            delta = stability(last, frame) if last is not None else 255.0
            if delta > QUIET_THRESHOLD:
                last, last_change, worst = frame, now, 0.0
            else:
                worst = max(worst, delta)
                if (now - last_change) * 1000 >= settle_ms:
                    return True
        if now - beat >= 15:
            beat = now
            await _refuse_if_closed(lab, run, segment)
            run.heartbeat(
                segment,
                operation=f"quiet:{settle_ms}",
                elapsed_s=now - started,
                probe="screen-stable",
                detail={"stillSince_s": round(now - last_change, 1), "delta": round(worst, 3)},
            )
        await asyncio.sleep(2)
    return False


async def probe_connected(lab: LabClient, run: Run, segment: str, arg: str, budget: float) -> bool:
    started = time.monotonic()
    beat = 0.0
    while time.monotonic() - started < budget:
        status = await lab.connection_status()
        if status.get("status") == "connected":
            return True
        now = time.monotonic()
        if now - beat >= 15:
            beat = now
            await _refuse_if_closed(lab, run, segment)
            run.heartbeat(
                segment,
                operation="connected",
                elapsed_s=now - started,
                probe=str(status.get("status")),
            )
        await asyncio.sleep(3)
    return False


PROBES = {"quiet": probe_quiet, "connected": probe_connected}


async def resolve_credential(lab: LabClient, run: Run, ref: str) -> str:
    """The value behind a credential ref, from the vault where there is one.

    The vault is preferred over the live Resources tab for two reasons beyond
    saving a tab switch. It is structured, so an ambiguous reference refuses
    instead of resolving to whichever row the tab listed first; and it
    understands *role* refs -- ``vm/password``, ``portal/username`` -- which name
    the sign-in rather than the scope, and so cannot be aimed at the wrong one.

    Falls back to reading the tab when a run has no vault, because a walk driven
    step by step against a lab launched by hand is still a supported way to use
    this, and it should degrade rather than stop.
    """
    with contextlib.suppress(Exception):
        if vault := Vault.load(run.dir, redactor=run.redactor):
            return vault.value(ref)
    return await lab.credential_value(ref)


async def do_signin(lab: LabClient, run: Run, segment: str, arg: str) -> int:
    """Sign in to one thing, with the credential that thing issued.

    ``signin:vm`` / ``signin:portal`` type that sign-in's **password**;
    ``signin:portal/username`` types its username. The field is explicit because
    sign-ins are multi-screen and the two screens look different: a Windows lock
    screen arrives with the account already chosen and shows a password box
    alone, while a portal asks for the account first. Typing a username into a
    password box is a visible, harmless mistake; the field defaults to
    ``password`` because that is the screen both flows share.

    What is *not* a parameter is which credential to use. Every other action
    here lets the caller say what to type; this one does not, and that asymmetry
    is the entire point. A lab that hands out two username/password pairs -- one
    for the Windows machine, one for the cloud portal -- has two logins that look
    almost identical and share no credentials. Choosing between them by reading
    the task name is how an Azure e-mail address ends up in a Windows password
    box, and how the rejection that follows gets written up as a lab defect.

    **The order is not a parameter either.** These keystrokes go to the VM, and
    a cloud sign-in inside the VM's browser is unreachable until the machine
    itself is unlocked, so ``signin:portal`` before any ``signin:vm`` is a
    request that cannot be correct whatever the screen shows. It is refused
    rather than typed. That refusal exists because binding the credential to the
    role fixed only half the problem: the second live run *did* call ``signin:``,
    and still asked for ``portal`` while looking at a Windows lock screen
    captioned ``Admin`` with a password box on it.

    **The verdict does not come from the pixels**, and the measurements are the
    reason. A *failed* sign-in -- lock screen to "The password is incorrect" --
    scores 0.80. A *successful* one -- lock screen to "Welcome" -- scores 0.23
    and 1.20 in the reference run. Success can measure less than failure,
    because both screens are the same flat blue with the same avatar and the
    only difference is a line of text. Nothing separates them by magnitude, so
    this records ``DEFERRED`` and names the next capture as what settles it.
    Reading "The password is incorrect" off a screenshot is something the model
    does reliably; inventing a threshold that cannot exist is not.
    """
    role, _, field = arg.partition("/")
    role, field = role.strip().lower(), (field.strip().lower() or "password")
    if field not in SIGNIN_FIELDS:
        raise Stop(f"signin field must be one of {sorted(SIGNIN_FIELDS)}, not {field!r}")

    # The ordering guard. Read from the trace rather than kept in memory so a
    # resumed run inherits it: `auto --run <folder>` rebuilds everything else
    # from disk and this must not be the one fact that resets.
    if role != "vm" and not any(
        str(s.get("action", "")).startswith("signin:vm") for s in run.steps()
    ):
        raise Stop(
            f"signin:{arg} refused: these keystrokes go to the VM, and nothing has "
            "signed in to the VM yet. A cloud sign-in inside the VM's browser is "
            "unreachable until the machine is unlocked, so this cannot be the right "
            "move whatever the screen looks like -- and a Windows lock screen "
            "showing an account name and a password box is exactly what it looks "
            "like. Use signin:vm first."
        )

    # Priming happens inside load, so a resumed run cannot type a secret the
    # writer has never been told about.
    vault = Vault.load(run.dir, redactor=run.redactor)
    if vault is None:
        raise Stop(
            f"signin:{arg} needs the credentials this lab issued, and this run "
            "captured none. Launch through `lab-validator walk` so the Resources "
            "tab is read at launch, or type the fields with cred: refs."
        )
    try:
        chosen = vault.signin_field(role, field)
    except VaultError as exc:
        raise Stop(f"signin:{arg} refused: {exc}") from exc

    # No re-registration here: `Vault.load` above primed the redactor with every
    # credential it holds. Masking at the boundary rather than at each use is
    # the point -- a second copy of the rule here would be the thing that gets
    # forgotten in the next function that types a secret.

    before = await lab.screen_bytes()
    await lab.type(chosen.value)
    await lab.key("Enter")
    await asyncio.sleep(6)
    after = await lab.screen_bytes()

    # Recorded for audit, never used to decide anything. Measured on real
    # frames from this lab:
    #
    #     lock screen -> "The password is incorrect"   0.80   (FAILED)
    #     lock screen -> "Welcome"                     0.23   (SUCCEEDED)
    #     lock screen -> "Welcome"                     1.20   (SUCCEEDED)
    #
    # A success can score below a failure, because both screens are the same
    # flat blue with the same avatar and the same account name; the only
    # difference is one line of text. No threshold separates those populations,
    # and the earlier version's 0.6 line recorded PASS for the rejection above.
    # Byte equality is worse still -- consecutive identical frames from this
    # console measure 0.00, so even "nothing moved" proves nothing.
    delta = stability(before, after)

    # DEFERRED, always: the action was performed and its outcome is settled
    # somewhere else. That is not a hedge, it is the honest reading -- and the
    # place it gets settled is a screenshot, which the model reads well. It
    # transcribed "The password is incorrect. Try again." correctly on the run
    # that failed; what it could not do was choose the credential. Perception
    # to the model, binding to the code.
    run.step(
        segment,
        action=f"signin:{role}/{field}",
        surface="vm",
        verdict="DEFERRED",
        severity=None,
        note=(
            f"{chosen.scope}/{chosen.label} typed (delta {delta:.1f}); the delta "
            "cannot tell acceptance from rejection on this console -- capture the "
            "screen and read it. A password box or an error message means it failed"
        ),
    )
    return 0


class Step:
    """Everything a verb handler needs, so handlers can take (step, arg).

    The action loop used to be one 148-line if/elif chain over twelve verbs.
    Each arm closed over the same six locals, which is why it could not be
    broken up without threading all six through by hand. Naming that set once
    lets every verb become a small function that can be read -- and tested --
    on its own, and lets `ACTIONS` below be the single list of what the engine
    understands, derived rather than restated.

    Deliberately not a dataclass: `cli._load` executes this file under a
    synthetic module name that is never put in `sys.modules`, and
    `dataclasses` resolves string annotations through there, so the decorator
    raises at import time. A hand-written `__init__` costs four lines.
    """

    def __init__(
        self,
        lab: LabClient,
        run: Run,
        segment: str,
        label: str,
        watch: ConsoleWatch | None = None,
        log: DebugLog | None = None,
    ):
        self.lab = lab
        self.run = run
        self.segment = segment
        self.label = label
        self.watch = watch
        self.log = log

    async def capture(self, label: str | None = None):
        return await capture(
            self.lab, self.run, self.segment, label or self.label, self.watch, self.log
        )


def coords(verb: str, arg: str, need: int) -> list[int]:
    """Parse `x,y[,delta]`, refusing rather than crashing.

    `scroll:400` and `click:Not now` used to reach `int(...)` and raise a raw
    `IndexError`/`ValueError`. A traceback in the middle of a walk reads as
    "the tool broke" when the truth is "that is not what this verb takes", and
    the operator learns nothing about the right form. So the error names the
    verb, shows what arrived, and gives the shape.
    """
    parts = [p.strip() for p in arg.split(",") if p.strip()]
    shape = "x,y" if need == 2 else "x,y[,delta]"
    try:
        values = [int(p) for p in parts]
    except ValueError as exc:
        raise Stop(
            f"{verb}:{arg!r} takes screen coordinates, not text -- {shape}.\n"
            f"    example: {verb}:640,400\n"
            "    There is no click-by-text on the VM: it is a video frame, not a\n"
            "    DOM. Take a `shot`, read the pixel position, then click it."
        ) from exc
    if len(values) < need:
        raise Stop(
            f"{verb}:{arg!r} needs {shape} -- {len(values)} value(s) given.\n"
            f"    example: {verb}:640,400"
        )
    return values


async def _do_click(step: Step, arg: str) -> int:
    x, y = coords("click", arg, 2)[:2]
    await step.lab.click(x, y)
    step.run.step(step.segment, action=f"click:{x},{y}", surface="vm")
    return 0


async def _do_dblclick(step: Step, arg: str) -> int:
    x, y = coords("dblclick", arg, 2)[:2]
    await step.lab.click(x, y, double=True)
    step.run.step(step.segment, action=f"dblclick:{x},{y}", surface="vm")
    return 0


async def _do_move(step: Step, arg: str) -> int:
    x, y = coords("move", arg, 2)[:2]
    await step.lab.move(x, y)
    step.run.step(step.segment, action=f"move:{x},{y}", surface="vm")
    return 0


async def _do_scroll(step: Step, arg: str) -> int:
    parts = coords("scroll", arg, 2)
    x, y = parts[0], parts[1]
    delta = parts[2] if len(parts) > 2 else 400
    await step.lab.wheel(x, y, delta)
    step.run.step(step.segment, action=f"scroll:{x},{y},{delta}", surface="vm")
    return 0


async def _do_focus(step: Step, arg: str) -> int:
    await step.lab.focus_vm()
    step.run.step(step.segment, action="focus", surface="vm")
    return 0


async def _do_type(step: Step, arg: str) -> int:
    await step.lab.type(arg)
    step.run.step(step.segment, action=f"type:{arg}", surface="vm")
    return 0


async def _do_cred(step: Step, arg: str) -> int:
    value = await resolve_credential(step.lab, step.run, arg)
    step.run.redactor.add(value, arg.replace("/", "-").lower())
    await step.lab.type(value)
    step.run.step(
        step.segment, action=f"cred:{arg}", surface="vm", note=f"{len(value)} chars"
    )
    return 0


async def _do_signin(step: Step, arg: str) -> int:
    return await do_signin(step.lab, step.run, step.segment, arg.strip().lower())


async def _do_key(step: Step, arg: str) -> int:
    keys = [k.strip() for k in arg.split("+")] if "+" not in arg else [arg]
    await step.lab.key(*keys)
    step.run.step(step.segment, action=f"key:{arg}", surface="vm")
    return 0


async def _do_wait(step: Step, arg: str) -> int:
    if not arg.strip().isdigit():
        raise Stop(f"wait:{arg!r} takes milliseconds.\n    example: wait:2000")
    await asyncio.sleep(int(arg) / 1000)
    step.run.step(step.segment, action=f"wait:{arg}", surface="vm")
    return 0


async def _do_until(step: Step, arg: str) -> int:
    name, _, rest = arg.partition(":")
    budget_s = 300.0
    probe_arg = rest
    if rest and rest.rsplit(":", 1)[-1].isdigit() and ":" in rest:
        probe_arg, budget_s = rest.rsplit(":", 1)[0], float(rest.rsplit(":", 1)[1])
    elif rest.isdigit() and name == "connected":
        probe_arg, budget_s = "", float(rest)
    probe = PROBES.get(name)
    if probe is None:
        raise Stop(f"unknown probe {name!r}; known: {sorted(PROBES)}")
    started = time.monotonic()
    ok = await probe(step.lab, step.run, step.segment, probe_arg, budget_s)
    elapsed = time.monotonic() - started
    if ok:
        step.run.step(
            step.segment,
            action=f"until:{arg}",
            surface="probe",
            note=f"settled after {elapsed:.0f}s",
        )
        return 0
    shot = await step.capture(f"{step.label}-timeout")
    step.run.step(
        step.segment,
        verdict="LAB007",
        severity="major",
        action=f"until:{arg}",
        surface="probe",
        images=[shot],
        note=f"did not complete within {budget_s:.0f}s",
    )
    print(f"  ! LAB007 {arg} did not complete within {budget_s:.0f}s")
    return 1


async def _do_dialog(step: Step, arg: str) -> int:
    text = await step.lab.dismiss_dialog()
    step.run.step(
        step.segment,
        action="dialog",
        surface="dom",
        observed={"kind": "dialog", "value": text},
    )
    if text:
        print(f"  dialog: {text[:160]}")
    return 0


async def _do_page(step: Step, arg: str) -> int:
    if not arg.strip().isdigit():
        raise Stop(f"page:{arg!r} takes an instruction page number.\n    example: page:3")
    await step.lab.goto_page(int(arg))
    step.run.step(step.segment, action=f"page:{arg}", surface="dom")
    return 0


async def _do_read(step: Step, arg: str) -> int:
    # The learner's way through the instruction pane. `page:` is faster
    # and exact, which is exactly why it is a bypass: it never touches
    # the pane's own navigation, so a pane that will not scroll reads as
    # a clean section.
    scrolled = await step.lab.scroll_instructions(int(arg) if arg else 600)
    if scrolled.stuck:
        step.run.step(
            step.segment, verdict="LAB003", severity="major", domain="setup",
            action=f"read:{arg or 600}", surface="dom",
            note=scrolled.describe(),
        )
        print(f"  !! {scrolled.describe()}")
        return 1
    # A section that fits its pane still counts as read the learner's way --
    # there was no scroll for the learner to be denied. Reporting it as a
    # defect is how the first live run filed a major finding against a page
    # that was simply short.
    step.run.step(step.segment, action=f"read:{arg or 600}", surface="dom",
                  note=scrolled.describe())
    return 0


async def _do_shot(step: Step, arg: str) -> int:
    shot = await step.capture(arg or step.label)
    step.run.step(step.segment, action="shot", surface="vm", images=[shot])
    print(f"  -> {shot.relative_to(step.run.dir)}")
    if step.watch is not None and step.watch.intervals:
        last = step.watch.intervals[-1]
        if step.log is not None and step.log.verbose:
            print(f"     {last.describe()}")
    return 0


#: verb -> handler. The engine's vocabulary, in one place, so `--help`, the
#: capability ledger and the tests can all read the same list instead of each
#: keeping a copy that drifts.
ACTIONS = {
    "click": _do_click,
    "dblclick": _do_dblclick,
    "move": _do_move,
    "scroll": _do_scroll,
    "focus": _do_focus,
    "type": _do_type,
    "cred": _do_cred,
    "signin": _do_signin,
    "key": _do_key,
    "wait": _do_wait,
    "until": _do_until,
    "dialog": _do_dialog,
    "page": _do_page,
    "read": _do_read,
    "shot": _do_shot,
}


async def run_actions(
    lab: LabClient, run: Run, segment: str, label: str, actions: list[str],
    ledger: Ledger | None = None,
    watch: ConsoleWatch | None = None, log: DebugLog | None = None,
) -> int:
    findings = 0
    step = Step(lab=lab, run=run, segment=segment, label=label, watch=watch, log=log)
    # Which channels this step used, so the run can state what it did *not*
    # exercise. Owned by the caller because the coverage claim belongs to the
    # whole walk, and this function is one step of many.
    ledger = ledger if ledger is not None else Ledger()
    for raw in actions:
        verb, _, arg = raw.partition(":")
        verb = verb.strip().lower()
        ledger.record_action(verb)
        if watch is not None:
            # Banked against the next frame, whenever that arrives. An action
            # is credited to the interval it happened in, not to the one whose
            # capture it happens to precede.
            watch.did(raw)

        handler = ACTIONS.get(verb)
        if handler is None:
            raise Stop(f"unknown action {raw!r}\n\n{HELP}")
        findings += await handler(step, arg)
    return findings


async def main_async(args) -> int:
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, args.port)
        try:
            lab = LabClient.find(context)
            await lab.page.bring_to_front()

            # Before anything is recorded. A closed lab keeps its tab, its
            # title, its /LabClient/<guid> URL and its frames, so every identity
            # check still passes -- and the walk carries on writing steps about
            # a lab that is not there. Observed live: a major "the instruction
            # pane will not scroll" finding filed against a dead frame, then
            # three PASS steps for work done against nothing.
            try:
                await lab.ensure_open()
            except LabClosed as exc:
                print(f"\n!! {exc}", file=sys.stderr)
                # Best effort: if there is no run to write to, the message
                # above is still the useful part, so never fail in here.
                try:
                    run = Run.open_or_latest(RUNS, args.run)
                except RunNotFound:
                    run = None
                if run is not None:
                    segment = args.segment
                    try:
                        segment = run.resolve_segment(args.segment)
                    except KeyError:
                        pass
                    run.step(
                        segment, verdict="BLOCKED",
                        domain="setup", action="lab-closed", surface="dom",
                        note=str(exc),
                    )
                return 4

            run = Run.open_or_latest(RUNS, args.run)

            try:
                args.segment = run.resolve_segment(args.segment)
            except KeyError as exc:
                print(exc.args[0], file=sys.stderr)
                return 2

            problem = check_ref(run, args.ref)
            if problem:
                print(problem, file=sys.stderr)
                return 2

            if args.start_segment:
                run.start_segment(args.segment, await lab.minutes_remaining())

            # The ledger has to survive whatever the step does, including
            # aborting mid-way -- a walk that dies is exactly the one whose
            # coverage claim needs to be honest.
            ledger = Ledger.load(run.dir)
            # Always on, and read back from disk rather than held in memory:
            # every `step` is its own process, so a watch that did not resume
            # would forget the run between commands and could never see a stall
            # spanning two of them -- which is every stall that matters.
            #
            # Not opt-in, for the same reason the run folder is not opt-in. You
            # never know in advance which run will be the one that goes wrong,
            # and a diagnostic switched on afterwards has nothing to say about
            # what already happened. `--debug` controls what is *printed*, not
            # what is recorded.
            log = DebugLog(run.dir)
            log.verbose = bool(getattr(args, "debug", False))
            watch = ConsoleWatch.resume(run.dir)
            log.write("step", segment=args.segment, label=args.label, actions=list(args.do or []))
            try:
                findings = await run_actions(
                    lab, run, args.segment, args.label, args.do or [], ledger,
                    watch, log,
                )
            except LabClosed as exc:
                # The lab ended *during* the step. Everything recorded before
                # this point stands -- it was measured against a live lab --
                # but the step did not finish, and saying so is the whole
                # point: the alternative is a LAB007 major finding about a wait
                # that could never have completed.
                print(f"\n!! {exc}", file=sys.stderr)
                run.step(
                    args.segment, verdict="BLOCKED",
                    domain="setup", action="lab-closed", surface="dom",
                    note=str(exc),
                )
                return 4
            finally:
                ledger.save(run.dir)

            if args.end_segment:
                run.end_segment(args.segment, args.end_segment, await lab.minutes_remaining())

            findings += record_judgement(run, args.segment, args)
            report = refresh_section_report(run, args.segment)
            where = f"  -> {report.relative_to(run.dir)}" if report else ""
            print(f"run: {run.dir.name}  segment: {args.segment}  "
                  f"findings this step: {findings}{where}")

            # Last, so it is the thing a reader -- human or model -- sees most
            # recently. The whole reason this exists is that a walk once did
            # sixty-five actions against a desktop with no browser open and was
            # told PASS every time; being told so on the third action is the
            # difference between a typo and a wasted run.
            notice = watch.notice()
            if notice:
                log.write("notice", segment=args.segment, text=notice)
                print("\n" + notice)
            return 0
        finally:
            await browser.close()


def check_ref(run: Run, ref: str | None) -> str | None:
    """Reject an ``--ref`` that names no heading in this lab's corpus.

    An unresolvable reference is the worst kind of mistake this tool can make,
    because nothing about it looks wrong: the verdict is written, the note lands
    in the section report, and only the coverage count -- "1 task(s) unjudged",
    with no name attached -- ever hints that the judgement vouched for nothing.
    Observed live: a task titled "Microsoft Foundry - Overview page" has the id
    ``...foundry---overview-page``, three hyphens for the spaced dash, and the
    single-hyphen guess was accepted in silence.

    Returns an error message, or ``None`` when the reference is good or cannot
    be checked (no corpus on disk yet -- absence of evidence must not block a
    walk that is otherwise working).
    """
    if not ref:
        return None
    path = run.dir / "outline.json"
    if not path.exists():
        return None
    try:
        outline = Outline.load(path)
    except (OSError, ValueError):
        return None
    if outline.by_id(ref) is not None:
        return None
    lines = [f"--ref {ref} matches no heading in this lab's instructions."]
    near = outline.suggest(ref)
    if near:
        lines.append("Did you mean:")
        lines.extend(f"  #{i}" for i in near)
    else:
        lines.append("List a section's task anchors with: lab-validator text --run <run> "
                     "--segment <id> --tasks")
    lines.append("Nothing was recorded. Re-run with the anchor as the corpus spells it.")
    return "\n".join(lines)


def record_judgement(run: Run, segment: str, args) -> int:
    """Record the analysis attached to a step and return its finding count.

    Browser-driven and record-only steps must write the same trace shape. The
    two paths used to spell this call independently, which made adding a field
    to one and forgetting the other an easy way to lose evidence depending on
    whether the lab happened to be reachable.
    """
    if not args.note and not args.deviation:
        return 0
    run.step(
        segment,
        verdict=args.verdict,
        severity=args.severity,
        note=args.note,
        instruction_ref=args.ref,
        domain=args.domain,
        deviation=args.deviation,
        surface="analysis",
    )
    return 1 if args.verdict in FINDING_VERDICTS else 0


def record_only(args, lab_minutes: int | None = None) -> int:
    """Append bookkeeping without requiring a reachable lab.

    Judgements about instruction text -- a wrong variable name, a stale path,
    a step the corpus never mentions -- need no screenshot, and paying a CDP
    attach plus a lab-clock query for each one is pure overhead on a walk that
    records hundreds of them.

    Segment transitions come through here too. Sampling the lab clock is
    best-effort: a checkpoint must never be *blocked* by an unreachable lab,
    because that is precisely when an honest record of how far the run got
    matters most.
    """
    try:
        run = Run.open_or_latest(RUNS, args.run)
    except RunNotFound as exc:
        print(str(exc), file=sys.stderr)
        return 2
    try:
        segment = run.resolve_segment(args.segment)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2

    problem = check_ref(run, args.ref)
    if problem:
        print(problem, file=sys.stderr)
        return 2

    if args.start_segment:
        run.start_segment(segment, lab_minutes)

    finding = record_judgement(run, segment, args)

    if args.end_segment:
        run.end_segment(segment, args.end_segment, lab_minutes)

    report = refresh_section_report(run, segment)
    where = f"  -> {report.relative_to(run.dir)}" if report else ""
    clock = "unknown" if lab_minutes is None else f"{lab_minutes} min"
    print(f"run: {run.dir.name}  segment: {segment}  findings this step: {finding}"
          f"  lab clock: {clock}{where}")
    return 0


async def sample_minutes(port: int) -> int | None:
    """Read the lab clock, or ``None`` if the lab client cannot be reached."""
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, port)
        try:
            return await LabClient.find(context).minutes_remaining()
        finally:
            await browser.close()


def main() -> int:
    p = argparse.ArgumentParser(
        description="Drive a lab step, recording every action as trace evidence.",
        epilog=HELP,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--segment", required=True, help="segment id this step belongs to")
    p.add_argument("--label", default="step", help="filename label for captures")
    p.add_argument("--do", action="append", metavar="ACTION", help="action; repeat, order kept")
    p.add_argument("--run", help="run folder (default: most recent under runs/)")
    p.add_argument("--debug", action="store_true",
                   help="print what each action did to the screen (always logged to debug.jsonl)")
    p.add_argument("--start-segment", action="store_true", help="mark the segment started")
    p.add_argument("--end-segment", metavar="STATUS", help="mark the segment done/blocked/skipped")
    p.add_argument("--note", help="record an observation as its own trace record")
    p.add_argument("--deviation",
                   help="record how the learner departed from the written instructions")
    p.add_argument("--verdict", default="PASS", help="verdict for --note")
    p.add_argument("--severity", help="severity for --note")
    p.add_argument("--domain", choices=DOMAINS,
                   help="which side is at fault: the lab text (instruction) or the "
                        "environment (setup). Findings default to 'undetermined' -- "
                        "leave it there unless the evidence settles it.")
    p.add_argument("--ref", help="instruction anchor for --note, e.g. #setup-env-file")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    # Anything without --do is bookkeeping: notes and segment transitions. Those
    # only *want* the lab clock, they do not need it, so try for it and carry on
    # without if the lab is gone.
    if not args.do:
        minutes = None
        if args.start_segment or args.end_segment:
            try:
                minutes = asyncio.run(sample_minutes(args.port))
            except Exception as exc:  # noqa: BLE001 - clock is strictly optional
                print(f"  (lab clock unavailable: {type(exc).__name__})", file=sys.stderr)
        return record_only(args, minutes)

    try:
        return asyncio.run(main_async(args))
    except RunNotFound as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 2
    except (BrowserError, Stop) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
