"""What did each action actually do to the screen?

A live run recorded **PASS on all 77 steps** while doing nothing whatsoever. The
VM sign-in worked, the desktop appeared -- and then the walk spent sixty-odd
actions typing `https://portal.azure.com`, pressing `ctrl+l`, `/` and `g`, and
clicking at (500,60), (700,72) and (640,50), **into bare wallpaper, with no
browser ever opened**. Every action was dispatched, every action was recorded
`PASS`, and not one of them changed a pixel. The user's report was four words:
*the next few steps don't seem to move anything.*

The tool had the evidence to say so and threw it away. Only `signin:` ever
looked at the screen; every other verb reported success on the strength of
having been dispatched. So the model clicked, was told PASS, and had no way on
earth to learn that nothing had happened.

## So this module measures, and does not judge

The delta goes to the model as an observation in plain words, and to
:class:`DebugLog` for reading afterwards. It never becomes a verdict, never
becomes a finding, and never stops the walk. Perception and judgement belong to
the model, which has the screenshot; binding and sequencing belong to the code,
which has the vault and the trace. *Did that click accomplish anything* is
squarely a perception question, and the honest answer is a number together with
what the number is worth.

## What the numbers were worth, on the one console measured

======================================  ===========
transition                              delta
======================================  ===========
click on empty wallpaper                0.0
clock digit / caret blink               0.002-0.005
`Tab` moving a desktop focus ring       0.28
typing into a lock screen               0.52
lock screen giving way to the desktop   94.75
======================================  ===========

Which is why nothing here is compared against a constant. A run measures its own
idle noise from the intervals where **nothing was sent**, and describes an
action relative to that. One console at one resolution is not a population, and
a number tuned to it would be exactly that.
"""

from __future__ import annotations

import json
import statistics
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .imaging import stability
from .runlog import iso

#: Verbs that put something *into* the VM, and so ought to leave a mark.
#:
#: `move` and `focus` are deliberately absent: moving the pointer or focusing
#: the canvas can legitimately leave every pixel alone, so counting them would
#: report a healthy console as unresponsive.
INPUT_VERBS = frozenset({"click", "dblclick", "scroll", "type", "cred", "signin", "key"})

#: Fallback noise floor, used only until a run has measured its own.
#:
#: Taken from the idle intervals of the one run available (largest 0.0048) with
#: room to spare. It is a placeholder for the first few frames, not a threshold:
#: as soon as two idle intervals exist, the run's own measurement replaces it.
ASSUMED_IDLE = 0.01

#: How many consecutive unanswered input intervals before the walk is *told to
#: look*. Not a verdict -- see :meth:`ConsoleWatch.notice`.
PATIENCE = 3


@dataclass(frozen=True)
class Interval:
    """One gap between two frames, and what was sent during it."""

    delta: float
    actions: tuple[str, ...]
    label: str = ""
    floor: float = ASSUMED_IDLE

    @property
    def had_input(self) -> bool:
        return any(a.partition(":")[0].strip().lower() in INPUT_VERBS for a in self.actions)

    @property
    def moved(self) -> bool:
        """Did the screen change by more than this console does on its own?"""
        return self.delta > self.floor

    @property
    def unmoved_input(self) -> bool:
        return self.had_input and not self.moved

    def describe(self) -> str:
        """One sentence for the model, stating the reading and its worth."""
        if not self.had_input:
            return f"screen delta {self.delta:.2f}"
        if self.moved:
            return f"the screen changed (delta {self.delta:.2f})"
        return (
            f"the screen did NOT change (delta {self.delta:.2f}, at or below "
            f"this console's own idle noise of {self.floor:.2f}) -- whatever "
            "was sent had no visible effect"
        )


@dataclass
class ConsoleWatch:
    """Watches frames go past and says what moved between them.

    Fed from the single place every image the walk writes passes through, so it
    sees the whole run without asking for one extra screenshot.
    """

    patience: int = PATIENCE
    intervals: list[Interval] = field(default_factory=list)
    _last: bytes | None = field(default=None, repr=False)
    _pending: list[str] = field(default_factory=list, repr=False)

    def did(self, action: str) -> None:
        """Note an action performed since the last frame."""
        self._pending.append(action)

    @property
    def idle_floor(self) -> float:
        """What this console does when nothing is sent to it.

        The median of the idle intervals, not the maximum: a screen still
        settling from an earlier action shows up as a huge idle delta (94.75, on
        the run that prompted this), and a maximum would swallow it and then
        declare every subsequent action ineffective.
        """
        idle = [i.delta for i in self.intervals if not i.had_input]
        if len(idle) < 2:
            return ASSUMED_IDLE
        return max(statistics.median(idle), ASSUMED_IDLE)

    def saw(self, frame: bytes, label: str = "") -> Interval | None:
        """Record a frame. Returns the interval since the last one, or None.

        None means this is the first frame, which measures nothing -- worth
        keeping distinct, because "no comparison yet" and "nothing changed" are
        very different claims, and only one of them is about the console.
        """
        actions, self._pending = tuple(self._pending), []
        if self._last is None:
            self._last = frame
            return None
        delta = stability(self._last, frame)
        self._last = frame
        interval = Interval(delta=delta, actions=actions, label=label, floor=self.idle_floor)
        self.intervals.append(interval)
        return interval

    @classmethod
    def resume(cls, run_dir: Path, patience: int = PATIENCE) -> ConsoleWatch:
        """Rebuild a watch from what a previous process left on disk.

        Every `step` invocation is its own process, so a watch held only in
        memory would forget the run each time and could never see a stall that
        spans two commands -- which is every stall that matters. The state is
        read back rather than passed along, so `auto --run` on a folder from
        last week inherits it exactly as a fresh walk does.

        The baseline frame comes from the newest image already captured, so the
        first action of a new process is measured against where the last one
        left off instead of starting blind.
        """
        watch = cls(patience=patience)
        for record in DebugLog.read(run_dir):
            if record.get("kind") != "interval":
                continue
            watch.intervals.append(
                Interval(
                    delta=float(record.get("delta", 0.0)),
                    actions=tuple(record.get("actions", ())),
                    label=str(record.get("label", "")),
                    floor=float(record.get("floor", ASSUMED_IDLE)),
                )
            )
        images = sorted(
            p for p in (Path(run_dir) / "images").glob("[0-9][0-9][0-9][0-9]-*")
            if "view" not in p.name
        )
        if images:
            watch._last = images[-1].read_bytes()
        return watch

    @property
    def unmoved_run(self) -> list[Interval]:
        """The unbroken run of ineffective input intervals ending at the latest.

        Trailing, not total: a walk that got stuck and recovered is not stuck,
        and counting every stall in a long run would eventually convict it.
        """
        out: list[Interval] = []
        for interval in reversed(self.intervals):
            if interval.unmoved_input:
                out.append(interval)
            elif interval.had_input or interval.moved:
                break
            # An idle interval that did not move says nothing either way: a bare
            # `shot` between two clicks must not reset the count.
        return list(reversed(out))

    def notice(self) -> str | None:
        """A prompt to look at the screen -- explicitly not a conclusion.

        Returned once the walk has sent input to a screen that has not answered
        for :attr:`patience` intervals. It lists what that can mean and chooses
        none of them, because from a delta alone they are indistinguishable, and
        the first draft of this module proved how readily a plausible one gets
        picked and believed.
        """
        run = self.unmoved_run
        if len(run) < self.patience:
            return None
        did = [a for i in run for a in i.actions if a.partition(":")[0].lower() in INPUT_VERBS]
        return (
            f"NOTHING YOU HAVE DONE IN THE LAST {len(run)} CAPTURES HAS CHANGED "
            f"THE SCREEN. {len(did)} input action(s) were sent "
            f"({', '.join(did[:5])}{' ...' if len(did) > 5 else ''}) and every "
            "time the screen stayed within its own idle noise.\n"
            "This is an observation, not a verdict, and it is NOT a lab defect "
            "-- do not record a finding for it. Look at the current screenshot "
            "before doing anything else, then work out which of these it is:\n"
            "  - you are acting on the wrong surface: typing a URL or pressing "
            "ctrl+l with no browser window open, or clicking coordinates that "
            "are bare desktop. Read the screen and open the application first.\n"
            "  - the window you mean to drive is not focused, so the keystrokes "
            "are going somewhere else.\n"
            "  - the click coordinates are wrong -- check them against the "
            "screenshot rather than against where the control usually sits.\n"
            "  - the console really has stopped responding, in which case the "
            "clock in the taskbar will be frozen too.\n"
            "Take a screenshot and read it. Do not repeat the actions above."
        )


class DebugLog:
    """An append-only diagnostic record, written beside the run's evidence.

    Deliberately *not* the trace. The trace is what the report is built from and
    what a human is asked to believe; padding it with per-action pixel deltas
    would make the evidence harder to read in order to make debugging easier,
    which is the wrong trade. This file may be as noisy as it likes.

    Flushed per line for the reason every debug log is: the run it describes is
    the one most likely to die halfway through, and buffering loses precisely
    the last few lines that say why.
    """

    NAME = "debug.jsonl"

    def __init__(self, run_dir: Path, enabled: bool = True, verbose: bool = False) -> None:
        self.path = Path(run_dir) / self.NAME
        self.enabled = enabled
        #: Whether to also print diagnostics to the console as they happen.
        #: Separate from :attr:`enabled` because they answer different
        #: questions: one is "will I be able to read this tomorrow", the other
        #: is "do I want to watch it now".
        self.verbose = verbose

    def write(self, kind: str, **fields) -> None:
        if not self.enabled:
            return
        record = {"ts": iso(), "kind": kind, **fields}
        with self.path.open("a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")

    @classmethod
    def read(cls, run_dir: Path) -> list[dict]:
        path = Path(run_dir) / cls.NAME
        if not path.exists():
            return []
        out = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    # A run killed mid-write leaves half a line. Losing it is
                    # correct; refusing to read the 900 good lines above it is
                    # not -- this file exists for exactly that run.
                    continue
        return out


def replay(images: Iterable[Path], steps: Sequence[dict] | None = None) -> ConsoleWatch:
    """Rebuild a watch from a finished run's images.

    The reason this exists: the run that motivated the whole feature was
    recorded *before* any of it was written, and its frames held the answer the
    entire time. A diagnostic that only works when you already knew you would
    need it is not much of a diagnostic.

    Actions are attached from the trace when one is offered, so replaying an
    instrumented run and an old one read alike.
    """
    watch = ConsoleWatch()
    by_image = _actions_by_image(steps or [])
    for image in sorted(images):
        for action in by_image.get(image.name, ()):
            watch.did(action)
        watch.saw(image.read_bytes(), label=image.stem)
    return watch


def _actions_by_image(steps: Sequence[dict]) -> dict[str, list[str]]:
    """Map each captured image to the actions recorded since the previous one.

    Walks the trace in order, banking actions until a step names an image.
    """
    out: dict[str, list[str]] = {}
    pending: list[str] = []
    for step in steps:
        action = str(step.get("action", ""))
        images = [Path(str(i)).name for i in step.get("images", []) or []]
        if action:
            pending.append(action)
        if images:
            out.setdefault(images[0], []).extend(pending)
            pending = []
    return out
