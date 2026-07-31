"""Run folder, append-only trace, and evidence numbering for a validation run.

One *run* is one attempt to walk a lab end to end. It owns a timestamped folder::

    runs/2026-07-30T0015Z/
        run.json        manifest: target, ids, corpus hash, per-segment status
        trace.jsonl     one ``lab-validator/run-trace/v1`` record per step
        images/         NNNN-<segment>-<label>.png evidence
        run.log         free-text log

Two properties matter more than anything else here:

* **Append-only.** Every step is flushed to disk as it happens, so a run that
  dies at step 240 still yields 240 verified steps. Partial runs being valuable
  is the whole design, not a nicety.
* **Resumable.** :meth:`Run.open` rebuilds the sequence counters from what is
  already on disk, so a crashed run continues rather than restarting.

Redaction happens *here*, at the writer, rather than at each call site. A
:class:`Redactor` registered on the run scrubs known secret values out of every
string before it reaches ``trace.jsonl`` or ``run.log`` -- lab credentials are
short-lived but they should still never be written down.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from collections.abc import Iterator
from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any

SCHEMA = "lab-validator/run-trace/v1"

#: Terminal verdicts for a step.
#:
#: ``PASS`` is as important as any failure code: a differ with no positive
#: evidence cannot tell "verified correct" from "never reached", and those two
#: must never collapse into one another.
VERDICTS = (
    "PASS",
    "LAB000",  # environment transient -- recorded, never reported as a finding
    "LAB001",  # retired / renamed model
    "LAB002",  # missing resource or SKU
    "LAB003",  # changed UI label
    "LAB004",  # moved navigation
    "LAB005",  # removed feature
    "LAB006",  # broken link
    "LAB007",  # timing / quota -- includes "this step never finishes"
    "LAB008",  # undocumented mandatory step
    "LAB009",  # defective sample code -- swallows failure or produces no output
    "BLOCKED",  # a dependency failed, so this could not be attempted
    "DEFERRED",  # deliberately not attempted; requires a justification
)

SEVERITIES = ("critical", "major", "minor", "info")

#: Verdicts that represent a real, learner-facing defect.
#: Derived by name rather than by slice index so that adding a code to
#: ``VERDICTS`` cannot silently drop the last one out of the finding set.
FINDING_VERDICTS = frozenset(
    v for v in VERDICTS if v.startswith("LAB") and v != "LAB000"
)


def _is_judgement(step: dict) -> bool:
    """Does this step assert something about the lab, rather than just do work?

    Findings assert an instruction is wrong. Confirmations -- a ``PASS``
    recorded deliberately on the analysis surface with a note -- assert the
    opposite. Both are claims the report repeats, so both must be withdrawable.
    A click or a screenshot asserts nothing and has nothing to withdraw.
    """
    if step.get("verdict") in FINDING_VERDICTS:
        return True
    return (
        step.get("verdict") == "PASS"
        and step.get("surface") == "analysis"
        and bool(step.get("note"))
        and step.get("kind") != "retraction"
    )


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def stamp(when: dt.datetime | None = None) -> str:
    """Folder-safe UTC timestamp, e.g. ``2026-07-30T0015Z``."""
    return (when or utc_now()).strftime("%Y-%m-%dT%H%MZ")


def iso(when: dt.datetime | None = None) -> str:
    return (when or utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(text: str, limit: int = 40) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return (out[:limit].rstrip("-")) or "step"


class Redactor:
    """Replaces known secret values with ``[REDACTED:label]`` markers.

    Registered secrets are matched longest-first so that a password which
    happens to be a substring of a longer token does not mask it partially.
    Values shorter than ``min_length`` are ignored: masking a 3-character string
    would corrupt unrelated text far more often than it would protect anything.
    """

    min_length = 6

    def __init__(self) -> None:
        self._secrets: dict[str, str] = {}

    def add(self, value: str, label: str = "secret") -> None:
        if value and len(value) >= self.min_length:
            self._secrets[value] = label

    def add_many(self, pairs) -> None:
        for value, label in pairs:
            self.add(value, label)

    def __len__(self) -> int:
        return len(self._secrets)

    def text(self, value: str) -> str:
        for secret, label in sorted(self._secrets.items(), key=lambda kv: -len(kv[0])):
            value = value.replace(secret, f"[REDACTED:{label}]")
        return value

    def scrub(self, obj: Any) -> Any:
        """Recursively redact every string inside a JSON-shaped object."""
        if isinstance(obj, str):
            return self.text(obj)
        if isinstance(obj, dict):
            return {k: self.scrub(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self.scrub(v) for v in obj]
        return obj


@dataclass
class Segment:
    """One resumable checkpoint of the walk."""

    id: str
    title: str
    module: str | None = None
    anchor: str | None = None
    # Heading ordinals, not source line numbers. The corpus is addressed by
    # anchor and heading order because the instructions frame *accumulates*
    # pages, so a source line number is not stable across a run.
    start_heading: int | None = None
    end_heading: int | None = None
    status: str = "pending"  # pending | in_progress | done | blocked | skipped
    started: str | None = None
    ended: str | None = None
    lab_minutes_at_start: int | None = None
    lab_minutes_at_end: int | None = None
    note: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> Segment:
        """Build from a manifest entry, tolerating the old ``*_line`` keys.

        Run folders are evidence and outlive the code that wrote them, so a
        field rename must never make an existing run unreadable.
        """
        data = dict(data)
        for old, new in (("start_line", "start_heading"), ("end_line", "end_heading")):
            value = data.pop(old, None)
            if value is not None:
                data.setdefault(new, value)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class Run:
    """A single validation run, backed by a folder on disk."""

    dir: Path
    manifest: dict = field(default_factory=dict)
    redactor: Redactor = field(default_factory=Redactor)
    _seq: int = 0
    _img: int = 0

    # ---- lifecycle ------------------------------------------------------

    @classmethod
    def create(
        cls,
        runs_root: Path,
        target: str,
        *,
        lab: dict | None = None,
        instance: str | None = None,
        corpus: Path | None = None,
        agent: str | None = None,
        segments: list[Segment] | None = None,
    ) -> Run:
        runs_root = Path(runs_root)
        base = runs_root / stamp()
        # A second run inside the same minute must not clobber the first.
        path, n = base, 1
        while path.exists():
            n += 1
            path = runs_root / f"{base.name}-{n}"

        (path / "images").mkdir(parents=True)
        run = cls(dir=path)
        run.manifest = {
            "schema": SCHEMA,
            "target": target,
            "lab": lab or {},
            "instance": instance,
            "agent": agent,
            "startedUtc": iso(),
            "endedUtc": None,
            "status": "running",
            "corpus": _corpus_info(corpus),
            "segments": [s.to_dict() for s in (segments or [])],
            "events": [],
        }
        run._save()
        run.log(f"run started: target={target} instance={instance}")
        return run

    @classmethod
    def open(cls, path: Path) -> Run:
        """Reopen an existing run, restoring the sequence counters."""
        path = Path(path)
        manifest_path = path / "run.json"
        if not manifest_path.exists():
            raise FileNotFoundError(f"not a run folder (no run.json): {path}")
        run = cls(dir=path, manifest=json.loads(manifest_path.read_text("utf-8")))
        (path / "images").mkdir(exist_ok=True)
        run._seq = max((r.get("seq", 0) for r in run.steps()), default=0)
        # Consider both what is on disk and what the trace claims: a reserved
        # number whose capture failed must not be handed out twice.
        numbers = [int(p.name[:4]) for p in run.images_dir.glob("[0-9][0-9][0-9][0-9]-*")]
        for record in run.steps():
            for name in record.get("images", []):
                head = Path(name).name[:4]
                if head.isdigit():
                    numbers.append(int(head))
        run._img = max(numbers, default=0)
        return run

    @classmethod
    def latest(cls, runs_root: Path) -> Run | None:
        runs = sorted(p for p in Path(runs_root).glob("*") if (p / "run.json").exists())
        return cls.open(runs[-1]) if runs else None

    def finish(self, status: str = "complete", note: str | None = None) -> None:
        self.manifest["status"] = status
        self.manifest["endedUtc"] = iso()
        if note:
            self.manifest["note"] = note
        self._save()
        self.log(f"run finished: {status}")

    # ---- paths ----------------------------------------------------------

    @property
    def images_dir(self) -> Path:
        return self.dir / "images"

    @property
    def trace_path(self) -> Path:
        return self.dir / "trace.jsonl"

    @property
    def manifest_path(self) -> Path:
        return self.dir / "run.json"

    @property
    def log_path(self) -> Path:
        return self.dir / "run.log"

    def next_image(self, segment: str, label: str) -> Path:
        """Reserve the next numbered evidence path. Numbering is monotonic."""
        self._img += 1
        return self.images_dir / f"{self._img:04d}-{_slug(segment, 20)}-{_slug(label)}.png"

    # ---- writing --------------------------------------------------------

    def log(self, message: str) -> None:
        line = f"{iso()}  {self.redactor.text(message)}\n"
        with self.log_path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def step(
        self,
        segment: str,
        *,
        verdict: str = "PASS",
        instruction_ref: str | None = None,
        instruction_text: str | None = None,
        action: str | None = None,
        expected: dict | None = None,
        observed: dict | None = None,
        surface: str = "vision",
        images: list[Path | str] | None = None,
        severity: str | None = None,
        note: str | None = None,
        **extra: Any,
    ) -> dict:
        """Append one trace record and return it.

        ``verdict`` and ``severity`` are validated rather than free text: a
        typo'd verdict would silently vanish from every report that groups by
        it, which is the worst possible failure mode for a differ.
        """
        if verdict not in VERDICTS:
            raise ValueError(f"unknown verdict {verdict!r}; expected one of {VERDICTS}")
        if severity is not None and severity not in SEVERITIES:
            raise ValueError(f"unknown severity {severity!r}; expected one of {SEVERITIES}")
        if verdict == "DEFERRED" and not note:
            raise ValueError("DEFERRED requires a note justifying why it was not attempted")

        self._seq += 1
        record: dict[str, Any] = {
            "seq": self._seq,
            "ts": iso(),
            "segment": segment,
            "verdict": verdict,
            "surface": surface,
        }
        if instruction_ref:
            record["instructionRef"] = instruction_ref
        if instruction_text:
            record["instructionText"] = instruction_text.strip()
        if action:
            record["action"] = action
        if expected is not None:
            record["expected"] = expected
        if observed is not None:
            record["observed"] = observed
        if images:
            record["images"] = [self._rel(p) for p in images]
        if severity:
            record["severity"] = severity
        if note:
            record["note"] = note
        record.update(extra)

        record = self.redactor.scrub(record)
        with self.trace_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def heartbeat(
        self,
        segment: str,
        *,
        operation: str,
        elapsed_s: float,
        probe: str | None = None,
        detail: dict | None = None,
        images: list[Path | str] | None = None,
    ) -> dict:
        """Record liveness during a long-running operation.

        Heartbeats keep a long wait visible in the trace and make a crash
        mid-wait resumable rather than opaque. They are tagged so reports can
        exclude them from step counts.

        `detail` carries whatever the probe is measuring. Without it a probe
        that waits out its whole budget leaves no evidence of *why*, and the
        only way to tell a stuck lab from a broken probe is to run it again
        and watch.
        """
        return self.step(
            segment,
            verdict="PASS",
            action=f"heartbeat:{operation}",
            surface="probe",
            images=images,
            kind="heartbeat",
            elapsedS=round(elapsed_s, 1),
            **({"probe": probe} if probe else {}),
            **({"detail": detail} if detail else {}),
        )

    def retract(self, seq: int, reason: str) -> dict:
        """Withdraw an earlier judgement, keeping both records.

        Judgements get recorded before their cause is always understood, and
        some later turn out to be the harness misreading the lab. Deleting the
        record would be the tidy option and the wrong one: the trace is
        evidence, and a report that quietly loses entries cannot be audited.
        Appending a retraction keeps the original visible while removing it
        from the report, with the reason attached.

        Both directions are retractable. A wrong ``PASS`` is as damaging as a
        wrong finding -- it claims an instruction was verified correct when it
        was not -- so confirmations can be withdrawn too. Mechanical steps
        (clicks, screenshots) carry no claim and so cannot be retracted.
        """
        target = next((s for s in self.steps() if s.get("seq") == seq), None)
        if target is None:
            raise ValueError(f"No step with seq {seq} to retract")
        if not _is_judgement(target):
            raise ValueError(
                f"seq {seq} has verdict {target.get('verdict')!r} on surface "
                f"{target.get('surface')!r}, which carries no judgement to retract"
            )
        return self.step(
            target.get("segment", ""),
            verdict="PASS",
            action=f"retract:{seq}",
            surface="report",
            note=reason,
            kind="retraction",
            retracts=seq,
        )

    def retracted(self) -> set[int]:
        return {
            int(s["retracts"])
            for s in self.steps()
            if s.get("kind") == "retraction" and s.get("retracts") is not None
        }

    def event(self, kind: str, detail: str, **extra: Any) -> None:
        """Record a run-level event in the manifest (credential refresh, resume)."""
        self.manifest.setdefault("events", []).append(
            self.redactor.scrub({"ts": iso(), "kind": kind, "detail": detail, **extra})
        )
        self._save()
        self.log(f"[{kind}] {detail}")

    # ---- segments -------------------------------------------------------

    def set_segments(self, segments: list[Segment]) -> None:
        known = {s["id"]: s for s in self.manifest.get("segments", [])}
        merged = []
        for seg in segments:
            data = seg.to_dict()
            # Preserve progress already recorded for this segment on resume.
            data.update(
                {
                    k: v
                    for k, v in known.get(seg.id, {}).items()
                    if k in {"status", "started", "ended", "note"}
                }
            )
            merged.append(data)
        self.manifest["segments"] = merged
        self._save()

    def segment(self, segment_id: str) -> dict | None:
        for seg in self.manifest.get("segments", []):
            if seg["id"] == segment_id:
                return seg
        return None

    def segments(self) -> list[Segment]:
        """Manifest segments as typed objects.

        Goes through :meth:`Segment.from_dict`, which is what lets a run folder
        written by an older version still be read: the manifest is evidence, and
        evidence has to stay readable across renames.
        """
        return [Segment.from_dict(s) for s in self.manifest.get("segments", [])]

    def resolve_segment(self, segment_id: str) -> str:
        """Map a user-supplied segment id onto a real one, or refuse.

        A mistyped id used to be accepted silently, inventing a phantom segment
        and leaving the real one marked "not reached" -- coverage the report
        would then understate. Accept an exact id, or an unambiguous prefix so
        "s03" is enough, and fail loudly on anything else.
        """
        ids = [seg["id"] for seg in self.manifest.get("segments", [])]
        if segment_id in ids:
            return segment_id
        hits = [i for i in ids if i.startswith(segment_id)]
        if len(hits) == 1:
            return hits[0]
        if not hits:
            raise KeyError(f"unknown segment {segment_id!r}; known ids: {', '.join(ids)}")
        raise KeyError(f"ambiguous segment {segment_id!r}; matches: {', '.join(hits)}")

    def start_segment(self, segment_id: str, lab_minutes: int | None = None) -> None:
        seg = self.segment(segment_id)
        if seg is None:
            seg = {"id": segment_id, "title": segment_id}
            self.manifest.setdefault("segments", []).append(seg)
        seg.update(status="in_progress", started=iso())
        if lab_minutes is not None:
            seg["lab_minutes_at_start"] = lab_minutes
        self._save()
        self.log(f"segment {segment_id}: start (lab minutes left: {lab_minutes})")

    def end_segment(
        self,
        segment_id: str,
        status: str = "done",
        lab_minutes: int | None = None,
        note: str | None = None,
    ) -> None:
        seg = self.segment(segment_id) or {}
        seg.update(status=status, ended=iso())
        if lab_minutes is not None:
            seg["lab_minutes_at_end"] = lab_minutes
        if note:
            seg["note"] = note
        self._save()
        self.log(f"segment {segment_id}: {status}")

    def pending_segments(self) -> list[dict]:
        return [
            s
            for s in self.manifest.get("segments", [])
            if s.get("status") in (None, "pending", "in_progress")
        ]

    # ---- reading --------------------------------------------------------

    def steps(self) -> Iterator[dict]:
        if not self.trace_path.exists():
            return
        with self.trace_path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def findings(self) -> list[dict]:
        """Findings that still stand - retracted ones stay in the trace only."""
        gone = self.retracted()
        return [
            s
            for s in self.steps()
            if s.get("verdict") in FINDING_VERDICTS and s.get("seq") not in gone
        ]

    def summary(self) -> dict:
        """Verdict counts, excluding heartbeats, plus segment coverage."""
        counts: dict[str, int] = {}
        beats = 0
        for step in self.steps():
            if step.get("kind") == "heartbeat":
                beats += 1
                continue
            counts[step["verdict"]] = counts.get(step["verdict"], 0) + 1
        segments = self.manifest.get("segments", [])
        return {
            "steps": sum(counts.values()),
            "heartbeats": beats,
            "verdicts": counts,
            "segments": {
                "total": len(segments),
                "done": sum(1 for s in segments if s.get("status") == "done"),
                "blocked": sum(1 for s in segments if s.get("status") == "blocked"),
                "never_reached": [
                    s["id"] for s in segments if s.get("status") in (None, "pending")
                ],
            },
        }

    # ---- internals ------------------------------------------------------

    def _rel(self, path: Path | str) -> str:
        path = Path(path)
        try:
            return path.resolve().relative_to(self.dir.resolve()).as_posix()
        except ValueError:
            return path.as_posix()

    def _save(self) -> None:
        self.manifest_path.write_text(
            json.dumps(self.manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def _corpus_info(corpus: Path | None) -> dict | None:
    """Hash the instruction corpus so a run states exactly what it validated.

    Without this a drift report cannot distinguish "the product changed" from
    "the lab author rewrote the instructions", which are opposite conclusions.
    """
    if corpus is None:
        return None
    corpus = Path(corpus)
    if not corpus.exists():
        return {"path": corpus.as_posix(), "missing": True}
    data = corpus.read_bytes()
    return {
        "path": corpus.as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": data.count(b"\n") + 1,
    }
