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
from lab_validator.labclient import LabClient  # noqa: E402
from lab_validator.runlog import Run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"

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
  page:N             go to instruction page N

Probes for until: any literal text to find on screen is not supported (there is
no OCR here); probes are lab-client conditions:
  connected          environment status is connected
  quiet:MS           screen stops changing for MS (default 4000)
"""


class Stop(Exception):
    """Raised to abandon the remaining actions in a step."""


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
    while time.monotonic() - started < budget:
        try:
            frame = await lab.screen_bytes()
        except Exception as exc:  # transient console hiccup, keep polling
            run.log(f"probe quiet: screen failed ({type(exc).__name__})")
            frame = None
        now = time.monotonic()
        if frame is not None:
            if frame != last:
                last, last_change = frame, now
            elif (now - last_change) * 1000 >= settle_ms:
                return True
        if now - beat >= 15:
            beat = now
            run.heartbeat(
                segment,
                operation=f"quiet:{settle_ms}",
                elapsed_s=now - started,
                probe="screen-stable",
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
            run.heartbeat(
                segment,
                operation="connected",
                elapsed_s=now - started,
                probe=str(status.get("status")),
            )
        await asyncio.sleep(3)
    return False


PROBES = {"quiet": probe_quiet, "connected": probe_connected}


async def run_actions(
    lab: LabClient, run: Run, segment: str, label: str, actions: list[str]
) -> int:
    findings = 0
    for raw in actions:
        verb, _, arg = raw.partition(":")
        verb = verb.strip().lower()

        if verb in ("click", "dblclick", "move"):
            x, y = (int(v) for v in arg.split(","))
            if verb == "click":
                await lab.click(x, y)
            elif verb == "dblclick":
                await lab.click(x, y, double=True)
            else:
                await lab.move(x, y)
            run.step(segment, action=f"{verb}:{x},{y}", surface="vm")

        elif verb == "focus":
            await lab.focus_vm()
            run.step(segment, action="focus", surface="vm")

        elif verb == "type":
            await lab.type(arg)
            run.step(segment, action=f"type:{arg}", surface="vm")

        elif verb == "cred":
            value = await lab.credential_value(arg)
            run.redactor.add(value, arg.replace("/", "-").lower())
            await lab.type(value)
            run.step(segment, action=f"cred:{arg}", surface="vm", note=f"{len(value)} chars")

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
                shot = run.next_image(segment, f"{label}-timeout")
                await lab.screen(shot)
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

        elif verb == "shot":
            shot = run.next_image(segment, arg or label)
            await lab.screen(shot)
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

            run = Run.open(args.run) if args.run else Run.latest(RUNS)
            if run is None:
                print("No run folder. Create one with scripts/lab_run.py --start", file=sys.stderr)
                return 2

            if args.start_segment:
                run.start_segment(args.segment, await lab.minutes_remaining())

            findings = await run_actions(lab, run, args.segment, args.label, args.do or [])

            if args.end_segment:
                run.end_segment(args.segment, args.end_segment, await lab.minutes_remaining())

            if args.note:
                run.step(args.segment, verdict=args.verdict, severity=args.severity,
                         note=args.note, instruction_ref=args.ref, surface="analysis")
            print(f"run: {run.dir.name}  segment: {args.segment}  findings this step: {findings}")
            return 0
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
    p.add_argument("--ref", help="instruction anchor for --note, e.g. #setup-env-file")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    try:
        return asyncio.run(main_async(args))
    except (BrowserError, Stop) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
