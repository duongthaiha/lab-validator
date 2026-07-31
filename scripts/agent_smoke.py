"""Exercise the agent's SDK wiring with no lab and no browser.

Every test in ``tests/test_agent.py`` injects a fake ``ask`` and never reaches
the SDK -- which is exactly why none of them noticed that no tool could register
at all. A seam that is always stubbed is a seam nobody has tested.

So this builds a throwaway run and drives it, which reaches the parts a unit
test structurally cannot: does a session start, do the five tools register, do
the hooks arrive in the shape the SDK sends, does a turn come back, does a
finding land in the trace. It found four defects in about ten minutes that 486
passing tests could not see. Run it after any change to ``agent.py``'s SDK half,
and after any SDK upgrade.

``lab_act`` will fail, because there is no lab client. That is useful rather
than a nuisance: a tool erroring is precisely what a blocked lab looks like, and
the right outcome is a BLOCKED finding recorded against the task.

Safety: this creates its own run and primes only the run it created. It takes no
argument naming an existing one, because the priming step below records a step
the walk did not really take -- honest in a fixture, evidence-destroying
anywhere else.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator.corpus import Heading, Outline, Segment  # noqa: E402
from lab_validator.runlog import Run  # noqa: E402

#: Stamped into the manifest so the fixture is identifiable from its contents
#: rather than its name -- `Run.create` names folders by timestamp, so a glob
#: over names cannot tell a fixture from a real walk.
MARKER = "SMOKE FIXTURE - not a real lab"

SHARED_OUTLINE = ROOT / "artifacts" / "instructions" / "outline.json"


def synthetic() -> tuple[Outline, str, Path]:
    """A self-contained one-section lab, for when no corpus has been fetched."""
    corpus = ROOT / "runs" / "smoke-corpus.md"
    corpus.parent.mkdir(parents=True, exist_ok=True)
    corpus.write_text(
        "# Smoke\n"
        "### 1. Note the endpoint\n"
        "Record the endpoint shown in the Resources tab.\n",
        encoding="utf-8",
    )
    outline = Outline(
        title="Smoke",
        headings=[
            Heading(order=0, level=1, id="smoke", text="Smoke"),
            Heading(
                order=1,
                level=3,
                id="1-note-the-endpoint",
                text="1. Note the endpoint",
                body="Record the endpoint shown in the Resources tab.",
            ),
        ],
    )
    return outline, "smoke", corpus


def borrowed() -> tuple[Outline, str, Path] | None:
    """The real corpus, if one has been fetched.

    Preferred, because then ``lab_instructions`` returns text a learner would
    actually read and the prompt under test is the real one. The corpus is
    gitignored, so a fresh clone falls back to ``synthetic()``.
    """
    if not SHARED_OUTLINE.exists():
        return None
    outline = Outline.load(SHARED_OUTLINE)
    # A section that has tasks, so the loop has something to ask PERFORM about.
    # A section without them goes straight to ADVANCE and the model turn -- the
    # whole point of the exercise -- never happens.
    section = next((s for s in outline.sections() if outline.tasks(s)), None)
    corpus = next(SHARED_OUTLINE.parent.glob("*.md"), None)
    if section is None or corpus is None:
        return None
    return outline, section.id, corpus


def sweep(runs_root: Path) -> int:
    """Delete previous fixtures, identified by the marker in their manifest."""
    gone = 0
    for candidate in runs_root.glob("*"):
        manifest = candidate / "run.json"
        if not manifest.is_file():
            continue
        if MARKER in manifest.read_text(encoding="utf-8"):
            shutil.rmtree(candidate)
            gone += 1
    return gone


def build(runs_root: Path) -> Run:
    real = borrowed()
    outline, anchor, corpus = real or synthetic()
    if real is None:
        print(
            "no corpus under artifacts/instructions, so the fixture is synthetic:\n"
            "  lab_instructions will report a command failure, which still\n"
            "  exercises the tool path. Everything else is unaffected."
        )

    run = Run.create(
        runs_root,
        MARKER,
        lab={"id": 0},
        instance="smoke",
        agent="smoke",
        corpus=corpus,
        segments=[Segment(id="s01", title="Smoke", anchor=anchor, module="smoke")],
    )
    outline.save(run.dir / "outline.json")

    # The loop will not call a section read done without a recorded learner
    # scroll, and that refusal is correct -- but it also means the model turn,
    # the tools and the hooks are unreachable on a machine with no lab. This
    # records the scroll so the *rest* of the wiring can be exercised. It is a
    # deliberate lie to the loop, told once, to a run that is not evidence.
    run.step(
        "s01",
        verdict="PASS",
        action="read",
        capability="scroll_instructions",
        note="scrolled (smoke fixture, not a real observation)",
    )
    return run


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--runs", type=Path, default=ROOT / "runs", help="runs root")
    ap.add_argument("--drive", action="store_true", help="run `auto` against it now")
    ap.add_argument("--model", default="", help="pass a specific model to `auto`")
    ap.add_argument("--keep", action="store_true", help="keep earlier fixtures")
    args = ap.parse_args()

    args.runs.mkdir(parents=True, exist_ok=True)
    if not args.keep and (gone := sweep(args.runs)):
        print(f"removed {gone} earlier fixture(s)", flush=True)

    run = build(args.runs)
    print(f"\nfixture: {run.dir}", flush=True)

    if not args.drive:
        print(f"\n  lab-validator auto --run {run.dir}")
        return 0

    argv = [sys.executable, "-m", "lab_validator.cli", "auto", "--run", str(run.dir)]
    if args.model:
        argv += ["--model", args.model]
    # Flushed, because the child writes straight to the terminal while this
    # process's stdout is block-buffered when piped -- so without it the header
    # lands *after* the run it introduces.
    print(f"\n$ {' '.join(argv[2:])}\n", flush=True)
    return subprocess.run(argv, cwd=str(ROOT), check=False).returncode  # noqa: S603


if __name__ == "__main__":
    raise SystemExit(main())
