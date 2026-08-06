"""Where the tool keeps things on disk.

Five modules used to each redefine ``ROOT / "artifacts" / "instructions" /
"outline.json"`` from their own ``Path(__file__).parents[N]``. That is five
chances to disagree about the layout, and the ``parents`` index differs between
``scripts/`` (1) and ``src/lab_validator/`` (2), so the copies were not even
textually the same. One home instead.

``scripts/*.py`` still compute their own ``ROOT`` before importing anything --
they need it to put ``src/`` on ``sys.path`` in the first place -- but they take
the artifact paths from here.

Orientation
-----------
Role:     one home for the repo, run and artifact paths every other module needs.
Entry:    `REPO_ROOT`, `RUNS`, `TARGETS`, `OUTLINE`
Talks to: nothing
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["INSTRUCTIONS", "MARKDOWN", "OUTLINE", "REPO_ROOT", "RUNS", "TARGETS"]

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNS = REPO_ROOT / "runs"
TARGETS = REPO_ROOT / "targets"
INSTRUCTIONS = REPO_ROOT / "artifacts" / "instructions"
OUTLINE = INSTRUCTIONS / "outline.json"
MARKDOWN = INSTRUCTIONS / "outline.md"
