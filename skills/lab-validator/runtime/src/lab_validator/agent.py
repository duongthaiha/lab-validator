"""Drive a whole lab walk with an agent, so the human only signs in.

The temptation here is to hand a model every tool and a prompt that says "walk
this lab". That would throw away the most expensive thing this project learned.
``walkloop.next_move`` is a deterministic function whose refusals -- won't
advance past an unjudged task, won't trust a section report older than the last
finding, won't call a section read without a recorded scroll -- each cost a wrong
report to discover. A model that owns sequencing turns every one of those into a
suggestion it may ignore, silently, in the middle of an unattended run.

So sequencing stays in Python and the model is called only where judgement is
genuinely required:

    next_move() decides            ->  Python executes it (open/read/report/advance)
    next_move() says perform       ->  one scoped model turn, then re-ask

Two properties follow, and both matter more than the token saving:

* **A mechanical move cannot be skipped**, because no model is consulted for it.
* **The model's claim of success is never believed.** After every turn the loop
  re-reads the run folder and compares a fingerprint taken from the trace. "I
  completed the section" is not evidence; a step appearing in the trace is.
  Nothing measurable changed means no progress, whatever the transcript says.

The permission hook is the third property, and it is a correctness guard rather
than security hygiene. A validator that reaches the goal by a route the learner
does not have has proved nothing (approach.md 2.16), and the fastest such route
is always a shell. So the agent gets the learner's controls and nothing else.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
import sys
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import BaseModel, Field

from .corpus import Outline
from .runlog import Redactor, Run
from .vault import Vault, role_of
from .walkloop import Move, next_move, unjudged_tasks

ROOT = Path(__file__).resolve().parents[2]

#: Moves the loop can decide without judgement. Executed directly, which is the
#: point: a move nobody is asked about is a move nobody can skip.
MECHANICAL = ("open", "read", "report", "advance")

#: Moves that need a model: what an instruction means, whether the screen
#: matches it, and which side is at fault are not mechanical questions.
JUDGEMENT = ("perform", "assess")

#: Tools the agent may call. Everything else is denied. This list *is* the
#: learner path: each entry corresponds to something a human sitting in front of
#: the lab could do, and there is deliberately no way to reach the product's API,
#: the host shell, or the file system behind the VM.
ALLOWED_TOOLS = (
    "lab_instructions",
    "lab_tasks",
    "lab_act",
    "lab_record",
    "lab_look",
)

# Let the CLI choose. Naming a model here would pin the walk to something that
# retires -- and a validator whose own dependency has silently gone stale, while
# it reports on other people's stale dependencies, is the joke this project
# exists to avoid. `--model` overrides when a specific one is wanted.
DEFAULT_MODEL = "auto"
DEFAULT_TURN_TIMEOUT = 900.0
#: Consecutive turns that change nothing in the run folder before we stop. One
#: is noise -- a model can spend a turn reading. Three in a row is a loop that
#: has stopped making progress, and continuing burns lab clock for nothing.
STALL_LIMIT = 3
#: Consecutive model turns that outlast ``--turn-timeout`` before we stop. A
#: PERFORM that drives a VM through a portal sign-in can legitimately take
#: longer than its budget, and the steps it recorded are on disk either way --
#: so one timeout is slowness, not failure. Two in a row is a wedged session,
#: and waiting a third budget proves nothing.
TIMEOUT_LIMIT = 2

#: How a closed lab announces itself in a mechanical move's output. `lab_step`
#: refuses and prints this; the loop recognises it and stops rather than
#: retrying, because the lab is not coming back on its own.
#:
#: Matched on the message, not on the exit code, because `_do_mechanical`
#: deliberately returns what the command *said* -- the diagnosis a human reads
#: -- and adding a second channel would let the two disagree.
LAB_CLOSED_MARK = "has ended, so nothing observed from here is evidence"


class AgentUnavailable(RuntimeError):
    """The Copilot SDK is not installed, or the CLI it needs is missing."""


# --- talking to the existing CLI --------------------------------------------
#
# Every tool shells out to the real `lab-validator` rather than importing the
# scripts. That is deliberate. The CLI is the surface the walk was proven
# through: it refreshes the section report after every step, resolves the run
# folder the same way, and applies the same argument validation. Reimplementing
# any of that here would create a second path with its own bugs, and the agent
# would be the only caller exercising it.


def _cli(*args: str, timeout: int = 600) -> subprocess.CompletedProcess:
    # Decode explicitly. `text=True` alone decodes with the *parent's* locale
    # codec, while the child is told to write UTF-8 on the next line -- so on
    # any non-UTF-8 locale (cp1252 is the Windows default) a single em-dash in
    # an instruction blows up subprocess's reader thread and `stdout` arrives
    # empty. Empty, not an error: the tool then hands the model a blank section
    # and lets it judge instructions it never saw. `errors="replace"` because a
    # mangled character is a far better outcome than a lost section.
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        [sys.executable, "-m", "lab_validator.cli", *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )


def _say(proc: subprocess.CompletedProcess) -> str:
    """Both streams, because the interesting half is often stderr.

    A tool that reports only stdout on failure hands the model an empty string
    and lets it invent a reason for something it cannot see.
    """
    out = (proc.stdout or "").strip()
    err = (proc.stderr or "").strip()
    if proc.returncode != 0:
        return f"command failed (exit {proc.returncode})\n{out}\n{err}".strip()
    # Silence and success are different claims, and "" reads as neither. A
    # command that exited clean having printed nothing is a signal worth
    # passing on rather than a blank the model will fill in for itself.
    return "\n".join(p for p in (out, err) if p) or "(the command printed nothing)"


@dataclass
class Tools:
    """The learner's controls, as callables.

    Kept as a class so tests can drive the same five operations without an SDK
    process, and so the run folder is bound once rather than threaded through
    every call.
    """

    run_dir: Path

    def instructions(self, segment: str) -> str:
        return _say(_cli("text", "--segment", segment, "--run", str(self.run_dir)))

    def inventory(self) -> list[str]:
        """Every credential ref this lab handed out, grouped by sign-in.

        The model needs this for a reason the ask-matcher cannot cover: a lab
        can *require* a credential its instructions never mention. The reference
        workshop presents a locked Windows VM before its first written step and
        says nothing about it anywhere in 109,703 characters of text; the
        machine password is on the Resources tab and nowhere else. Told only
        about credentials the text asked for, a model facing that screen reaches
        for the one family it has heard of and types an Azure e-mail address
        into a Windows password box.

        Roles are shown alongside, so the two families are visibly separate
        rather than a flat list in which one password looks like another.
        """
        with contextlib.suppress(Exception):
            if vault := Vault.load(self.run_dir):
                by_role = {
                    f"{c.scope}/{c.label}": role_of(c.scope) for c in vault.credentials
                }
                return [
                    ref + (f"  [signin:{role}]" if role else "")
                    for ref, role in by_role.items()
                ]
        return []

    def tasks(self, segment: str) -> str:
        return _say(
            _cli("text", "--segment", segment, "--tasks", "--run", str(self.run_dir))
        )

    def act(self, segment: str, actions: Sequence[str], label: str = "") -> str:
        argv = ["step", "--segment", segment, "--run", str(self.run_dir)]
        for action in actions:
            argv += ["--do", action]
        if label:
            argv += ["--label", label]
        return _say(_cli(*argv))

    def record(
        self,
        segment: str,
        ref: str,
        verdict: str,
        note: str,
        severity: str = "",
        domain: str = "",
    ) -> str:
        argv = [
            "step", "--segment", segment, "--run", str(self.run_dir),
            "--note", note, "--verdict", verdict, "--ref", ref,
        ]
        if severity:
            argv += ["--severity", severity]
        if domain:
            argv += ["--domain", domain]
        return _say(_cli(*argv))

    def look(self, segment: str, label: str = "look") -> Path | None:
        """Capture the VM and return the newest image, so it can be attached.

        Returns ``None`` rather than raising when no image lands: a blind turn
        is worth attempting and worth *saying*, where an exception would abort a
        walk that could still produce findings.
        """
        before = self._images()
        self.act(segment, ["shot"], label=label)
        fresh = sorted(set(self._images()) - set(before))
        return fresh[-1] if fresh else None

    # The three below are deliberately *not* offered to the model. They move the
    # run through its states, and a model that can open, close or re-report a
    # section can also skip one. The loop calls them; nobody asks permission.

    def open_segment(self, segment: str) -> str:
        return _say(_cli(
            "step", "--segment", segment, "--start-segment", "--run", str(self.run_dir),
        ))

    def close_segment(self, segment: str, status: str) -> str:
        return _say(_cli(
            "step", "--segment", segment, "--end-segment", status,
            "--run", str(self.run_dir),
        ))

    def refresh_report(self) -> str:
        return _say(_cli("run", "--report", "--run", str(self.run_dir)))

    def _images(self) -> list[Path]:
        images = self.run_dir / "images"
        return sorted(images.glob("*.png")) if images.is_dir() else []


# --- progress measured from the run folder, never from the transcript --------


@dataclass(frozen=True)
class Fingerprint:
    """What the run folder says, reduced to the things a turn should change.

    Compared before and after each model turn. A model that reports success
    without moving any of these did not do the work, and this is the only place
    that can tell -- the transcript will read exactly the same either way.
    """

    steps: int
    unjudged: tuple[str, ...]
    status: str

    @classmethod
    def take(cls, run: Run, segment_id: str, outline: Outline | None) -> Fingerprint:
        run = Run.open(run.dir)  # re-read: the CLI wrote through a separate process
        segment = next((s for s in run.segments() if s.id == segment_id), None)
        if segment is None:
            return cls(0, (), "missing")
        steps = sum(1 for line in _trace(run) if line.get("segment") == segment_id)
        return cls(
            steps=steps,
            unjudged=tuple(unjudged_tasks(run, segment, outline)),
            status=segment.status,
        )


def _trace(run: Run) -> list[dict]:
    path = run.dir / "trace.jsonl"
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a half-written final line is normal for a live run
    return out


# --- the prompt for one move ------------------------------------------------


def prompt_for(move: Move, tools: Tools) -> str:
    """One move, one prompt. Never "walk the lab".

    The prompt names the exact tasks the loop is still waiting on, because a
    model told to "finish the section" will decide for itself what finishing
    means, and the whole point of task-level coverage is that it does not get
    to.
    """
    text = tools.instructions(move.segment_id)
    anchors = ", ".join(move.tasks) or "(none named)"
    asks = _asks_line(move)
    held = tools.inventory()
    vault = (
        "\nCredentials this lab issued, and which sign-in each belongs to: "
        + "; ".join(held)
        if held
        else ""
    )

    if move.action == "assess":
        job = (
            "This section is BLOCKED: the environment will not let a learner do "
            "the work. Judge the remaining tasks from the instruction text alone. "
            "Record each as DEFERRED with a note saying what could not be "
            "verified and why. Do not guess whether they would have passed."
        )
    else:
        job = (
            "Do these tasks in the lab, as a learner would, and record a verdict "
            "for each one separately."
        )

    return f"""{job}

Section: {move.segment_id} - {move.why}
Tasks still without a verdict: {anchors}{asks}{vault}

The instruction text a learner reads:
---
{text}
---

Rules:
- Act only through lab_act. The lab VM is the only route; there is no shell and
  no product API. If you cannot do it the way the instructions describe, that is
  the finding.
- Call lab_record once per task, with --ref set to that task's anchor exactly as
  listed above. A section anchor is rejected: it would vouch for every task
  under it.
- A verdict needs evidence you actually saw. Use lab_look before judging.
- PASS means the instruction matched what happened. If it did not, record the
  taxonomy code that fits and leave domain undetermined unless the evidence
  settles which side is wrong.
- Never type a credential literally. Use the action cred:SCOPE/LABEL so the
  value is sent without being printed.
- Match the credential to the screen, not to the task. For a sign-in, name the
  login and let the tool pick: signin:vm types the machine password,
  signin:portal the cloud password, and /username (signin:portal/username) the
  account field. This lab issues more than one password and they are not
  interchangeable, so choosing between them yourself is how a working lab gets
  reported as broken. A task called "Sign in to Azure Portal" can still be
  sitting behind a Windows sign-in that wants the machine account: read the
  screen first, and say what you see before you type.
- The machine sign-in always comes first. Everything you can reach -- browser,
  portal, terminal -- is inside the VM, so until the VM is unlocked there is
  nothing else to sign in to. signin:portal is refused before signin:vm has
  run, and the refusal is not something to work around by typing the password
  another way.
- A sign-in never reports success. It records DEFERRED, because the screen
  cannot be measured for it: a rejected sign-in and an accepted one look almost
  identical on a Windows console -- same blue, same avatar, same account name,
  one line of text apart. So capture the screen afterwards and read it. A
  password box still showing, or "The password is incorrect", means it failed;
  say so and try the other login rather than repeating the same one.
- A screen the instructions never mention is itself worth recording. Get past
  it if the Resources tab gives you what it needs, and record the omission
  against the task it blocked.
"""


def _asks_line(move: Move) -> str:
    asks = move.detail.get("asks") or {}
    if not asks:
        return ""
    pairs = "; ".join(
        f"{ref} -> {', '.join(labels)}" for ref, labels in sorted(asks.items()) if labels
    )
    if not pairs:
        return ""
    return f"\nCredentials these tasks are asking for (labels only): {pairs}"


# --- hooks ------------------------------------------------------------------


def build_hooks(redactor: Redactor, allowed: Sequence[str] = ALLOWED_TOOLS):
    """Refuse anything off the learner path, and never print a lab secret.

    ``on_pre_tool_use`` is the load-bearing one. Denying the shell is not about
    trust; it is that a shell makes the *wrong* answer reachable. An agent that
    fixes a broken deployment from a terminal will report the lab as working,
    and the learner following the written instructions still cannot complete it.
    """

    async def on_pre_tool_use(input_data, invocation=None):
        name = _tool_name(input_data)
        if name in allowed:
            return {"permissionDecision": "allow"}
        return {
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"{name!r} is not one of the learner's controls. This walk must "
                "reach every result the way a learner would, through the lab VM. "
                f"Available: {', '.join(allowed)}."
            ),
        }

    async def on_post_tool_use(input_data, invocation=None):
        result = _tool_result(input_data)
        if not isinstance(result, str):
            return None
        clean = redactor.text(result)
        return {"modifiedResult": clean} if clean != result else None

    return {"on_pre_tool_use": on_pre_tool_use, "on_post_tool_use": on_post_tool_use}


def _tool_name(input_data) -> str:
    if isinstance(input_data, dict):
        return input_data.get("toolName") or input_data.get("tool_name") or ""
    return getattr(input_data, "tool_name", None) or getattr(input_data, "toolName", "")


def _tool_result(input_data):
    if isinstance(input_data, dict):
        return input_data.get("toolResult", input_data.get("tool_result"))
    return getattr(input_data, "tool_result", None) or getattr(
        input_data, "toolResult", None
    )


# --- the loop ---------------------------------------------------------------


@dataclass
class Progress:
    """What happened, in enough detail to explain a stop without guessing."""

    turns: int = 0
    mechanical: int = 0
    stalls: int = 0
    timeouts: int = 0
    moves: list[str] = field(default_factory=list)
    stopped: str = ""

    def summary(self) -> str:
        timed_out = f", {self.timeouts} timed-out turn(s)" if self.timeouts else ""
        return (
            f"{self.turns} model turn(s), {self.mechanical} mechanical move(s), "
            f"{self.stalls} stall(s){timed_out}. {self.stopped}"
        )


async def drive(
    run: Run,
    ask: Callable[[Move, Path | None], Awaitable[None]],
    *,
    outline: Outline | None = None,
    tools: Tools | None = None,
    minutes: Callable[[], int | None] | None = None,
    max_turns: int = 200,
    turn_timeout: float = DEFAULT_TURN_TIMEOUT,
    say: Callable[[str], None] = print,
) -> Progress:
    """Walk the run to completion, asking ``ask`` only where judgement is needed.

    ``ask`` is injected rather than constructed here so the whole loop is
    testable without an SDK process or a browser: the interesting failures are a
    model that lies about progress and a move that should never have reached a
    model at all, and neither needs a real one to reproduce.

    ``turn_timeout`` is not enforced here -- ``ask`` owns that -- but the loop
    is told what it is so it can say how long a timed-out turn was given.
    """
    tools = tools or Tools(run.dir)
    progress = Progress()
    last_mechanical = ""
    repeats = 0
    last_output = ""
    consecutive_timeouts = 0

    # Which credentials the lab issued, by label. `next_move` needs these to
    # spot an instruction that is *asking* for one ("sign in with the username
    # from the Resources tab") and name it in the move. Values stay in the
    # vault: the loop passes labels so the model can request a credential by
    # name without one ever entering a prompt or a transcript.
    vault = Vault.load(run.dir)
    labels = vault.label_index() if vault else None

    while progress.turns + progress.mechanical < max_turns:
        run = Run.open(run.dir)
        move = next_move(
            run,
            outline,
            minutes_remaining=minutes() if minutes else None,
            labels=labels,
        )
        progress.moves.append(f"{move.action}:{move.segment_id or '-'}")
        say(f"  {move.action.upper()} {move.segment_id or ''} - {move.why}")

        if move.is_terminal:
            progress.stopped = move.why
            return progress

        if move.action in MECHANICAL:
            # The loop does not get to trust itself either. `next_move` derives
            # each mechanical move from state, so a working move changes the
            # state that produced it and the next move differs. An identical one
            # coming straight back means the command did not take -- a report
            # that failed to write, a segment that would not open -- and
            # repeating it will not help. One retry absorbs a transient browser
            # failure; three identical moves in a row is a stuck run, and saying
            # so beats burning the ceiling and reporting nothing.
            key = f"{move.action}:{move.segment_id}"
            repeats = repeats + 1 if key == last_mechanical else 0
            last_mechanical = key
            if repeats >= STALL_LIMIT - 1:
                progress.stopped = (
                    f"{move.action} {move.segment_id} came back {repeats + 1} times "
                    "and the run did not move on. What the command said last time:\n"
                    f"    {(last_output or '(no output)').strip()}\n"
                    "Sections already walked keep their reports; the rest are "
                    "unknown, not correct."
                )
                return progress
            last_output = _do_mechanical(move, tools, say)
            if LAB_CLOSED_MARK in last_output:
                # Not a stall. A stall is "this keeps failing"; this is "the
                # thing under test has gone". Grinding three more moves out of
                # a closed lab costs time and writes trace nobody can use, and
                # the run reads afterwards as though the lab were at fault.
                progress.stopped = (
                    f"The lab has closed. {last_output.strip()}\n"
                    "Nothing observed after this point is evidence about the "
                    "lab. Sections already walked keep their reports; the rest "
                    "are unknown, not correct. Launch the lab again and resume "
                    "with `lab-validator auto --run <dir>`."
                )
                return progress
            progress.mechanical += 1
            continue

        last_mechanical = ""
        before = Fingerprint.take(run, move.segment_id, outline)
        shot = tools.look(move.segment_id, label=f"{move.action}-{move.segment_id}")
        try:
            await ask(move, shot)
        except TimeoutError:
            # A turn that outlasts its budget is slow, not broken. The steps it
            # recorded are already on disk, the loop re-derives the next move
            # from the folder rather than from the model's memory, and the run
            # is resumable -- so dying here would throw away a walk that is
            # still valuable. It used to surface as a traceback ending inside
            # the SDK, which reads as "the tool crashed" when the agent was
            # part-way through signing into a portal and working correctly.
            consecutive_timeouts += 1
            progress.timeouts += 1
            say(
                f"  (that turn outlasted its {turn_timeout:.0f}s budget - "
                f"timeout {consecutive_timeouts}/{TIMEOUT_LIMIT}; "
                "anything it recorded is kept)"
            )
            if consecutive_timeouts >= TIMEOUT_LIMIT:
                progress.stopped = (
                    f"{consecutive_timeouts} model turns in a row outlasted the "
                    f"{turn_timeout:.0f}s budget while {move.action} "
                    f"{move.segment_id} was outstanding. Raise --turn-timeout if "
                    "the moves are simply long; the sections already walked keep "
                    "their reports, and this run can be resumed with "
                    "`lab-validator auto --run <dir>`."
                )
                return progress
        else:
            consecutive_timeouts = 0
        progress.turns += 1
        after = Fingerprint.take(run, move.segment_id, outline)

        if after == before:
            progress.stalls += 1
            say(
                f"  (no change in the run folder after that turn - "
                f"stall {progress.stalls}/{STALL_LIMIT})"
            )
            if progress.stalls >= STALL_LIMIT:
                progress.stopped = (
                    f"{STALL_LIMIT} consecutive turns changed nothing in the run "
                    f"folder while {move.action} {move.segment_id} was outstanding. "
                    "The sections already walked keep their reports; the rest are "
                    "unknown, not correct."
                )
                return progress
        else:
            progress.stalls = 0

    progress.stopped = f"reached the {max_turns}-move ceiling before the lab ended."
    return progress


def _do_mechanical(move: Move, tools: Tools, say: Callable[[str], None]) -> str:
    """Execute a move nobody needs to think about, and return what it said.

    The output is returned rather than only printed because when one of these
    starts failing it is the single most useful sentence in the run -- the first
    real walk stopped on a repeated READ, and "nothing is listening on port
    9222" was the whole diagnosis. A stop message that has to say "run it by
    hand to see why" is withholding an answer it already has.
    """
    segment = move.segment_id
    if move.action == "open":
        out = tools.open_segment(segment)
    elif move.action == "read":
        out = tools.act(segment, ["read"], label="read")
    elif move.action == "report":
        out = tools.refresh_report()
    elif move.action == "advance":
        status = "blocked" if move.detail.get("blocked") else "done"
        out = tools.close_segment(segment, status)
    else:
        return ""
    say(f"    {out}")
    return out


# --- wiring the real SDK ----------------------------------------------------


def _require_sdk():
    try:
        from copilot import CopilotClient  # noqa: PLC0415
        from copilot.tools import define_tool  # noqa: PLC0415
    except ImportError as exc:
        raise AgentUnavailable(
            "the Copilot SDK is not installed, so `auto` cannot drive this run.\n"
            "  pip install -e .[agent]\n"
            "and check `copilot --version` works.\n"
            "Nothing else is blocked: walk it yourself with `lab-validator next`, "
            "which asks the same loop for the same moves."
        ) from exc
    return CopilotClient, define_tool


def _verdict_menu() -> str:
    """The finding codes, named, generated from the taxonomy.

    Written into the tool description rather than left to the skill because the
    description is what the model reads *at the moment it chooses*. The first
    real run recorded "the lab environment is unreachable" as `LAB001 Retired or
    renamed model` -- the first code in the list -- because the description said
    only "a LAB0NN code" and never said what any of them meant. Given no
    information a model picks the first plausible option, and a
    misfiled finding goes to the wrong owner, who correctly rejects it.

    Generated, so it cannot drift from `taxonomy.py` the way `report.CODE_NAMES`
    once did -- that drift is what left 40 findings rendering as ``LAB009 --
    `LAB009` `` with no name at all.
    """
    from .taxonomy import FINDING_VERDICTS, name_of  # noqa: PLC0415

    return "; ".join(f"{code} = {name_of(code)}" for code in sorted(FINDING_VERDICTS))


_VERDICT_MENU = _verdict_menu()


class SegmentP(BaseModel):
    segment: str = Field(description="section id, e.g. s01")


class ActP(BaseModel):
    segment: str = Field(description="section id this step belongs to")
    actions: list[str] = Field(
        description=(
            "lab actions in order: click:X,Y  dblclick:X,Y  move:X,Y  focus  "
            "type:TEXT  signin:vm  signin:portal  cred:SCOPE/LABEL  key:Control+s  "
            "wait:MS  until:connected  shot  dialog  read  page:N. "
            "signin:vm unlocks the Windows desktop and must come before any "
            "signin:portal, which is refused until it has. A sign-in records "
            "DEFERRED, never PASS -- take a shot afterwards and read whether it "
            "was accepted."
        )
    )
    label: str = Field(default="", description="filename label for captures")


class RecordP(BaseModel):
    segment: str = Field(description="section id")
    ref: str = Field(
        description=(
            "the TASK anchor this verdict answers, e.g. 3-deploy-the-model. "
            "A section anchor is rejected -- it would vouch for every task "
            "beneath it."
        )
    )
    verdict: str = Field(
        description=(
            "PASS, BLOCKED, DEFERRED, or one of the finding codes below. "
            "Choose by definition, not by position: " + _VERDICT_MENU
        )
    )
    note: str = Field(description="what was observed, in a learner's words")
    severity: str = Field(
        default="", description="critical, major, minor or info -- findings only"
    )
    domain: str = Field(
        default="",
        description=(
            "instruction (the text is wrong) or setup (the environment is). "
            "Leave empty unless the evidence settles it."
        ),
    )


def build_tools(tools: Tools):
    """Expose the five learner controls to the model.

    Descriptions carry the *rule*, not just the shape, because the model reads
    them at the moment it is choosing what to do. "ref must be a task anchor"
    written here prevents the mistake; written only in the prompt it competes
    with everything else in the context.

    The parameter models live at module scope for a reason that is invisible
    until you run this: ``from __future__ import annotations`` turns every hint
    into a string, and ``define_tool`` resolves those with ``get_type_hints``,
    which looks in the *module's* globals. Declared inside this function they
    are unreachable there, and every tool fails to register with a bare
    ``NameError``. Nothing catches it earlier -- the annotation is never
    evaluated until the SDK asks.
    """
    _, define_tool = _require_sdk()

    @define_tool(description="Read the instruction text a learner sees for a section.")
    async def lab_instructions(params: SegmentP, invocation=None) -> str:
        return tools.instructions(params.segment)

    @define_tool(
        description="List the task anchors in a section. Use these for lab_record ref."
    )
    async def lab_tasks(params: SegmentP, invocation=None) -> str:
        return tools.tasks(params.segment)

    @define_tool(
        description="Act in the lab VM the way a learner would. The only route to the product."
    )
    async def lab_act(params: ActP, invocation=None) -> str:
        return tools.act(params.segment, params.actions, params.label)

    @define_tool(description="Record the verdict for exactly one task. Evidence required.")
    async def lab_record(params: RecordP, invocation=None) -> str:
        return tools.record(
            params.segment, params.ref, params.verdict,
            params.note, params.severity, params.domain,
        )

    @define_tool(description="Capture the VM screen so you can see what the learner sees.")
    async def lab_look(params: SegmentP, invocation=None) -> str:
        shot = tools.look(params.segment)
        return str(shot) if shot else "no screenshot was captured"

    return [lab_instructions, lab_tasks, lab_act, lab_record, lab_look]


def _why_no_session(exc: Exception, model: str) -> str:
    """Turn an SDK failure into the sentence that fixes it.

    Matched on the message rather than an exception type because the SDK
    delivers all of these as one generic JSON-RPC error; there is nothing else
    to match on. An unrecognised failure keeps its original text -- guessing a
    cause would be worse than admitting we do not know it.
    """
    said = str(exc)
    if "is not available" in said or "model" in said.lower() and "not" in said.lower():
        return (
            f"the model {model!r} is not available to your Copilot CLI.\n"
            "  copilot --help          # lists what this CLI accepts\n"
            "  lab-validator auto --model auto ...\n"
            "'auto' lets Copilot choose, and is the default for exactly this "
            "reason: a pinned model name eventually retires."
        )
    if "auth" in said.lower() or "token" in said.lower() or "401" in said:
        return (
            "the Copilot CLI is not authenticated, so no session could start.\n"
            "  copilot         # then /login\n"
            f"Original error: {said}"
        )
    return (
        f"could not start a Copilot session: {said}\n"
        "Nothing else is blocked -- `lab-validator next` walks the same loop "
        "without a model."
    )


async def run_agent(
    run: Run,
    *,
    outline: Outline | None = None,
    model: str = DEFAULT_MODEL,
    minutes: Callable[[], int | None] | None = None,
    max_turns: int = 200,
    turn_timeout: float = DEFAULT_TURN_TIMEOUT,
    say: Callable[[str], None] = print,
) -> Progress:
    """Create the session, then hand the loop an ``ask`` that uses it."""
    CopilotClient, _ = _require_sdk()
    tools = Tools(run.dir)

    redactor = Redactor()
    vault = Vault.load(run.dir)
    if vault:
        redactor.add_many((c.value, c.label) for c in vault.credentials)
        say(f"  redactor primed with {len(redactor)} lab-issued value(s)")

    client = CopilotClient(log_level="error")
    await client.start()
    try:
        try:
            session = await client.create_session(
                model=model,
                session_id=f"labwalk-{run.dir.name}",
                tools=build_tools(tools),
                hooks=build_hooks(redactor),
                skill_directories=[
                    str(
                        ROOT / "skills" / "lab-validator"
                        if (ROOT / "skills" / "lab-validator").is_dir()
                        else ROOT.parent
                        if ROOT.name == "runtime" and (ROOT.parent / "SKILL.md").is_file()
                        else ROOT
                    )
                ],
                infinite_sessions={"enabled": True},
                working_directory=str(ROOT),
                on_permission_request=lambda request: {"approved": True},
                system_message={
                    "content": (
                        "You are validating a hands-on lab by doing it as a learner "
                        "would. Your job is to find where the written instructions no "
                        "longer match reality. You are not here to make the lab "
                        "succeed: a step you cannot complete the documented way is a "
                        "finding, and working around it destroys the evidence. Follow "
                        "the lab-validator skill's judgement rules."
                    )
                },
            )
        except Exception as exc:
            # A JSON-RPC traceback is not an answer. The two things that
            # actually go wrong here -- a model name that has retired, and a CLI
            # that is not signed in -- both have a one-line fix, and both look
            # like an SDK crash if the error is allowed through raw.
            raise AgentUnavailable(_why_no_session(exc, model)) from exc

        async def ask(move: Move, shot: Path | None) -> None:
            attachments = (
                [{"type": "file", "path": str(shot), "displayName": shot.name}]
                if shot
                else None
            )
            await session.send_and_wait(
                prompt_for(move, tools),
                attachments=attachments,
                timeout=turn_timeout,
            )

        return await drive(
            run, ask, outline=outline, tools=tools,
            minutes=minutes, max_turns=max_turns,
            turn_timeout=turn_timeout, say=say,
        )
    finally:
        await client.stop()


def walk_autonomously(run_dir: Path, **kwargs) -> Progress:
    """Synchronous entry point, for the CLI.

    Resolves the outline through ``cli._outline_for`` rather than loading
    ``outline.json`` directly, so the agent inherits the hash check: a run whose
    saved outline no longer matches its corpus enumerates *a different lab's*
    tasks, with total confidence and no error. That defect cost a fix once
    already (`ba03729`); reading the file blind here would have reintroduced it
    on the one path nobody watches.
    """
    from .cli import _outline_for  # noqa: PLC0415  (cli imports us; break the cycle)

    run = Run.open(run_dir)
    outline, why_not = _outline_for(run)
    if outline is None and why_not:
        print(f"  no task-level coverage: {why_not}")
    return asyncio.run(run_agent(run, outline=outline, **kwargs))


__all__ = [
    "ALLOWED_TOOLS",
    "AgentUnavailable",
    "Fingerprint",
    "Progress",
    "Tools",
    "build_hooks",
    "drive",
    "prompt_for",
    "run_agent",
    "walk_autonomously",
]
