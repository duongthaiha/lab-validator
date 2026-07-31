"""The learner's path: which channel may be used for which act, and what it costs.

The engine reads instructions through ``window.api.v1`` paging because it is
faster and exact. A learner scrolls. If the instruction pane's scroll were
broken, today's walk would sail past it and report a clean section -- and that
is the shape of every blind spot this module is about: *the validator succeeded
by a route the learner does not have.*

The naive fix -- ban the API -- is wrong twice. Some API calls are the only
honest way to observe something (how many minutes remain, what the environment
believes its own state is), and one of them, sending keystrokes to the remote
desktop, **is** the learner's input path rather than a way around it. A rule
that forbade those would trade a real blind spot for a slower, more fragile
walk and no extra coverage.

So the rule is narrower and, being narrower, is actually enforceable:

    On a surface the learner operates by hand, an action performed through the
    API is a **bypass**. Bypasses are allowed -- they are often the only way to
    finish -- but each one is a hole in the coverage claim, and must be recorded
    as loudly as a failure.

That last clause is the whole point. This module does not stop anything. It
makes the report able to say *"section 4 was completed, but the instruction
pane's own navigation was never exercised, so a defect in it would not have been
found"* -- which is a true and useful sentence, and one no run could previously
produce.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

__all__ = [
    "Capability",
    "Ledger",
    "CAPABILITIES",
    "ACTION_CAPABILITY",
    "is_bypass",
    "classify",
]

#: Where the act lands.
#:
#: ``vm``          the remote desktop. Input reaches it as keystrokes and mouse
#:                 events whatever we do, so the API is the input path, not a
#:                 way around it.
#: ``labui``       the lab client's own chrome -- instruction pane, Resources
#:                 tab, page controls. The learner clicks these. Anything we do
#:                 here without clicking is a surface we did not test.
#: ``bookkeeping`` neither: run state, clocks, metadata the learner never sees.
SURFACES = ("vm", "labui", "bookkeeping")

#: How we did it. ``control`` = a visible affordance a learner could use.
CHANNELS = ("control", "api", "dom")


@dataclass(frozen=True)
class Capability:
    """One thing the engine can do, and what using it does to the coverage claim.

    ``covered_by`` names the control-channel capability that would have tested
    the same surface. It is what makes a bypass *closeable* rather than a
    permanent complaint: use the API to get on with the walk, exercise the
    control once somewhere, and the hole is gone. A bypass with no ``covered_by``
    is a hole nothing in the engine can currently close -- worth knowing, and
    worth a test that says so out loud.
    """

    name: str
    surface: str
    channel: str
    acts: bool
    note: str = ""
    covered_by: str | None = None

    def __post_init__(self) -> None:
        if self.surface not in SURFACES:
            raise ValueError(f"{self.name}: unknown surface {self.surface!r}")
        if self.channel not in CHANNELS:
            raise ValueError(f"{self.name}: unknown channel {self.channel!r}")


def _cap(name, surface, channel, acts, note="", covered_by=None):
    return Capability(name=name, surface=surface, channel=channel, acts=acts,
                      note=note, covered_by=covered_by)


#: Every engine capability, classified. This table is the rule; the functions
#: below only read it. Adding a capability without classifying it is caught by a
#: test, because an unclassified capability is one whose coverage cost nobody
#: considered.
CAPABILITIES: dict[str, Capability] = {
    c.name: c
    for c in (
        # -- VM input. Through the API, and legitimately so: keystrokes and
        # mouse events are what a learner produces, and this is how they travel.
        _cap("click", "vm", "api", True, "mouse event to the remote desktop"),
        _cap("move", "vm", "api", True, "mouse event to the remote desktop"),
        _cap("wheel", "vm", "api", True, "scroll event to the remote desktop"),
        _cap("type", "vm", "api", True, "keystrokes to the remote desktop"),
        _cap("key", "vm", "api", True, "keystrokes to the remote desktop"),
        _cap("focus_vm", "vm", "control", True, "clicks the console to take focus"),
        # -- VM observation.
        _cap("screen", "vm", "api", False, "framebuffer capture"),
        _cap("screen_bytes", "vm", "api", False, "framebuffer capture"),
        _cap("resolution", "vm", "api", False),
        _cap("connection_status", "vm", "api", False),
        # -- Lab UI, through its own controls. The learner's path.
        _cap("show_instructions", "labui", "control", True, "clicks the tab"),
        _cap("scroll_instructions", "labui", "control", True,
             "a real wheel event on the pane, the way a learner reads it"),
        _cap("type_credential_natively", "labui", "control", True,
             "clicks the Resources-tab affordance, so the replay is the lab's own"),
        _cap("dismiss_dialog", "labui", "control", True, "clicks the dialog button"),
        # -- Lab UI, around its controls. Each of these is a bypass.
        _cap("goto_page", "labui", "api", True,
             "pages the instruction pane without touching its navigation",
             covered_by="scroll_instructions"),
        _cap("instructions_text", "labui", "api", False,
             "reads the pane without scrolling it"),
        _cap("credentials", "labui", "dom", False,
             "scrapes the Resources tab rather than reading it as rendered"),
        # -- Bookkeeping. Invisible to the learner; no coverage claim attaches.
        _cap("minutes_remaining", "bookkeeping", "api", False),
        _cap("page_index", "bookkeeping", "api", False),
        _cap("instance_id", "bookkeeping", "api", False),
    )
}


#: ``lab_step.py`` verb -> capability. One table rather than a ``record()`` call
#: sprinkled through the action loop, so a new verb that forgets to declare
#: itself is caught by a test instead of quietly costing coverage nobody notices.
#: ``None`` means the verb touches neither the lab nor the VM.
ACTION_CAPABILITY: dict[str, str | None] = {
    "click": "click",
    "dblclick": "click",
    "move": "move",
    "scroll": "wheel",
    "focus": "focus_vm",
    "type": "type",
    "cred": "type",
    "key": "key",
    "page": "goto_page",
    "read": "scroll_instructions",
    "shot": "screen",
    "dialog": "dismiss_dialog",
    "wait": None,
    "until": None,
}


def is_bypass(capability: str) -> bool:
    """Did this route around a control the learner has to use?

    True only for an **action** on the **lab's own UI** through something other
    than a visible control. Observation is not a bypass -- looking at a pane
    without scrolling it claims nothing about the scroll. VM input is not a
    bypass -- there is no control being skipped.
    """
    cap = CAPABILITIES.get(capability)
    if cap is None:
        raise KeyError(
            f"{capability!r} is not classified. Every capability has to declare what "
            "using it costs the coverage claim, or the report quietly overstates itself."
        )
    return cap.acts and cap.surface == "labui" and cap.channel != "control"


def classify(capability: str) -> Capability:
    cap = CAPABILITIES.get(capability)
    if cap is None:
        raise KeyError(f"{capability!r} is not classified")
    return cap


@dataclass
class Ledger:
    """What the walk exercised, and what it therefore cannot vouch for.

    Deliberately additive and never fatal. A walk that bypasses everything still
    finishes and still reports; it just cannot claim the lab's own UI works, and
    this is what stops it claiming that by omission.
    """

    used: dict[str, int] = field(default_factory=dict)
    bypassed: dict[str, int] = field(default_factory=dict)

    def record(self, capability: str) -> None:
        self.used[capability] = self.used.get(capability, 0) + 1
        if is_bypass(capability):
            self.bypassed[capability] = self.bypassed.get(capability, 0) + 1

    def record_action(self, verb: str) -> None:
        """Record a ``lab_step.py`` verb. Unknown verbs are an error, not a no-op."""
        if verb not in ACTION_CAPABILITY:
            raise KeyError(
                f"action {verb!r} does not declare a capability. Add it to "
                "learnerpath.ACTION_CAPABILITY -- silently skipping it would let a "
                "new bypass appear without ever showing up in the coverage claim."
            )
        capability = ACTION_CAPABILITY[verb]
        if capability is not None:
            self.record(capability)

    # ---- persistence ----------------------------------------------------
    #
    # A ledger has to survive between steps, because a walk is many separate
    # process invocations and the coverage claim is about the whole run. It
    # holds counts of capability names -- no secrets, ever -- so unlike the
    # vault it needs no location guard.

    FILE = "coverage.json"

    @classmethod
    def load(cls, run_dir) -> Ledger:
        """Never fails. A missing or corrupt ledger starts empty rather than
        ending the run -- bookkeeping that can refuse to load is bookkeeping
        that fails exactly when the run is already in trouble."""
        path = Path(run_dir) / cls.FILE
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return cls(used=dict(data.get("used", {})), bypassed=dict(data.get("bypassed", {})))
        except (OSError, ValueError, TypeError):
            return cls()

    def save(self, run_dir) -> Path:
        path = Path(run_dir) / self.FILE
        path.write_text(
            json.dumps({"used": self.used, "bypassed": self.bypassed}, indent=2),
            encoding="utf-8",
        )
        return path

    @property
    def clean(self) -> bool:
        return not self.bypassed

    def untested_surfaces(self) -> list[str]:
        """Controls that were bypassed and never exercised for real.

        A bypass costs nothing if the control it skipped was *also* used at some
        point during the walk -- the control was exercised, so a defect in it
        would have shown up, and the API route was merely a shortcut. Only a
        control that was never used at all is a hole.

        The pairing is per-capability, not per-surface. Clicking the Instructions
        tab does not exercise the instruction pane's *pager*, so it must not be
        allowed to close that hole; the only thing that closes it is the control
        the capability nominates.
        """
        holes = []
        for name in sorted(self.bypassed):
            cap = CAPABILITIES[name]
            if cap.covered_by and self.used.get(cap.covered_by):
                continue
            note = cap.note or name
            if cap.covered_by:
                holes.append(f"{name} — {note} (use `{cap.covered_by}` to close this)")
            else:
                holes.append(f"{name} — {note} (nothing in the engine tests this yet)")
        return holes

    def to_markdown(self) -> str:
        out = ["### Interaction coverage", ""]
        if not self.used:
            return "\n".join(out + ["Nothing was recorded.", ""])
        if self.clean:
            out += [
                "Every action went through a control the learner has, so a defect in "
                "the lab's own UI would have been hit.",
                "",
            ]
            return "\n".join(out)
        total = sum(self.bypassed.values())
        out += [
            f"{total} action(s) routed around a control the learner has to use. "
            "Those controls were therefore **not tested**, and a defect in them "
            "would not have been found by this run:",
            "",
        ]
        out += [f"- {hole}" for hole in self.untested_surfaces()]
        out += ["", "This is a coverage limit, not a defect in the lab.", ""]
        return "\n".join(out)
