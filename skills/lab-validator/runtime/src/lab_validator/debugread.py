"""Read a run back afterwards and say what it actually did.

The run this was written for was recorded weeks before any of it existed, and
its frames held the answer the whole time. So the reader does not require the
run to have been instrumented: given a folder, it measures the images on disk
and reconstructs the same picture. A diagnostic that only works when you already
knew you would need it is not much of a diagnostic.

What it reports is what happened to the screen, action by action. What it does
not do is decide *why*, and the reason is written into `console.py`: the first
version of this feature measured twenty-four identical frames, concluded the
console had frozen, and was wrong -- the console was fine, and the walk was
typing URLs at a desktop with no browser open. The numbers were right and the
story was invented. So this prints the numbers, the actions beside them, and the
frames to go and look at.
"""

from __future__ import annotations

import json
from pathlib import Path

from .console import DebugLog, replay


def _trace(run_dir: Path) -> list[dict]:
    path = Path(run_dir) / "trace.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def _frames(run_dir: Path) -> list[Path]:
    images = (Path(run_dir) / "images").glob("[0-9][0-9][0-9][0-9]-*")
    return sorted(p for p in images if "view" not in p.name)


def report(run_dir: Path, tail: int = 0, moved: bool | None = None) -> str:
    """Render the diagnostic view of a run.

    ``tail`` limits the output to the last N intervals -- the usual question is
    "what was it doing when it stopped", and a 1 000-image run answers that
    badly at full length. ``moved=False`` shows only the intervals where input
    went in and nothing came back, which is the shape of a stuck walk.
    """
    run_dir = Path(run_dir)
    if not (run_dir / "run.json").exists():
        inside = sorted(p.name for p in run_dir.glob("*") if (p / "run.json").exists())
        if inside:
            listed = "\n".join(f"  {n}" for n in inside[-10:])
            raise FileNotFoundError(
                f"{run_dir} is a runs root, not a run. Runs inside it:\n{listed}"
            )
        raise FileNotFoundError(f"not a run folder (no run.json): {run_dir}")

    frames = _frames(run_dir)
    steps = _trace(run_dir)
    logged = DebugLog.read(run_dir)
    watch = replay(frames, steps)

    lines = [
        f"# {run_dir.name}",
        "",
        f"{len(frames)} captures, {len(steps)} trace records, "
        f"{len(logged)} debug records"
        f"{' (run was not instrumented -- measured from the images)' if not logged else ''}",
        f"idle noise measured from this run: {watch.idle_floor:.4f}",
        "",
    ]

    intervals = watch.intervals
    if moved is not None:
        intervals = [i for i in intervals if i.moved is moved and i.had_input]
    shown = intervals[-tail:] if tail else intervals
    if len(shown) < len(intervals):
        lines.append(f"(showing the last {len(shown)} of {len(intervals)})")
        lines.append("")

    lines.append(f"{'capture':<40}{'delta':>9}  {'effect':<9}  actions")
    lines.append("-" * 100)
    for i in shown:
        if not i.had_input:
            effect = "--"
        elif i.moved:
            effect = "moved"
        else:
            effect = "NO CHANGE"
        acts = ", ".join(i.actions) or "(none)"
        lines.append(f"{i.label[:40]:<40}{i.delta:>9.3f}  {effect:<9}  {acts[:80]}")

    dead = [i for i in watch.intervals if i.unmoved_input]
    lines += [
        "",
        f"{len(dead)} of {sum(1 for i in watch.intervals if i.had_input)} input "
        "intervals changed nothing on screen.",
    ]

    notice = watch.notice()
    if notice:
        lines += ["", "## The walk was stuck when it stopped", "", notice]

    if frames:
        lines += [
            "",
            f"Last capture: images/{frames[-1].name}",
            "Open it. Whatever the numbers say, the screen is the evidence.",
        ]
    return "\n".join(lines)
