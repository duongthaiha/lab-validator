"""Turn a lab's instruction outline into a report.

The trace is the product; this renders it. Two rules shape the output:

* **Coverage comes first.** A findings list with no coverage figure invites the
  reader to assume the whole lab was walked. Naming what was never reached is
  the difference between an honest report and a misleading one.
* **Passes are printed too.** Without positive evidence a reader cannot tell
  "verified correct" from "never attempted", and those are opposite claims.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from .corpus import Anomaly, Outline
from .runlog import FINDING_VERDICTS, Run

CODE_NAMES = {
    "LAB000": "Environment transient (not a defect)",
    "LAB001": "Retired or renamed model",
    "LAB002": "Missing resource or SKU",
    "LAB003": "Changed UI label or inconsistent structure",
    "LAB004": "Moved navigation",
    "LAB005": "Removed feature",
    "LAB006": "Broken link",
    "LAB007": "Timing or quota",
    "LAB008": "Undocumented mandatory step",
}

SEVERITY_ICON = {"critical": "[!!]", "major": "[!]", "minor": "[~]", "info": "[i]"}
SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2, "info": 3}


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

    # ---- coverage -------------------------------------------------------
    done = summary["segments"]["done"]
    total = summary["segments"]["total"]
    pct = (done / total * 100) if total else 0.0
    add("## Coverage")
    add("")
    add(f"**{done} of {total} sections completed ({pct:.0f}%)** across "
        f"{summary['steps']:,} recorded steps and {summary['heartbeats']:,} heartbeats.")
    add("")
    add("| Section | Module | Status | Steps | Findings |")
    add("|---|---|---|---|---|")
    retracted = run.retracted()
    for seg in segments:
        rows = by_segment.get(seg["id"], [])
        finds = sum(
            1
            for r in rows
            if r.get("verdict") in FINDING_VERDICTS and r.get("seq") not in retracted
        )
        status = seg.get("status") or "pending"
        mark = {"done": "done", "blocked": "**blocked**", "skipped": "skipped",
                "in_progress": "*part*"}.get(status, "*not reached*")
        add(f"| {seg.get('title', seg['id'])[:52]} | {(seg.get('module') or '-')[:26]} "
            f"| {mark} | {len(rows)} | {finds or '-'} |")
    add("")
    never = summary["segments"]["never_reached"]
    if never:
        add(f"> **{len(never)} sections were never reached.** Nothing in this report "
            "says anything about them — they are unknown, not correct.")
        add("")

    # ---- findings -------------------------------------------------------
    findings = run.findings()
    findings.sort(key=lambda s: (SEVERITY_ORDER.get(s.get("severity", "minor"), 9), s["seq"]))
    add("## Findings")
    add("")
    if not findings:
        add("No defects recorded in the sections that were walked.")
        add("")
    else:
        counts = Counter(s["verdict"] for s in findings)
        add(" · ".join(f"**{v}** ×{n}" for v, n in sorted(counts.items())))
        add("")
        for i, f in enumerate(findings, 1):
            sev = f.get("severity", "minor")
            icon = SEVERITY_ICON.get(sev, "[~]")
            name = CODE_NAMES.get(f["verdict"], f["verdict"])
            add(f"### {i}. {icon} {name} — `{f['verdict']}`")
            add("")
            seg = next((s for s in segments if s["id"] == f["segment"]), {})
            add(f"*Section:* {seg.get('title', f['segment'])}  ")
            if f.get("instructionRef"):
                add(f"*Instruction:* `{f['instructionRef']}`  ")
            add(f"*Severity:* {sev}")
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
    passes = [s for s in steps if s["verdict"] == "PASS" and (s.get("note") or s.get("expected"))]
    add("## Verified correct")
    add("")
    if not passes:
        add("_No explicit confirmations recorded._")
    else:
        add(f"{len(passes)} instruction(s) were checked and matched reality:")
        add("")
        for s in passes:
            seg = next((x for x in segments if x["id"] == s["segment"]), {})
            label = s.get("note") or s.get("instructionText") or s.get("action")
            add(f"- **{seg.get('title', s['segment'])[:40]}** — {label}")
    add("")

    # ---- blocked / deferred --------------------------------------------
    blocked = [s for s in steps if s["verdict"] in ("BLOCKED", "DEFERRED")]
    if blocked:
        add("## Blocked and deferred")
        add("")
        for s in blocked:
            seg = next((x for x in segments if x["id"] == s["segment"]), {})
            add(f"- `{s['verdict']}` **{seg.get('title', s['segment'])[:40]}** — "
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
        add("## Withdrawn findings")
        add("")
        add("Recorded during the walk, then withdrawn once the cause was understood. "
            "They are listed rather than deleted so the report can be audited against "
            "the raw trace.")
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
