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

SKILL = ROOT / "SKILL.md"
INSTALLED = Path.home() / ".copilot" / "skills" / "lab-validator" / "SKILL.md"

INVOCATION = re.compile(r"^[ \t]*lab-validator[ \t]+(?P<rest>.+?)[ \t]*$", re.M)

# The README is executed too -- by a human following it, which is the same
# failure with a slower feedback loop. A guide that teaches a renamed flag does
# not produce a helpful error; it produces a run that dies partway through a lab
# with somebody waiting on it. So both documents get the same guard.
README = ROOT / "README.md"
# `docs/cli.md` is executed the same way: someone whose walk has just stopped,
# copying a resume command out of it at speed.
CLI_DOC = ROOT / "docs" / "cli.md"
DOCS = {"SKILL.md": SKILL, "README.md": README, "docs/cli.md": CLI_DOC}

#: How many invocations each document must yield for the vacuity guard to mean
#: anything. The regex is shared, so one command-dense document proves it still
#: matches; a focused document only has to prove it was parsed at all. Set from
#: what each file is *for*, not from what it happens to contain today.
MINIMUM = {"SKILL.md": 8, "README.md": 8, "docs/cli.md": 2}


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

    Derived rather than listed. A hand-kept copy of a flag list is a second
    source of truth that goes stale silently, and this test exists precisely to
    catch documentation drifting from code — it should not be the thing drifting.

    For built-ins this now *builds the parser and asks it*, rather than scraping
    `add_argument("--…")` calls out of `main()` with a regex. The regex had to
    be taught about shared flag helpers once already; a parser cannot lie about
    what it accepts.
    """
    if command in cli.BUILTINS:
        build, _handler = cli.BUILTIN_PARSERS[command]
        parser = build()
        return {
            option
            for action in parser._actions
            for option in action.option_strings
            if option.startswith("--")
        }
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


#: Readers that still work but were dropped from the walk loop for agreeing when
#: they should refuse. Every guard above passes on them -- `run` is a real
#: command and `--next` is a real flag -- which is exactly why one survived in
#: SKILL.md Step 5 long after being removed from the loop and from the CLI's
#: own hints. A command being *valid* says nothing about it being the one to
#: recommend, and nothing else here was asking that question.
DEPRECATED_READERS = {("run", "--next")}


@pytest.mark.parametrize("doc,line", documented())
def test_no_doc_recommends_a_reader_that_was_dropped(doc, line):
    parts = line.split()
    command, flags = parts[0], {p for p in parts[1:] if p.startswith("--")}
    for dropped_command, dropped_flag in DEPRECATED_READERS:
        assert not (command == dropped_command and dropped_flag in flags), (
            f"{doc} tells the reader to run `lab-validator {dropped_command} "
            f"{dropped_flag}`, which was dropped in favour of `lab-validator next`"
        )


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


#: `references/taxonomy.md` calls itself generated from `taxonomy.py` and says
#: the module wins in a disagreement -- but nothing made that true, so the file
#: was a hand-maintained copy wearing a generated file's disclaimer. The table
#: renders `--` as an em dash and `None` as one too, so both are normalised
#: before comparing rather than being written back into the Python.
TAXONOMY_DOC = ROOT / "references" / "taxonomy.md"
DOC_ROW = re.compile(r"^\| `([A-Z0-9]+)` \| (.+?) \| (.+?) \| (.+?) \| (.+?) \|$", re.M)


def _documented_codes() -> dict[str, tuple[str, str, str, str]]:
    rows = DOC_ROW.findall(TAXONOMY_DOC.read_text(encoding="utf-8"))
    return {row[0]: row[1:] for row in rows}


def test_the_generated_taxonomy_reference_matches_the_module():
    """The reference is what a model reads to choose a code; the module is what
    accepts one. Nothing forced them to agree.

    This is the incident the file's own header describes, one level up. The
    codes previously lived in three places that disagreed and **40 findings
    printed as `LAB009 — LAB009`** in a delivered report. The fix put the
    definitions in one module and wrote the document from it -- by hand, once,
    with a comment asking the next person to re-run a command. So the drift the
    header warns about was still available to anyone who added a code and
    forgot, which is exactly what it costs nothing to forget.
    """
    from lab_validator.taxonomy import BY_CODE

    documented = _documented_codes()
    assert set(documented) == set(BY_CODE), (
        "references/taxonomy.md and taxonomy.py disagree about which codes exist: "
        f"only in the doc {sorted(set(documented) - set(BY_CODE))}, "
        f"only in the module {sorted(set(BY_CODE) - set(documented))}"
    )
    for code, verdict in BY_CODE.items():
        name, domain, severity, definition = documented[code]
        assert name == verdict.name, f"{code}: the doc calls it {name!r}"
        assert domain == verdict.typical_domain, f"{code}: the doc says domain {domain!r}"
        assert severity == (verdict.default_severity or "—"), (
            f"{code}: the doc says severity {severity!r}"
        )
        assert definition == verdict.definition.replace("--", "—"), (
            f"{code}: the doc's definition has drifted from the module's"
        )


def test_every_finding_code_is_reachable_from_the_skill_body():
    """A code nothing tells a model to look for is a code nothing ever files.

    Most codes need no prompting -- the step fails and the walk reaches for a
    name. `LAB010` is recorded at a step that *succeeded*, so unless the body
    asks the question at that moment it stays permanently unused, and the report
    quietly loses its only signal that a passing lab is dating.
    """
    body = SKILL.read_text(encoding="utf-8")
    assert "LAB010" in body, (
        "nothing in the skill body asks whether a working path is the current "
        "one, so LAB010 can never be filed"
    )


def test_every_referenced_reference_file_is_present():
    body = SKILL.read_text(encoding="utf-8")
    for name in set(re.findall(r"references/([a-z-]+\.md)", body)):
        assert (SKILL.parent / "references" / name).exists(), f"references/{name} is missing"


def test_no_reference_file_is_orphaned():
    """An unreferenced reference is one nothing will ever load."""
    body = SKILL.read_text(encoding="utf-8")
    for path in (SKILL.parent / "references").glob("*.md"):
        assert path.name in body, f"references/{path.name} is never referenced from SKILL.md"


def test_every_referenced_asset_file_is_present():
    body = SKILL.read_text(encoding="utf-8")
    for name in set(re.findall(r"assets/([a-z-]+\.md)", body)):
        assert (SKILL.parent / "assets" / name).exists(), f"assets/{name} is missing"


def test_no_asset_file_is_orphaned():
    body = SKILL.read_text(encoding="utf-8")
    for path in (SKILL.parent / "assets").glob("*"):
        assert path.name in body, f"assets/{path.name} is never referenced from SKILL.md"


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
    disagree -- and the running one wins, silently.

    The comparison runs over `_skill_files()` rather than everything under the
    repo root, because the repo root is now the skill: sweeping it would drag in
    `tests/`, `docs/` and whatever a browser profile has left lying around.
    """
    for relative, content in cli._skill_files().items():
        live = INSTALLED.parent / relative
        assert live.exists(), f"{relative} is in the repo but not installed; re-run install-skill"
        assert live.read_bytes() == content, (
            f"{relative} differs between the repo and ~/.copilot/skills; "
            "the repo is the source of truth"
        )


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
    """Headings start at column 0 *on their own line*, so `^#` finds every one.

    Two ways to lose a heading, both of which render acceptably and are
    therefore invisible until someone greps for a section, gets nothing, and
    concludes it does not exist.

    Indenting one was the first, and is what this test was written for. Gluing
    one to the end of the paragraph above it -- `...wrong thing.## 3. Title` --
    is the second, found when an insertion swallowed the newline before
    `## 3. Recommended architecture`. That one is worse: an indented heading
    still renders as a heading, while a glued one renders as *body text*, so
    the document silently loses a section from its own structure. It also
    quietly breaks the cross-reference check below, whose heading set is built
    with `^#{1,6}` -- so a real `\u00a73.1` would have been reported as a citation
    to a section that does not exist.
    """
    path = DOCS.get(name) or GUIDANCE
    body = path.read_text(encoding="utf-8")

    indented = [
        line
        for line in body.splitlines()
        if re.match(r"[ \t]+#{1,6} \S", line) and not line.lstrip().startswith("#!")
    ]
    assert not indented, f"{name}: indented headings are invisible to a plain search: {indented}"

    # Fenced blocks hold comments -- `# /User/CurrentTraining/{userId}` in TOML,
    # `#!/usr/bin/env` in shell -- which are not headings and never will be.
    # Blanked rather than deleted so the reported context stays near the right
    # place in the file.
    prose = re.sub(
        r"^```.*?^```", lambda m: "\n" * m.group(0).count("\n"), body, flags=re.M | re.S
    )

    # A `#` that follows anything other than a newline is not opening a heading.
    # The lookbehind must exclude `#` as well, or the pattern simply starts at
    # the second hash of a legitimate `##` and reports every heading in the
    # file -- which is what the first draft of this guard did. Backticks and
    # backslashes are excluded because `## 3.` inside prose or a code span is a
    # reference to a heading, not one.
    glued = [
        prose[max(0, m.start() - 45) : m.end() + 35]
        for m in re.finditer(r"(?<=[^\n#`\\])#{1,6} \S", prose)
    ]
    assert not glued, (
        f"{name}: a heading glued to the line above renders as body text and "
        f"disappears from the document's structure: {glued}"
    )


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
# behind. A stale listing renders perfectly; a reader simply concludes the code
# is not there and either writes it again or gives up. Neither failure leaves a
# trace.

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

    The docs point at the guards that make their claims true -- "the
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


# `--help` is the doc nobody has to go looking for, and it drifted first: all
# three copies still offered ids only, which is the one form nobody can type
# before a lab has been captured.

SECTIONS_COMMANDS = ["walk", "scope"]


def _help_text(command: str, capsys) -> str:
    """What `lab-validator <command> --help` actually prints.

    Goes through `main()` and `sys.argv` rather than reaching for the parser,
    because the parsers are built inline per command -- and the thing that
    drifted was what a user sees, not what a constant says.
    """
    argv = sys.argv
    sys.argv = ["lab-validator", command, "--help"]
    try:
        with pytest.raises(SystemExit):
            cli.main()
    finally:
        sys.argv = argv
    return capsys.readouterr().out


@pytest.mark.parametrize("command", SECTIONS_COMMANDS)
def test_every_sections_help_offers_the_numbers(command, capsys):
    """`--help` must offer the form a first-time user can actually type.

    Ids do not exist until a lab has been captured, so a help string listing
    only `s01,s04` describes a flag nobody can use on a first run. One
    constant, checked at the surface argparse prints rather than at the
    constant, because the bug was three copies that had drifted apart.
    """
    from lab_validator import scope

    # argparse rewraps help across lines; compare on collapsed whitespace.
    printed = " ".join(_help_text(command, capsys).split())
    expected = " ".join(scope.SECTIONS_HELP.split())
    assert expected in printed, f"`{command} --help` does not show SECTIONS_HELP"


@pytest.mark.parametrize("command", SECTIONS_COMMANDS)
def test_every_example_in_the_sections_help_parses(command, capsys, tmp_path):
    """Every example `--help` offers must be one the parser accepts.

    Same property as the documented-syntax guard above, applied to the surface
    a user reaches without opening a document.
    """
    from lab_validator import scope

    printed = " ".join(_help_text(command, capsys).split())
    body = printed.split("which sections to walk:", 1)[1]
    body = body.split(".")[0] if "Omit" in body else body.split("--")[0]
    examples = [e.strip() for e in body.split("|") if e.strip()]
    assert len(examples) >= 4, f"`{command} --help` offers too few examples: {examples}"

    run = _run_covering_documented_ids(tmp_path)
    for example in examples:
        selection = scope.parse(example, run)
        assert selection.chosen, f"`{command} --help` offers `{example}`, which selects nothing"
def test_no_doc_shows_a_prompt_the_code_does_not_print():
    """The other direction, and the one that let a wrong copy through.

    The test above is satisfied by *one* correct copy anywhere in the file. A
    second, paraphrased copy -- "Which sections should this run walk?" -- sat
    in the Quick start next to it and passed, because the real wording still
    appeared further down. A reader starting at the top would have learned a
    prompt that is never printed, and looked for options that do not exist.

    So: any line that asks about sections has to be the line the code prints.
    """
    from lab_validator import scope

    real = scope.PROMPT_HELP.split("|")[0].strip()
    # A line that asks about sections *and* ends in a question is claiming to
    # be the prompt. Prose that merely mentions "which sections to walk" is
    # describing it, and reads correctly however the prompt is worded.
    asking = re.compile(r"^.*\bsections\b[^\n]*\?[^\n]*$", re.M | re.I)

    for name, path in DOCS.items():
        for line in asking.findall(path.read_text(encoding="utf-8")):
            stripped = line.strip().lstrip("#").strip()
            if stripped.startswith(("|", "-", "*", ">")) or "`" in stripped:
                continue  # prose, a table cell, or an inline code span
            assert real in line, (
                f"{name} shows {stripped!r}, but the code prints {real!r}"
            )
