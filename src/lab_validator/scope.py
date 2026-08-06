"""Choosing what to walk -- and making the report say what it did not check.

Walking every section costs hours. Somebody who has just edited section 4 wants
to check section 4, and that is a reasonable thing to want.

It is also the most dangerous convenience in this tool, because the obvious
implementation produces a report that reads exactly like a full one. A run that
walked three of twenty-three sections and opens with *"Can a learner complete
this lab? YES"* is a confident answer about twenty sections nobody looked at --
manufactured by a feature added to save time.

So selection is only half of what lives here. The other half is that an excluded
section gets a status of its own, ``not_selected``, which the loop refuses to
walk and the report counts and names *separately*.

``skipped`` was the obvious word for that and it was already taken:
``lab_step.py --end-segment skipped`` means *the walker passed over this
mid-walk*. That is a different fact, with a different cause and a different
reader reaction, and collapsing the two would lose the only useful difference
between them. Two facts, two words.

Orientation
-----------
Role:     review the lab, choose which sections to walk, and record what was left out.
Entry:    `review`, `parse`, `apply`, `Selection`
Talks to: corpus, runlog, vault, walkloop
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

from .corpus import Outline
from .runlog import NOT_SELECTED, Run, iso
from .walkloop import coverage_kind

#: Re-exported. The status word itself lives in :mod:`lab_validator.runlog`,
#: beside the other segment statuses, so the walk loop can honour it without
#: importing this module back.
__all_status__ = ("NOT_SELECTED",)

#: What that status means, written into the segment so a run folder read years
#: later explains itself without this module.
NOT_SELECTED_NOTE = "not selected for this run; never attempted"

#: Statuses that carry evidence. Re-scoping may widen a run, but it may not
#: erase what a previous pass actually observed.
FROZEN = ("done", "blocked", "in_progress")

#: Ranges between *ids* use ``..`` because section ids contain hyphens
#: ("s04-deploy-model"), so ``s04-s06`` is indistinguishable from an id prefix.
#: Between bare numbers a hyphen is unambiguous, so ``4-6`` is a range too.
RANGE = ".."

#: Said whenever a selection cannot be resolved. One sentence, one place: an
#: error that tells you what is wrong without telling you what to type instead
#: is half an error, and three copies of it drift.
HOW_TO_CHOOSE = (
    "use 'all', or the numbers in the review's # column: '4', '1,4,7', '4-6'. "
    "Ids work too ('s04', 's04..s06')."
)

#: The ``--sections`` flag's help text, in one place because it had already
#: drifted into three: every ``--help`` still offered ids only, which is the one
#: form nobody can type before a lab has been captured. Numbers lead for the
#: same reason they lead in the prompt.
SECTIONS_HELP = "which sections to walk: all | 4 | 1,4,7 | 4-6 | s04 | s04..s06"

REVIEW_FILENAME = "review.md"


class ScopeError(Exception):
    """A selection that could not be resolved. Always refuse, never guess."""


@dataclass(frozen=True)
class Selection:
    """What was chosen, by whom, and in what words.

    ``how`` matters as much as ``chosen``. ``prompt`` means a human looked at
    the review and decided; ``default`` means nobody was asked and everything
    was walked. A manifest that cannot tell those apart will eventually be read
    as though a human approved a scope they never saw.
    """

    chosen: tuple[str, ...]
    excluded: tuple[str, ...]
    expression: str
    how: str
    at: str

    @property
    def is_everything(self) -> bool:
        return not self.excluded

    def to_dict(self) -> dict:
        return {
            "chosen": list(self.chosen),
            "excluded": list(self.excluded),
            "expression": self.expression,
            "how": self.how,
            "at": self.at,
        }


@dataclass(frozen=True)
class Applied:
    """What changed on disk, including what the run refused to change."""

    selection: Selection
    excluded: tuple[str, ...]
    reopened: tuple[str, ...]
    refused: tuple[tuple[str, str], ...]
    not_selected_now: tuple[str, ...] = ()

    def summary(self) -> str:
        """Describe the resulting state, not the requested one.

        Those differ whenever a section was already walked: asking to exclude it
        does not un-walk it. Reporting the request would say "4 not selected"
        when three of the four are sitting there marked ``done`` with reports
        beside them -- a count that neither adds up nor matches the folder.
        """
        sel = self.selection
        total = len(sel.chosen) + len(sel.excluded)
        parts = [f"scope: {len(sel.chosen)} of {total} sections selected"]
        if self.not_selected_now:
            parts.append(f"{len(self.not_selected_now)} not selected")
        if self.reopened:
            parts.append(f"{len(self.reopened)} reopened")
        if self.refused:
            walked = ", ".join(f"{i} ({s})" for i, s in self.refused)
            parts.append(f"{len(self.refused)} kept as already walked: {walked}")
        return "; ".join(parts)


# ---- parsing -------------------------------------------------------------


def everything(run: Run, *, how: str = "default", expression: str = "all") -> Selection:
    return Selection(
        chosen=tuple(s.id for s in run.segments()),
        excluded=(),
        expression=expression,
        how=how,
        at=iso(),
    )


def parse(expression: str, run: Run, *, how: str = "flag") -> Selection:
    """Resolve a selection expression against this run's sections, or refuse.

    Accepts ``all``, the numbers the review prints (``4``, ``1,4,7``, ``4-6``),
    ids, unambiguous id prefixes, and ranges between ids written ``s04..s06``.
    Anything else raises, naming the candidates.

    Refusing is the whole point. A mistyped id that quietly selects nothing
    would produce an empty walk and a clean-looking report -- the same failure
    shape as every other defect this project has paid for.
    """
    ids = [s.id for s in run.segments()]
    if not ids:
        raise ScopeError("this run has no sections, so there is nothing to select")

    text = (expression or "").strip()
    if not text:
        raise ScopeError(HOW_TO_CHOOSE)
    if text.lower() in ("all", "*"):
        return everything(run, how=how, expression=text)

    wanted: set[str] = set()
    for token in _tokens(text):
        wanted.update(_resolve(token, run, ids))
    if not wanted:
        raise ScopeError(f"{text!r} selected no sections. {HOW_TO_CHOOSE}")

    return Selection(
        chosen=tuple(i for i in ids if i in wanted),
        excluded=tuple(i for i in ids if i not in wanted),
        expression=text,
        how=how,
        at=iso(),
    )


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[,\s]+", text) if t]


def _resolve(token: str, run: Run, ids: list[str]) -> list[str]:
    lo, hi = _split_range(token)
    if lo is not None:
        if not lo or not hi:
            raise ScopeError(
                f"range {token!r} is missing an end; write it as '4-6' or 's04..s06'"
            )
        first, last = _one(lo, run), _one(hi, run)
        i, j = ids.index(first), ids.index(last)
        if i > j:
            raise ScopeError(
                f"range {token!r} runs backwards: {first} comes after {last} in the lab. "
                "Ranges are written low to high."
            )
        return ids[i : j + 1]
    return [_one(token, run)]


def _split_range(token: str) -> tuple[str | None, str | None]:
    """Split a range token, or return ``(None, None)`` if it is not one.

    ``..`` always means a range. A single ``-`` means one too, but *only*
    between bare numbers: section ids contain hyphens, so `s01-s03` is
    indistinguishable from an id and must stay an id. Numbers have no such
    ambiguity, and `1-3` is what a person types when they are reading a
    numbered list -- which, at the prompt, is exactly what they are doing.
    """
    if RANGE in token:
        lo, _, hi = token.partition(RANGE)
        return lo, hi
    match = re.fullmatch(r"(\d+)-(\d+)", token)
    if match:
        return match.group(1), match.group(2)
    return None, None


def _one(token: str, run: Run) -> str:
    try:
        return run.resolve_segment(_as_id(token))
    except KeyError as exc:
        # ``exc.args[0]``, not ``str(exc)``: KeyError reprs its argument, so
        # str() wraps an already-quoted message in a second set of quotes.
        raise ScopeError(f"{exc.args[0]}{_range_hint(token, run)}") from exc


def _as_id(token: str) -> str:
    """Turn a bare number into the id prefix it names: ``4`` -> ``s04``.

    The review prints these numbers, so they are the only handle a person has
    at the prompt: section ids cannot be known until the lab has been launched
    and its instructions segmented, which is minutes after the command was
    typed. Refusing the number the tool just printed is the tool's fault.
    """
    return f"s{int(token):02d}" if token.isdigit() else token


def _range_hint(token: str, run: Run) -> str:
    """Suggest ``a..b`` when someone reasonably wrote ``a-b`` with ids.

    Section ids contain hyphens, so a hyphen between *ids* cannot mean "range".
    That is a defensible choice and an unguessable one, so the error explains it
    at the moment it bites rather than in documentation nobody is reading yet.
    (Between bare numbers a hyphen *is* a range -- see ``_split_range`` -- so
    this only ever fires for the ambiguous case.)
    """
    for i, ch in enumerate(token):
        if ch != "-" or i == 0 or i == len(token) - 1:
            continue
        lo, hi = token[:i], token[i + 1 :]
        try:
            run.resolve_segment(_as_id(lo))
            run.resolve_segment(_as_id(hi))
        except KeyError:
            continue
        return (
            f". Section ids contain hyphens, so ranges between ids use '..' -- "
            f"did you mean '{lo}{RANGE}{hi}'?"
        )
    return ""


# ---- the review ----------------------------------------------------------


def review(run: Run, outline: Outline | None = None, vault=None) -> str:
    """Everything a human needs to decide what is worth walking.

    Deliberately excludes credential *values*. This is a text artefact a
    reviewer may well paste into a bug or a chat, and the redactor only masks
    what it is told about -- so the safe design is for the values never to be
    written here at all, not for them to be masked afterwards.
    """
    lines: list[str] = []
    add = lines.append
    manifest = run.manifest

    add(f"# Review before walking — {manifest.get('target') or run.dir.name}")
    add("")
    add(f"- run: `{run.dir.name}`")
    if manifest.get("labMinutesAtStart") is not None:
        add(f"- lab clock: {manifest['labMinutesAtStart']} min remaining")
    if manifest.get("instance"):
        add(f"- instance: `{manifest['instance']}`")
    add("")

    _add_preflight(add, manifest)
    _add_anomalies(add, manifest)
    _add_credentials(add, run, vault)
    _add_sections(add, run, outline)
    _add_how_to_choose(add)

    return "\n".join(lines).rstrip() + "\n"


def _add_preflight(add, manifest: dict) -> None:
    checks = manifest.get("preflight") or {}
    if not checks:
        return
    failures = checks.get("failures") or []
    add("## Setup preflight")
    add("")
    if failures:
        add(f"**{len(failures)} setup defect(s) before section 1.**")
        add("")
        for f in failures:
            add(f"- `{f.get('verdict', '?')}` {f.get('name', '?')} — "
                f"{(f.get('detail') or '').splitlines()[0] if f.get('detail') else ''}")
    else:
        add(f"{checks.get('checks', 0)} check(s), clean.")
    unchecked = checks.get("unchecked") or []
    if unchecked:
        add("")
        add(f"It could not check {len(unchecked)} thing(s); a clean preflight means "
            "*the things we knew to check* passed.")
    add("")


def _add_anomalies(add, manifest: dict) -> None:
    anomalies = manifest.get("structuralAnomalies") or []
    if not anomalies:
        return
    add(f"## Structural anomalies ({len(anomalies)})")
    add("")
    for a in anomalies:
        add(f"- `{a.get('code', '?')}` ({a.get('severity', '?')}) {a.get('message', '')}")
    add("")


def _add_credentials(add, run: Run, vault) -> None:
    if vault is None:
        vault = _load_vault(run)
    add("## Credentials captured")
    add("")
    if not vault or not len(vault):
        add("None. Reuse falls back to the live Resources tab.")
        add("")
        return
    add(f"{len(vault)} captured. **Values are held in the run folder and are never "
        "written here.**")
    add("")
    add("| Scope | Label | Shape |")
    add("| --- | --- | --- |")
    for row in vault.redacted_rows():
        add(f"| {row['scope']} | {row['label']} | {row['shape']} |")
    add("")


def _load_vault(run: Run):
    try:
        from .vault import Vault

        return Vault.load(run.dir)
    except Exception:  # noqa: BLE001 - a missing vault must not block a review
        return None


def _add_sections(add, run: Run, outline: Outline | None) -> None:
    segments = run.segments()
    add(f"## Sections ({len(segments)})")
    add("")
    if outline is None:
        add("> No instruction outline available, so task counts are unknown.")
        add("")
    add("| # | id | Section | Tasks | Status |")
    add("| --- | --- | --- | --- | --- |")
    for seg in segments:
        # The number shown is the one *inside the id*, not the row's position.
        # They differ -- ids start at s00, rows at 1 -- and a review that showed
        # row 5 beside `s04-deploy-models` taught the reader to type `s05`,
        # which selects a different section and says nothing about it. A wrong
        # answer, not a refusal. One number, meaning one thing.
        add(f"| {_number(seg.id)} | `{seg.id}` | {seg.title[:60]} "
            f"| {_task_count(seg, outline)} | {(seg.status or 'pending').replace('_', ' ')} |")
    add("")


def _number(segment_id: str) -> str:
    """The digits a section id leads with: ``s04-deploy-models`` -> ``4``."""
    match = re.match(r"s(\d+)", segment_id)
    return str(int(match.group(1))) if match else "-"


def _task_count(segment, outline: Outline | None) -> str:
    kind = coverage_kind(segment, outline)
    if kind == "unresolved":
        return "?"
    if kind == "no-tasks":
        return "-"
    section = outline.section_by_anchor(segment.anchor)
    return str(len(outline.tasks(section)))


def _add_how_to_choose(add) -> None:
    add("## Choosing")
    add("")
    add("Type the numbers in the **#** column above:")
    add("")
    add("- `all` — walk everything.")
    add("- `4` — one section.")
    add("- `1,4,7` — several.")
    add("- `4-6` — an inclusive range.")
    add("")
    add("Ids work too (`s04`, or any unambiguous prefix). Ranges *between ids* "
        "are written `s04..s06`, because ids contain hyphens.")
    add("")
    add("Sections you leave out are recorded as **not selected**: never attempted, "
        "and reported as unknown rather than correct. A scoped run cannot answer "
        "*\"can a learner complete this lab?\"* — only *\"can a learner complete the "
        "sections I chose\"*.")
    add("")


def write_review(run: Run, outline: Outline | None = None, vault=None) -> Path:
    path = run.dir / REVIEW_FILENAME
    path.write_text(run.redactor.scrub(review(run, outline, vault)), encoding="utf-8")
    return path


# ---- applying ------------------------------------------------------------


def apply(run: Run, selection: Selection) -> Applied:
    """Write the selection into the run, refusing to un-walk anything.

    Re-scoping is expected: a walk that turns up something interesting in
    section 4 is a good reason to add sections 5 and 6. What it must never do is
    reset a section that has already been observed, because the observation is
    the evidence and the manifest is where it lives.

    The selection is *appended* to a ``selections`` list rather than replacing
    one, so the run records the sequence of decisions instead of only the last.
    """
    excluded_now: list[str] = []
    reopened: list[str] = []
    refused: list[tuple[str, str]] = []
    chosen = set(selection.chosen)

    for seg in run.manifest.get("segments", []):
        seg_id = seg["id"]
        status = seg.get("status") or "pending"
        if seg_id in chosen:
            if status == NOT_SELECTED:
                seg["status"] = "pending"
                seg.pop("note", None)
                reopened.append(seg_id)
            continue
        if status in FROZEN:
            refused.append((seg_id, status))
            continue
        if status == NOT_SELECTED:
            continue
        seg["status"] = NOT_SELECTED
        seg["note"] = NOT_SELECTED_NOTE
        excluded_now.append(seg_id)

    record = selection.to_dict()
    record["refused"] = [{"id": i, "status": s} for i, s in refused]
    run.manifest.setdefault("selections", []).append(record)
    run._save()

    applied = Applied(
        selection=selection,
        excluded=tuple(excluded_now),
        reopened=tuple(reopened),
        refused=tuple(refused),
        not_selected_now=tuple(not_selected_ids(run)),
    )
    run.log(f"scope ({selection.how}): {applied.summary()}")
    return applied


def not_selected_ids(run: Run) -> list[str]:
    return [s.id for s in run.segments() if s.status == NOT_SELECTED]


# ---- asking a human ------------------------------------------------------

PROMPT = "sections> "
PROMPT_HELP = (
    "Which sections should I walk?  'all' | '4' | '1,4,7' | '4-6' | '?' to "
    "re-print the review"
)

#: How many silent answers to absorb before concluding nobody is there.
BLANK_ANSWER_LIMIT = 3


def _nobody_answered(run: Run) -> ScopeError:
    """Refuse a scope nobody chose, and name the way back.

    Walking everything was the old fallback here, and it is the wrong one: it
    commits hours of a live lab's clock to sections nobody asked for, and files
    it as a decision. Everything captured is already on disk, so refusing costs
    one command and loses nothing.
    """
    return ScopeError(
        "nobody answered the scope prompt, so no section was chosen. Re-run "
        f"with an explicit selection: `lab-validator scope --run {run.dir} "
        "--sections all` (or '1,4,7', '4-6', a single number)."
    )


def prompt(
    run: Run,
    outline: Outline | None = None,
    vault=None,
    *,
    out=None,
    reader=None,
) -> Selection:
    """Show the review and block until a human decides.

    Only ever called when a terminal is attached. The human has just signed in
    by hand, so they are already at the keyboard: this is the cheapest moment in
    the whole run to ask them anything.
    """
    out = out or sys.stdout
    reader = reader or input
    text = review(run, outline, vault)
    print(text, file=out)
    #: A reader that answers nothing forever must not spin forever. `input()`
    #: raises at a real EOF, but a piped or stubbed reader can return "" on
    #: every call, and an unbounded re-ask would hang holding a live lab open.
    blanks = 0
    while True:
        print(PROMPT_HELP, file=out)
        try:
            raw = reader(PROMPT)
        except EOFError:
            raise _nobody_answered(run) from None
        raw = (raw or "").strip()
        if raw == "?":
            print(text, file=out)
            continue
        if not raw:
            # A bare Enter is silence, and silence is not approval. Reading it
            # as "all" turned the least deliberate keystroke available into the
            # most expensive choice this tool can make -- hours of lab clock
            # across every section -- and recorded it as a human's decision.
            blanks += 1
            if blanks >= BLANK_ANSWER_LIMIT:
                raise _nobody_answered(run)
            print("  nothing entered. Say 'all' if you mean all of them.", file=out)
            continue
        blanks = 0
        try:
            return parse(raw, run, how="prompt")
        except ScopeError as exc:
            print(f"  {exc}", file=out)


def select(
    run: Run,
    expression: str | None = None,
    *,
    outline: Outline | None = None,
    vault=None,
    interactive: bool | None = None,
    out=None,
    reader=None,
) -> Applied:
    """The one place the flag / prompt / default decision is made.

    ``walk``, ``auto`` and ``scope`` all route through here so they cannot drift
    apart on the question of who chose what.
    """
    out = out or sys.stdout
    if interactive is None:
        interactive = bool(getattr(sys.stdin, "isatty", lambda: False)())

    write_review(run, outline, vault)

    if expression:
        selection = parse(expression, run, how="flag")
    elif interactive:
        selection = prompt(run, outline, vault, out=out, reader=reader)
    else:
        print(review(run, outline, vault), file=out)
        print(
            "No --sections given and no terminal to ask at, so ALL sections are "
            "selected. Pass --sections to narrow it.",
            file=out,
        )
        selection = everything(run, how="default")

    applied = apply(run, selection)
    print(applied.summary(), file=out)
    if applied.refused:
        print(
            "  kept because they were already walked; re-scoping widens a run, "
            "it never erases evidence.",
            file=out,
        )
    return applied
