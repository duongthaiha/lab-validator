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
