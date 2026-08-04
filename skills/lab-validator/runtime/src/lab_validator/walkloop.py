"""The walk loop: what should happen next, decided from the run folder alone.

This module deliberately does **not** drive a browser and does **not** judge
anything. Both of those need a live lab and an agent's reading of what is on
screen. What can be packaged, and what is packaged here, is the *control flow*
that a hand-driven walk gets wrong:

- which section comes next, and whether it was really finished;
- whether every numbered task in it actually got a verdict;
- when a blocked section should keep reading rather than stop;
- when the lab clock leaves too little time to write the reports;
- what must be on disk before the loop is allowed to advance.

Every decision is a pure function of state already persisted in the run folder.
That is not stylistic. A multi-hour unattended walk *will* be interrupted, and a
loop whose position lives in a Python variable cannot survive that. Because
``next_move`` reads only the folder, resuming a killed run is the same call as
continuing a live one, and the tests can drive years of walk in milliseconds
with no browser anywhere.

The unit of progress is the **numbered task**, not the section. A section is a
heading; a task is a thing the instructions told a learner to do. The failure
mode of the reference walk was a task quietly skipped inside a section that then
reported clean, and only task-level bookkeeping can see that.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .asks import Ask, asks_in
from .corpus import Outline
from .report import _last_seq, segment_filename
from .runlog import FINDING_VERDICTS, NOT_SELECTED, Run, Segment

__all__ = [
    "Move",
    "credential_asks",
    "coverage_kind",
    "RESERVE_MINUTES",
    "next_move",
    "task_coverage",
    "unjudged_tasks",
]

# Minutes of lab clock kept back for writing reports and sealing the run.
#
# A walk that spends its last minute walking has nothing to show for any of it:
# per-section reports are written as it goes, but the roll-up, the coverage
# tables and the seal are not. Stopping early with a complete deliverable beats
# stopping late with a folder somebody has to reconstruct by hand.
RESERVE_MINUTES = 20

# What a section-level move is asking the caller to do.
#
# `perform` and `assess` are the same reading of the same text with different
# powers available: `assess` is what remains once the environment has refused,
# and it exists because a blocked section still has judgeable claims in it.
ACTIONS = (
    "open",      # start_segment: mark the section in progress
    "read",      # read the section, including through the learner's own scroll
    "perform",   # do the numbered tasks and record a verdict for each
    "assess",    # blocked: judge the remaining tasks from the text alone
    "report",    # write the section report before advancing
    "advance",   # end_segment and move on
    "stop",      # nothing further should be attempted
)


@dataclass
class Move:
    """One instruction to the caller, with the reason it was chosen.

    ``why`` is not decoration. When a walk stops, the single most useful thing
    in the folder is the sentence explaining what the loop believed at the time,
    because the alternative is inferring it from an absence.
    """

    action: str
    segment_id: str | None = None
    why: str = ""
    tasks: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in ACTIONS:
            raise ValueError(f"unknown move: {self.action!r}")

    @property
    def is_terminal(self) -> bool:
        return self.action == "stop"

    def __str__(self) -> str:
        where = f" {self.segment_id}" if self.segment_id else ""
        return f"{self.action}{where}: {self.why}"


def _steps_for(run: Run, segment_id: str) -> list[dict]:
    retracted = run.retracted()
    return [
        s for s in run.steps()
        if s.get("segment") == segment_id and s.get("seq") not in retracted
    ]


def coverage_kind(segment: Segment, outline: Outline | None) -> str:
    """Can this section's tasks be enumerated at all, and if not, why not?

    Three answers that a bare ``(judged, unjudged)`` pair collapses into one:

    - ``enumerated`` — the section has numbered tasks and we know them;
    - ``no-tasks``   — the section genuinely has none (an overview, a summary);
    - ``unresolved`` — the anchor does not resolve, or there is no corpus.

    Collapsing them is the failure the corpus parser already warns about: an
    unresolvable anchor yields an empty task list, which looks like "nothing to
    check" rather than "could not check". A section that completes with zero
    tasks because we could not find it must never read the same as a section
    that completes with zero tasks because it has none.
    """
    if outline is None:
        return "unresolved"
    if not segment.anchor:
        return "unresolved"
    section = outline.section_by_anchor(segment.anchor)
    if section is None:
        return "unresolved"
    return "enumerated" if outline.tasks(section) else "no-tasks"


def task_coverage(
    run: Run, segment: Segment, outline: Outline | None
) -> tuple[list[str], list[str]]:
    """Return ``(judged, unjudged)`` task references for one section.

    A task counts as judged when some step names it in ``instructionRef``.
    Matching is on the reference the corpus assigns, not on prose, because
    prose is what an agent writes and would therefore be marking its own
    homework.
    """
    if coverage_kind(segment, outline) != "enumerated":
        return [], []
    section = outline.section_by_anchor(segment.anchor)
    refs = [t.id for t in outline.tasks(section) if t.id]

    seen: set[str] = set()
    for step in _steps_for(run, segment.id):
        # The trace writes camelCase; accept the snake_case spelling too, because
        # run folders are evidence and outlive the code that wrote them.
        ref = (step.get("instructionRef") or step.get("instruction_ref") or "").lstrip("#")
        if ref in refs:
            seen.add(ref)
    return [r for r in refs if r in seen], [r for r in refs if r not in seen]


def unjudged_tasks(run: Run, segment: Segment, outline: Outline | None) -> list[str]:
    return task_coverage(run, segment, outline)[1]


def _refs_used(run: Run, segment_id: str) -> set[str]:
    return {
        (s.get("instructionRef") or s.get("instruction_ref") or "").lstrip("#")
        for s in _steps_for(run, segment_id)
    } - {""}


def _mis_scoped(run: Run, segment: Segment, outline: Outline | None) -> bool:
    """Is work being recorded against the *section* instead of its tasks?

    This is the livelock: the loop asks for a task, the caller does it and
    references the section it was in, the task stays unjudged, and the loop asks
    again — forever, with no error. It is not hypothetical. The reference walk
    recorded 394 references and every one of them named a section, because the
    convention it was written under had no task level.

    The loop cannot accept a section reference as coverage — that would restore
    the exact hole it exists to close, since one reference would vouch for every
    task under it. So it must instead say plainly what is wrong.
    """
    if outline is None or not segment.anchor:
        return False
    return segment.anchor.lstrip("#") in _refs_used(run, segment.id)


def _task_bodies(segment: Segment, outline: Outline | None) -> dict[str, str]:
    if coverage_kind(segment, outline) != "enumerated":
        return {}
    section = outline.section_by_anchor(segment.anchor)
    return {t.id: (t.text + "\n" + t.body) for t in outline.tasks(section) if t.id}


def credential_asks(
    segment: Segment,
    outline: Outline | None,
    labels: dict[str, str] | None,
    refs: list[str] | None = None,
) -> dict[str, list[Ask]]:
    """Which lab-issued values each task is asking for.

    Operating a walk by hand, a human notices "sign in with the username from
    the Resources tab" and goes and fetches it. An autonomous walk has to be
    told, and the only place that can say so is the move that asks for the task.

    Only labels cross this boundary, never values: resolution runs over
    :meth:`Vault.label_index`, so nothing here can leak a secret even if the
    move is printed to a console or written to the manifest.
    """
    bodies = _task_bodies(segment, outline)
    wanted = refs if refs is not None else list(bodies)
    found = {}
    for ref in wanted:
        if (body := bodies.get(ref)) and (a := asks_in(body, labels)):
            found[ref] = a
    return found


def _has_read(run: Run, segment_id: str) -> bool:
    """Did this section get read through the learner's own scroll?

    Paging the instructions by API is faster and exact, and blind to a pane the
    learner cannot scroll. One real scroll per section is the whole cost of not
    being blind to it.
    """
    return any(
        (s.get("action") or "").startswith("read")
        or s.get("capability") == "scroll_instructions"
        for s in _steps_for(run, segment_id)
    )


def _is_blocked(run: Run, segment_id: str) -> bool:
    return any(s.get("verdict") == "BLOCKED" for s in _steps_for(run, segment_id))


def _report_written(run: Run, segment: Segment) -> bool:
    """Is there a section report that reflects what the run currently knows?

    Two claims, not one. The file must exist *and* have been written from at
    least as far through the trace as the last step recorded for this section.
    Existence alone was the original test, and it accepts a report written
    before the last three findings -- which is exactly the report that reads
    clean while the evidence beside it does not.
    """
    if not (run.dir / segment_filename(segment.id)).exists():
        return False
    through = segment.reported_through
    if through is None:
        # Written by an older version that did not record this. Run folders are
        # evidence and outlive the code, so trust the file rather than demand a
        # rewrite of a sealed run.
        return True
    return through >= _last_seq(run, segment.id)


def next_move(
    run: Run,
    outline: Outline | None = None,
    *,
    minutes_remaining: int | None = None,
    reserve: int = RESERVE_MINUTES,
    labels: dict[str, str] | None = None,
) -> Move:
    """Decide the next move from persisted state alone.

    Called with no arguments beyond the run, this is also the resume path: a
    killed walk continues by asking the same question again.

    ``labels`` is the vault's label index — labels only, never values — so the
    move can name the credentials the next tasks are asking for.
    """
    # The clock comes first, and it is checked before anything else because
    # every other move costs lab time. A stop decided halfway through a section
    # would leave that section unreported, which is the one outcome worse than
    # stopping early.
    if minutes_remaining is not None and minutes_remaining <= reserve:
        return Move(
            "stop",
            why=(
                f"{minutes_remaining} min left on the lab clock, at or under the "
                f"{reserve} min reserved for writing up. Sections already walked "
                "keep their reports; the rest are unknown, not correct."
            ),
            detail={"reason": "clock", "minutesRemaining": minutes_remaining},
        )

    segments = run.segments()
    current = next((s for s in segments if s.status == "in_progress"), None)

    if current is None:
        nxt = next((s for s in segments if s.status == "pending"), None)
        if nxt is None:
            # The run is over, and this sentence is the last thing anyone reads.
            # A section can reach 'done' under an older convention, or by a
            # caller that closed it early; either way the tasks under it have no
            # recorded verdict, and saying "complete" without saying that would
            # be the exact misreading this module exists to prevent.
            gaps = {
                s.id: unjudged
                for s in segments
                if s.status != NOT_SELECTED and (unjudged := task_coverage(run, s, outline)[1])
            }
            selected = [s for s in segments if s.status != NOT_SELECTED]
            excluded = [s for s in segments if s.status == NOT_SELECTED]
            if excluded:
                why = (
                    f"all {len(selected)} selected section(s) have been walked or "
                    "accounted for"
                )
            else:
                why = f"all {len(segments)} sections have been walked or accounted for"
            # Order matters more than it looks. "N task(s) across M of them" has
            # to sit next to the sections it is talking about -- put the
            # not-selected clause in between and "them" silently comes to mean
            # the sections nobody walked, which is the opposite of the truth.
            if gaps:
                total = sum(len(v) for v in gaps.values())
                why += (
                    f", but {total} task(s) across {len(gaps)} of the sections that were "
                    "walked have no recorded verdict. Those tasks are unknown, not correct."
                )
            if excluded:
                why += (
                    f"{'' if gaps else '.'} Separately, {len(excluded)} of {len(segments)} "
                    "sections were not selected for this run: never attempted, and "
                    "unknown rather than correct."
                )
            return Move(
                "stop",
                why=why,
                detail={
                    "reason": "complete",
                    "unjudgedTasks": gaps,
                    "notSelected": [s.id for s in excluded],
                },
            )
        return Move("open", nxt.id, why=f"next unwalked section: {nxt.title}")

    if not _has_read(run, current.id):
        return Move(
            "read",
            current.id,
            why=(
                "the section has not been read through the learner's own scroll, "
                "so a pane the learner cannot move would go unnoticed"
            ),
        )

    judged, unjudged = task_coverage(run, current, outline)
    if unjudged:
        blocked = _is_blocked(run, current.id)
        if blocked:
            why = (
                f"{len(unjudged)} task(s) still have no verdict, and the section "
                "is blocked — judge what the text alone can settle rather than "
                "ending on the blocker"
            )
        else:
            why = f"{len(unjudged)} of {len(judged) + len(unjudged)} task(s) have no verdict yet"
        if _mis_scoped(run, current, outline):
            why += (
                f". NOTE: steps here reference the section (#{current.anchor}) rather "
                "than a task. A section reference cannot count as coverage — one would "
                "vouch for every task under it — so pass --ref with the task's own "
                "anchor, listed below, or this will keep asking."
            )
        found = credential_asks(current, outline, labels, unjudged)
        missing = sorted({a.term for asked in found.values() for a in asked if not a.satisfied})
        if missing:
            why += (
                f". These task(s) ask for {', '.join(missing)}, which this lab did not "
                "issue — that is a finding about the setup, not a reason to stop."
            )
        return Move(
            "assess" if blocked else "perform",
            current.id,
            why=why,
            tasks=unjudged,
            detail={
                "judged": judged,
                "blocked": blocked,
                "misScopedRefs": _mis_scoped(run, current, outline),
                # Labels and vault references only. No value ever reaches a Move,
                # so printing one or writing it to the manifest cannot leak.
                "asks": {ref: [str(a) for a in asked] for ref, asked in found.items()},
                "unsatisfiedAsks": missing,
            },
        )

    if not _report_written(run, current):
        kind = coverage_kind(current, outline)
        why = (
            "every task has a verdict; write the section report before advancing "
            "so an interrupted run still delivers this section"
        )
        if kind == "no-tasks":
            why = "the section has no numbered tasks; report what was observed in it"
        elif kind == "unresolved":
            why = (
                "this section's tasks COULD NOT BE ENUMERATED — the anchor does not "
                "resolve against the corpus, so nothing here says the section is "
                "complete, only that we could not tell. Say so in the report."
            )
        return Move(
            "report",
            current.id,
            why=why,
            detail={"tasks": len(judged), "taskCoverage": kind},
        )

    return Move(
        "advance",
        current.id,
        why="section reported and complete",
        detail={"blocked": _is_blocked(run, current.id),
                "taskCoverage": coverage_kind(current, outline)},
    )


def describe(run: Run, outline: Outline | None = None) -> str:
    """A one-screen answer to 'where is this walk?', for the console."""
    segments = run.segments()
    selected = [s for s in segments if s.status != NOT_SELECTED]
    excluded = len(segments) - len(selected)
    done = sum(1 for s in selected if s.status in ("done", "blocked", "skipped"))
    head = f"{done}/{len(selected)} sections accounted for"
    if excluded:
        # Never folded into the numerator or the denominator. A scoped walk that
        # reported "23/23" would be claiming exactly the thing it did not do.
        head += f" ({excluded} not selected, still unknown)"
    lines = [head]
    for seg in segments:
        if seg.status in ("pending", NOT_SELECTED):
            continue
        _, unjudged = task_coverage(run, seg, outline)
        note = ""
        if unjudged:
            note = f", {len(unjudged)} task(s) unjudged"
        elif coverage_kind(seg, outline) == "unresolved":
            note = ", TASKS NOT ENUMERABLE"
        lines.append(f"  {seg.id} {seg.status}{note}")
    return "\n".join(lines)


def findings_since(run: Run, segment_id: str) -> int:
    return sum(
        1 for s in _steps_for(run, segment_id) if s.get("verdict") in FINDING_VERDICTS
    )
