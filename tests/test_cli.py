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
    assert "walk" in text and "install-skill" in text


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
