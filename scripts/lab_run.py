"""Start, inspect and report on a validation run.

    python scripts/lab_run.py --start                 # new run from the live lab
    python scripts/lab_run.py --status                # progress of the latest run
    python scripts/lab_run.py --next                  # next section to walk
    python scripts/lab_run.py --report                # write gap-analysis.md
    python scripts/lab_run.py --finish complete
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
)
from lab_validator.corpus import Outline, extract  # noqa: E402
from lab_validator.labclient import LabClient  # noqa: E402
from lab_validator.report import render  # noqa: E402
from lab_validator.runlog import Run  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs"
TARGETS = ROOT / "targets"
OUTLINE = ROOT / "artifacts" / "instructions" / "outline.json"
MARKDOWN = ROOT / "artifacts" / "instructions" / "outline.md"


def load_target(slug: str) -> dict:
    path = TARGETS / f"{slug}.toml"
    if not path.exists():
        raise BrowserError(f"No target descriptor at {path}")
    return tomllib.loads(path.read_text("utf-8"))


async def cmd_start(args) -> int:
    target = load_target(args.target)
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, args.port)
        try:
            lab = LabClient.find(context)
            outline = await extract(lab.instructions)
            outline.save(OUTLINE)
            MARKDOWN.write_text(outline.to_markdown(), encoding="utf-8")

            run = Run.create(
                RUNS,
                target.get("name", args.target),
                lab=target.get("lab", {}),
                instance=lab.instance_id,
                corpus=MARKDOWN,
                agent=args.agent,
                segments=outline.segments(),
            )
            run.manifest["targetSlug"] = args.target
            run.manifest["labMinutesAtStart"] = await lab.minutes_remaining()
            run.manifest["structuralAnomalies"] = [
                {"code": a.code, "severity": a.severity, "message": a.message}
                for a in outline.anomalies()
            ]
            run._save()

            # Credential values are registered with the redactor up front so
            # they can never reach the trace, whatever a later step does.
            try:
                for cred in await lab.credentials():
                    run.redactor.add(cred.value, f"{cred.scope}-{cred.label}".lower())
                await lab.show_instructions()
            except Exception as exc:
                run.log(f"credential preload skipped: {type(exc).__name__}")

            print(f"run       : {run.dir}")
            print(f"instance  : {lab.instance_id}")
            print(f"lab clock : {run.manifest['labMinutesAtStart']} min")
            print(f"segments  : {len(outline.segments())}")
            print(f"anomalies : {len(outline.anomalies())} structural")
            print(f"secrets   : {len(run.redactor)} registered for redaction")
            return 0
        finally:
            await browser.close()


def latest(args) -> Run:
    run = Run.open(args.run) if args.run else Run.latest(RUNS)
    if run is None:
        raise BrowserError("No run folder yet. Start one with --start.")
    return run


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
    for item in run.manifest.get("segments", []):
        mark = {"done": "x", "in_progress": ">", "blocked": "!", "skipped": "-"}.get(
            item.get("status"), " "
        )
        print(f"  [{mark}] {item['id']:<34} {item.get('title', '')[:42]}")
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
    text = render(run, outline, anomalies)
    out = run.dir / "gap-analysis.md"
    out.write_text(text, encoding="utf-8")
    print(f"-> {out}  ({len(text):,} chars)")
    return 0


def cmd_finish(args) -> int:
    run = latest(args)
    run.finish(args.finish)
    return cmd_report(args)


def main() -> int:
    p = argparse.ArgumentParser(description="Start, inspect and report on a validation run.")
    p.add_argument("--start", action="store_true", help="create a run from the live lab")
    p.add_argument("--status", action="store_true", help="progress of the latest run")
    p.add_argument("--next", action="store_true", help="next section to walk")
    p.add_argument("--report", action="store_true", help="write gap-analysis.md")
    p.add_argument("--finish", metavar="STATUS", help="seal the run and report")
    p.add_argument("--target", default="azure-ai-platform", help="target descriptor slug")
    p.add_argument("--agent", default="copilot-cli", help="who is driving")
    p.add_argument("--run", help="run folder (default: most recent)")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    try:
        if args.start:
            return asyncio.run(cmd_start(args))
        if args.finish:
            return cmd_finish(args)
        if args.report:
            return cmd_report(args)
        if args.next:
            return cmd_next(args)
        return cmd_status(args)
    except BrowserError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
