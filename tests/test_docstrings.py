"""Every runtime module must orient a new reader, and must not lie while doing it.

The module docstrings in this repo are unusually good at explaining *why* a file
exists -- `console.py` opens with the live run that recorded PASS on all 77 steps
while doing nothing at all. What none of them did was answer the three questions
somebody opening the file for the first time asks first: what do I call, what
does this talk to, and where does it sit. Those facts were consistently absent,
which is what made a set of well-written docstrings read as inconsistent.

The `Orientation` block carries them. These tests exist because a block of
hand-maintained metadata next to code is worth nothing once it drifts: a docstring
naming an entry point that was renamed away still reads perfectly, and sends its
reader looking for a symbol that is not there. Two of the three fields are
checkable against the AST, so they are checked.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = sorted((ROOT / "src" / "lab_validator").glob("*.py")) + sorted(
    (ROOT / "scripts").glob("*.py")
)

HEADING = "Orientation\n-----------\n"
FIELD = re.compile(r"^(Role|Entry|Talks to):\s+(.*\S)\s*$")
BACKTICKED = re.compile(r"`([^`]+)`")

#: A module may legitimately depend on no sibling and export no callable --
#: `paths.py` is a table of constants, `__init__.py` is a marker. Spelling that
#: out as a word beats leaving the field blank, which reads like an oversight.
NONE = "nothing"


def modules() -> list[Path]:
    return RUNTIME


def docstring_of(path: Path) -> str:
    """Read the docstring without importing.

    `scripts/*.py` put `src/` on `sys.path` and run argparse at import time, and
    `cli._load` executes them under a synthetic module name that is never
    registered. Importing them here to read `__doc__` would run all of that.
    """
    return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"))) or ""


def orientation(path: Path) -> dict[str, str]:
    """The block's fields, or `{}` when the module has no block at all."""
    doc = docstring_of(path)
    if HEADING not in doc:
        return {}
    fields = {}
    for line in doc.split(HEADING, 1)[1].splitlines():
        if not line.strip():
            continue
        matched = FIELD.match(line.strip())
        if matched:
            fields[matched.group(1)] = matched.group(2)
    return fields


def defined_names(path: Path) -> set[str]:
    """Module-level definitions only -- what this file actually provides."""
    names: set[str] = set()
    for node in ast.parse(path.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def imported_siblings(path: Path) -> set[str]:
    """Sibling `lab_validator` modules this file imports.

    `src/` says `from .runlog import Run` and `scripts/` says
    `from lab_validator.runlog import Run`; both land here as `runlog`.
    """
    siblings: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.level == 1:
                siblings.add(node.module.split(".")[0])
            elif node.module.startswith("lab_validator."):
                siblings.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("lab_validator."):
                    siblings.add(alias.name.split(".")[1])
    return siblings


def test_every_runtime_module_orients_a_new_reader():
    """A module with no block is a module a newcomer has to reverse-engineer.

    Without this the convention would hold for whichever files somebody got
    round to, and the next reader would have no way to tell "this module has no
    collaborators" from "nobody filled this in".
    """
    for path in modules():
        fields = orientation(path)
        assert fields, f"{path.name} has no Orientation block"
        assert list(fields) == ["Role", "Entry", "Talks to"], (
            f"{path.name} lists {list(fields)}, expected Role, Entry, Talks to in that order"
        )


def test_an_entry_point_named_in_a_docstring_still_exists():
    """A rename leaves the docstring reading perfectly and pointing nowhere.

    That is the whole hazard of hand-written module metadata: nothing about
    `Entry: ``render_section``` looks stale after `render_section` becomes
    `render`, so the reader concludes their checkout is wrong.
    """
    for path in modules():
        entry = orientation(path).get("Entry", "")
        if entry == NONE:
            continue
        named = BACKTICKED.findall(entry)
        assert named, f"{path.name} Entry names nothing; say '{NONE}' if that is deliberate"
        defined = defined_names(path)
        unknown = sorted({n.split(".")[0] for n in named} - defined)
        assert not unknown, f"{path.name} Entry names undefined: {unknown}"


def test_a_module_cannot_claim_a_collaborator_it_dropped():
    """The other direction: dependencies get deleted more quietly than they get added.

    A `Talks to:` line surviving the removal of the import it describes turns
    the block into a map of the architecture as it used to be.
    """
    for path in modules():
        claimed = orientation(path).get("Talks to", "")
        if claimed == NONE:
            continue
        names = [n.strip() for n in claimed.split(",") if n.strip()]
        assert names, f"{path.name} Talks to is empty; say '{NONE}' if that is deliberate"
        actual = imported_siblings(path)
        missing = sorted(n for n in names if n not in actual)
        assert not missing, f"{path.name} claims to talk to {missing} but imports no such module"


def test_orientation_never_displaces_the_rationale():
    """The block goes last, and this is the test that keeps it there.

    The first screen of `console.py` is the story of the run that passed 77
    steps without touching a pixel -- the reason the module exists at all.
    Hoisting a metadata table above it would be an obvious tidy-up to make and
    would bury the most valuable paragraph in the repository below the fold.
    """
    for path in modules():
        doc = docstring_of(path)
        assert HEADING in doc, f"{path.name} has no Orientation block"
        before, after = doc.split(HEADING, 1)
        assert before.strip(), f"{path.name} opens with the block; the rationale must come first"
        for line in after.splitlines():
            assert not line.strip() or FIELD.match(line.strip()), (
                f"{path.name} has prose after the Orientation block: {line!r}"
            )
