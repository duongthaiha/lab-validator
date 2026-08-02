"""What the console watch may say, and what it must refuse to say.

This module exists because a live walk did sixty-five actions against a Windows
desktop with no browser open and was told `PASS` every single time. So most of
these tests are about the feedback loop being real: an action that changed
nothing must be *reported* as having changed nothing.

The rest guard something more specific. The first draft of `console.py`
measured that same run, found twenty-four byte-identical frames, and concluded
the console had frozen -- with a stop, and a message telling the user to
reconnect the lab. The console was in perfect health; the clock in the last
frame reads 5:39 PM. Every number was right and the story built on them was
invented. Several tests below exist purely so that story cannot come back.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

from lab_validator.console import (
    ASSUMED_IDLE,
    INPUT_VERBS,
    ConsoleWatch,
    DebugLog,
    Interval,
    _actions_by_image,
    replay,
)

ROOT = Path(__file__).resolve().parents[1]


def _lab_step():
    if "lab_step" in sys.modules:
        return sys.modules["lab_step"]
    spec = importlib.util.spec_from_file_location("lab_step", ROOT / "scripts" / "lab_step.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lab_step"] = module
    spec.loader.exec_module(module)
    return module


def _frame(colour: tuple[int, int, int] = (90, 140, 190), speck: int = 0) -> bytes:
    """A PNG the shape a console produces, optionally with pixels disturbed.

    Textured on purpose. An earlier version was flat colour, and flat colour
    survives JPEG compression *exactly* -- so a test comparing a raw PNG against
    the saved JPEG measured 0.0 and passed while the code under test was wrong.
    A real console is icons, text and a taskbar, which is precisely the
    high-frequency detail JPEG disturbs. Measured: flat 0.000, textured 3.383.
    """
    img = Image.new("RGB", (320, 240), colour)
    for y in range(0, 240, 3):
        for x in range(0, 320, 3):
            v = (x * 37 + y * 91) % 256
            img.putpixel((x, y), (v, 255 - v, (v * 3) % 256))
    for i in range(speck):
        img.putpixel((i * 7 % 320, i * 11 % 240), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------
# The reading itself


def test_an_action_that_changed_nothing_is_reported_as_changing_nothing():
    """The whole point. A click that moved no pixels must say so."""
    watch = ConsoleWatch()
    still = _frame()
    watch.saw(still)
    watch.did("click:500,60")
    interval = watch.saw(still)

    assert interval.had_input
    assert not interval.moved
    assert interval.unmoved_input
    assert "did NOT change" in interval.describe()


def test_an_action_that_moved_the_screen_says_so():
    watch = ConsoleWatch()
    watch.saw(_frame((90, 140, 190)))
    watch.did("click:500,60")
    interval = watch.saw(_frame((200, 40, 40)))

    assert interval.moved
    assert "the screen changed" in interval.describe()


def test_the_first_frame_measures_nothing_and_says_so_by_returning_none():
    """"Nothing to compare yet" and "nothing changed" must not collapse.

    Both are falsy, and only one of them is a statement about the console.
    """
    assert ConsoleWatch().saw(_frame()) is None


def test_a_still_screen_nobody_touched_is_not_called_unresponsive():
    """A walk may capture twice without acting. That is not a symptom."""
    watch = ConsoleWatch()
    still = _frame()
    watch.saw(still)
    watch.did("shot")
    interval = watch.saw(still)

    assert not interval.had_input
    assert not interval.unmoved_input
    assert "did NOT change" not in interval.describe()


def test_pointer_moves_and_focus_are_not_counted_as_input():
    """Both can legitimately leave every pixel alone on a healthy console.

    Counting them would report a working console as unresponsive, which is the
    exact class of wrong answer this module was rewritten to avoid.
    """
    assert "move" not in INPUT_VERBS
    assert "focus" not in INPUT_VERBS
    watch = ConsoleWatch()
    still = _frame()
    watch.saw(still)
    watch.did("move:10,10")
    watch.did("focus")
    assert not watch.saw(still).had_input


# --------------------------------------------------------------------------
# The floor is measured, not chosen


def test_the_floor_comes_from_the_runs_own_idle_intervals():
    """No constant to tune. A busier console raises its own bar."""
    watch = ConsoleWatch()
    watch.saw(_frame(speck=0))
    for n in (60, 120, 180, 240):  # idle churn: no input, real pixel movement
        watch.did("shot")
        watch.saw(_frame(speck=n))

    assert watch.idle_floor > ASSUMED_IDLE

    # An action producing no more movement than that churn has not been shown
    # to have done anything.
    watch.did("key:Enter")
    interval = watch.saw(_frame(speck=300))
    assert not interval.moved


def test_the_floor_is_a_median_so_one_settling_frame_cannot_raise_it():
    """A screen still settling from an earlier action shows up as a huge idle
    delta -- 94.75 on the run that prompted this, when the desktop replaced the
    lock screen. A maximum would swallow it and then declare every subsequent
    action ineffective.
    """
    watch = ConsoleWatch()
    watch.intervals = [
        Interval(delta=0.0, actions=("shot",)),
        Interval(delta=0.0, actions=("shot",)),
        Interval(delta=94.75, actions=("shot",)),  # the desktop appearing
        Interval(delta=0.0, actions=("shot",)),
    ]
    assert watch.idle_floor == pytest.approx(ASSUMED_IDLE)


def test_the_floor_never_drops_below_the_assumed_one():
    """A perfectly still console must not set a floor of zero, or a single
    JPEG artefact would count as the screen responding."""
    watch = ConsoleWatch()
    watch.intervals = [Interval(delta=0.0, actions=("shot",)) for _ in range(6)]
    assert watch.idle_floor >= ASSUMED_IDLE


# --------------------------------------------------------------------------
# The trailing run


def test_a_bare_capture_between_two_clicks_does_not_reset_the_count():
    """Walks capture constantly. If an idle frame broke the streak, a stuck
    walk would never accumulate one."""
    watch = ConsoleWatch()
    still = _frame()
    watch.saw(still)
    for action in ("click:1,1", "shot", "click:2,2", "shot", "key:Enter"):
        watch.did(action)
        watch.saw(still)

    assert len(watch.unmoved_run) == 3


def test_a_walk_that_recovered_is_not_reported_as_stuck():
    """Trailing, not total. Otherwise a long run eventually convicts itself."""
    watch = ConsoleWatch()
    still = _frame()
    watch.saw(still)
    for _ in range(5):
        watch.did("click:1,1")
        watch.saw(still)
    watch.did("click:2,2")
    watch.saw(_frame((10, 200, 10)))  # something finally happened

    assert watch.unmoved_run == []
    assert watch.notice() is None


def test_the_notice_holds_its_tongue_until_the_evidence_is_in():
    """One ineffective click is normal -- clicking empty desktop changes
    nothing and is not a symptom of anything."""
    watch = ConsoleWatch(patience=3)
    still = _frame()
    watch.saw(still)
    for n in range(2):
        watch.did(f"click:{n},{n}")
        watch.saw(still)
        assert watch.notice() is None

    watch.did("click:9,9")
    watch.saw(still)
    assert watch.notice() is not None


# --------------------------------------------------------------------------
# What the notice must never claim
#
# The first draft said the console had frozen and told the user to reconnect
# the lab. It was wrong: the console was fine and the walk was typing URLs at a
# desktop with no browser. These four tests are the anti-regression.


def _stuck_notice() -> str:
    watch = ConsoleWatch(patience=3)
    still = _frame()
    watch.saw(still)
    for n in range(4):
        watch.did(f"click:{n},{n}")
        watch.saw(still)
    return watch.notice()


def test_the_notice_never_concludes_the_console_is_dead():
    """It cannot know that. A still screen is equally consistent with a walk
    acting on the wrong surface, which is what it actually was."""
    notice = _stuck_notice().lower()
    for claim in ("has frozen", "is frozen", "session dropped", "reconnect the lab"):
        assert claim not in notice, f"the notice asserts {claim!r}, which it cannot know"


def test_the_notice_offers_the_cause_that_was_actually_true():
    """A prompt to look, with the real answer among the options. The run this
    came from was driving a browser that had never been launched."""
    notice = _stuck_notice().lower()
    assert "wrong surface" in notice
    assert "no browser window open" in notice
    assert "open the application first" in notice


def test_the_notice_offers_more_than_one_cause_and_picks_none():
    """Naming a single cause is how the first draft went wrong. The value here
    is the enumeration; a notice that chose would be a verdict."""
    notice = _stuck_notice()
    bullets = [ln for ln in notice.splitlines() if ln.strip().startswith("- ")]
    assert len(bullets) >= 3, f"only {len(bullets)} candidate causes offered"


def test_the_notice_forbids_recording_it_as_a_finding():
    """A screen that will not move is a fact about the harness or the walk, not
    about the lab's instructions. Filing it repeats the dead-pane mistake: a
    real observation attributed to the wrong subject."""
    notice = _stuck_notice()
    assert "NOT a lab defect" in notice
    assert "do not record a finding" in notice.lower()
    assert "observation, not a verdict" in notice


def test_the_notice_says_what_to_do_instead_of_only_what_is_wrong():
    """An instruction to look, with no statement of what to look for, is how
    thirteen wrong passwords got typed in the first place."""
    notice = _stuck_notice().lower()
    assert "take a screenshot and read it" in notice
    assert "do not repeat the actions above" in notice


def test_the_notice_names_the_actions_that_achieved_nothing():
    """Without them a reader cannot tell which surface was being driven."""
    watch = ConsoleWatch(patience=3)
    still = _frame()
    watch.saw(still)
    for action in ("type:https://portal.azure.com", "key:ctrl+l", "click:640,50", "key:Enter"):
        watch.did(action)
        watch.saw(still)

    notice = watch.notice()
    assert "ctrl+l" in notice
    assert "portal.azure.com" in notice


# --------------------------------------------------------------------------
# Resuming, because every step is its own process


def test_a_watch_resumes_what_an_earlier_process_recorded(tmp_path):
    """Every `step` is a separate process. A watch that forgot the run between
    commands could never see a stall spanning two of them -- which is every
    stall that matters."""
    (tmp_path / "images").mkdir()
    log = DebugLog(tmp_path)
    for n in range(3):
        log.write("interval", delta=0.0, actions=[f"click:{n},{n}"], label=f"f{n}",
                  floor=ASSUMED_IDLE, moved=False)

    watch = ConsoleWatch.resume(tmp_path)
    assert len(watch.intervals) == 3
    assert watch.notice() is not None, "a stall spanning processes went unseen"


def test_a_resumed_watch_starts_from_the_newest_frame_on_disk(tmp_path):
    """Otherwise the first action of every process is measured against nothing
    and silently reported as unmeasurable."""
    images = tmp_path / "images"
    images.mkdir()
    (images / "0007-s00-thing.jpg").write_bytes(_frame())

    watch = ConsoleWatch.resume(tmp_path)
    watch.did("click:1,1")
    assert watch.saw(_frame()) is not None, "the baseline frame was not restored"


def test_a_resumed_watch_ignores_the_reader_sized_copies(tmp_path):
    """`view` copies are a different size, so mixing them in would measure the
    resize rather than the screen."""
    images = tmp_path / "images"
    images.mkdir()
    (images / "0007-s00-thing.jpg").write_bytes(_frame())
    (images / "0008-s00-thing-view.jpg").write_bytes(_frame((1, 2, 3)))

    watch = ConsoleWatch.resume(tmp_path)
    watch.did("click:1,1")
    assert watch.saw(_frame()).delta == pytest.approx(0.0)


# --------------------------------------------------------------------------
# The live defect: like must be compared with like


def test_capture_measures_the_saved_frame_not_the_raw_one(tmp_path):
    """Found against a live lab, and it would have made the feature useless
    while looking healthy.

    A resumed watch reads its baseline back from disk, where the frame is a
    JPEG. `capture` was handing the watch the lossless PNG, so each process's
    first comparison measured one encoder against another rather than one
    moment against another. Live, that scored every interval at ~0.02 against a
    0.01 floor: everything "moved", nothing was ever reported as ineffective,
    and the notice could never fire.

    The test has to span two processes, because that is the only place the
    defect lives -- inside a single process both frames are raw and agree. An
    earlier draft captured twice in one process, passed, and proved nothing.

    Stated without reference to either encoder: a screen that did not change
    between two processes must measure zero.
    """
    lab_step = _lab_step()

    class FakeLab:
        async def screen_bytes(self):
            return _frame()

    class FakeRun:
        def __init__(self):
            self.dir = tmp_path
            self.n = 0

        def next_image(self, segment, label):
            self.n += 1
            (tmp_path / "images").mkdir(exist_ok=True)
            return tmp_path / "images" / f"{self.n:04d}-{segment}-{label}.jpg"

    async def first_process():
        await lab_step.capture(FakeLab(), FakeRun(), "s00-x", "one", ConsoleWatch())

    async def second_process():
        run = FakeRun()
        run.n = 1
        watch = ConsoleWatch.resume(tmp_path)
        watch.did("click:500,60")
        await lab_step.capture(FakeLab(), run, "s00-x", "two", watch)
        return watch

    asyncio.run(first_process())
    watch = asyncio.run(second_process())

    assert watch.intervals[-1].delta == pytest.approx(0.0), (
        "an unchanged screen measured as movement across a resume -- the watch "
        "is being fed a differently encoded frame from the one it resumes "
        "against, so every action will look effective and no stall can be seen"
    )
    assert watch.intervals[-1].unmoved_input


def test_capture_still_works_with_no_watch(tmp_path):
    """The measurement is an addition, not a precondition."""
    lab_step = _lab_step()

    class FakeLab:
        async def screen_bytes(self):
            return _frame()

    class FakeRun:
        dir = tmp_path

        def next_image(self, segment, label):
            (tmp_path / "images").mkdir(exist_ok=True)
            return tmp_path / "images" / "0001-x.jpg"

    out = asyncio.run(lab_step.capture(FakeLab(), FakeRun(), "s00-x", "one"))
    assert out.exists()


# --------------------------------------------------------------------------
# The log


def test_the_log_survives_a_run_that_died_mid_write(tmp_path):
    """This file exists for exactly the run that dies. Losing the truncated
    last line is correct; refusing to read the good lines above it is not."""
    log = DebugLog(tmp_path)
    log.write("interval", delta=0.0, actions=["click:1,1"])
    log.write("interval", delta=1.0, actions=["click:2,2"])
    with (tmp_path / DebugLog.NAME).open("a", encoding="utf-8") as fh:
        fh.write('{"kind": "interval", "delta": 0.')

    assert len(DebugLog.read(tmp_path)) == 2


def test_the_log_is_written_without_being_asked_for(tmp_path):
    """Not opt-in, for the same reason the run folder is not. You never know
    which run will be the one that goes wrong, and a diagnostic switched on
    afterwards has nothing to say about what already happened."""
    source = (ROOT / "scripts" / "lab_step.py").read_text(encoding="utf-8")
    assert "log = DebugLog(run.dir)" in source
    assert "DebugLog(run.dir, enabled=args.debug" not in source
    assert "if args.debug" not in source.split("log.verbose")[0][-400:], (
        "the log is gated on --debug; it must record always and print on request"
    )


def test_verbosity_and_recording_are_separate_switches(tmp_path):
    """They answer different questions: "will I be able to read this tomorrow"
    and "do I want to watch it now"."""
    log = DebugLog(tmp_path, enabled=True, verbose=False)
    log.write("interval", delta=0.0)
    assert DebugLog.read(tmp_path), "recording followed verbosity"


def test_a_disabled_log_writes_no_file(tmp_path):
    DebugLog(tmp_path, enabled=False).write("interval", delta=0.0)
    assert not (tmp_path / DebugLog.NAME).exists()


def test_the_log_never_dies_on_something_json_cannot_hold(tmp_path):
    """A debug log that raises inside the run it is debugging is worse than
    none."""
    log = DebugLog(tmp_path)
    log.write("interval", where=Path("images/0001.jpg"))
    assert DebugLog.read(tmp_path)[0]["where"]


# --------------------------------------------------------------------------
# Replaying a run that was never instrumented


def test_a_run_recorded_before_any_of_this_can_still_be_explained(tmp_path):
    """The run that motivated the feature predates it by weeks, and its frames
    held the answer the whole time. A diagnostic that only works when you
    already knew you would need it is not much of one."""
    images = tmp_path / "images"
    images.mkdir()
    still = _frame()
    for n in range(1, 5):
        (images / f"{n:04d}-s00-x-look.jpg").write_bytes(still)

    steps = [
        {"action": "click:1,1"},
        {"action": "shot", "images": ["images/0002-s00-x-look.jpg"]},
        {"action": "type:hello"},
        {"action": "shot", "images": ["images/0003-s00-x-look.jpg"]},
        {"action": "key:Enter"},
        {"action": "shot", "images": ["images/0004-s00-x-look.jpg"]},
    ]
    watch = replay(sorted(images.glob("*.jpg")), steps)

    assert len(watch.intervals) == 3
    assert watch.notice() is not None, "an entirely ineffective run read as fine"


def test_actions_are_credited_to_the_interval_they_happened_in():
    """Otherwise the report names the wrong actions beside a delta, which is a
    quieter version of the mistake this whole module is about."""
    mapping = _actions_by_image([
        {"action": "click:1,1"},
        {"action": "type:abc"},
        {"action": "shot", "images": ["images/0002-x.jpg"]},
        {"action": "key:Enter"},
        {"action": "shot", "images": ["images/0003-x.jpg"]},
    ])
    assert mapping["0002-x.jpg"] == ["click:1,1", "type:abc", "shot"]
    assert mapping["0003-x.jpg"] == ["key:Enter", "shot"]


def test_replay_and_a_live_watch_read_a_still_screen_the_same_way(tmp_path):
    """Live and retrospective must not disagree, or a run explained after the
    fact would contradict what the walk was told at the time."""
    images = tmp_path / "images"
    images.mkdir()
    still = _frame()
    for n in range(1, 4):
        (images / f"{n:04d}-s00-x.jpg").write_bytes(still)

    live = ConsoleWatch()
    live.saw(still, label="0001")
    for _ in range(2):
        live.did("click:1,1")
        live.saw(still)

    back = replay(sorted(images.glob("*.jpg")), [
        {"action": "click:1,1"},
        {"action": "shot", "images": ["images/0002-s00-x.jpg"]},
        {"action": "click:1,1"},
        {"action": "shot", "images": ["images/0003-s00-x.jpg"]},
    ])

    assert [i.delta for i in back.intervals] == [i.delta for i in live.intervals]
    assert all(i.unmoved_input for i in back.intervals)


# --------------------------------------------------------------------------
# The command


def test_the_debug_command_is_offered_in_the_help():
    from lab_validator.cli import BUILTINS

    assert "debug" in BUILTINS


def test_the_reader_refuses_a_runs_root_and_names_the_runs_inside(tmp_path):
    """`--run` and `--runs` sit next to each other and mean opposite things, so
    this is the mistake people actually make. A traceback reads as a crash
    rather than as a typo."""
    from lab_validator.debugread import report

    (tmp_path / "2026-01-01T0000Z").mkdir()
    (tmp_path / "2026-01-01T0000Z" / "run.json").write_text("{}", encoding="utf-8")
    with pytest.raises(FileNotFoundError) as exc:
        report(tmp_path)

    assert "runs root" in str(exc.value)
    assert "2026-01-01T0000Z" in str(exc.value)


def test_the_report_says_when_it_measured_the_images_itself(tmp_path):
    """A reader must know whether they are seeing what the walk was told at the
    time or what was reconstructed afterwards."""
    from lab_validator.debugread import report

    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    images = tmp_path / "images"
    images.mkdir()
    for n in range(1, 4):
        (images / f"{n:04d}-s00-x.jpg").write_bytes(_frame())
    (tmp_path / "trace.jsonl").write_text(
        "\n".join(json.dumps(s) for s in [
            {"action": "click:1,1"},
            {"action": "shot", "images": ["images/0002-s00-x.jpg"]},
        ]), encoding="utf-8")

    text = report(tmp_path)
    assert "not instrumented" in text
    assert "measured from the images" in text


def test_the_report_ends_by_sending_the_reader_to_the_screen(tmp_path):
    """Every wrong conclusion in this feature's history was fixed by somebody
    looking at the picture."""
    from lab_validator.debugread import report

    (tmp_path / "run.json").write_text("{}", encoding="utf-8")
    images = tmp_path / "images"
    images.mkdir()
    (images / "0001-s00-x.jpg").write_bytes(_frame())

    text = report(tmp_path)
    assert "Last capture: images/0001-s00-x.jpg" in text
    assert "the screen is the evidence" in text


# --- The skill quotes the notice verbatim, so it can go stale silently -------


def _quoted_notice() -> str:
    """The notice text as SKILL.md reproduces it, unwrapped to one line.

    The skill shows the agent what this warning looks like so it recognises it
    in its own transcript. That makes it a copy of a string owned by
    console.py, and a copy is free to drift the moment the original is
    reworded -- leaving the agent looking for words it will never be sent.
    """
    doc = Path(__file__).resolve().parents[1] / "skills" / "lab-validator" / "SKILL.md"
    text = doc.read_text(encoding="utf-8")
    marker = "NOTHING YOU HAVE DONE"
    start = text.index(marker)
    end = text.index("```", start)
    return " ".join(text[start:end].split())


def _real_notice() -> str:
    watch = ConsoleWatch()
    watch.saw(_frame(0))
    for _ in range(4):
        watch.did("key:ctrl+l")
        watch.did("type:https://portal.azure.com")
        watch.saw(_frame(0))
    notice = watch.notice()
    assert notice, "the fixture should have produced a notice"
    return " ".join(notice.split())


def test_the_notice_quoted_in_the_skill_is_the_notice_the_agent_receives():
    """Every fixed phrase in the skill's quote must really be sent.

    Matched fragment-wise rather than whole, because the counts and the action
    list are run-specific -- but the prose around them is not, and that is the
    part an agent would be scanning for.
    """
    quoted = _quoted_notice()
    real = _real_notice()
    fragments = [f.strip() for f in re.split(r"\d+|\([^)]*\)", quoted)]
    checked = 0
    for fragment in fragments:
        if len(fragment) < 12:
            continue
        checked += 1
        assert fragment in real, (
            f"SKILL.md quotes {fragment!r}, which console.notice() no longer says. "
            "The skill teaches the agent to recognise this warning; update the quote."
        )
    assert checked >= 2, "the fragment split found almost nothing to check -- it is vacuous"


def test_the_skill_says_the_still_screen_is_not_a_finding():
    """The one claim in that section that must survive any rewording.

    Everything else there is advice. This is the instruction that stops a
    harness problem being filed as a defect in the lab -- which is the mistake
    the whole module exists because of.
    """
    doc = Path(__file__).resolve().parents[1] / "skills" / "lab-validator" / "SKILL.md"
    text = doc.read_text(encoding="utf-8")
    start = text.index("NOTHING YOU HAVE DONE")
    section = text[start : text.index("\n## ", start)].lower()
    assert "not a lab defect" in section
    assert "do not record a finding" in section
    assert "look at the most recent screenshot" in section
