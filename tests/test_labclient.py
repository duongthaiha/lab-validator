"""Tests for reading the instruction pane the way a learner does.

The first live run filed a *major* finding saying the pane would not scroll. It
was not true. Two independent mistakes pointed the same way -- towards inventing
a defect -- and that is the worst direction for this project to fail in, because
a false finding is indistinguishable from a real one to whoever receives it:

1. the offset was read from ``document.scrollingElement``, while the pane is a
   ``div`` with ``overflow-y: auto``, so it was pinned at 0 whatever happened;
2. the wheel was aimed by hovering the frame's ``body``, whose box on this
   product is a 101px strip *above* the pane, so the event went to the tab bar.

Neither could fail loudly. Both produced a confident, well-worded, wrong answer.
These tests pin the semantics that make the difference reportable.
"""

from __future__ import annotations

import ast
import asyncio
import builtins
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator.labclient import (  # noqa: E402
    CLOSED_MARKERS,
    MARKER_PROVENANCE,
    SCROLL_SLACK,
    LabClient,
    LabClosed,
    Scrolled,
    closed_reason,
    instance_id_of,
)


def scrolled(before=0, after=0, overflow=1000, where="div#pane", view_changed=False,
             delta=600):
    return Scrolled(before=before, after=after, overflow=overflow,
                    where=where, view_changed=view_changed, delta=delta)


# --- the four outcomes, which an int could only tell as two ----------------


def test_a_pane_that_will_not_move_is_the_defect():
    assert scrolled(before=0, after=0, overflow=21033).stuck


def test_a_pane_already_at_its_bottom_is_not_a_defect():
    """Observed live: `div#instructionsContent` at scrollTop 518 with 518px of
    total travel. The learner had read to the end, the wheel correctly did
    nothing, and it was filed as "a learner would be stuck". `overflow` is the
    pane's whole travel, so comparing against it accuses every fully-read
    section."""
    finished = scrolled(before=518, after=518, overflow=518)
    assert finished.scrollable
    assert finished.at_end
    assert not finished.stuck
    assert "stuck" not in finished.describe().lower()


def test_content_still_ahead_of_the_learner_is_what_stuck_measures():
    """Same pane, same total travel -- but stopped halfway. Here the wheel
    refusing to move really does strand the learner."""
    assert scrolled(before=259, after=259, overflow=518).stuck


def test_scrolling_up_measures_the_content_behind_the_learner():
    """A negative wheel at the top has nothing to reach; the same wheel from
    the bottom has the whole pane behind it."""
    assert not scrolled(before=0, after=0, overflow=518, delta=-600).stuck
    assert scrolled(before=518, after=518, overflow=518, delta=-600).stuck


def test_a_section_short_enough_to_fit_is_not_a_defect():
    """Nothing to scroll is not a broken scroll. Conflating them files a major
    finding against every short section in the lab."""
    short = scrolled(before=0, after=0, overflow=0)
    assert not short.stuck
    assert not short.scrollable


def test_a_pane_that_scrolls_is_not_a_defect():
    assert not scrolled(before=0, after=600, overflow=21033).stuck


def test_layout_rounding_does_not_count_as_content():
    """Sub-pixel rounding routinely overflows by a pixel or two on content that
    visibly fits, and that must not read as 'there is more to read'."""
    assert not scrolled(overflow=SCROLL_SLACK).scrollable
    assert scrolled(overflow=SCROLL_SLACK + 1).scrollable


# --- what counts as having moved -------------------------------------------


def test_a_changed_offset_counts_as_movement():
    assert scrolled(before=0, after=600).moved


def test_a_changed_view_counts_as_movement_even_with_no_offset():
    """If the pane shows something new, the learner scrolled -- whatever we
    failed to measure. Requiring the offset is how a scroller we picked wrongly
    turns into a defect report about the product."""
    assert scrolled(before=0, after=0, view_changed=True).moved


def test_an_unchanged_view_alone_does_not_mean_stuck():
    """Two screenfuls of the same long paragraph look identical at a sampled
    point; the offset settles it. Observed live at scrollTop 2304 -> 2904."""
    assert scrolled(before=2304, after=2904, view_changed=False).moved


def test_neither_signal_moving_is_what_stuck_means():
    assert scrolled(before=0, after=0, view_changed=False, overflow=9999).stuck


# --- the evidence a human reads --------------------------------------------


def test_the_defect_names_what_was_measured():
    """A wrong guess at the scroller has to be visible in the evidence rather
    than hidden inside a verdict -- that is what made the live one hard to spot."""
    note = scrolled(before=0, after=0, overflow=21033,
                    where="div#instructionsContent").describe()
    assert "div#instructionsContent" in note
    assert "21033" in note


def test_nothing_to_scroll_does_not_read_like_a_failure():
    note = scrolled(overflow=0).describe()
    assert "nothing to scroll" in note
    assert "stuck" not in note.lower()


def test_the_four_outcomes_do_not_read_the_same():
    notes = {
        scrolled(before=0, after=0, overflow=21033).describe(),
        scrolled(overflow=0).describe(),
        scrolled(before=0, after=600, overflow=21033).describe(),
        scrolled(before=518, after=518, overflow=518).describe(),
    }
    assert len(notes) == 4


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://labclient.labondemand.com/LabClient/"
         "d0e61878-f06a-4db7-b242-77d3c15cedbb", "d0e61878-f06a-4db7-b242-77d3c15cedbb"),
        # Launch opens this first, and it becomes the lab client on its own once
        # provisioning finishes. It carries the same instance id, but it is not
        # the client yet, and treating it as one reads an empty page.
        ("https://labclient.labondemand.com/Setup/"
         "d0e61878-f06a-4db7-b242-77d3c15cedbb", "?"),
        ("https://mslearningcampus.com/ClassEnrollment/5928204", "?"),
    ],
)
def test_only_a_lab_client_url_yields_an_instance_id(url, expected):
    assert instance_id_of(url) == expected


# --- the call site, which is where the false finding was actually filed ------
#
# `Scrolled` can distinguish "nothing to scroll" from "would not scroll" and
# still report the wrong thing, because the decision to file a finding is taken
# in `scripts/lab_step.py`, not here. Gating that decision on `.moved` rather
# than `.stuck` files a major defect against every section short enough to fit
# its pane -- which is exactly the shape of the live false positive.
#
# Asserted over the AST rather than the text: a substring search for "stuck"
# passes on a file that merely mentions it in a comment.

LAB_STEP = ROOT / "scripts" / "lab_step.py"


def _files_a_finding(node) -> bool:
    body = "\n".join(ast.unparse(child) for child in node.body)
    return "scrolled.describe()" in body and "verdict=" in body


def _finding_branches(tree) -> list[ast.If]:
    """The innermost `if` whose body files a scroll finding.

    Innermost matters: the verb dispatch is one long elif chain, so every
    ancestor's body contains the finding too, and testing an ancestor asserts
    `verb == "read"` -- which is true, unrelated, and passes forever.
    """
    matches = [n for n in ast.walk(tree) if isinstance(n, ast.If) and _files_a_finding(n)]
    return [
        node for node in matches
        if not any(other is not node and other in ast.walk(node) for other in matches)
    ]


def test_a_scroll_finding_is_filed_only_when_the_pane_is_stuck():
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    branches = _finding_branches(tree)

    assert branches, (
        "no branch in lab_step.py files a scroll finding -- either the guard's "
        "pattern has drifted or the learner scroll check has been removed"
    )
    for branch in branches:
        test = ast.unparse(branch.test)
        assert test == "scrolled.stuck", (
            f"a scroll finding is filed when `{test}`. A pane with nothing "
            "below the fold has not denied the learner anything; only "
            "`scrolled.stuck` means the scroll was refused."
        )


def test_a_pane_that_did_not_move_is_still_recorded():
    """The evidence is written either way.

    A section that simply fits must still record that it was read the learner's
    way -- otherwise the coverage table cannot tell "read and fine" from "never
    read", and principle 9 says the second must be as loud as a failure.
    """
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    branches = _finding_branches(tree)
    assert branches and branches[0].orelse, (
        "the non-finding path records nothing, so a short section looks unread"
    )
    otherwise = "\n".join(ast.unparse(child) for child in branches[0].orelse)
    assert "run.step(" in otherwise and "scrolled.describe()" in otherwise, otherwise
    assert "verdict=" not in otherwise, (
        "the else branch files a verdict too, so it is not a clean read"
    )


# --- the lab closed while we were walking it --------------------------------
#
# Observed live, and the most dangerous shape found so far: the lab ended, and
# every identity check still passed. The tab was open, titled correctly, on the
# right /LabClient/<guid> URL, listing the console and instructions frames. Only
# the *content* had changed to "Lab Closed". The walk carried on -- it filed a
# major "the instruction pane will not scroll" finding against a dead frame, and
# recorded three PASS steps for work done against nothing.
#
# Identity was never the problem. Liveness was, and nothing was asking.


class FakeFrame:
    def __init__(self, text, boom=False):
        self.text = text
        self.boom = boom

    async def inner_text(self, selector):
        if self.boom:
            raise RuntimeError("target closed")
        return self.text


class FakeClientPage:
    url = "https://labclient.labondemand.com/LabClient/" + "d" * 8 + "-f06a-4db7-b242-77d3c15cedbb"

    def __init__(self, text, boom=False):
        self.main_frame = FakeFrame(text, boom)


LIVE_PAGE = "Instructions\nResources\nAzure AI: Platform and Services\n95:12 remaining"
CLOSED_PAGE = "Lab Closed\nYour lab has been closed.\nClose Window"


@pytest.mark.asyncio
async def test_a_working_lab_client_is_not_reported_as_closed():
    assert await closed_reason(FakeClientPage(LIVE_PAGE)) is None


@pytest.mark.asyncio
async def test_the_closed_lab_page_observed_live_is_recognised():
    reason = await closed_reason(FakeClientPage(CLOSED_PAGE))
    assert reason and "Lab Closed" in reason


@pytest.mark.asyncio
async def test_an_unreadable_page_is_not_called_closed():
    """A page that cannot be read is a different failure with a different fix.

    Reporting it as "the lab closed" would end a run with a confident,
    specific, wrong explanation -- which is worse than the exception.
    """
    assert await closed_reason(FakeClientPage("", boom=True)) is None


@pytest.mark.asyncio
async def test_ensure_open_refuses_and_says_the_run_is_still_worth_something():
    lab = LabClient(FakeClientPage(CLOSED_PAGE))
    with pytest.raises(LabClosed) as caught:
        await lab.ensure_open()
    message = str(caught.value)
    assert "unknown, not correct" in message, message
    assert "Launch the lab again" in message, message


@pytest.mark.asyncio
async def test_ensure_open_says_nothing_when_the_lab_is_live():
    await LabClient(FakeClientPage(LIVE_PAGE)).ensure_open()


def test_the_documented_closed_lab_refusal_is_what_a_step_actually_prints():
    """A harness stops on this refusal's own words, so the two must not drift.

    `SKILL.md` quotes the refusal and tells the reader to stop on it. Wording
    that has moved on does not fail: the harness silently stops matching, and
    goes back to grinding out its stall ceiling against a lab that is not there.
    """
    skill = (Path(__file__).resolve().parents[1] / "SKILL.md").read_text(encoding="utf-8")
    quoted = re.search(r"^!! (The lab client says:[^.]*)\.", skill, re.M)
    assert quoted, "SKILL.md no longer quotes the closed-lab refusal at all"
    marker = quoted.group(1).split(":")[0]

    lab = LabClient(FakeClientPage(CLOSED_PAGE))
    try:
        asyncio.run(lab.ensure_open())
    except LabClosed as exc:
        message = str(exc)
    else:  # pragma: no cover - the refusal is asserted above
        raise AssertionError("ensure_open did not refuse a closed lab")
    assert marker in message and "Lab Closed" in message, (
        f"SKILL.md quotes a refusal the CLI no longer prints:\n"
        f"  documented: {quoted.group(1)!r}\n  actual:     {message!r}"
    )


# --- the liveness check has to run before anything is recorded ---------------
#
# `closed_reason` and `ensure_open` are tested above, but a check that is never
# called is a check that does not exist -- and mutating the call site to `pass`
# left every one of those tests green. This is the same miss as the scroll
# finding: the semantics were guarded, the decision to *use* them was not.


def _main_async(tree) -> ast.AsyncFunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "main_async":
            return node
    raise AssertionError("lab_step.main_async has gone; this guard is stale")


def _closed_handler(fn) -> ast.ExceptHandler:
    for node in ast.walk(fn):
        if isinstance(node, ast.ExceptHandler) and "LabClosed" in ast.unparse(node.type):
            return node
    raise AssertionError(
        "nothing in lab_step.main_async handles LabClosed, so a closed lab "
        "would surface as a traceback rather than a refusal"
    )


def _recording_calls(fn) -> list[ast.Call]:
    """Every call that writes to the run: `run.step(...)` and friends."""
    out = []
    for node in ast.walk(fn):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if node.func.attr in {"step", "finding", "end_segment"}:
            out.append(node)
    return out


def test_the_lab_is_checked_for_closure_before_the_step_runs():
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    fn = _main_async(tree)

    awaited = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "ensure_open"
    ]
    assert awaited, (
        "lab_step never asks whether the lab is still open. A closed lab keeps "
        "its tab, title, URL and frames, so every identity check passes and the "
        "walk records steps about a lab that is not there."
    )


def test_nothing_is_recorded_before_the_closure_check():
    """Order is the whole point.

    Calling `ensure_open` after the work would satisfy 'is it called?' while
    the trace already held steps taken against a dead lab. Only the refusal's
    own handler may record before the check has passed -- that record *is* the
    refusal.
    """
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    fn = _main_async(tree)
    handler = _closed_handler(fn)

    checks = [
        node.lineno for node in ast.walk(fn)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "ensure_open"
    ]
    assert checks, "no closure check to be before; see the guard above"
    check = min(checks)

    # The handler needs no exclusion: it is the `except` of the `try` that runs
    # the check, so every line in it is necessarily after `check`. Asserting
    # that here rather than filtering for it, because if the refusal ever moves
    # somewhere it could record first, this should fail rather than allow it.
    assert handler.lineno > check, (
        "the LabClosed handler no longer follows the check it handles"
    )

    early = [node.lineno for node in _recording_calls(fn) if node.lineno < check]
    assert early == [], (
        f"lab_step writes to the run at line(s) {early} before checking at line "
        f"{check} whether there is still a lab to write about"
    )


def test_the_closed_lab_refusal_records_the_blocker_and_stops():
    """A closed lab must leave a mark, and must not look like a passing step."""
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    handler = _closed_handler(_main_async(tree))
    body = ast.unparse(handler)

    assert 'verdict="BLOCKED"' in body or "verdict='BLOCKED'" in body, (
        "the refusal does not record a BLOCKED step, so a run that ended "
        "against a closed lab reads as though the walk simply stopped"
    )
    assert "return 4" in body, (
        "the refusal does not exit non-zero, so `auto` reads it as a step that "
        "worked and asks for the next one"
    )


def test_every_closure_marker_says_where_it_came_from():
    """The project's rule is not to invent; this makes the rule checkable.

    A guessed wording is not wrong to keep -- a miss costs a whole walk against
    a dead lab -- but it must be legible as a guess, or the next reader treats
    all three as things the product was seen to say.
    """

    assert set(CLOSED_MARKERS) == set(MARKER_PROVENANCE), (
        "a marker exists with no provenance; every wording has to declare "
        "whether it was observed or guessed"
    )
    for marker, why in MARKER_PROVENANCE.items():
        assert why.startswith(("observed", "unverified")), (
            f"{marker!r} declares {why!r}, which says nothing about whether "
            "anyone has seen the product say it"
        )


def test_at_least_one_marker_was_actually_observed():
    """Otherwise the whole check rests on guesswork and nobody would know."""

    observed = [m for m, why in MARKER_PROVENANCE.items() if why.startswith("observed")]
    assert observed, (
        "every closure marker is a guess. This check would then be a heuristic "
        "presented as a fact -- the exact failure it was written to stop."
    )
    assert CLOSED_MARKERS[0] in observed, (
        "the first wording tried is a guess; the observed ones should be tried "
        "first so the reason a walk stopped is the strongest one available"
    )


# --- a lab that closes *during* a long wait ---------------------------------
#
# The step-boundary check above catches a lab that was already closed. It does
# nothing for one that ends mid-step, and the probes are where that costs
# most: `until:connected` polls for its whole budget and then files
# `LAB007 ... did not complete within Ns` -- a **major** finding about a lab
# that had already gone. Observed live in the mirror image (a false LAB003
# about a dead instruction pane).


def test_every_name_lab_step_uses_is_actually_imported():
    """A guard that runs only when a lab closes is a guard nobody runs.

    `_refuse_if_closed` called `closed_reason` before it was imported. Every
    test passed, because reaching that line needs a lab that closes mid-step --
    so the first thing the new code would ever have done in anger was raise
    NameError, on the one path where a clear message matters most.
    """
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    imported = {"__name__", "__file__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom | ast.Import):
            imported |= {(a.asname or a.name).split(".")[0] for a in node.names}
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            imported.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            imported.add(node.id)
        elif isinstance(node, ast.arg):
            imported.add(node.arg)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            imported.add(node.name)

    used = {
        node.id for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
    }
    unresolved = sorted(used - imported - set(dir(builtins)))
    assert unresolved == [], f"used but never bound in lab_step: {unresolved}"


def _probe_functions(tree) -> list[ast.AsyncFunctionDef]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("probe_")
    ]


def test_every_probe_checks_for_closure_while_it_waits():
    """One probe checking is not enough -- the next one added must too."""
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    probes = _probe_functions(tree)
    assert probes, "no probes found; this guard is stale"

    missing = [
        fn.name for fn in probes
        if "_refuse_if_closed" not in ast.unparse(fn)
    ]
    assert missing == [], (
        f"{missing} poll without ever asking whether the lab is still there. "
        "A probe that outlives its lab spends its whole budget and then files "
        "LAB007 against it."
    )


def test_the_closure_check_is_not_run_on_every_iteration():
    """Cheap enough to be worth doing, expensive enough not to do blindly.

    Bounded at one heartbeat interval. Asserting the shape rather than the cost
    because the cost is not measurable from here -- but a check moved into the
    tight loop would read the page every two seconds for the length of a
    multi-minute wait, which is the sort of thing that gets it deleted later.
    """
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    for fn in _probe_functions(tree):
        beats = [
            node for node in ast.walk(fn)
            if isinstance(node, ast.If) and "beat = now" in ast.unparse(node)
        ]
        assert beats, f"{fn.name} has no heartbeat branch to hang the check on"
        assert any("_refuse_if_closed" in ast.unparse(b) for b in beats), (
            f"{fn.name} checks for closure outside its heartbeat branch, so it "
            "reads the page on every poll"
        )


def test_a_lab_that_closes_mid_step_is_recorded_as_blocked_not_as_a_defect():
    tree = ast.parse(LAB_STEP.read_text(encoding="utf-8"))
    fn = _main_async(tree)

    handlers = [
        node for node in ast.walk(fn)
        if isinstance(node, ast.ExceptHandler)
        and node.type is not None
        and "LabClosed" in ast.unparse(node.type)
    ]
    assert len(handlers) >= 2, (
        "only the step-boundary closure is handled. A lab that ends during "
        "run_actions would surface as a traceback, which reads as a tool crash"
    )
    for handler in handlers:
        body = ast.unparse(handler)
        assert "BLOCKED" in body, (
            "a closure handler records something other than BLOCKED; a lab "
            "that ended is not a defect in the lab"
        )
        assert "return 4" in body, (
            "a closure handler exits 0, so the caller reads it as a step that "
            "worked and asks for the next one"
        )


# --- literals handed to run.step have to be real ----------------------------
#
# `severity="blocker"` sat in the closed-lab handler through a full test suite,
# a mutation sweep and a commit. It is not a severity -- the taxonomy has four,
# and BLOCKED has none at all, because blocked is a *status*, not a finding.
# Nothing caught it because reaching that line needs a lab that has closed, so
# the first thing the refusal did in anger was raise ValueError from inside
# runlog: a correct detection, published as a tool crash.
#
# Same shape as the missing import above, one layer along: these are error
# paths, and error paths are the least-executed code carrying the most
# load-bearing prose in the system.

SOURCES = sorted(
    p for p in [*(ROOT / "src" / "lab_validator").rglob("*.py"),
                *(ROOT / "scripts").rglob("*.py")]
)


def _keyword_literals(path: Path, keyword: str) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        for kw in node.keywords:
            if kw.arg == keyword and isinstance(kw.value, ast.Constant):
                if isinstance(kw.value.value, str):
                    out.append((kw.value.lineno, kw.value.value))
    return out


def test_every_severity_literal_is_a_real_severity():
    from lab_validator import runlog

    bad = [
        f"{path.name}:{line} severity={value!r}"
        for path in SOURCES
        for line, value in _keyword_literals(path, "severity")
        if value not in runlog.SEVERITIES
    ]
    assert bad == [], (
        f"{bad} -- runlog.step raises on an unknown severity, so this only "
        f"shows up on the path that uses it. Known: {runlog.SEVERITIES}"
    )


def test_every_verdict_literal_is_a_real_verdict():
    from lab_validator import runlog

    bad = [
        f"{path.name}:{line} verdict={value!r}"
        for path in SOURCES
        for line, value in _keyword_literals(path, "verdict")
        if value not in runlog.VERDICTS
    ]
    assert bad == [], f"{bad} -- known verdicts: {sorted(runlog.VERDICTS)}"


def test_blocked_is_recorded_without_a_severity():
    """Blocked is a status, not a finding (approach.md 2.11).

    Giving it a severity would rank it among the defects, which is exactly
    backwards: a blocked lab is the most important thing a run can find, and it
    belongs in the Blockers section rather than sorted in with the majors.
    """
    from lab_validator import taxonomy

    assert taxonomy.default_severity("BLOCKED") is None, (
        "BLOCKED has acquired a default severity; the report's blockers "
        "section and its findings list would now disagree about what it is"
    )

    for path in SOURCES:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            kws = {kw.arg: kw.value for kw in node.keywords}
            verdict = kws.get("verdict")
            if not isinstance(verdict, ast.Constant) or verdict.value != "BLOCKED":
                continue
            assert "severity" not in kws, (
                f"{path.name}:{node.lineno} records BLOCKED with a severity"
            )
