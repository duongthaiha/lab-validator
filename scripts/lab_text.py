"""Print the instruction text for a segment, so a step can be checked against its source.

The walker needs the exact wording a learner would read. Reading it from the saved
outline rather than the live frame keeps the text stable for the whole run and ties
every finding to the corpus the manifest hashed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator.corpus import Outline  # noqa: E402
from lab_validator.paths import OUTLINE, RUNS  # noqa: E402
from lab_validator.runlog import Run, RunNotFound  # noqa: E402


def resolve(outline: Outline, run: Run, segment: str):
    """Find the section heading a segment id points at."""
    for seg in run.segments():
        if seg.id == segment or seg.id.startswith(segment):
            head = outline.section_by_anchor(seg.anchor)
            if head is None:
                raise SystemExit(f"segment '{seg.id}' anchor {seg.anchor} not in outline")
            return seg, head
    known = ", ".join(s.id for s in run.segments())
    raise SystemExit(f"unknown segment '{segment}'; known ids: {known}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--segment", required=True, help="segment id or unique prefix")
    ap.add_argument("--run", type=Path, help="run folder (default: most recent)")
    ap.add_argument("--tasks", action="store_true", help="list task headings only")
    ap.add_argument("--start", type=int, default=0, help="first line to print")
    ap.add_argument("--lines", type=int, default=0, help="how many lines (0 = all)")
    args = ap.parse_args()

    try:
        run = Run.open_or_latest(RUNS, args.run)
    except RunNotFound as exc:
        raise SystemExit(str(exc)) from exc
    outline = Outline.load(OUTLINE)
    seg, head = resolve(outline, run, args.segment)

    if args.tasks:
        print(f"{seg.id}  {seg.title}  [{seg.module}]")
        for task in outline.tasks(head):
            print(f"  h{task.level}  {task.text}")
        return 0

    body = outline.section_text(head).splitlines()
    end = args.start + args.lines if args.lines else len(body)
    print(f"# {seg.id}  {seg.title}  [{seg.module}]  {seg.anchor}")
    print(f"# lines {args.start}-{min(end, len(body))} of {len(body)}\n")
    for n, line in enumerate(body[args.start : end], start=args.start):
        print(f"{n:4} | {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
