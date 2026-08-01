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
from lab_validator.report import write_segment  # noqa: E402
from lab_validator.runlog import DOMAINS, FINDING_VERDICTS, Run  # noqa: E402
from lab_validator.vault import ROLE_FIELDS, Vault, VaultError  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
OUTLINE = ROOT / "artifacts" / "instructions" / "outline.json"


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
            from lab_validator.corpus import Outline

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
  focus              click the centre of the VM to give it keyboard focus
  type:TEXT          send text to the VM (settle time scales with length)
  cred:SCOPE/LABEL   send a Resources-tab credential without printing it
  key:A+B            press keys, e.g. key:Enter  key:Control+s
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


async def capture(lab: LabClient, run: Run, segment: str, label: str) -> Path:
    """Capture the VM screen as evidence, plus a reader-sized copy.

    Evidence frames must stay legible enough to read a portal label or a
    traceback; the agent's reader has a much smaller size limit than that
    requires. Writing both keeps each fit for purpose.
    """
    png = await lab.screen_bytes()
    out = save_evidence(png, run.next_image(segment, label))
    save_view(png, out)
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
    if field not in ROLE_FIELDS:
        raise Stop(f"signin field must be one of {sorted(ROLE_FIELDS)}, not {field!r}")

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
        username, password = vault.signin(role)
    except VaultError as exc:
        raise Stop(f"signin:{arg} refused: {exc}") from exc

    # No re-registration here: `Vault.load` above primed the redactor with every
    # credential it holds. Masking at the boundary rather than at each use is
    # the point -- a second copy of the rule here would be the thing that gets
    # forgotten in the next function that types a secret.
    chosen = username if field == "username" else password

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


async def run_actions(
    lab: LabClient, run: Run, segment: str, label: str, actions: list[str],
    ledger: Ledger | None = None,
) -> int:
    findings = 0
    # Which channels this step used, so the run can state what it did *not*
    # exercise. Owned by the caller because the coverage claim belongs to the
    # whole walk, and this function is one step of many.
    ledger = ledger if ledger is not None else Ledger()
    for raw in actions:
        verb, _, arg = raw.partition(":")
        verb = verb.strip().lower()
        ledger.record_action(verb)

        if verb in ("click", "dblclick", "move"):
            x, y = (int(v) for v in arg.split(","))
            if verb == "click":
                await lab.click(x, y)
            elif verb == "dblclick":
                await lab.click(x, y, double=True)
            else:
                await lab.move(x, y)
            run.step(segment, action=f"{verb}:{x},{y}", surface="vm")

        elif verb == "scroll":
            parts = [p.strip() for p in arg.split(",")]
            x, y = int(parts[0]), int(parts[1])
            delta = int(parts[2]) if len(parts) > 2 else 400
            await lab.wheel(x, y, delta)
            run.step(segment, action=f"scroll:{x},{y},{delta}", surface="vm")

        elif verb == "focus":
            await lab.focus_vm()
            run.step(segment, action="focus", surface="vm")

        elif verb == "type":
            await lab.type(arg)
            run.step(segment, action=f"type:{arg}", surface="vm")

        elif verb == "cred":
            value = await resolve_credential(lab, run, arg)
            run.redactor.add(value, arg.replace("/", "-").lower())
            await lab.type(value)
            run.step(segment, action=f"cred:{arg}", surface="vm", note=f"{len(value)} chars")

        elif verb == "signin":
            n = await do_signin(lab, run, segment, arg.strip().lower())
            findings += n

        elif verb == "key":
            keys = [k.strip() for k in arg.split("+")] if "+" not in arg else [arg]
            await lab.key(*keys)
            run.step(segment, action=f"key:{arg}", surface="vm")

        elif verb == "wait":
            await asyncio.sleep(int(arg) / 1000)
            run.step(segment, action=f"wait:{arg}", surface="vm")

        elif verb == "until":
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
            ok = await probe(lab, run, segment, probe_arg, budget_s)
            elapsed = time.monotonic() - started
            if ok:
                run.step(
                    segment,
                    action=f"until:{arg}",
                    surface="probe",
                    note=f"settled after {elapsed:.0f}s",
                )
            else:
                shot = await capture(lab, run, segment, f"{label}-timeout")
                findings += 1
                run.step(
                    segment,
                    verdict="LAB007",
                    severity="major",
                    action=f"until:{arg}",
                    surface="probe",
                    images=[shot],
                    note=f"did not complete within {budget_s:.0f}s",
                )
                print(f"  ! LAB007 {arg} did not complete within {budget_s:.0f}s")

        elif verb == "dialog":
            text = await lab.dismiss_dialog()
            run.step(
                segment,
                action="dialog",
                surface="dom",
                observed={"kind": "dialog", "value": text},
            )
            if text:
                print(f"  dialog: {text[:160]}")

        elif verb == "page":
            await lab.goto_page(int(arg))
            run.step(segment, action=f"page:{arg}", surface="dom")

        elif verb == "read":
            # The learner's way through the instruction pane. `page:` is faster
            # and exact, which is exactly why it is a bypass: it never touches
            # the pane's own navigation, so a pane that will not scroll reads as
            # a clean section.
            scrolled = await lab.scroll_instructions(int(arg) if arg else 600)
            if scrolled.stuck:
                findings += 1
                run.step(
                    segment, verdict="LAB003", severity="major", domain="setup",
                    action=f"read:{arg or 600}", surface="dom",
                    note=scrolled.describe(),
                )
                print(f"  !! {scrolled.describe()}")
            else:
                # A section that fits its pane still counts as read the
                # learner's way -- there was no scroll for the learner to be
                # denied. Reporting it as a defect is how the first live run
                # filed a major finding against a page that was simply short.
                run.step(segment, action=f"read:{arg or 600}", surface="dom",
                         note=scrolled.describe())

        elif verb == "shot":
            shot = await capture(lab, run, segment, arg or label)
            run.step(segment, action="shot", surface="vm", images=[shot])
            print(f"  -> {shot.relative_to(run.dir)}")

        else:
            raise Stop(f"unknown action {raw!r}\n\n{HELP}")
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
                run = Run.open(args.run) if args.run else Run.latest(RUNS)
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

            run = Run.open(args.run) if args.run else Run.latest(RUNS)
            if run is None:
                print("No run folder. Create one with scripts/lab_run.py --start", file=sys.stderr)
                return 2

            try:
                args.segment = run.resolve_segment(args.segment)
            except KeyError as exc:
                print(exc.args[0], file=sys.stderr)
                return 2

            if args.start_segment:
                run.start_segment(args.segment, await lab.minutes_remaining())

            # The ledger has to survive whatever the step does, including
            # aborting mid-way -- a walk that dies is exactly the one whose
            # coverage claim needs to be honest.
            ledger = Ledger.load(run.dir)
            try:
                findings = await run_actions(
                    lab, run, args.segment, args.label, args.do or [], ledger
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

            if args.note:
                run.step(args.segment, verdict=args.verdict, severity=args.severity,
                         note=args.note, instruction_ref=args.ref, domain=args.domain,
                         surface="analysis")
                if args.verdict in FINDING_VERDICTS:
                    findings += 1
            report = refresh_section_report(run, args.segment)
            where = f"  -> {report.relative_to(run.dir)}" if report else ""
            print(f"run: {run.dir.name}  segment: {args.segment}  "
                  f"findings this step: {findings}{where}")
            return 0
        finally:
            await browser.close()


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
    run = Run.open(args.run) if args.run else Run.latest(RUNS)
    if run is None:
        print("No run folder. Create one with scripts/lab_run.py --start", file=sys.stderr)
        return 2
    try:
        segment = run.resolve_segment(args.segment)
    except KeyError as exc:
        print(exc.args[0], file=sys.stderr)
        return 2

    if args.start_segment:
        run.start_segment(segment, lab_minutes)

    finding = 0
    if args.note:
        run.step(segment, verdict=args.verdict, severity=args.severity,
                 note=args.note, instruction_ref=args.ref, domain=args.domain,
                 surface="analysis")
        finding = 1 if args.verdict in FINDING_VERDICTS else 0

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
    p.add_argument("--start-segment", action="store_true", help="mark the segment started")
    p.add_argument("--end-segment", metavar="STATUS", help="mark the segment done/blocked/skipped")
    p.add_argument("--note", help="record an observation as its own trace record")
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
    except (BrowserError, Stop) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
