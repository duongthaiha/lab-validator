"""Recognising when an instruction is *asking* for a lab-issued value.

The engine could already type a named credential into a VM. What it could not do
is notice that it should. An operator read *"sign in with the username and
password from the Resources tab"* and decided; an unattended walk has to make
that decision itself, or it stops at every sign-in prompt and the run dies
waiting for a human who has gone home.

Two things come out of doing this properly, and the second was not the goal.

**Supply.** Which captured value does this sentence want? That turns a blocking
prompt into a lookup.

**A defect detector, for free.** An instruction that asks for a value the
environment never issued is a real defect, and a common one -- the text survives
an edition where the provisioning changed, and now says *"use the Resource Group
from the Resources tab"* about a resource group that is no longer handed out.
The learner reads it, goes looking, finds nothing, and blames themselves. Today
that surfaces as an operator being confused; here it surfaces as
:attr:`Ask.satisfied` being ``False``, with the term quoted.

Deliberately conservative. Every rule below exists to make a *false* ask
impossible, because the cost is asymmetric: a missed ask stops the walk and a
human notices, while an invented one types a credential into whatever happens to
be focused. Prose about a credential is not a request for one, so this matches
only sentences that also carry an instruction cue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = ["Ask", "asks_in", "TERMS", "CUES"]

#: What the instruction calls it -> substrings that identify the credential row.
#: Ordered longest-phrase-first at match time, so "subscription id" is not
#: consumed by "id" and "user name" is not consumed by "name".
TERMS: dict[str, tuple[str, ...]] = {
    "subscription id": ("subscription",),
    "subscription": ("subscription",),
    "resource group": ("resource group",),
    "tenant id": ("tenant", "directory"),
    "directory id": ("tenant", "directory"),
    "api key": ("key",),
    "access key": ("key",),
    "primary key": ("key",),
    "endpoint": ("endpoint", "url"),
    "user name": ("username", "user"),
    "username": ("username", "user"),
    "user id": ("username", "user"),
    "password": ("password",),
    "deployment name": ("deployment",),
    "region": ("region", "location"),
    "location": ("region", "location"),
}

#: An instruction cue. Without one this is prose *about* a credential, not a
#: request for one -- "the password policy requires 12 characters" must never
#: cause anything to be typed.
CUES: tuple[str, ...] = (
    "enter", "type", "paste", "provide", "supply", "input", "fill in",
    "sign in", "signin", "log in", "login", "authenticate",
    "copy the", "use the", "using the", "replace", "set the", "specify",
    "from the resources tab", "on the resources tab", "in the resources tab",
    "from the resource tab", "shown in the resources",
)

#: Cues that reverse the reading. "You do not need to enter a password" is the
#: opposite of an instruction to enter one, and acting on it is destructive.
NEGATIONS: tuple[str, ...] = (
    "do not", "don't", "no need to", "not required", "skip", "leave blank",
    "leave it blank", "without entering", "you will not", "won't need",
)

_SENTENCE = re.compile(r"[^.!?\n]+[.!?]?")


@dataclass(frozen=True)
class Ask:
    """One request for a lab-issued value, found in one sentence.

    ``ref`` is the vault reference to type, or ``None`` when the environment
    never issued anything matching -- which is the finding, not an error.
    """

    term: str
    sentence: str
    ref: str | None = None
    label: str | None = None

    @property
    def satisfied(self) -> bool:
        return self.ref is not None

    def action(self) -> str | None:
        """The ``--do`` action that answers this ask, if it can be answered."""
        return f"cred:{self.ref}" if self.ref else None

    def __str__(self) -> str:
        if self.satisfied:
            return f"{self.term} -> {self.ref}"
        return f"{self.term} -> NOT ISSUED by this lab"


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE.findall(text) if s.strip()]


def _match(term: str, labels: dict[str, str]) -> tuple[str, str] | None:
    """Resolve an instruction's word for a value to an actual captured row.

    Matches on the *label the environment used*, never on a name derived from
    the instruction. The lab calls it "Subscription ID"; the text may call it
    "your subscription"; the mapping between the two is the whole job, and
    guessing it is how you type the wrong secret into the wrong box.
    """
    for needle in TERMS[term]:
        for lowered, ref in labels.items():
            if needle in lowered:
                return ref, lowered
    return None


def asks_in(text: str, labels: dict[str, str] | None = None) -> list[Ask]:
    """Every request for a lab-issued value in ``text``.

    ``labels`` maps a lower-cased credential label to its vault reference; pass
    :meth:`Vault.label_index`. With no labels every ask comes back unsatisfied,
    which is the honest answer -- nothing was captured, so nothing can be
    supplied -- rather than an empty list implying nothing was asked for.

    Duplicates collapse per term, because a section that says "enter the
    password" four times wants one password, not four.
    """
    labels = labels or {}
    found: dict[str, Ask] = {}

    for sentence in _sentences(text):
        lowered = sentence.lower()
        if not any(cue in lowered for cue in CUES):
            continue
        if any(neg in lowered for neg in NEGATIONS):
            continue
        # Longest first: "subscription id" must win over "subscription", and
        # "user name" over "name", or the reference resolves to the wrong row.
        consumed: list[tuple[int, int]] = []
        for term in sorted(TERMS, key=len, reverse=True):
            for hit in re.finditer(rf"\b{re.escape(term)}\b", lowered):
                span = hit.span()
                if any(a <= span[0] and span[1] <= b for a, b in consumed):
                    continue
                consumed.append(span)
                if term in found:
                    continue
                match = _match(term, labels)
                found[term] = Ask(
                    term=term,
                    sentence=sentence,
                    ref=match[0] if match else None,
                    label=match[1] if match else None,
                )
    return list(found.values())
