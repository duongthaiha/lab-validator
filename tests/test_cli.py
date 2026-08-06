"""Tests for the front door.

The dispatcher is a mapping from a name to a file, and a mapping is exactly the
shape of thing that rots silently: rename a script, and ``lab-validator step``
dies at the moment someone is mid-walk. That is the LAB009 failure again -- a
table that drifted away from the thing it described, and nothing noticed until
it reached a deliverable. So the important test here is not that the parser
parses; it is that every promise the help text makes is backed by a file that
exists and exposes the entry point the dispatcher calls.
"""

from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator import cli  # noqa: E402


def test_every_advertised_command_has_a_script():
    missing = [name for name, (f, _) in cli.COMMANDS.items() if not (cli.SCRIPTS / f).exists()]
    assert not missing, f"the help text promises commands with no script: {missing}"


@pytest.mark.parametrize("name", sorted(cli.COMMANDS))
def test_every_script_exposes_the_entry_point_the_dispatcher_calls(name):
    """``_delegate`` calls ``module.main()``. A script without one fails only
    when a human runs that sub-command, which is the worst time to find out."""
    script, _ = cli.COMMANDS[name]
    source = (cli.SCRIPTS / script).read_text(encoding="utf-8")
    assert "def main(" in source, f"{script} has no main() for the dispatcher to call"


def test_every_command_is_described():
    for name, (_, help_text) in cli.COMMANDS.items():
        assert help_text.strip(), f"{name} has no description in the help text"


def test_walk_is_not_in_the_dispatch_table():
    """It is the one command implemented here rather than delegated, so having
    it in both places would shadow the real implementation."""
    assert "walk" not in cli.COMMANDS


def test_install_skill_is_also_implemented_locally():
    assert "install-skill" not in cli.COMMANDS
    assert callable(cli.cmd_install_skill)


def test_package_skill_is_also_implemented_locally():
    assert "package-skill" not in cli.COMMANDS
    assert callable(cli.cmd_package_skill)


def test_the_help_advertises_the_locally_implemented_commands():
    """They are not in COMMANDS, so nothing else would notice them going
    missing from the epilog."""
    import contextlib
    import io

    buf = io.StringIO()
    saved = sys.argv
    sys.argv = ["lab-validator"]
    try:
        with contextlib.redirect_stdout(buf):
            cli.main()
    finally:
        sys.argv = saved
    text = buf.getvalue()
    assert all(
        command in text
        for command in ("walk", "install-skill", "package-skill")
    )


def test_installing_the_skill_writes_every_file(tmp_path):
    args = type("N", (), {"into": str(tmp_path), "dry_run": False})()
    assert cli.cmd_install_skill(args) == 0
    written = sorted(p.name for p in (tmp_path / "lab-validator").rglob("*.md"))
    assert "SKILL.md" in written
    assert len(written) >= 4


def test_a_dry_run_writes_nothing(tmp_path):
    args = type("N", (), {"into": str(tmp_path), "dry_run": True})()
    assert cli.cmd_install_skill(args) == 0
    assert not list(tmp_path.rglob("*.md")), "a dry run must not touch the filesystem"


def test_packaging_the_skill_writes_one_portable_archive(tmp_path):
    output = tmp_path / "lab-validator.skill"
    args = type("N", (), {"out": str(output)})()

    assert cli.cmd_package_skill(args) == 0

    with zipfile.ZipFile(output) as archive:
        names = set(archive.namelist())
        assert {
            "lab-validator/SKILL.md",
            "lab-validator/references/judgement.md",
            "lab-validator/assets/gap-analysis-template.md",
            "lab-validator/scripts/install_runtime.py",
            "lab-validator/scripts/lab_step.py",
            "lab-validator/src/lab_validator/cli.py",
            "lab-validator/pyproject.toml",
            "lab-validator/targets/azure-ai-platform.toml",
        } <= names
        assert all(info.date_time == (1980, 1, 1, 0, 0, 0) for info in archive.infolist())
        pyproject = archive.read("lab-validator/pyproject.toml").decode()
        assert 'lab-validator = "lab_validator.cli:main"' in pyproject
        assert "readme =" not in pyproject


def test_the_package_ships_nothing_the_repository_only_needs(tmp_path):
    """The repository *is* the skill, so over-inclusion is the new failure mode.

    While the runtime lived in a staged copy, the risk ran the other way: the
    copy went stale and packaging refused. Publishing straight from the repo
    removes that, and replaces it with a quieter one -- a careless glob ships
    the test suite, the docs, the git history, or whatever a tool has just
    written into the working tree. None of that announces itself in an archive
    that extracts and loads perfectly well.
    """
    output = tmp_path / "lab-validator.skill"
    assert cli.cmd_package_skill(type("N", (), {"out": str(output)})()) == 0

    with zipfile.ZipFile(output) as archive:
        names = [name.split("/", 1)[1] for name in archive.namelist()]

    for name in names:
        assert not name.startswith(
            ("tests/", "docs/", "evals/", ".git", ".venv/", "runs/", "dist/")
        ), f"{name} is repository-only and must not be published"
        assert "__pycache__" not in name and not name.endswith((".pyc", ".egg-info")), (
            f"{name} is generated and must not be published"
        )
    shipped_scripts = {name for name in names if name.startswith("scripts/")}
    assert shipped_scripts == {f"scripts/{s}" for s in cli.SKILL_SCRIPTS}, (
        "scripts ship by enumeration, not by glob -- a development harness that "
        "expects the test corpus would ship as a command that cannot work from "
        "an extracted archive"
    )


def test_skill_package_is_reproducible(tmp_path):
    first = tmp_path / "first.skill"
    second = tmp_path / "second.skill"

    assert cli.cmd_package_skill(type("N", (), {"out": str(first)})()) == 0
    assert cli.cmd_package_skill(type("N", (), {"out": str(second)})()) == 0
    assert first.read_bytes() == second.read_bytes()


def test_the_committed_archive_is_what_the_sources_build_today(tmp_path):
    """A published archive that lags the sources is worse than no archive.

    `dist/lab-validator.skill` is committed so another harness can take it
    straight from the repository, which means it is the one copy of the skill
    nobody rebuilds before using. A stale one does not announce itself: it
    extracts, validates and loads perfectly well, and then behaves like whatever
    the repository looked like on the day it was built. That already happened
    once -- a `dist/lab-validator.zip` sat here for three days holding SKILL.md
    and `references/` and no engine at all, so every dispatched command in it
    would have failed.

    Reproducible packaging is what makes this checkable at all: identical
    sources produce identical bytes, so a plain comparison is a drift test.
    """
    committed = cli.ROOT / "dist" / "lab-validator.skill"
    assert committed.exists(), (
        "dist/lab-validator.skill is committed and missing -- rebuild it with "
        "`lab-validator package-skill`"
    )

    fresh = tmp_path / "fresh.skill"
    assert cli.cmd_package_skill(type("N", (), {"out": str(fresh)})()) == 0

    assert committed.read_bytes() == fresh.read_bytes(), (
        "the committed archive no longer matches the sources -- rebuild it with "
        "`lab-validator package-skill` and commit the result in the same change"
    )


def test_skill_validation_rejects_a_missing_reference():
    with pytest.raises(ValueError, match="references/missing.md"):
        cli._validate_skill(
            "---\nname: lab-validator\ndescription: demo skill\n---\n"
            "Read references/missing.md before acting.\n"
        )


def test_skill_validation_does_not_depend_on_the_checkout_name():
    """A clone into `lab-validator-2/` is somebody's working copy, not a defect.

    The name is fixed by the spec and by the directory the archive extracts to,
    so it is checked against a constant rather than against `ROOT.name`.
    """
    with pytest.raises(ValueError, match="lab-validator"):
        cli._validate_skill("---\nname: something-else\ndescription: d\n---\nbody\n")


def test_installing_removes_files_the_skill_no_longer_contains(tmp_path):
    """An install that only adds leaves the previous layout lying underneath.

    That debris is not inert. When the skill's runtime moved out of a nested
    `runtime/` directory, the old copy stayed behind in `~/.copilot/skills` --
    a second, frozen engine inside the very skill an agent reads.
    """
    dest = tmp_path / "lab-validator"
    (dest / "runtime" / "src").mkdir(parents=True)
    (dest / "runtime" / "src" / "cli.py").write_text("stale", encoding="utf-8")

    args = type("N", (), {"into": str(tmp_path), "dry_run": False})()
    assert cli.cmd_install_skill(args) == 0

    assert not (dest / "runtime").exists(), "the empty directory should go too"
    assert (dest / "SKILL.md").exists()


def test_a_dry_run_installs_and_removes_nothing(tmp_path):
    dest = tmp_path / "lab-validator"
    dest.mkdir()
    (dest / "stale.md").write_text("stale", encoding="utf-8")

    args = type("N", (), {"into": str(tmp_path), "dry_run": True})()
    assert cli.cmd_install_skill(args) == 0

    assert (dest / "stale.md").exists()
    assert not (dest / "SKILL.md").exists()


def test_the_installed_and_packaged_trees_are_the_same_files(tmp_path):
    """One list drives both, so neither can quietly gain or lose a file."""
    args = type("N", (), {"into": str(tmp_path), "dry_run": False})()
    assert cli.cmd_install_skill(args) == 0
    installed = {
        path.relative_to(tmp_path / "lab-validator").as_posix()
        for path in (tmp_path / "lab-validator").rglob("*")
        if path.is_file()
    }
    assert installed == set(cli._skill_files())


def test_the_scripts_directory_is_found_relative_to_the_package():
    assert cli.SCRIPTS.is_dir()
    assert (cli.ROOT / "pyproject.toml").exists()


def test_an_unknown_command_is_refused_rather_than_guessed():
    saved = sys.argv
    sys.argv = ["lab-validator", "waalk"]
    try:
        assert cli.main() == 2
    finally:
        sys.argv = saved


def test_no_command_prints_help_and_succeeds():
    """Running the bare name is how someone finds out what exists; that is a
    successful outcome, not a usage error."""
    saved = sys.argv
    sys.argv = ["lab-validator"]
    try:
        assert cli.main() == 0
    finally:
        sys.argv = saved


def test_a_lab_title_with_a_dash_does_not_kill_the_run(capsys):
    """Skillable titles are full of en-dashes and Windows consoles are cp1252.
    Printing one used to raise mid-line and take down the command."""
    cli._console_utf8()
    print("WorkshopPLUS \u2013 Azure AI Platform \u2014 Lab: Using Vector Databases")
    assert "Azure AI Platform" in capsys.readouterr().out


def test_console_hardening_survives_a_stream_that_refuses(monkeypatch):
    class Stubborn:
        def reconfigure(self, **_):
            raise ValueError("redirected")

    monkeypatch.setattr(cli.sys, "stdout", Stubborn())
    cli._console_utf8()  # must not raise


# ---- the outline a run was actually walked against ------------------------
#
# artifacts/instructions/ is shared and the next walk overwrites it. Reading it
# for an older run would enumerate a different lab's tasks and answer with
# complete confidence -- worse than answering nothing, because a wrong answer
# nobody can see is wrong is how a validator stops being worth running.


def _run_with_corpus(tmp_path, body: str):
    import hashlib

    from lab_validator.corpus import Heading, Outline
    from lab_validator.runlog import Run, Segment

    shared = tmp_path / "artifacts"
    shared.mkdir()
    md = shared / "outline.md"
    md.write_text(body, encoding="utf-8")
    Outline(title="Demo", headings=[
        Heading(order=0, level=1, id="setup", text="Setup"),
        Heading(order=1, level=3, id="task-1", text="1. Do the thing"),
    ]).save(shared / "outline.json")

    run = Run.create(
        tmp_path / "runs", "Demo", lab={"id": 1}, instance="i", agent="t",
        corpus=md, segments=[Segment(id="s00", title="Setup", anchor="setup")],
    )
    assert run.manifest["corpus"]["sha256"] == hashlib.sha256(md.read_bytes()).hexdigest()
    return run, md


def test_the_run_local_outline_is_preferred(tmp_path):
    from lab_validator.corpus import Heading, Outline

    run, md = _run_with_corpus(tmp_path, "shared")
    Outline(title="Local", headings=[
        Heading(order=0, level=1, id="setup", text="Setup"),
    ]).save(run.dir / "outline.json")

    outline, why = cli._outline_for(run)

    assert outline.title == "Local", "the run's own copy is evidence; the shared one is not"
    assert why == ""


def test_an_overwritten_shared_outline_is_refused_not_used(tmp_path):
    run, md = _run_with_corpus(tmp_path, "the lab this run walked")

    md.write_text("a completely different lab", encoding="utf-8")
    outline, why = cli._outline_for(run)

    assert outline is None, (
        "enumerating another lab's tasks would produce confident nonsense; refusing "
        "is the only honest answer"
    )
    assert "different lab" in why


def test_an_unchanged_shared_outline_is_still_usable(tmp_path):
    run, md = _run_with_corpus(tmp_path, "the lab this run walked")

    outline, why = cli._outline_for(run)

    assert outline is not None and why == ""


def test_a_run_with_no_corpus_says_so_rather_than_guessing(tmp_path):
    from lab_validator.runlog import Run, Segment

    run = Run.create(tmp_path, "Demo", lab={"id": 1}, instance="i", agent="t",
                     segments=[Segment(id="s00", title="Setup")])

    outline, why = cli._outline_for(run)

    assert outline is None
    assert "no corpus" in why


# --- the next-step hint ----------------------------------------------------
#
# Every command that finishes a stage tells the human what to do next, and that
# hint is the path most people will take. `walk` -- the primary entry point --
# was still pointing at `run --next`, the older reader that was deliberately
# dropped from the skill for agreeing when it should refuse, while `scope`
# beside it pointed at `next`. Two hints, two answers, and the more visible one
# was the worse one.

#: Every `lab-validator <verb>` the CLI puts in front of a human, wherever it is
#: built. The first version of this scraper required a literal `next: ` or `or: `
#: prefix, so it read the two `print` calls and missed
#: `hint = f"lab-validator next --run ..."` on the line above -- the exact line
#: that had been wrong. A guard written after the fix, and tested only against
#: the fix, will happily agree with the bug. The lookbehind keeps
#: `skills/lab-validator` (a path, not a command) out.
HINT = re.compile(r"(?<![\w/-])lab-validator ([a-z-]+)")

#: The reader that was dropped from the skill for agreeing when it should
#: refuse. `run` is still a builtin, so "names a real command" cannot catch it.
DEPRECATED_READER = "run --next"



def _hints() -> list[str]:
    source = (ROOT / "src" / "lab_validator" / "cli.py").read_text(encoding="utf-8")
    return HINT.findall(source)


def test_the_cli_hints_at_something_at_all():
    """Guards the guard: a scraper that finds nothing passes every assertion
    below it."""
    assert _hints(), "no next-step hints found -- the pattern has drifted"


@pytest.mark.parametrize("verb", sorted(set(_hints())))
def test_every_next_step_hint_names_a_real_builtin(verb):
    assert verb in cli.BUILTINS, (
        f"the CLI tells the human to run `lab-validator {verb}`, which is not a "
        f"built-in command. Known: {sorted(cli.BUILTINS)}"
    )


def test_no_hint_sends_the_human_to_the_reader_that_agrees():
    """The live defect, named directly.

    `walk` -- the primary entry point, and so the most-read hint in the tool --
    pointed at `lab-validator run --next` while `scope` beside it pointed at
    `next`. Both commands exist and both run, so nothing failed; one of them
    simply agrees where the other refuses, and the more visible hint was the
    worse one.
    """
    source = (ROOT / "src" / "lab_validator" / "cli.py").read_text(encoding="utf-8")
    assert DEPRECATED_READER not in source, (
        f"cli.py still points somebody at `lab-validator {DEPRECATED_READER}`"
    )


#: The two commands that continue an existing walk. Both work; only one of them
#: refuses when it should. Named explicitly rather than by excluding everything
#: else, because `scope` and `walk` are also legitimately suggested and an
#: exclusion list quietly grows until it excludes the thing under test.
CONTINUATIONS = {"next", "run"}


def test_the_continuation_commands_are_real():
    """Guards the guard: a set naming commands that do not exist filters to
    nothing, and an empty filter satisfies every assertion made about it.

    Checked against everything the dispatcher accepts, not just the builtins:
    `run` is delegated to a script, which is exactly why pointing a human at it
    looked harmless.
    """
    dispatchable = set(cli.BUILTINS) | set(cli.COMMANDS)
    assert CONTINUATIONS <= dispatchable, sorted(dispatchable)


def test_the_hints_do_not_send_two_people_down_two_paths():
    """Whichever reader is chosen, every hint must agree on it."""
    forward = {v for v in _hints() if v in CONTINUATIONS}
    assert forward, "the CLI never says how to continue a walk"
    assert len(forward) == 1, (
        f"the CLI recommends more than one way to continue a walk: {sorted(forward)}"
    )
