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

INVOCATION = re.compile(r"^[ \t]*lab-validator[ \t]+(?P<rest>.+?)[ \t]*$", re.M)

# The README is executed too -- by a human following it, which is the same
# failure with a slower feedback loop. A guide that teaches a renamed flag does
# not produce a helpful error; it produces a run that dies partway through a lab
# with somebody waiting on it. So both documents get the same guard.
README = ROOT / "README.md"
# `docs/agent.md` is executed the same way: someone whose unattended walk has
# just stopped, copying a resume command out of it at speed.
AGENT_DOC = ROOT / "docs" / "agent.md"
DOCS = {"SKILL.md": SKILL, "README.md": README, "docs/agent.md": AGENT_DOC}

#: How many invocations each document must yield for the vacuity guard to mean
#: anything. The regex is shared, so one command-dense document proves it still
#: matches; a focused document only has to prove it was parsed at all. Set from
#: what each file is *for*, not from what it happens to contain today.
MINIMUM = {"SKILL.md": 8, "README.md": 8, "docs/agent.md": 2}


def invocations(path: Path = SKILL) -> list[str]:
    body = path.read_text(encoding="utf-8")
    # Continuation lines end with a PowerShell backtick; join them first.
    body = re.sub(r"`\r?\n\s*", " ", body)
    # Both docs annotate examples with an aligned trailing comment. Require two
    # spaces before the `#` so a real argument that contains one -- an
    # instruction anchor like `--ref #setup-env-file` -- is not truncated into a
    # different, still-plausible command.
    body = re.sub(r"[ \t]{2,}#.*$", "", body, flags=re.M)
    return [m.group("rest").strip() for m in INVOCATION.finditer(body) if m.group("rest").strip()]


def documented() -> list[tuple[str, str]]:
    return [(name, line) for name, path in DOCS.items() for line in invocations(path)]


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


@pytest.mark.parametrize("name", sorted(DOCS))
def test_the_docs_contain_commands_at_all(name):
    """A guard on the guard: if the parsing regex ever stops matching, every
    other test here would pass vacuously."""
    found = len(invocations(DOCS[name]))
    assert found >= MINIMUM[name], f"{name} yielded {found} commands, expected {MINIMUM[name]}"


@pytest.mark.parametrize("doc,line", documented())
def test_every_documented_command_exists(doc, line):
    command = line.split()[0]
    assert command in cli.BUILTINS or command in cli.COMMANDS, (
        f"{doc} documents `lab-validator {command}`, which is not a command"
    )


@pytest.mark.parametrize("doc,line", documented())
def test_every_documented_flag_exists(doc, line):
    parts = line.split()
    command, rest = parts[0], parts[1:]
    real = flags_of(command)
    used = {p for p in rest if p.startswith("--")}
    unknown = sorted(used - real)
    assert not unknown, f"{doc}: `lab-validator {command}` has no {unknown} (real: {sorted(real)})"


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

# --- Structure, not just commands -------------------------------------------
#
# A guidance document has a second way to mislead, and it is quieter than a
# renamed flag: its own structure can drift out of reach of the tools used to
# navigate it. Both tests below were written after that happened. Two whole
# sections of `approach.md` -- and one top-level heading -- had been written
# indented by two spaces. Markdown still renders an indented ATX heading, so
# nothing looked wrong and nothing failed. But every `^###` search missed them,
# so the document's own author could not see the sections existed and wrote a
# cross-reference to the wrong one.

GUIDANCE = ROOT / "docs" / "approach.md"


@pytest.mark.parametrize("name", sorted(DOCS) + ["docs/approach.md"])
def test_no_heading_is_hidden_from_a_plain_search(name):
    """Headings start at column 0, so `^#` finds every one of them.

    Indented headings render fine and are therefore invisible until someone
    greps for a section, gets nothing, and concludes it does not exist.
    """
    path = DOCS.get(name) or GUIDANCE
    hidden = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if re.match(r"[ \t]+#{1,6} \S", line) and not line.lstrip().startswith("#!")
    ]
    assert not hidden, f"{name}: indented headings are invisible to a plain search: {hidden}"


def test_every_section_cross_reference_resolves():
    """A cited section number must be a section that exists.

    Scoped to `approach.md` deliberately. `gapanalysis.md` also writes things
    like "Required Lab Setup S5", but there the section belongs to the *lab
    under test*, not to the document -- a different namespace that happens to
    share a sigil, and checking it against local headings would be nonsense.

    Honest limit: this catches a reference to a section that is not there. It
    cannot catch a reference that resolves to the *wrong* section, which is the
    mistake that prompted it. Only reading catches that one.
    """
    body = GUIDANCE.read_text(encoding="utf-8")
    headings = set(re.findall(r"^#{1,6} (\d+(?:\.\d+[a-z]?)?)[ .]", body, re.M))
    assert headings, "approach.md must have numbered sections at all"
    cited = {m.group(1) for m in re.finditer(r"\u00a7\s?(\d+(?:\.\d+[a-z]?)?)", body)}
    missing = sorted(cited - headings)
    assert not missing, f"approach.md cites sections that do not exist: {missing}"

# --- the map -----------------------------------------------------------------
#
# The README's Layout block is the only index of what this project contains.
# Both tests below were written after it had silently fallen five modules
# behind -- including `agent.py`, the entire autonomous walker. A stale listing
# renders perfectly; a reader simply concludes the code is not there and either
# writes it again or gives up. Neither failure leaves a trace.

CODE = {
    "src/lab_validator": lambda p: p.name != "__init__.py",
    "scripts": lambda p: True,
}


def layout_cites() -> set[str]:
    body = README.read_text(encoding="utf-8")
    return set(re.findall(r"^((?:src/lab_validator|scripts)/\S+\.py)", body, re.M))


def code_files() -> set[str]:
    return {
        f"{folder}/{p.name}"
        for folder, keep in CODE.items()
        for p in (ROOT / folder).glob("*.py")
        if keep(p)
    }


def test_the_layout_lists_every_module_and_script():
    missing = sorted(code_files() - layout_cites())
    assert not missing, f"README's Layout never mentions: {missing}"


def test_the_layout_lists_nothing_that_is_gone():
    """The other direction, which is the one that misleads hardest.

    A listed file that no longer exists sends a reader looking for something
    that was deleted, and the natural conclusion is that their checkout is
    broken rather than that the map is.
    """
    gone = sorted(layout_cites() - code_files())
    assert not gone, f"README's Layout lists files that do not exist: {gone}"

def test_every_test_named_in_the_docs_exists():
    """Citing a test by name is a promise that it is still called that.

    `agent.md` points at the guards that make its claims true -- "the
    set-equality test will fail otherwise" is only reassuring if that test is
    still there under that name. A rename leaves the sentence reading perfectly
    while the guarantee behind it has quietly moved.
    """
    suite = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py"))
    defined = set(re.findall(r"^def (test_\w+)", suite, re.M))
    for name, path in DOCS.items():
        cited = set(re.findall(r"\b(test_[a-z0-9_]{12,})\b", path.read_text(encoding="utf-8")))
        unknown = sorted(cited - defined)
        assert not unknown, f"{name} names tests that do not exist: {unknown}"


# --- Documented syntax, not just documented flags ---------------------------
#
# The checks above prove `--sections` is a real flag. They say nothing about
# whether the *values* beside it are ones the parser accepts -- and that is
# where this flag has already gone wrong once. The review printed a `#` column
# the parser refused every number from, and the plausible correction (`s05` for
# the row labelled `5`) resolved to a different section. A doc that teaches a
# refused syntax is a bug report waiting to be filed against the tool; a doc
# that teaches a syntax which quietly selects the wrong thing is worse.

SECTIONS_FLAG = re.compile(r"--sections\s+([^\s#`]+)")
SECTION_ID = re.compile(r"\bs(\d{2})-([a-z0-9][a-z0-9-]*)\b")
SYNTAX_DOCS = dict(DOCS, **{"docs/approach.md": ROOT / "docs" / "approach.md"})


def _documented_sections_expressions() -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for name, path in SYNTAX_DOCS.items():
        for m in SECTIONS_FLAG.finditer(path.read_text(encoding="utf-8")):
            expr = m.group(1).strip().strip("`'\"")
            # `<expr>` and `...` are placeholders standing in for a value, not
            # values. Everything else is being offered to a reader as typable.
            if not expr or expr.startswith(("<", ".")):
                continue
            if (name, expr) not in seen:
                seen.add((name, expr))
                found.append((name, expr))
    return found


def _run_covering_documented_ids(tmp_path: Path):
    """A run whose section ids include every id the docs name.

    Ids are lab-scoped: no document could name one that exists in every lab, so
    a doc example naming `s04-deploy-models` is not wrong -- it is quoting the
    reference workshop. What is under test here is the syntax, so the fixture
    adopts the slugs the docs use and leaves the rest generic.

    It adopts them only *within* the reference workshop's 23 sections, so a doc
    citing `s99-...` is refused rather than conjured into existence. Honest
    limit: a doc that misspells the slug of a real section is still adopted and
    still passes. Closing that would need the lab's own ids, which is precisely
    what no checked-in test can have.
    """
    from lab_validator.corpus import Heading, Outline
    from lab_validator.runlog import Run

    total = 23
    slugs: dict[int, str] = {}
    for path in SYNTAX_DOCS.values():
        for m in SECTION_ID.finditer(path.read_text(encoding="utf-8")):
            index = int(m.group(1))
            if index < total:
                slugs.setdefault(index, m.group(2))
    heads: list[Heading] = []
    order = 0
    for i in range(total):
        heads.append(
            Heading(order=order, level=1, id=slugs.get(i, f"lab-{i:02d}"), text=f"Lab {i:02d}")
        )
        order += 1
        heads.append(Heading(order=order, level=3, id=f"l{i}-t0", text="1. Do the thing"))
        order += 1
    outline = Outline(title="Demo Workshop", headings=heads)
    return Run.create(
        tmp_path / "runs", "Demo Workshop", instance="i-1", agent="doc-check",
        segments=outline.segments(),
    )


def test_the_docs_offer_sections_expressions_at_all():
    """Vacuity guard: the scraper must actually find something to check."""
    found = _documented_sections_expressions()
    assert len(found) >= 4, f"only {len(found)} --sections examples scraped: {found}"


def test_every_documented_sections_expression_parses(tmp_path):
    """Every `--sections` value a reader could copy must resolve to sections.

    Not merely "does not raise": an expression that parses to an empty
    selection would walk nothing while looking like it worked, which is the
    failure this whole feature exists to make impossible.
    """
    from lab_validator import scope

    run = _run_covering_documented_ids(tmp_path)
    known = {s.id for s in run.segments()}
    for name, expr in _documented_sections_expressions():
        try:
            selection = scope.parse(expr, run)
        except Exception as exc:  # noqa: BLE001 -- any refusal is the failure
            raise AssertionError(f"{name} documents `--sections {expr}`, refused: {exc}") from exc
        assert selection.chosen, f"{name}: `--sections {expr}` selects nothing"
        unknown = sorted(set(selection.chosen) - known)
        assert not unknown, f"{name}: `--sections {expr}` resolved to unknown ids {unknown}"


def test_the_readme_shows_the_prompt_the_code_actually_prints():
    """The README illustrates the prompt; an illustration that has drifted
    teaches a syntax nobody is offered.

    Checks the question and every example inside `PROMPT_HELP`, because the
    examples are the part a reader copies -- and the part that changed when
    numbers were added.
    """
    from lab_validator import scope

    body = README.read_text(encoding="utf-8")
    question = scope.PROMPT_HELP.split("|")[0].strip()
    assert question in body, f"README does not show the real prompt: {question!r}"
    for example in re.findall(r"'([^']+)'", scope.PROMPT_HELP):
        assert f"'{example}'" in body, f"README omits the prompt's own example {example!r}"