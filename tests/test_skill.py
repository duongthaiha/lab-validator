"""The skill must not teach commands that do not exist.

A skill is documentation that an agent will follow literally and at speed. A
flag that was renamed, or a sub-command that never existed, does not produce a
helpful error -- it produces a run that dies partway through a lab with a human
waiting. This is the same rot the taxonomy and the CLI dispatch table both
suffered: a table drifting away from the thing it describes, with nothing
noticing until it reached someone who trusted it.

So: parse every ``lab-validator`` invocation out of the skill and check it
against the real argparse surface.

The copy under ``skills/`` in this repo is the source of truth, because a skill
that lives only in ``~/.copilot/skills`` is unreviewable, unversioned and lost
with the machine. The installed copy is a deployment of it, and the last test
here guards the two against drifting apart.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator import cli  # noqa: E402

SKILL = ROOT / "skills" / "lab-validator" / "SKILL.md"
INSTALLED = Path.home() / ".copilot" / "skills" / "lab-validator" / "SKILL.md"

INVOCATION = re.compile(r"^\s*lab-validator\s+(?P<rest>.+?)\s*$", re.M)


def invocations() -> list[str]:
    body = SKILL.read_text(encoding="utf-8")
    # Continuation lines end with a PowerShell backtick; join them first.
    body = re.sub(r"`\r?\n\s*", " ", body)
    return [m.group("rest") for m in INVOCATION.finditer(body)]


def flags_of(command: str) -> set[str]:
    """The real long options a sub-command accepts.

    Scraped rather than listed. A hand-kept copy of a flag list is a second
    source of truth that goes stale silently, and this test exists precisely to
    catch documentation drifting from code — it should not be the thing drifting.
    """
    if command in cli.BUILTINS:
        src = Path(cli.__file__).read_text(encoding="utf-8")
        # main() builds each built-in's parser inside its own dispatch block.
        blocks = src.split('if args.command == "')
        block = next((b for b in blocks if b.startswith(f'{command}"')), None)
        assert block is not None, f"no dispatch block for built-in {command!r}"
        block = block.split("return ", 1)[0]
        return set(re.findall(r'add_argument\(\s*"(--[a-z][a-z0-9-]*)"', block)) | {"--help"}
    module = cli._load(cli.COMMANDS[command][0])
    src = (cli.SCRIPTS / cli.COMMANDS[command][0]).read_text(encoding="utf-8")
    assert module is not None
    return set(re.findall(r'"(--[a-z][a-z0-9-]*)"', src)) | {"--help"}


def test_the_skill_contains_commands_at_all():
    """A guard on the guard: if the parsing regex ever stops matching, every
    other test here would pass vacuously."""
    assert len(invocations()) >= 8


@pytest.mark.parametrize("line", invocations())
def test_every_documented_command_exists(line):
    command = line.split()[0]
    assert command in cli.BUILTINS or command in cli.COMMANDS, (
        f"the skill documents `lab-validator {command}`, which is not a command"
    )


@pytest.mark.parametrize("line", invocations())
def test_every_documented_flag_exists(line):
    parts = line.split()
    command, rest = parts[0], parts[1:]
    real = flags_of(command)
    used = {p for p in rest if p.startswith("--")}
    unknown = sorted(used - real)
    assert not unknown, f"`lab-validator {command}` has no {unknown} (real: {sorted(real)})"


def test_documented_verdict_codes_are_real():
    from lab_validator.taxonomy import VERDICTS

    body = SKILL.read_text(encoding="utf-8")
    used = set(re.findall(r"\b(LAB\d{3})\b", body))
    assert used, "the skill should name at least one verdict code"
    assert not used - set(VERDICTS), f"unknown codes in the skill: {sorted(used - set(VERDICTS))}"


def test_documented_domains_are_real():
    from lab_validator.taxonomy import DOMAINS

    body = SKILL.read_text(encoding="utf-8")
    for used in re.findall(r"--domain\s+(\w+)", body):
        assert used in DOMAINS, f"--domain {used} is not one of {DOMAINS}"


def test_every_referenced_reference_file_is_present():
    body = SKILL.read_text(encoding="utf-8")
    for name in set(re.findall(r"references/([a-z-]+\.md)", body)):
        assert (SKILL.parent / "references" / name).exists(), f"references/{name} is missing"


def test_no_reference_file_is_orphaned():
    """An unreferenced reference is one nothing will ever load."""
    body = SKILL.read_text(encoding="utf-8")
    for path in (SKILL.parent / "references").glob("*.md"):
        assert path.name in body, f"references/{path.name} is never referenced from SKILL.md"


def test_the_skill_stays_within_the_progressive_disclosure_budget():
    """Past ~500 lines the body stops being something an agent reads and starts
    being something it skims."""
    assert len(SKILL.read_text(encoding="utf-8").splitlines()) < 500


def test_the_description_carries_triggers():
    head = SKILL.read_text(encoding="utf-8").split("---", 2)[1]
    assert "Triggers:" in head, "without triggers the skill will not be matched to a request"


@pytest.mark.skipif(not INSTALLED.exists(), reason="the skill is not installed here")
def test_the_installed_copy_has_not_drifted_from_the_repo():
    """The tests above check the repo copy; the agent reads the installed one.
    Without this, the reviewed version and the running version are free to
    disagree -- and the running one wins, silently."""
    repo_files = sorted(p.relative_to(SKILL.parent) for p in SKILL.parent.rglob("*.md"))
    for rel in repo_files:
        live = INSTALLED.parent / rel
        assert live.exists(), f"{rel} is in the repo but not installed; re-run the install step"
        assert (
            live.read_text(encoding="utf-8") == (SKILL.parent / rel).read_text(encoding="utf-8")
        ), f"{rel} differs between the repo and ~/.copilot/skills; the repo is the source of truth"


def test_the_steps_are_numbered_sequentially_from_one():
    """An agent executes these in order, so a duplicate or gap misroutes a walk.

    Written after inserting a step renumbered the one below it into a collision:
    two "Step 5" headings, no error, and nothing to notice it.
    """
    body = SKILL.read_text(encoding="utf-8")
    numbers = [int(n) for n in re.findall(r"^## Step (\d+) . ", body, re.M)]
    assert numbers, "the skill must have numbered steps at all"
    assert numbers == list(range(1, len(numbers) + 1)), numbers


def test_every_referenced_step_number_exists():
    body = SKILL.read_text(encoding="utf-8")
    numbers = {int(n) for n in re.findall(r"^## Step (\d+) . ", body, re.M)}
    for cited in re.findall(r"\(see Step (\d+)\)", body):
        assert int(cited) in numbers, f"Step {cited} is cited but does not exist"