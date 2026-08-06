"""Turn a lab's instruction outline into a report.

The trace is the product; this renders it. Three rules shape the output:

* **Coverage comes first.** A findings list with no coverage figure invites the
  reader to assume the whole lab was walked. Naming what was never reached is
  the difference between an honest report and a misleading one.
* **Passes are printed too.** Without positive evidence a reader cannot tell
  "verified correct" from "never attempted", and those are opposite claims.
* **Every section reports on itself, as it finishes.** A single roll-up written
  at the end only exists if the run reaches the end, and runs get cut short by
  expiring instances and dropped sessions. Per-section reports mean the walk is
  worth something the moment each section lands, and they are what the lab
  author actually acts on — nobody edits a lab by reading a 30-finding digest.

Orientation
-----------
Role:     renders the trace into per-section reports and the roll-up; the last stage of a walk.
Entry:    `render`, `render_segment`, `write_segment`, `completability`
Talks to: corpus, learnerpath, runlog, taxonomy
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass

from .corpus import Anomaly, Outline
from .learnerpath import Ledger
from .runlog import FINDING_VERDICTS, Run, Segment
from .taxonomy import CODE_NAMES

SEVERITY_ICON = {"critical": "[!!]", "major": "[!]", "minor": "[~]", "info": "[i]"}
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}

# Setup first, deliberately. Setup defects are the ones that do not announce
# themselves -- a deployment named `gpt-4o` that serves something else, a
# shipped `.env` with a valid URL of the wrong kind -- so they get misattributed
# to five unrelated labs before anyone looks at the environment. They are also
# usually a one-line fix by a different owner than the lab author.
DOMAIN_ORDER = {"setup": 0, "instruction": 1, "undetermined": 2}
DOMAIN_TITLE = {
    "setup": "Setup defects — the environment cannot deliver what the text describes",
    "instruction": "Instruction defects — the lab text is wrong",
    "undetermined": "Unattributed — the evidence does not yet say which side is wrong",
}
DOMAIN_OWNER = {
    "setup": "lab profile / image / subscription owner",
    "instruction": "lab author",
    "undetermined": "needs one more observation before it can be routed",
}

STATUS_WORD = {
    "done": "walked to the end",
    "blocked": "**blocked part-way**",
    "skipped": "skipped",
    "not_selected": "not selected for this run",
    "in_progress": "*still in progress*",
    "pending": "*not started*",
}

COMPLETABILITY_WORD = {
    "no": "**NO** — a learner cannot complete this as written",
    "partially": "**PARTIALLY** — reachable, but not by following the instructions as written",
    "yes": "**YES** — a learner following the instructions can complete this",
    "unknown": "**UNKNOWN** — too little was walked to answer",
}


@dataclass(frozen=True)
class Completability:
    """The one question every reader opens the report to answer.

    Today this lives in prose -- *"two structural defects gate the entire
    workshop"* -- which is true, well argued, and unreadable by anything but a
    human. Deriving it from the trace makes it comparable across runs and
    forces the report to name the evidence that gates the lab.
    """

    verdict: str
    blockers: list[dict]

    @property
    def word(self) -> str:
        return COMPLETABILITY_WORD[self.verdict]


def completability(
    findings: list[dict], blocked: list[dict], *, all_walked: bool
) -> Completability:
    """Decide, structurally, whether a learner could get through.

    A blocker is something that stops *every* learner: a section that could not
    be walked at all, or a critical finding. ``DEFERRED`` is not a blocker --
    it records that the walker chose to come back later, which says nothing
    about the lab.

    Absence of evidence is never a yes: if any section went unwalked the honest
    answer is that we do not know, because unreached content is unknown, not
    correct.
    """
    gates = [s for s in blocked if s.get("verdict") == "BLOCKED"]
    gates += [f for f in findings if f.get("severity") == "critical"]
    gates.sort(key=lambda s: s.get("seq", 0))
    if gates:
        return Completability("no", gates)
    if any(f.get("severity") == "major" for f in findings):
        return Completability("partially", [])
    if not all_walked:
        return Completability("unknown", [])
    return Completability("yes", [])


def render_blockers(add, verdict: Completability, label: dict[int, str] | None = None) -> None:
    """A blocked run has found the most important thing there is to find.

    So it is printed up front, with its evidence, rather than as a footnote
    after the passes -- otherwise a run that discovered the lab is unusable
    reads as a run that failed to finish.
    """
    if not verdict.blockers:
        return
    add("## Blockers")
    add("")
    add("These stop a learner outright. Everything after this point was "
        "observed either before the block or around it.")
    add("")
    for s in verdict.blockers:
        where = f" *({label[s['seq']]})*" if label and s.get("seq") in label else ""
        code = s.get("verdict", "BLOCKED")
        name = CODE_NAMES.get(code, code)
        why = s.get("note") or s.get("observed") or "no reason recorded"
        add(f"- **{name}** `{code}`{where} — {why}")
        add(f"  <br>evidence: step `{s.get('seq')}`"
            + (f", instruction `{s['instructionRef']}`" if s.get("instructionRef") else ""))
    add("")


def render_domain_routing(add, findings: list[dict]) -> None:
    """Split the findings by who has to fix them.

    Instruction and setup defects have different owners and different fixes,
    and the numbering is left alone on purpose -- a finding that changes number
    between runs cannot be tracked, so this routes by reference instead of by
    re-ordering.
    """
    if not findings:
        return
    grouped: dict[str, list[str]] = defaultdict(list)
    for i, f in enumerate(findings, 1):
        domain = f.get("domain") or "undetermined"
        name = CODE_NAMES.get(f["verdict"], f["verdict"])
        grouped[domain].append(f"**#{i}** {name} (`{f['verdict']}`)")
    add("### Who fixes what")
    add("")
    for domain in sorted(grouped, key=lambda d: DOMAIN_ORDER.get(d, 9)):
        add(f"**{DOMAIN_TITLE.get(domain, domain)}** — {DOMAIN_OWNER.get(domain, 'unknown owner')}")
        add("")
        for line in grouped[domain]:
            add(f"- {line}")
        add("")



def render_ageing(add, findings: list[dict], label: dict[str, str] | None = None) -> None:
    """Findings whose step *succeeded*, printed where a clean bill of health follows.

    Every other code is discovered by something going wrong. This one is only
    visible at a step that worked, which means a report can be entirely green
    and still describe a lab built on an experience the product is retiring --
    correct today, and wrong on a date somebody has already published. Left in
    the findings list it inherits the severity it deserves, `info`, and `info`
    is what a reader skips.

    So it is lifted out and placed immediately before "Verified correct", to
    qualify the passes that follow rather than trail after them. The numbering
    is the global one, recomputed from the same sorted list the findings section
    enumerates, because a finding that changes number between sections of the
    same report cannot be discussed.
    """
    ageing = [(i, f) for i, f in enumerate(findings, 1) if f["verdict"] == "LAB010"]
    if not ageing:
        return
    add("## Ageing guidance (works today)")
    add("")
    add("Nothing here stopped a learner. Each is a step that *succeeded* while "
        "following a path the product has moved on from, so it dates the lab "
        "rather than breaking it.")
    add("")
    for i, f in ageing:
        where = f" *({label[f['segment']]})*" if label and f.get("segment") in label else ""
        why = f.get("observed") or f.get("note") or "no detail recorded"
        add(f"- **#{i}** {CODE_NAMES.get(f['verdict'], f['verdict'])}{where} — {why}")
        if f.get("instructionRef"):
            add(f"  <br>instruction: `{f['instructionRef']}`")
    add("")


def is_confirmation(step: dict) -> bool:
    """Is this step a deliberate judgement that an instruction matched reality?

    Driving a step emits mechanical notes of its own -- ``settled after 7s``,
    ``42 chars`` -- and those are trace bookkeeping, not evidence that anything
    was checked. Listing them under "Verified correct" would pad the section
    with claims nobody made, which is the same failure as counting a screenshot
    as a verification. Judgements are the ones recorded on the analysis surface.
    """
    return (
        step.get("verdict") == "PASS"
        and step.get("surface") == "analysis"
        and bool(step.get("note"))
    )


def segment_filename(segment_id: str) -> str:
    """Where a section's own report lives, relative to the run folder."""
    return f"sections/{segment_id}.md"


def render_segment(run: Run, segment: Segment, outline: Outline | None = None) -> str:
    """Render one section's report.

    This is a pure function of the trace, so it can be regenerated at any point —
    mid-section for a progress check, or again after a retraction. That matters
    because the alternative, accumulating text as the walk goes, cannot survive a
    withdrawn finding without rewriting history.
    """
    steps = [
        s
        for s in run.steps()
        if s.get("segment") == segment.id and s.get("kind") != "heartbeat"
    ]
    heartbeats = sum(
        1 for s in run.steps() if s.get("segment") == segment.id and s.get("kind") == "heartbeat"
    )
    retracted = run.retracted()
    findings = [
        s
        for s in steps
        if s.get("verdict") in FINDING_VERDICTS and s.get("seq") not in retracted
    ]
    findings.sort(key=lambda s: (SEVERITY_ORDER.get(s.get("severity", "minor"), 9), s["seq"]))

    out: list[str] = []
    add = out.append

    add(f"# {segment.title}")
    add("")
    add(f"*Section* `{segment.id}`" + (f" · *Module* {segment.module}" if segment.module else ""))
    add("")
    manifest = run.manifest
    add(f"**Lab.** {manifest.get('target')} — instance `{manifest.get('instance')}`  ")
    add(f"**Run.** `{run.dir.name}`  ")
    add(f"**Status.** {STATUS_WORD.get(segment.status, segment.status)}  ")
    if segment.anchor:
        add(f"**Instructions.** `{segment.anchor}`  ")
    clock = []
    if segment.lab_minutes_at_start is not None:
        clock.append(f"{segment.lab_minutes_at_start:,} min at start")
    if segment.lab_minutes_at_end is not None:
        clock.append(f"{segment.lab_minutes_at_end:,} min at end")
    if clock:
        add(f"**Lab clock.** {' → '.join(clock)}  ")
    add(f"**Evidence.** {len(steps)} recorded step(s)"
        + (f", {heartbeats} heartbeat(s)" if heartbeats else "")
        + f", {len(findings)} finding(s)")
    add("")

    blocked_steps = [s for s in steps if s.get("verdict") in ("BLOCKED", "DEFERRED")]
    verdict = completability(findings, blocked_steps, all_walked=segment.status == "done")
    add(f"**Can a learner finish this section?** {verdict.word}")
    add("")
    if segment.note:
        add(f"> {segment.note}")
        add("")

    render_blockers(add, verdict)

    if outline is not None and segment.anchor:
        head = outline.section_by_anchor(segment.anchor)
        if head is not None:
            tasks = outline.tasks(head)
            if tasks:
                base = min(t.level for t in tasks)
                add("## What the lab asks the learner to do")
                add("")
                for task in tasks:
                    add(f"{'  ' * (task.level - base)}- {task.text}")
                add("")

    add("## Findings")
    add("")
    if not findings:
        if segment.status in ("done", "blocked"):
            add("No defects recorded in this section.")
        else:
            add("_None yet — this section is not finished, so absence of findings "
                "means nothing._")
        add("")
    else:
        counts = Counter(s["verdict"] for s in findings)
        add(" · ".join(f"**{v}** ×{n}" for v, n in sorted(counts.items())))
        add("")
        render_domain_routing(add, findings)
        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "minor")
            icon = SEVERITY_ICON.get(sev, "[~]")
            name = CODE_NAMES.get(f["verdict"], f["verdict"])
            add(f"### {i}. {icon} {name} — `{f['verdict']}`")
            add("")
            if f.get("instructionRef"):
                add(f"*Instruction:* `{f['instructionRef']}`  ")
            domain = f.get("domain") or "undetermined"
            add(f"*Severity:* {sev} · *At fault:* {domain} · "
                f"*Step:* `{f['seq']}` · *{f.get('ts', '')}*")
            add("")
            if f.get("instructionText"):
                add("**The lab says**")
                add("")
                add(f"> {f['instructionText']}")
                add("")
            if f.get("observed"):
                add(f"**Actually observed:** `{f['observed']}`")
                add("")
            if f.get("note"):
                add(f["note"])
                add("")
            for img in f.get("images", []):
                add(f"![evidence](../{img})")
            if f.get("images"):
                add("")

    render_ageing(add, findings)
    passes = [s for s in steps if is_confirmation(s) and s.get("seq") not in retracted]
    add("## Verified correct")
    add("")
    if not passes:
        add("_No explicit confirmations recorded in this section._")
    else:
        for s in passes:
            add(f"- {s['note']}")
    add("")

    deferred = [s for s in steps if s.get("verdict") == "DEFERRED"]
    if deferred:
        add("## Deferred")
        add("")
        add("_Postponed by the walk, not by the lab. These say nothing about the lab._")
        add("")
        for s in deferred:
            add(f"- {s.get('note', 'no reason recorded')}")
        add("")

    transients = [s for s in steps if s.get("verdict") == "LAB000"]
    if transients:
        add("## Environment transients (not defects)")
        add("")
        for s in transients:
            add(f"- {s.get('note') or s.get('action')}")
        add("")

    withdrawn = [
        s
        for s in run.steps()
        if s.get("kind") == "retraction" and s.get("segment") == segment.id
    ]
    if withdrawn:
        add("## Withdrawn judgements")
        add("")
        for s in withdrawn:
            add(f"- step `{s.get('retracts')}` — {s.get('note', 'no reason recorded')}")
        add("")

    images = [img for s in steps for img in s.get("images", [])]
    if images:
        add("## Evidence")
        add("")
        add(f"{len(images)} capture(s), in the order the learner would have seen them.")
        add("")
        for s in steps:
            for img in s.get("images", []):
                name = img.rsplit("/", 1)[-1]
                # The capture label already lives in the filename; repeating the
                # action verb here would print "shot" against every single row.
                note = s.get("note") if s.get("surface") == "analysis" else ""
                add(f"- [`{name}`](../{img}){f' — {note[:80]}' if note else ''}")
        add("")

    return "\n".join(out).rstrip() + "\n"


def write_segment(run: Run, segment: Segment, outline: Outline | None = None):
    """Write a section's report into the run folder and return its path.

    Records how far through the trace the report was written from, so a later
    reader can tell a current report from a stale one. Without it, "the file
    exists" is the only available test, and a report written before the last
    three findings passes it.
    """
    path = run.dir / segment_filename(segment.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_segment(run, segment, outline), encoding="utf-8")
    entry = run.segment(segment.id)
    if entry is not None:
        entry["reported_through"] = _last_seq(run, segment.id)
        run._save()
    return path


def _last_seq(run: Run, segment_id: str) -> int:
    """The highest trace seq recorded against this section, or 0."""
    seqs = [
        s.get("seq") or 0
        for s in run.steps()
        if s.get("segment") == segment_id
    ]
    return max(seqs, default=0)


def _sections_were(n: int) -> str:
    """'1 section was' / '2 sections were'. These two warning blocks are the
    sentences a reader is most likely to quote into a bug, so they should not
    read as if nobody proofread them. Verb included because agreement is the
    half that gets forgotten."""
    return "1 section was" if n == 1 else f"{n} sections were"


def render(run: Run, outline: Outline | None = None, anomalies: list[Anomaly] | None = None) -> str:
    summary = run.summary()
    manifest = run.manifest
    segments = manifest.get("segments", [])
    steps = [s for s in run.steps() if s.get("kind") != "heartbeat"]
    by_segment: dict[str, list[dict]] = defaultdict(list)
    for step in steps:
        by_segment[step["segment"]].append(step)

    out: list[str] = []
    add = out.append

    add("# Gap analysis")
    add("")
    add(f"**Lab.** {manifest.get('target')} — instance `{manifest.get('instance')}`  ")
    add(f"**Run.** `{run.dir.name}` started {manifest.get('startedUtc')}, "
        f"status **{manifest.get('status')}**  ")
    corpus = manifest.get("corpus") or {}
    if corpus.get("sha256"):
        add(f"**Instructions.** `{corpus['sha256'][:16]}…` "
            f"({corpus.get('lines', 0):,} lines). A future run that hashes differently "
            "is comparing against rewritten content, not drifted product.  ")
    add("")
    add("This report is what a simulated learner encountered while doing the lab. "
        "It records what was verified correct as well as what was wrong, because a "
        "list of failures alone cannot distinguish a checked step from a skipped one.")
    add("")

    # ---- the headline question ------------------------------------------
    retracted = run.retracted()
    findings = run.findings()
    findings.sort(key=lambda s: (SEVERITY_ORDER.get(s.get("severity", "minor"), 9), s["seq"]))
    # A scoped run answers a *different question*, and must never be allowed to
    # answer the whole one. Written as its own term rather than left to fall out
    # of `done != total`: that arithmetic happens to be right today, and a
    # coincidence is not a guarantee.
    not_selected = summary["segments"].get("not_selected") or []
    all_walked = (
        summary["segments"]["done"] == summary["segments"]["total"]
        and not summary["segments"]["never_reached"]
        and not not_selected
    )
    blocked_steps = [s for s in steps if s.get("verdict") in ("BLOCKED", "DEFERRED")]
    verdict = completability(findings, blocked_steps, all_walked=all_walked)
    seg_title = {s["id"]: s.get("title", s["id"]) for s in segments}
    # The lab a section belongs to. Skillable modules carry the lab name; a
    # single-lab document has none, so the section title is the lab.
    seg_lab = {
        s["id"]: (s.get("module") or "").strip() or s.get("title", s["id"])
        for s in segments
    }
    where = {
        s["seq"]: seg_title.get(s.get("segment"), s.get("segment", ""))
        for s in steps
        if s.get("seq") is not None
    }
    add("## Can a learner complete this lab?")
    add("")
    add(verdict.word)
    add("")
    if not_selected:
        add(f"> **Scoped run.** {len(not_selected)} of {summary['segments']['total']} "
            "sections were not selected and were never attempted, so this answers "
            "*\"can a learner complete the sections that were chosen\"* — not the "
            "whole lab.")
        add("")
    if not all_walked and verdict.verdict != "unknown":
        add("> Scoped to what was walked. Sections that were never reached are "
            "unknown, not correct — see Coverage.")
        add("")
    render_blockers(add, verdict, where)

    # ---- coverage -------------------------------------------------------
    done = summary["segments"]["done"]
    total = summary["segments"]["total"]
    selected = total - len(not_selected)
    add("## Coverage")
    add("")
    if not_selected:
        pct = (done / selected * 100) if selected else 0.0
        add(f"**{done} of {selected} selected sections completed ({pct:.0f}%)** across "
            f"{summary['steps']:,} recorded steps and {summary['heartbeats']:,} heartbeats.")
        add("")
        add(f"**{len(not_selected)} of {total} sections were not selected for this run.**")
    else:
        pct = (done / total * 100) if total else 0.0
        add(f"**{done} of {total} sections completed ({pct:.0f}%)** across "
            f"{summary['steps']:,} recorded steps and {summary['heartbeats']:,} heartbeats.")
    add("")
    add("| Section | Module | Status | Steps | Findings | Report |")
    add("|---|---|---|---|---|---|")
    for seg in segments:
        rows = by_segment.get(seg["id"], [])
        finds = sum(
            1
            for r in rows
            if r.get("verdict") in FINDING_VERDICTS and r.get("seq") not in retracted
        )
        status = seg.get("status") or "pending"
        mark = {"done": "done", "blocked": "**blocked**", "skipped": "skipped",
                "not_selected": "*not selected*",
                "in_progress": "*part*"}.get(status, "*not reached*")
        report = segment_filename(seg["id"])
        link = f"[section]({report})" if (run.dir / report).exists() else "-"
        add(f"| {seg.get('title', seg['id'])[:52]} | {(seg.get('module') or '-')[:26]} "
            f"| {mark} | {len(rows)} | {finds or '-'} | {link} |")
    add("")
    never = summary["segments"]["never_reached"]
    if never:
        add(f"> **{_sections_were(len(never))} never reached.** Nothing in this report "
            "says anything about them — they are unknown, not correct.")
        add("")
    if not_selected:
        # A separate sentence from the one above, because they are separate
        # facts: "never reached" is a walk that ran out of road, "not selected"
        # is a decision somebody made before it started. Same ignorance,
        # different cause, different thing to do about it.
        add(f"> **{_sections_were(len(not_selected))} not selected for this run.** They "
            "were never attempted — out of scope, not correct. Re-run with a wider "
            "`--sections` to cover them.")
        add("")

    # Two coverage claims the section table cannot make, both of the same kind:
    # things that went unexamined rather than things that failed. Neither is a
    # defect in the lab, and both change what a clean report is worth.
    ledger = Ledger.load(run.dir)
    if ledger.used:
        add(ledger.to_markdown())

    preflight = run.manifest.get("preflight") or {}
    if preflight.get("unchecked"):
        add("### What the setup preflight could not check")
        add("")
        add("A clean preflight means *the things we knew to check* passed:")
        add("")
        for reason in preflight["unchecked"]:
            add(f"- {reason}")
        add("")

    # ---- findings -------------------------------------------------------
    add("## Findings")
    add("")
    if not findings:
        add("No defects recorded in the sections that were walked.")
        add("")
    else:
        counts = Counter(s["verdict"] for s in findings)
        add(" · ".join(f"**{v}** ×{n}" for v, n in sorted(counts.items())))
        add("")
        render_domain_routing(add, findings)

        # Grouped by lab, because that is the unit somebody fixes. A run over a
        # multi-lab module produces one flat severity-ordered list otherwise,
        # and whoever owns lab 3 has to read all of it to find their two
        # findings. Numbering stays global and severity-ordered so a finding
        # keeps the same number here, in the routing above, and between runs.
        numbered = list(enumerate(findings, 1))
        by_lab: dict[str, list[tuple[int, dict]]] = defaultdict(list)
        for i, f in numbered:
            by_lab[seg_lab.get(f["segment"], f["segment"])].append((i, f))

        add("Findings are grouped by lab below. Numbering is global and ordered "
            "by severity, so a finding keeps its number wherever it is read.")
        add("")
        add("| ID | Sev | Lab | Gap |")
        add("|---|---|---|---|")
        for i, f in numbered:
            add(f"| #{i} | {f.get('severity', 'minor')} | "
                f"{seg_lab.get(f['segment'], f['segment'])} | "
                f"{CODE_NAMES.get(f['verdict'], f['verdict'])} |")
        add("")

        for lab, entries in by_lab.items():
            add(f"### {lab}")
            add("")
            for i, f in entries:
                sev = f.get("severity", "minor")
                icon = SEVERITY_ICON.get(sev, "[~]")
                name = CODE_NAMES.get(f["verdict"], f["verdict"])
                add(f"#### {i}. {icon} {name} — `{f['verdict']}`")
                add("")
                add(f"*Section:* {seg_title.get(f['segment'], f['segment'])}  ")
                if f.get("instructionRef"):
                    add(f"*Instruction:* `{f['instructionRef']}`  ")
                add(f"*Severity:* {sev} · *At fault:* {f.get('domain') or 'undetermined'}")
                add("")
                if f.get("instructionText"):
                    add("**The lab says**")
                    add("")
                    add(f"> {f['instructionText']}")
                    add("")
                if f.get("observed"):
                    add(f"**Actually observed:** `{f['observed']}`")
                    add("")
                if f.get("note"):
                    add(f["note"])
                    add("")
                for img in f.get("images", []):
                    add(f"![evidence]({img})")
                if f.get("images"):
                    add("")

    # ---- structural anomalies ------------------------------------------
    if anomalies:
        add("## Structural problems in the instruction content")
        add("")
        add("Found by parsing the instruction document itself, independently of "
            "walking the lab, so these hold regardless of coverage.")
        add("")
        for a in sorted(anomalies, key=lambda x: SEVERITY_ORDER.get(x.severity, 9)):
            add(f"- {SEVERITY_ICON.get(a.severity, '[~]')} **`{a.code}`** {a.message}")
        add("")

    # ---- verified correct ----------------------------------------------
    render_ageing(add, findings, seg_title)
    passes = [s for s in steps if is_confirmation(s) and s.get("seq") not in retracted]
    add("## Verified correct")
    add("")
    if not passes:
        add("_No explicit confirmations recorded._")
    else:
        add(f"{len(passes)} instruction(s) were checked and matched reality:")
        add("")
        for s in passes:
            seg = next((x for x in segments if x["id"] == s["segment"]), {})
            add(f"- **{seg.get('title', s['segment'])[:40]}** — {s['note']}")
    add("")

    # ---- deferred --------------------------------------------------------
    deferred = [s for s in steps if s["verdict"] == "DEFERRED"]
    if deferred:
        add("## Deferred")
        add("")
        add("_Postponed by the walk, not by the lab. Blockers are reported up front._")
        add("")
        for s in deferred:
            seg = next((x for x in segments if x["id"] == s["segment"]), {})
            add(f"- **{seg.get('title', s['segment'])[:40]}** — "
                f"{s.get('note', 'no reason recorded')}")
        add("")

    # ---- transients -----------------------------------------------------
    transients = [s for s in steps if s["verdict"] == "LAB000"]
    if transients:
        add("## Environment transients (recorded, not reported as defects)")
        add("")
        add(f"{len(transients)} recovered failure(s). These are kept so the run's "
            "noisiness stays visible without inflating the findings count.")
        add("")
        for s in transients:
            add(f"- {s.get('note') or s.get('action')}")
        add("")

    # ---- retractions ----------------------------------------------------
    withdrawals = [s for s in steps if s.get("kind") == "retraction"]
    if withdrawals:
        add("## Withdrawn judgements")
        add("")
        add("Findings and confirmations recorded during the walk, then withdrawn once "
            "the cause was understood. They are listed rather than deleted so the report "
            "can be audited against the raw trace.")
        add("")
        for s in withdrawals:
            original = next(
                (x for x in steps if x.get("seq") == s.get("retracts")), {}
            )
            add(f"- `{original.get('verdict', '?')}` on `{original.get('action', '?')}` "
                f"— {s.get('note', 'no reason recorded')}")
        add("")

    events = manifest.get("events") or []
    if events:
        add("## Run events")
        add("")
        for e in events:
            add(f"- `{e['ts']}` **{e['kind']}** — {e['detail']}")
        add("")

    return "\n".join(out).rstrip() + "\n"
