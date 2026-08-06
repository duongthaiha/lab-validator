"""Start, inspect and report on a validation run.

    python scripts/lab_run.py --start                 # new run from the live lab
    python scripts/lab_run.py --status                # progress of the latest run
    python scripts/lab_run.py --next                  # next section to walk
    python scripts/lab_run.py --report                # write gap-analysis.md
    python scripts/lab_run.py --finish complete
    python scripts/lab_run.py --targets               # list target descriptors
    python scripts/lab_run.py --check-target SLUG     # validate one strictly
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
    script_main,
)
from lab_validator.corpus import Outline, extract  # noqa: E402
from lab_validator.labclient import LabClient  # noqa: E402
from lab_validator.paths import MARKDOWN, OUTLINE, RUNS, TARGETS  # noqa: E402
from lab_validator.report import render, write_segment  # noqa: E402
from lab_validator.runlog import Run, RunNotFound  # noqa: E402
from lab_validator.targets import Target, TargetError  # noqa: E402
from lab_validator.vault import Vault  # noqa: E402


def load_target(slug: str) -> Target:
    try:
        return Target.load(slug, root=TARGETS)
    except TargetError as exc:
        raise BrowserError(str(exc)) from exc


def cmd_targets(args) -> int:
    """List descriptors, or validate one. The onboarding entry point."""
    if args.check_target:
        try:
            target = Target.load(args.check_target, root=TARGETS, strict=True)
        except TargetError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(target.summary())
        print("\nOK - descriptor is valid.")
        return 0

    slugs = Target.available(TARGETS)
    if not slugs:
        print(f"No target descriptors in {TARGETS}")
        return 1
    for slug in slugs:
        try:
            target = Target.load(slug, root=TARGETS)
            warn = len(target.problems)
            flag = f"  ({warn} warning{'s' if warn != 1 else ''})" if warn else ""
            print(f"  {slug:<24} {target.name}{flag}")
        except TargetError:
            print(f"  {slug:<24} !! invalid -- run --check-target {slug}")
    return 0


async def cmd_start(args) -> int:
    slug = args.target or Target.default(TARGETS)
    target = load_target(slug)
    for problem in target.problems:
        print(f"descriptor: {problem}", file=sys.stderr)
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, args.port)
        try:
            lab = LabClient.find(context)
            outline = await extract(lab.instructions)
            outline.save(OUTLINE)
            MARKDOWN.write_text(outline.to_markdown(), encoding="utf-8")

            run = Run.create(
                RUNS,
                target.name,
                lab=target.lab,
                instance=lab.instance_id,
                corpus=MARKDOWN,
                agent=args.agent,
                segments=outline.segments(),
            )
            run.manifest["targetSlug"] = slug
            run.manifest["labMinutesAtStart"] = await lab.minutes_remaining()
            run.manifest["structuralAnomalies"] = [
                {"code": a.code, "severity": a.severity, "message": a.message}
                for a in outline.anomalies()
            ]
            run._save()

            # Capture the lab's own credentials once, at the start. Two jobs in
            # one action: every value is registered with the redactor so it can
            # never reach the trace whatever a later step does, and the rows are
            # kept so the run can use a credential as *data* -- which is what
            # makes it possible to compare what the lab hands out against what
            # the lab ships.
            try:
                vault = Vault.capture(await lab.credentials(), run.redactor)
                vault.save(run.dir)
                await lab.show_instructions()
            except Exception as exc:
                vault = None
                run.log(f"credential capture skipped: {type(exc).__name__}: {exc}")

            print(f"run       : {run.dir}")
            print(f"instance  : {lab.instance_id}")
            print(f"lab clock : {run.manifest['labMinutesAtStart']} min")
            print(f"segments  : {len(outline.segments())}")
            print(f"anomalies : {len(outline.anomalies())} structural")
            print(f"secrets   : {len(run.redactor)} registered for redaction")
            if vault is not None:
                print(f"vault     : {len(vault)} credential(s) captured "
                      f"-> {Vault.path_in(run.dir).name} (gitignored)")
            else:
                print("vault     : none -- credential reuse will fall back to the "
                      "Resources tab")
            if not target.is_enriched:
                print("descriptor: none -- observation-based findings only; "
                      "no expectation can be checked")
            return 0
        finally:
            await browser.close()


def latest(args) -> Run:
    try:
        return Run.open_or_latest(RUNS, args.run)
    except RunNotFound as exc:
        raise BrowserError(str(exc)) from exc


def cmd_status(args) -> int:
    run = latest(args)
    s = run.summary()
    print(f"run      : {run.dir.name}   status: {run.manifest.get('status')}")
    print(f"instance : {run.manifest.get('instance')}")
    print(f"steps    : {s['steps']} (+{s['heartbeats']} heartbeats)")
    print(f"verdicts : {s['verdicts']}")
    seg = s["segments"]
    print(f"segments : {seg['done']}/{seg['total']} done, {seg['blocked']} blocked, "
          f"{len(seg['never_reached'])} not reached")
    print()
    for item in run.segments():
        mark = {"done": "x", "in_progress": ">", "blocked": "!", "skipped": "-"}.get(
            item.status, " "
        )
        print(f"  [{mark}] {item.id:<34} {(item.title or '')[:42]}")
    return 0


def cmd_next(args) -> int:
    run = latest(args)
    pending = run.pending_segments()
    if not pending:
        print("all segments complete")
        return 0
    seg = pending[0]
    print(f"{seg['id']}\t{seg.get('anchor', '')}\t{seg.get('title', '')}")
    return 0


def cmd_report(args) -> int:
    run = latest(args)
    outline = Outline.load(OUTLINE) if OUTLINE.exists() else None
    anomalies = outline.anomalies() if outline else []

    # Sections first: the roll-up links to them, and a link to a file that was
    # never written is worse than no link at all.
    written = 0
    for segment in run.segments():
        if segment.status == "pending":
            continue
        write_segment(run, segment, outline)
        written += 1

    text = render(run, outline, anomalies)
    out = run.dir / "gap-analysis.md"
    out.write_text(text, encoding="utf-8")
    print(f"-> {out}  ({len(text):,} chars)")
    print(f"-> {written} section report(s) under {run.dir / 'sections'}")
    return 0


def cmd_retract(args) -> int:
    run = latest(args)
    if not args.note:
        raise BrowserError("--retract requires --note explaining why it was withdrawn")
    rec = run.retract(args.retract, args.note)
    print(f"retracted seq {args.retract} (retraction is seq {rec['seq']})")
    return 0


def cmd_finish(args) -> int:
    run = latest(args)
    run.finish(args.finish)
    return cmd_report(args)


@script_main
def main() -> int:
    p = argparse.ArgumentParser(description="Start, inspect and report on a validation run.")
    p.add_argument("--start", action="store_true", help="create a run from the live lab")
    p.add_argument("--status", action="store_true", help="progress of the latest run")
    p.add_argument("--next", action="store_true", help="next section to walk")
    p.add_argument("--report", action="store_true", help="write gap-analysis.md")
    p.add_argument("--finish", metavar="STATUS", help="seal the run and report")
    p.add_argument("--retract", type=int, metavar="SEQ", help="withdraw a finding by seq")
    p.add_argument("--note", help="reason, required with --retract")
    p.add_argument(
        "--target",
        default=None,
        help="target descriptor slug (default: the only one on disk)",
    )
    p.add_argument("--targets", action="store_true", help="list available target descriptors")
    p.add_argument("--check-target", metavar="SLUG", help="validate a descriptor strictly")
    p.add_argument("--agent", default="copilot-cli", help="who is driving")
    p.add_argument("--run", help="run folder (default: most recent)")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    if args.targets or args.check_target:
        return cmd_targets(args)
    if args.start:
        return asyncio.run(cmd_start(args))
    if args.retract is not None:
        return cmd_retract(args)
    if args.finish:
        return cmd_finish(args)
    if args.report:
        return cmd_report(args)
    if args.next:
        return cmd_next(args)
    return cmd_status(args)


if __name__ == "__main__":
    raise SystemExit(main())
