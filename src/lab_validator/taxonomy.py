"""The verdict taxonomy: what a finding can be, and which side is at fault.

This module is the single source of truth for verdict codes. It exists because
they previously lived in three places that disagreed: :mod:`runlog` accepted
``LAB009``, :mod:`report` had no name for it, and no document defined it at all.
Forty findings -- the second-largest category in run 005 -- rendered as a bare
code with no human-readable name. The taxonomy is the public interface of the
whole capability, so a disagreement here is not cosmetic.

Two axes describe a finding, and they are deliberately independent:

**The code** says *what kind of wrong* it is -- a retired model, a moved menu, a
broken link.

**The domain** says *which side is wrong*, and therefore who fixes it:

``instruction``
    The text is wrong. The environment is fine. The lab author edits words.
``setup``
    The text is right but the lab cannot deliver it -- a resource was never
    provisioned, the shipped config is wrong, the image serves something other
    than what it claims. The lab profile or image owner fixes the environment.
``undetermined``
    Not yet established. A first-class and respectable answer, but it must name
    the evidence that would settle it.

The two axes are independent because the *same code* falls either way. A
missing resource is a setup defect if the lab was supposed to provision it, and
an instruction defect if the text names a SKU that never existed. Guessing is
worse than not knowing: a defect attributed to the wrong owner is correctly
rejected by that owner, and then it dies. Ruling out quota, region and
transience took a deliberate experiment for ``G-08``; that is the standard.

Orientation
-----------
Role:     the verdict codes and the instruction/setup axis every finding is filed under.
Entry:    `VERDICTS`, `BY_CODE`, `default_severity`, `undocumented_codes`
Talks to: nothing
"""

from __future__ import annotations

from dataclasses import dataclass

#: Which side of the lab is at fault. ``undetermined`` is not a failure to try;
#: it is the honest answer until an experiment distinguishes the two, and it
#: carries the evidence that would settle it.
DOMAINS = ("instruction", "setup", "undetermined")

SEVERITIES = ("critical", "major", "minor", "info")


@dataclass(frozen=True)
class Verdict:
    """One terminal verdict a step can carry."""

    code: str
    name: str
    definition: str
    #: Where the fault usually lies. Only a starting point -- the finding's own
    #: ``domain`` field carries the truth, established by evidence. ``either``
    #: means the code genuinely falls both ways and must always be established.
    typical_domain: str
    #: Severity to assume when the caller does not say. Always a starting point:
    #: a broken link is minor unless it is the only route to the lab's files.
    default_severity: str | None
    is_finding: bool

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.code} {self.name}"


_VERDICTS: tuple[Verdict, ...] = (
    Verdict(
        "PASS",
        "Verified correct",
        "The instruction was followed and the product behaved as described. "
        "As important as any failure code: a differ with no positive evidence "
        "cannot tell 'verified correct' from 'never reached'.",
        "instruction",
        None,
        False,
    ),
    Verdict(
        "LAB000",
        "Environment transient",
        "A failure that did not reproduce, or that resolved on retry. Recorded "
        "so the trace stays honest, never reported as a finding.",
        "setup",
        None,
        False,
    ),
    Verdict(
        "LAB001",
        "Retired or renamed model",
        "A model the instructions name cannot be used. An instruction defect "
        "when the text names a model that is gone; a setup defect when the "
        "model is alive but this subscription or region refuses it.",
        "either",
        "major",
        True,
    ),
    Verdict(
        "LAB002",
        "Missing resource or SKU",
        "Something the learner is told to find is not there. An instruction "
        "defect when the text names a SKU that never existed; a setup defect "
        "when the lab was supposed to provision it and did not.",
        "either",
        "major",
        True,
    ),
    Verdict(
        "LAB003",
        "Changed UI label or inconsistent structure",
        "The control exists but is not called what the instructions call it, "
        "or the instructions contradict themselves.",
        "instruction",
        "minor",
        True,
    ),
    Verdict(
        "LAB004",
        "Moved navigation",
        "The destination exists but is not reached the way the instructions "
        "describe.",
        "instruction",
        "minor",
        True,
    ),
    Verdict(
        "LAB005",
        "Removed feature",
        "A capability the instructions depend on no longer exists in the "
        "product at all.",
        "instruction",
        "major",
        True,
    ),
    Verdict(
        "LAB006",
        "Broken link",
        "A URL the instructions offer does not resolve, or resolves to "
        "something other than what it promises.",
        "instruction",
        "minor",
        True,
    ),
    Verdict(
        "LAB007",
        "Timing or quota",
        "The step cannot complete in the time or capacity available -- "
        "including 'this never finishes'. Usually the environment, not the "
        "text, unless the text promises a duration it cannot honour.",
        "setup",
        "major",
        True,
    ),
    Verdict(
        "LAB008",
        "Undocumented mandatory step",
        "Something the learner must do to proceed that the instructions never "
        "mention. Found by doing the lab, never by reading it.",
        "instruction",
        "major",
        True,
    ),
    Verdict(
        "LAB009",
        "Defective sample code",
        "Code or configuration shipped with the lab is wrong -- it swallows "
        "failure, produces no output, or reports success having done nothing. "
        "The most dangerous class, because it hides every other defect from "
        "the learner.",
        "either",
        "major",
        True,
    ),
    Verdict(
        "LAB010",
        "Superseded or retiring feature",
        "The instructions teach a path the product has moved on from -- a "
        "'classic' experience, a superseded API version, a feature with an "
        "announced retirement. Unique among the codes in that the step "
        "*succeeds*: it is a defect with a deadline rather than a defect today, "
        "and the only one that has to be looked for rather than tripped over. "
        "An instruction defect, because the newer path working here is what "
        "makes the older one superseded; if the environment cannot offer the "
        "newer path, that is LAB002 or LAB007 instead.",
        "instruction",
        "info",
        True,
    ),
    Verdict(
        "BLOCKED",
        "Could not be attempted",
        "A dependency failed, so this was never reached. A status, not a "
        "finding: the blocker itself is the finding, and the walk should carry "
        "on reading rather than stop here.",
        "undetermined",
        None,
        False,
    ),
    Verdict(
        "DEFERRED",
        "Deliberately not attempted",
        "Skipped on purpose, and requires a justification that survives "
        "review. Distinct from BLOCKED: nothing prevented it.",
        "undetermined",
        None,
        False,
    ),
)

BY_CODE: dict[str, Verdict] = {v.code: v for v in _VERDICTS}

#: Terminal verdicts for a step, in taxonomy order.
VERDICTS: tuple[str, ...] = tuple(v.code for v in _VERDICTS)

#: Verdicts that represent a real, learner-facing defect. Derived from the
#: table rather than by slicing, so adding a code cannot silently drop the
#: last one out of the finding set.
FINDING_VERDICTS = frozenset(v.code for v in _VERDICTS if v.is_finding)

#: Human-readable name per code, for report rendering.
CODE_NAMES: dict[str, str] = {v.code: v.name for v in _VERDICTS}


def name_of(code: str) -> str:
    """Human name for a code, falling back to the code itself.

    The fallback is why ``LAB009`` rendered as ``LAB009`` for forty findings
    instead of failing loudly. :func:`undocumented_codes` is the guard.
    """
    verdict = BY_CODE.get(code)
    return verdict.name if verdict else code


def default_severity(code: str) -> str | None:
    verdict = BY_CODE.get(code)
    return verdict.default_severity if verdict else None


def undocumented_codes(codes: frozenset[str] | set[str]) -> set[str]:
    """Codes that are accepted somewhere but carry no usable documentation.

    A finding code without a name renders as a bare code; without a definition
    nobody can tell whether it was applied correctly. Both are silent failures,
    so a test asserts this is empty rather than trusting review to catch it.
    """
    missing = set()
    for code in codes:
        verdict = BY_CODE.get(code)
        if verdict is None or not verdict.name or not verdict.definition:
            missing.add(code)
        elif verdict.is_finding and verdict.default_severity is None:
            missing.add(code)
    return missing
