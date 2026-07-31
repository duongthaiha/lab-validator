"""Lab-issued credentials, captured once at launch and reused for the whole run.

The lab hands the learner a Resources tab full of credentials -- a subscription
id, a portal username and password, endpoints, keys -- and the instructions then
refer back to it for hours. Reading them fresh from the DOM every time costs a
tab switch, depends on the pane still being reachable, and yields nothing but
keystrokes: there is no way to use a credential as *data*.

That last point is the expensive one. The most damaging defects in the corpus so
far were **setup** defects that could only be caught by comparing what the lab
*hands out* against what the lab *ships*:

* a shipped ``.env`` whose endpoint was a valid URL of the wrong kind, and
* deployments named after one model that served another.

Neither is visible in the lab text. Both are trivially visible if the handed-out
values are structured data you can compare against. So the vault captures once,
keeps the rows, and classifies them by shape.

Secrets position
----------------
These are ephemeral credentials scoped to a throwaway subscription, handed *to*
the agent by the lab itself. That is categorically different from the operator's
own Learning Campus password, which this project still never stores.

Capturing them **improves** safety rather than weakening it: the run's redactor
can only mask values it already knows, so capturing everything up front is
precisely what makes masking exact -- and it happens before any step has had a
chance to leak one.

The residual risk is unchanged and worth restating: **screenshots are pixels and
the redactor is text-only.** A key visible on screen is captured as an image no
text filter can reach. That is why ``runs/`` is gitignored and why :meth:`save`
refuses to write anywhere else.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from .labclient import Credential
from .runlog import utc_now

__all__ = ["Vault", "VaultError", "classify", "ROLES", "role_of"]

_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)
_URL = re.compile(r"^https?://", re.I)
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

#: Which sign-in a credential belongs to, keyed by words that appear in the
#: *scope* the lab itself printed on its Resources tab.
#:
#: This table exists so that "which credential does this login want" stops being
#: a judgement call. A lab commonly issues two username/password pairs -- one for
#: the Windows machine, one for the cloud portal -- and they are not
#: interchangeable. Asked to "sign in to the Azure portal" while looking at a
#: Windows sign-in screen, a model reaches for the portal credential, because
#: that is what the task is called. The password is rejected, the rejection looks
#: like a broken lab, and the walk reports a defect that does not exist.
#:
#: Matching is on the scope the environment wrote, never on a name derived from
#: the instructions -- the same rule the ask-matcher follows, for the same
#: reason. A scope matching two roles, or none, is not resolved: see
#: :func:`role_of`.
ROLES: dict[str, tuple[str, ...]] = {
    "vm": ("machine", "virtual machine", "vm", "rdp", "remote desktop", "computer", "windows"),
    "portal": ("azure", "portal", "entra", "office", "microsoft 365", "m365", "tenant"),
}

#: Labels that identify the two halves of a sign-in, in preference order. A lab
#: that calls it "User name" or "Login" is naming the same thing.
ROLE_FIELDS: dict[str, tuple[str, ...]] = {
    "username": ("username", "user name", "user", "login", "account", "email"),
    "password": ("password", "pass", "pwd"),
}


def role_of(scope: str) -> str | None:
    """Which sign-in this credential scope belongs to, or ``None``.

    ``None`` covers two cases that must both refuse rather than resolve: a scope
    naming no known role, and a scope naming more than one. "Azure VM
    credentials" matches both tables, and picking either would be a guess with a
    plausible-looking wrong answer.
    """
    lowered = scope.lower()
    hits = {role for role, words in ROLES.items() if any(w in lowered for w in words)}
    return hits.pop() if len(hits) == 1 else None

#: Values below this length are words, not secrets, and masking them would
#: corrupt ordinary prose in the trace. Mirrors ``runlog.Redactor``.
MIN_SECRET_LEN = 6


class VaultError(Exception):
    """A credential was asked for that the lab did not hand out."""


def classify(value: str) -> str:
    """What *shape* is this value? ``guid`` | ``url`` | ``email`` | ``text``.

    Shape is what makes a setup preflight possible. "The endpoint is a URL" is
    not enough -- an Azure OpenAI *operation* URL and a *base* URL are both
    valid URLs, and shipping one where the other is required broke five labs
    without a single line of the instructions being wrong. Classifying by shape
    is the first step; the preflight then checks the *kind* within the shape.
    """
    v = value.strip()
    if _GUID.match(v):
        return "guid"
    if _URL.match(v):
        return "url"
    if _EMAIL.match(v):
        return "email"
    return "text"


@dataclass(frozen=True)
class Vault:
    """Every credential the lab handed out, as structured rows."""

    credentials: tuple[Credential, ...]
    captured_utc: str

    # ---- capture --------------------------------------------------------

    @classmethod
    def capture(cls, credentials: list[Credential], redactor=None) -> Vault:
        """Take the Resources tab as it stood at launch.

        Registering with the redactor happens here rather than at the call site
        so the two can never drift apart: there is no way to capture a
        credential into the vault without also teaching the writer to mask it.
        """
        rows = tuple(credentials)
        if redactor is not None:
            for c in rows:
                if len(c.value) >= MIN_SECRET_LEN:
                    redactor.add(c.value, c.label)
        return cls(
            credentials=rows,
            captured_utc=utc_now().strftime("%Y-%m-%dT%H:%M:%SZ"),
        )

    # ---- lookup ---------------------------------------------------------

    def find(self, label: str, scope: str | None = None) -> Credential | None:
        """Case-insensitive lookup, optionally narrowed by scope.

        Label first, exactly as :mod:`labclient` does; then a contains-match,
        because instructions name credentials loosely ("your Azure username")
        and an exact-only lookup fails on wording rather than on substance.
        """
        exact, loose = self._pools(label, scope)
        if exact:
            return exact[0] if len(exact) == 1 else None
        return loose[0] if len(loose) == 1 else None

    def _pools(
        self, label: str, scope: str | None = None
    ) -> tuple[list[Credential], list[Credential]]:
        """Every exact and every loose match, in capture order.

        Split out so ambiguity is *visible* to the caller. The old lookup took
        the first exact match and returned it, which meant a lab issuing both an
        "Azure Portal / Password" and a "Machine credentials / Password"
        resolved a bare ``password`` to whichever the Resources tab happened to
        list first. That is selecting by position, and its wrong answer is
        indistinguishable from its right one: a secret gets typed, the login
        fails, and the failure reads as a defect in the lab.
        """
        wanted = label.strip().lower()
        pool = [
            c
            for c in self.credentials
            if scope is None or scope.strip().lower() in c.scope.lower()
        ]
        return (
            [c for c in pool if c.label.lower() == wanted],
            [c for c in pool if wanted in c.label.lower()],
        )

    def candidates(self, label: str, scope: str | None = None) -> list[str]:
        """The ``Scope/Label`` refs a loose lookup cannot choose between."""
        exact, loose = self._pools(label, scope)
        return [f"{c.scope}/{c.label}" for c in (exact or loose)]

    # ---- sign-ins, bound mechanically -----------------------------------

    def roles(self) -> dict[str, list[Credential]]:
        """Every credential grouped by the sign-in it belongs to."""
        out: dict[str, list[Credential]] = {}
        for c in self.credentials:
            if role := role_of(c.scope):
                out.setdefault(role, []).append(c)
        return out

    def signin(self, role: str) -> tuple[Credential, Credential]:
        """The username and password for one sign-in. Never a choice.

        This is the whole point of the role table. A caller says *which login*
        -- ``vm`` or ``portal`` -- and the pair comes back resolved from the
        scope the lab printed. There is no parameter through which the wrong
        credential can be requested, because deciding between two password rows
        by reading a task title is precisely the mistake this prevents.

        Raises rather than falling back. A sign-in with half a credential pair
        types a username into a password box, and the login failure that follows
        is indistinguishable from a lab whose credentials do not work.
        """
        if role not in ROLES:
            raise VaultError(f"Unknown sign-in {role!r}. Known: {', '.join(sorted(ROLES))}")
        pool = self.roles().get(role) or []
        if not pool:
            known = ", ".join(sorted(self.roles())) or "none"
            raise VaultError(
                f"This lab issued no {role!r} credentials. Scopes that did resolve: "
                f"{known}. Everything handed out: {self.summary() or 'nothing'}"
            )
        found: dict[str, Credential] = {}
        for field, words in ROLE_FIELDS.items():
            for word in words:
                hits = [c for c in pool if word in c.label.lower()]
                if len(hits) == 1:
                    found[field] = hits[0]
                    break
                if len(hits) > 1:
                    raise VaultError(
                        f"The {role!r} sign-in has {len(hits)} credentials matching "
                        f"{field!r}: {', '.join(f'{c.scope}/{c.label}' for c in hits)}. "
                        "Refusing to choose."
                    )
        missing = [f for f in ROLE_FIELDS if f not in found]
        if missing:
            have = ", ".join(f"{c.scope}/{c.label}" for c in pool)
            raise VaultError(
                f"The {role!r} sign-in is missing its {' and '.join(missing)}. "
                f"That scope only carries: {have}"
            )
        return found["username"], found["password"]

    def value(self, ref: str) -> str:
        """Resolve ``"Scope/Label"`` or ``"Label"`` to the verbatim secret.

        Raises rather than returning ``None``: a missing credential silently
        becoming an empty string is how an agent types nothing into a password
        box and then reports a login defect that is entirely its own.
        """
        scope, _, label = ref.rpartition("/")
        # A role ref -- "vm/password", "portal/username" -- names the *sign-in*
        # rather than the scope the lab happened to print, and resolves through
        # the role table. Checked before the scope lookup and matched exactly,
        # because "portal" is also a substring of "Azure Portal" and a ref that
        # sometimes means the role and sometimes means the scope would be worse
        # than either.
        if scope.lower() in ROLES and label.lower() in ROLE_FIELDS:
            username, password = self.signin(scope.lower())
            return username.value if label.lower() == "username" else password.value
        match = self.find(label, scope or None)
        if match is not None:
            return match.value
        rivals = self.candidates(label, scope or None)
        if len(rivals) > 1:
            raise VaultError(
                f"{ref!r} is ambiguous: this lab issued {len(rivals)} credentials "
                f"labelled that way -- {', '.join(rivals)}. Name the scope. "
                "Guessing types one secret into a box expecting the other, and "
                "the rejection that follows reads as a defect in the lab."
            )
        raise VaultError(
            f"No credential {ref!r} was handed out by this lab. Available: "
            + (self.summary() or "nothing -- the Resources tab was empty")
        )

    def has(self, ref: str) -> bool:
        scope, _, label = ref.rpartition("/")
        return self.find(label, scope or None) is not None

    # ---- as data, not only keystrokes -----------------------------------

    def of_shape(self, shape: str) -> list[Credential]:
        """Every credential whose value has the given shape."""
        return [c for c in self.credentials if classify(c.value) == shape]

    def subscription_id(self) -> str | None:
        """The Azure subscription the lab minted, if it handed one out.

        Matched on **shape and label together**, never on label alone: a lab
        that labels a field "Subscription" and puts a display name in it would
        otherwise produce a subscription "id" that no Azure call accepts, and
        the resulting failures would be blamed on the instructions.
        """
        for c in self.credentials:
            if "subscription" in c.label.lower() and classify(c.value) == "guid":
                return c.value
        return None

    def endpoints(self) -> dict[str, str]:
        """Every URL the lab handed out, keyed ``Scope/Label``.

        This is the left-hand side of the comparison that catches a wrong
        shipped config: what the lab *says* the endpoint is, against what its
        own files contain.
        """
        return {f"{c.scope}/{c.label}": c.value for c in self.of_shape("url")}

    def label_index(self) -> dict[str, tuple[str, ...]]:
        """Lower-cased label -> **every** ``Scope/Label`` reference carrying it.

        The lookup table :func:`asks.asks_in` resolves against. It deliberately
        exposes **labels only**: deciding which credential an instruction wants
        must never require holding the secret, so the matcher never sees one.

        A tuple, not a single ref, because labels are not unique and pretending
        they are destroys the evidence of it. This was a dict comprehension
        keyed on the label, so a lab handing out both an "Azure Portal /
        Password" and a "Machine credentials / Password" silently kept one and
        dropped the other -- last write wins, decided by the order of the
        Resources tab. Two of the eight credentials in the reference workshop
        were unreachable that way, and the two that survived were the wrong ones
        for the first screen the learner meets.
        """
        index: dict[str, list[str]] = {}
        for c in self.credentials:
            index.setdefault(c.label.lower(), []).append(f"{c.scope}/{c.label}")
        return {label: tuple(refs) for label, refs in index.items()}

    def asks_in(self, text: str):
        """Which lab-issued values this instruction text is asking for.

        Convenience join so callers do not have to know that resolution happens
        on labels. An ask that comes back unsatisfied means the text requests
        something this lab never issued -- a finding, not a lookup failure.
        """
        from .asks import asks_in

        return asks_in(text, self.label_index())

    # ---- reporting ------------------------------------------------------

    def redacted_rows(self) -> list[dict]:
        """Safe to print, safe to commit: labels and shapes, never values."""
        return [
            {
                "scope": c.scope,
                "label": c.label,
                "shape": classify(c.value),
                "value": c.redacted(),
            }
            for c in self.credentials
        ]

    def summary(self) -> str:
        return ", ".join(f"{c.scope}/{c.label}" for c in self.credentials)

    def __len__(self) -> int:
        return len(self.credentials)

    # ---- persistence ----------------------------------------------------

    #: The vault holds live secrets, so it may only ever be written inside a run
    #: folder. ``runs/`` is gitignored; nothing else here is guaranteed to be.
    FILENAME = "credentials.json"

    @classmethod
    def path_in(cls, run_dir: Path) -> Path:
        return run_dir / cls.FILENAME

    def save(self, run_dir: Path) -> Path:
        """Persist inside the run folder, and refuse to write anywhere else.

        A guard rather than a convention. "Do not write secrets outside
        ``runs/``" is the kind of rule that holds until someone adds a debug
        flag at 2am, so it is enforced where the write happens.
        """
        run_dir = Path(run_dir)
        if "runs" not in run_dir.resolve().parts:
            raise VaultError(
                f"refusing to write live credentials to {run_dir} -- the vault may only be "
                "written inside runs/, which is the only gitignored evidence tree"
            )
        path = self.path_in(run_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_warning": (
                "LIVE LAB CREDENTIALS. Ephemeral and scoped to a throwaway subscription, "
                "but real until the lab expires. runs/ is gitignored; keep it that way."
            ),
            "capturedUtc": self.captured_utc,
            "credentials": [
                {"scope": c.scope, "label": c.label, "value": c.value}
                for c in self.credentials
            ],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    @classmethod
    def load(cls, run_dir: Path) -> Vault | None:
        """Reopen a vault so a resumed run does not need the lab tab again.

        Returns ``None`` when there is nothing to load, because a run that was
        started before vaults existed is a normal thing to resume, not an error.
        """
        path = cls.path_in(Path(run_dir))
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls(
            credentials=tuple(
                Credential(scope=c["scope"], label=c["label"], value=c["value"])
                for c in data.get("credentials", [])
            ),
            captured_utc=data.get("capturedUtc", ""),
        )
