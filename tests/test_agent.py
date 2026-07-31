"""Does the orchestrator hold the line when the model does not?

The failure this file exists for is specific: an agent that reports success it
did not achieve. A model will say "I completed the section" whether or not it
did, and the transcript reads identically either way. So none of these tests
assert on what the model *said* -- they assert on what the run folder shows,
which is the only thing that can tell the two apart.

No SDK process and no browser. ``drive`` takes its ``ask`` as an argument
precisely so the interesting cases -- a model that lies, a move that should
never have reached a model, a walk that stops making progress -- can be
reproduced deterministically instead of hoped for during a live lab.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator import agent  # noqa: E402
from lab_validator.corpus import Heading, Outline  # noqa: E402
from lab_validator.runlog import Redactor, Run, Segment  # noqa: E402

BODY = (
    "# Sign in\n"
    "### 1. Open the portal\n"
    "Sign in with the password from the Resources tab.\n"
)


def _run(tmp_path):
    md = tmp_path / "outline.md"
    md.write_text(BODY, encoding="utf-8")
    outline = Outline(title="Demo", headings=[
        Heading(order=0, level=1, id="sign-in", text="Sign in"),
        Heading(order=1, level=3, id="1-open-the-portal", text="1. Open the portal",
                body="Sign in with the password from the Resources tab."),
    ])
    segment = Segment(id="s01", title="Sign in", anchor="sign-in")
    run = Run.create(
        tmp_path / "runs", "Demo", lab={"id": 1}, instance="i", agent="test",
        corpus=md, segments=[segment],
    )
    outline.save(run.dir / "outline.json")
    return run, outline


class FakeTools(agent.Tools):
    """The learner's controls, backed by the run folder instead of a lab.

    These write real steps and real segment transitions, so the loop's refusals
    are exercised against genuine state. What is faked is only the browser --
    the one part that can tell us nothing about whether the loop is correct.
    """

    def __init__(self, run):
        super().__init__(run.dir)
        self.run = run
        self.acted: list[tuple[str, tuple[str, ...]]] = []

    def instructions(self, segment):
        return "instructions for " + segment

    def tasks(self, segment):
        return "#1-open-the-portal"

    def act(self, segment, actions, label=""):
        self.acted.append((segment, tuple(actions)))
        if "read" in actions:
            self.run.step(segment, verdict="PASS", action="read",
                          capability="scroll_instructions", note="scrolled")
        return "ok"

    def look(self, segment, label="look"):
        return None

    def open_segment(self, segment):
        self.run.start_segment(segment)
        return f"opened {segment}"

    def close_segment(self, segment, status):
        self.run.end_segment(segment, status)
        return f"closed {segment} as {status}"

    def refresh_report(self):
        from lab_validator import report

        run = Run.open(self.run.dir)
        for segment in run.segments():
            if segment.status != "pending":
                report.write_segment(run, segment)
        return "report written"


def _drive(run, outline, ask, tools, **kw):
    return asyncio.run(agent.drive(run, ask, outline=outline, tools=tools,
                                   say=lambda _: None, **kw))


# --- the model never gets to decide sequencing ------------------------------


def test_mechanical_moves_never_reach_the_model(tmp_path):
    """OPEN, READ, REPORT and ADVANCE are done by the loop itself.

    If a model were asked to open a section it could decline, or open a
    different one, and the loop would have no way to tell. Not asking is the
    guarantee.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    seen = []

    async def ask(move, shot):
        seen.append(move.action)
        run.step("s01", verdict="PASS", action="do",
                 instruction_ref="#1-open-the-portal", note="did it")

    progress = _drive(run, outline, ask, tools)

    assert seen == ["perform"], seen
    assert [m.split(":")[0] for m in progress.moves] == [
        "open", "read", "perform", "report", "advance", "stop",
    ], progress.moves
    assert Run.open(run.dir).segments()[0].status == "done"


def test_a_model_that_changes_nothing_does_not_advance_the_run(tmp_path):
    """The central guard: a claim of success is not success.

    This ``ask`` does what a confidently wrong model does -- returns cleanly,
    having touched nothing. The loop must notice from the run folder alone.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)

    async def ask(move, shot):
        return None  # "Done!"

    progress = _drive(run, outline, ask, tools)

    assert progress.stalls == agent.STALL_LIMIT
    assert "changed nothing" in progress.stopped
    assert Run.open(run.dir).segments()[0].status != "done"


def test_a_turn_that_records_a_verdict_clears_the_stall(tmp_path):
    """Progress is real when the trace moves, and the counter must reset.

    Without the reset a slow walk that pauses to look twice would be killed for
    being stuck, which is the opposite of the intended behaviour.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    turns = {"n": 0}

    async def ask(move, shot):
        turns["n"] += 1
        if turns["n"] == 1:
            return  # a wasted turn
        run.step("s01", verdict="PASS", action="do",
                 instruction_ref="#1-open-the-portal", note="did it")

    progress = _drive(run, outline, ask, tools)

    assert progress.stalls == 0
    assert progress.turns == 2


def test_a_mechanical_move_that_does_not_take_stops_the_walk(tmp_path):
    """The loop applies its own scepticism to itself.

    Found by a test, not by reading: a ``refresh_report`` that returns happily
    without writing anything made the loop reissue REPORT until it hit the
    move ceiling -- 195 identical moves, then a run that reported nothing and
    blamed the budget. The failure it was papering over is precisely the one
    the REPORT move exists to catch.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    tools.refresh_report = lambda: "the report could not be written: disk full"

    async def ask(move, shot):
        run.step("s01", verdict="PASS", action="do",
                 instruction_ref="#1-open-the-portal", note="did it")

    progress = _drive(run, outline, ask, tools)

    assert progress.moves.count("report:s01") == agent.STALL_LIMIT
    assert progress.mechanical == 4  # open, read, report, report
    assert "came back 3 times" in progress.stopped
    # The diagnosis it already has, rather than "run it by hand to see why".
    # The first real walk stopped here on a dead browser port and said nothing
    # about it, while the answer had just been printed three times.
    assert "disk full" in progress.stopped


def test_the_ceiling_stops_a_walk_that_will_not_finish(tmp_path):
    """A budget the loop cannot argue with.

    The stall guard catches a model that does nothing; this catches one that
    does *something* every turn without ever closing a task -- busy, plausible,
    and endless.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)

    async def ask(move, shot):
        run.step("s01", verdict="PASS", action="do", note="churn")  # no ref: no coverage

    progress = _drive(run, outline, ask, tools, max_turns=6)

    assert "ceiling" in progress.stopped
    assert progress.turns + progress.mechanical <= 6


# --- the fingerprint is taken from the folder, not the transcript ------------


def test_the_fingerprint_sees_a_verdict_land(tmp_path):
    run, outline = _run(tmp_path)
    run.start_segment("s01")
    segment = run.segments()[0]
    before = agent.Fingerprint.take(run, "s01", outline)

    run.step("s01", verdict="PASS", action="do",
             instruction_ref="#1-open-the-portal", note="did it")
    after = agent.Fingerprint.take(run, "s01", outline)

    assert before != after
    assert before.unjudged == ("1-open-the-portal",)
    assert after.unjudged == ()
    assert segment.id == "s01"


def test_the_fingerprint_of_a_missing_section_is_not_an_error(tmp_path):
    """A section that vanished must not crash a walk mid-lab.

    Returning a sentinel keeps the run recoverable; raising here would lose
    every finding already recorded.
    """
    run, outline = _run(tmp_path)
    assert agent.Fingerprint.take(run, "nope", outline).status == "missing"


# --- the learner path, enforced ---------------------------------------------


@pytest.mark.parametrize("tool", ["shell", "bash", "str_replace_editor", "view"])
def test_tools_off_the_learner_path_are_refused(tool):
    """A shell makes the *wrong* answer reachable.

    An agent that repairs a broken deployment from a terminal will report the
    lab as working, while the learner following the written instructions still
    cannot finish it. That is worse than no validation, because it is confident.
    """
    hooks = agent.build_hooks(Redactor())
    out = asyncio.run(hooks["on_pre_tool_use"]({"toolName": tool}))
    assert out["permissionDecision"] == "deny"
    assert "learner" in out["permissionDecisionReason"]


@pytest.mark.parametrize("tool", agent.ALLOWED_TOOLS)
def test_the_learners_own_controls_are_allowed(tool):
    hooks = agent.build_hooks(Redactor())
    out = asyncio.run(hooks["on_pre_tool_use"]({"toolName": tool}))
    assert out["permissionDecision"] == "allow"


def test_every_allowed_tool_is_one_the_agent_actually_builds():
    """The allowlist and the tools must not drift.

    A name in one and not the other fails in the least useful way: the model is
    offered a tool the hook then denies, or a tool exists that the hook has
    never heard of. Both are silent until a live walk.
    """
    src = (Path(agent.__file__)).read_text(encoding="utf-8")
    defined = {
        line.split("async def ", 1)[1].split("(", 1)[0]
        for line in src.splitlines()
        if line.strip().startswith("async def lab_")
    }
    assert defined == set(agent.ALLOWED_TOOLS), defined ^ set(agent.ALLOWED_TOOLS)


def test_a_lab_credential_never_reaches_the_transcript(tmp_path):
    """Tool output is scrubbed on the way back to the model.

    The value here enters through the tool result, which is exactly how it would
    in a real walk: the agent reads a screen or a config file and the secret is
    simply *in* the string it gets back.
    """
    redactor = Redactor()
    redactor.add("Sup3rSecretPassw0rd", "VM/Password")
    hooks = agent.build_hooks(redactor)

    out = asyncio.run(hooks["on_post_tool_use"](
        {"toolResult": "logged in with Sup3rSecretPassw0rd and it worked"}
    ))

    assert "Sup3rSecretPassw0rd" not in out["modifiedResult"]
    assert "[REDACTED:VM/Password]" in out["modifiedResult"]


def test_clean_output_is_passed_through_untouched(tmp_path):
    hooks = agent.build_hooks(Redactor())
    assert asyncio.run(hooks["on_post_tool_use"]({"toolResult": "nothing secret"})) is None


# --- the prompt names the work, and only the work ---------------------------


def test_the_prompt_names_the_outstanding_tasks_not_the_section(tmp_path):
    """A model told to "finish the section" decides for itself what that means.

    Task-level coverage exists so it does not get to, and the prompt has to
    carry that or the loop and the model are working to different definitions.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    from lab_validator.walkloop import Move

    move = Move("perform", "s01", why="1 of 1 task(s) have no verdict yet",
                tasks=["1-open-the-portal"])
    text = agent.prompt_for(move, tools)

    assert "1-open-the-portal" in text
    assert "once per task" in text
    assert "no shell" in text


def test_a_blocked_section_is_asked_to_assess_not_to_guess(tmp_path):
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    from lab_validator.walkloop import Move

    move = Move("assess", "s01", why="blocked", tasks=["1-open-the-portal"])
    text = agent.prompt_for(move, tools)

    assert "DEFERRED" in text
    assert "Do not guess" in text


def test_a_missing_sdk_degrades_to_walking_it_yourself(monkeypatch):
    """The agent is a convenience, not the product.

    ``auto`` is one way to drive the loop; ``lab-validator next`` is the other,
    and it needs no model at all. So a missing SDK has to fail with the fallback
    in hand -- an import error at the top of the module would take the whole CLI
    down with it, for a dependency most runs never touch.
    """
    import builtins

    real = builtins.__import__

    def refuse(name, *a, **kw):
        if name == "copilot" or name.startswith("copilot."):
            raise ImportError("no copilot here")
        return real(name, *a, **kw)

    monkeypatch.setattr(builtins, "__import__", refuse)

    with pytest.raises(agent.AgentUnavailable) as caught:
        agent._require_sdk()

    said = str(caught.value)
    assert "pip install -e .[agent]" in said
    assert "lab-validator next" in said  # names the way forward, not just the fault


def test_the_sdk_is_never_imported_at_module_load():
    """Guarded because it is invisible until the one machine without the SDK.

    Every other test in this file imports ``agent`` successfully -- with the SDK
    installed, which it is here. Only reading the source can tell whether that
    would still hold without it.
    """
    src = Path(agent.__file__).read_text(encoding="utf-8")
    top = [
        line for line in src.splitlines()
        if line.startswith(("import ", "from ")) and "copilot" in line
    ]
    assert top == [], f"copilot imported at module level: {top}"


def test_build_tools_registers_all_five_controls():
    """Calling it is the test, because registration is where it broke.

    Found by running `auto` for the first time, not by any test here: this
    module uses `from __future__ import annotations`, so every hint is a string,
    and `define_tool` resolves them with `get_type_hints` against the *module's*
    globals. The parameter models were declared inside `build_tools`, invisible
    from there, so all five tools died with `NameError: name 'SegmentP' is not
    defined` -- the entire SDK integration could never have worked, and nothing
    said so until a session tried to start.

    Everything else in this file injects a fake `ask` and never reaches the SDK,
    which is exactly why none of it noticed.
    """
    try:
        built = agent.build_tools(agent.Tools(Path(".")))
    except agent.AgentUnavailable:
        pytest.skip("SDK not installed; nothing to register against")
    assert len(built) == len(agent.ALLOWED_TOOLS)


def test_the_param_models_are_importable_from_the_module():
    """The specific thing that was broken, stated plainly."""
    for model in ("SegmentP", "ActP", "RecordP"):
        assert hasattr(agent, model), (
            f"{model} is not at module scope; get_type_hints will not find it"
        )


def test_the_verdict_codes_are_named_where_the_model_chooses(tmp_path):
    """Observed, not theorised: the first real run misfiled a finding.

    It recorded "the lab environment is unreachable" as `LAB001 Retired or
    renamed model` -- the first code in the list -- because the tool description
    said only "a LAB0NN code". A model given no definitions picks the first
    plausible one, and the finding then goes to the wrong owner.
    """
    from lab_validator.taxonomy import FINDING_VERDICTS, name_of

    described = agent.RecordP.model_fields["verdict"].description
    for code in FINDING_VERDICTS:
        assert code in described, f"{code} is not offered to the model"
        assert name_of(code) in described, f"{code} is offered with no definition"


def test_the_verdict_menu_is_generated_not_transcribed():
    """A hand-copied list is a second source of truth waiting to disagree.

    `report.CODE_NAMES` already did exactly that: it stopped at LAB008 while
    `runlog` accepted LAB009, and 40 findings rendered with no name. So this
    asserts the menu *is* the taxonomy -- add a code there and it appears here
    with no edit, which a transcribed list cannot manage.
    """
    from lab_validator.taxonomy import FINDING_VERDICTS, name_of

    expected = "; ".join(
        f"{code} = {name_of(code)}" for code in sorted(FINDING_VERDICTS)
    )
    assert agent._verdict_menu() == expected
    assert expected in agent.RecordP.model_fields["verdict"].description


def test_a_retired_model_name_is_explained_not_dumped(tmp_path):
    """The SDK reports this as a generic JSON-RPC error 40 lines deep.

    Hit on the first real `auto` run: the default was a pinned model name that
    had retired, and the output was a stack trace ending in
    `JsonRpcError -32603`. The fix is one flag; nothing in that trace says so.
    """
    said = agent._why_no_session(
        RuntimeError('Request session.create failed with message: '
                     'Model "claude-sonnet-4.5" is not available.'),
        "claude-sonnet-4.5",
    )
    assert "not available" in said
    assert "--model auto" in said  # the fix, not just the fault


def test_an_unauthenticated_cli_is_named_as_such():
    said = agent._why_no_session(RuntimeError("401 unauthorized: bad token"), "auto")
    assert "not authenticated" in said
    assert "/login" in said


def test_an_unrecognised_failure_keeps_its_own_words():
    """Do not guess a cause. A confident wrong diagnosis costs more than none."""
    said = agent._why_no_session(RuntimeError("disk on fire"), "auto")
    assert "disk on fire" in said
    assert "lab-validator next" in said  # still names the way forward


def test_the_default_model_is_not_a_pinned_name():
    """A validator that reports stale dependencies must not pin one itself."""
    assert agent.DEFAULT_MODEL == "auto"


def _capture(driven):
    def walk_autonomously(run_dir, **kw):
        driven["dir"] = run_dir
        return _FakeProgress()

    return walk_autonomously


def test_auto_refuses_when_it_cannot_tell_which_run_it_just_made(tmp_path, monkeypatch, capsys):
    """Never pick the run by being newest.

    `Run.latest` would work almost always, and the exception is the expensive
    one: two walks in flight, or a clock that stepped, and `auto` silently
    drives somebody else's lab -- producing a full, plausible, wrong report.
    Set difference cannot make that mistake; when it is ambiguous it says so.
    """
    from lab_validator import cli

    runs = tmp_path / "runs"
    (runs / "before").mkdir(parents=True)

    def two_runs(_args):
        (runs / "a").mkdir()
        (runs / "b").mkdir()
        return 0

    monkeypatch.setattr(cli, "cmd_walk", two_runs)
    args = argparse.Namespace(run=None, runs=str(runs), model="m", max_turns=1,
                              turn_timeout=1.0)

    assert cli.cmd_auto(args) == 2
    said = capsys.readouterr().err
    assert "expected exactly one new run" in said
    assert "'a', 'b'" in said or "['a', 'b']" in said  # names the candidates


def test_auto_drives_the_run_the_walk_just_created(tmp_path, monkeypatch):
    """The pre-existing run must not be chosen, however the names sort.

    The old run is deliberately named to sort *after* the new one, so "take the
    last directory" -- the shape of every convenience helper that resolves a run
    by recency -- gets it wrong here. Only the set difference is right in both
    directions, and a fixture where the right answer happens to also be the last
    one proves nothing.
    """
    from lab_validator import cli

    runs = tmp_path / "runs"
    (runs / "zz-earlier-run").mkdir(parents=True)
    driven = {}

    def one_run(_args):
        (runs / "aa-this-walk").mkdir()
        return 0

    monkeypatch.setattr(cli, "cmd_walk", one_run)
    monkeypatch.setattr("lab_validator.agent.walk_autonomously", _capture(driven))
    monkeypatch.setattr("lab_validator.runlog.Run.open", lambda d: _FakeRun(d))

    args = argparse.Namespace(run=None, runs=str(runs), model="m", max_turns=1,
                              turn_timeout=1.0)

    assert cli.cmd_auto(args) == 0
    assert driven["dir"].name == "aa-this-walk"


def test_auto_does_not_walk_again_when_given_a_run(tmp_path, monkeypatch):
    """Resuming is the common case for a multi-hour walk that was interrupted."""
    from lab_validator import cli

    existing = tmp_path / "runs" / "2026-01-01T0000Z"
    existing.mkdir(parents=True)
    walked = []
    driven = {}

    monkeypatch.setattr(cli, "cmd_walk", lambda a: walked.append(1) or 0)
    monkeypatch.setattr("lab_validator.agent.walk_autonomously", _capture(driven))
    monkeypatch.setattr("lab_validator.runlog.Run.open", lambda d: _FakeRun(d))

    args = argparse.Namespace(run=str(existing), runs=None, model="m", max_turns=1,
                              turn_timeout=1.0)

    assert cli.cmd_auto(args) == 0
    assert walked == [], "resuming must not start a second walk"
    assert driven["dir"] == existing


def test_auto_reports_a_missing_sdk_without_a_traceback(tmp_path, monkeypatch, capsys):
    from lab_validator import agent as agent_mod
    from lab_validator import cli

    existing = tmp_path / "runs" / "r"
    existing.mkdir(parents=True)

    def unavailable(run_dir, **kw):
        raise agent_mod.AgentUnavailable("no SDK; walk it yourself")

    monkeypatch.setattr("lab_validator.agent.walk_autonomously", unavailable)
    args = argparse.Namespace(run=str(existing), runs=None, model="m", max_turns=1,
                              turn_timeout=1.0)

    assert cli.cmd_auto(args) == 3
    assert "walk it yourself" in capsys.readouterr().err


class _FakeProgress:
    stopped = "done"

    def summary(self):
        return "0 model turn(s)"


class _FakeRun:
    def __init__(self, d):
        self.dir = Path(d)


def test_the_vault_reaches_the_loop_so_credential_asks_are_recognised(tmp_path):
    """Labels have to be threaded in, or the whole credential path is dead.

    ``next_move`` can only spot "sign in with the username from the Resources
    tab" if it is handed the labels the lab issued. Forget the argument and
    nothing breaks -- the asks are simply never detected, the prompts never
    mention a credential, and the walk stalls on a sign-in screen for reasons
    no log explains. Asserting the wiring is the only way to see it.
    """
    from lab_validator.labclient import Credential
    from lab_validator.vault import Vault

    run, outline = _run(tmp_path)
    Vault((Credential("VM", "Password", "Sup3rSecret"),), "now").save(run.dir)

    tools = FakeTools(run)
    seen: list[dict] = []

    async def ask(move, shot):
        seen.append(move.detail)
        run.step("s01", verdict="PASS", action="do",
                 instruction_ref="#1-open-the-portal", note="did it")

    _drive(run, outline, ask, tools)

    assert seen, "the model was never asked to perform anything"
    asked = seen[0].get("asks", {})
    named = [line for lines in asked.values() for line in lines]
    assert any("VM/Password" in line for line in named), asked


def test_credential_asks_reach_the_prompt_as_labels(tmp_path):
    """Labels cross the boundary; values never do.

    Worth asserting because the prompt is the one place a value could plausibly
    be substituted for convenience, and it is the one place it would be logged.
    """
    run, outline = _run(tmp_path)
    tools = FakeTools(run)
    from lab_validator.walkloop import Move

    move = Move("perform", "s01", why="w", tasks=["1-open-the-portal"],
                detail={"asks": {"1-open-the-portal": ["password -> VM/Password"]}})
    text = agent.prompt_for(move, tools)

    assert "VM/Password" in text
    assert "labels only" in text
