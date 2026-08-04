"""The setup preflight: check the environment *before* walking it.

The three most damaging findings in the reference workshop were all setup
defects, and all three were found **late and by accident** -- after many
sections had been walked and their failures misattributed to unrelated causes:

* deployments *named* ``gpt-4o`` that actually served a different model;
* a shipped ``.env`` whose endpoint was an *operation* URL where a *base* URL
  was required, which broke five labs;
* notebooks loading that ``.env`` from three different wrong relative paths.

None of them announce themselves. The lab appears to work and then fails
obliquely, in several places at once, each of which reads as an unrelated bug.
That is the argument for a deliberate first pass rather than incidental
discovery: a preflight would have caught all three before section 1, and every
later failure would then have been attributable.

Two design commitments follow from the plan's own risk list.

**A failed preflight does not stop the run.** It sets the completability verdict
and changes what the rest of the walk *means*. Partial runs must stay valuable,
and "blocked" is a status rather than a failure.

**A passing preflight does not mean the setup is correct.** It means *the things
we knew to check* passed. So :class:`Preflight` carries its own coverage and the
report prints it -- an absent finding must never read as a pass.

Everything here is pure: it takes already-captured strings and returns findings.
The live probes (does this deployment serve what it claims? does this resource
exist?) sit above it, so the judgement is testable without a lab.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

from . import taxonomy

#: Every preflight defect is a lab-shipped artefact being wrong, which is
#: exactly what ``LAB009`` covers: "code *or configuration* shipped with the lab
#: is wrong". Bound to the taxonomy rather than spelled as a literal, so a
#: renamed code breaks here loudly instead of drifting quietly -- the failure
#: this repo has now designed against three times.
DEFECT = taxonomy.BY_CODE["LAB009"].code
SETUP = "setup"
assert SETUP in taxonomy.DOMAINS
assert {"critical", "major"} <= set(taxonomy.SEVERITIES)

__all__ = [
    "Check",
    "Preflight",
    "endpoint_kind",
    "shape_of",
    "differs_in",
    "parse_config",
    "check_endpoints",
    "check_shipped_config",
    "check_config_paths",
    "preflight",
    "PLACEHOLDERS",
]

#: Values that mean "nobody filled this in". Matched case-insensitively against
#: the whole value, never as a substring -- "your-resource-name" is a
#: placeholder, but a real key could contain "xxx" by chance.
PLACEHOLDERS = (
    "", "<your-endpoint>", "<your-key>", "your-endpoint", "your-key",
    "your-resource-name", "changeme", "todo", "tbd", "xxx", "xxxxxxxx",
    "<subscription-id>", "your-subscription-id", "none", "null",
)

#: Config keys whose value must be a *base* endpoint. An operation URL parses,
#: resolves and looks right -- and then every SDK call built on it 404s, because
#: the SDK appends its own path. This is the G-71 class.
BASE_URL_KEYS = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_AI_ENDPOINT",
    "AZURE_INFERENCE_ENDPOINT",
    "OPENAI_API_BASE",
    "AZURE_SEARCH_ENDPOINT",
    "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
)

#: Config keys that must hold a GUID.
GUID_KEYS = ("AZURE_SUBSCRIPTION_ID", "AZURE_TENANT_ID", "AZURE_CLIENT_ID")

_GUID = re.compile(r"^[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$")


@dataclass(frozen=True)
class Check:
    """One preflight observation.

    ``verdict``/``domain``/``severity`` line up with the run taxonomy so a check
    can be recorded as a finding without translation. ``evidence`` is what makes
    it arguable -- a preflight finding that says only "endpoint looks wrong"
    will be dismissed, and correctly so.
    """

    name: str
    ok: bool
    detail: str
    verdict: str = "PASS"
    domain: str = SETUP
    severity: str | None = None
    evidence: str = ""

    def __str__(self) -> str:
        mark = "ok  " if self.ok else "FAIL"
        return f"{mark} {self.name}: {self.detail}"


@dataclass
class Preflight:
    """The result of the setup pass, including what it could *not* check.

    ``unchecked`` is not decoration. A preflight that reports only its findings
    invites the reading "the setup is correct", when the truthful claim is much
    narrower: the things we knew to look at were fine. The most damaging defect
    in the reference run was only catchable because somebody thought to ask what
    a deployment actually served -- so the list of unasked questions belongs in
    the output.
    """

    checks: list[Check] = field(default_factory=list)
    unchecked: list[str] = field(default_factory=list)

    @property
    def failures(self) -> list[Check]:
        return [c for c in self.checks if not c.ok]

    @property
    def ok(self) -> bool:
        return not self.failures

    def add(self, check: Check) -> Check:
        self.checks.append(check)
        return check

    def cannot_check(self, reason: str) -> None:
        if reason not in self.unchecked:
            self.unchecked.append(reason)

    def to_markdown(self) -> str:
        out = ["## Setup preflight", ""]
        if not self.checks:
            out += ["Nothing was checked.", ""]
        else:
            verdict = "clean" if self.ok else f"**{len(self.failures)} defect(s)**"
            out += [f"{len(self.checks)} check(s) ran, {verdict}.", ""]
        for check in self.failures:
            out.append(f"- **{check.name}** — {check.detail}")
            if check.evidence:
                out.append(f"  - evidence: `{check.evidence}`")
        if self.failures:
            out.append("")
        passed = [c for c in self.checks if c.ok]
        if passed:
            out += ["<details><summary>Checks that passed</summary>", ""]
            out += [f"- {c.name} — {c.detail}" for c in passed]
            out += ["", "</details>", ""]
        # Deliberately last and never collapsed: this is the part that stops a
        # clean preflight being read as "the setup is correct".
        out += ["### What this preflight did *not* check", ""]
        if self.unchecked:
            out += [f"- {reason}" for reason in self.unchecked]
        else:
            out.append("- Nothing recorded. That is itself suspicious.")
        out += ["", "A passing preflight means *the things we knew to check* passed.", ""]
        return "\n".join(out)


def endpoint_kind(url: str) -> str:
    """``base`` | ``operation`` | ``not-a-url``.

    The distinction that matters and the one nobody looks for. Both forms parse,
    both resolve, and both look right in a config file -- but an SDK given an
    operation URL appends its own path and every call 404s, several labs later,
    in a way that reads as an unrelated bug.
    """
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return "not-a-url"
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return "not-a-url"
    path = parsed.path.strip("/")
    if not path:
        return "base"
    # A bare stage segment ("openai", "v1") is still a base for most SDKs; a
    # path naming a resource or an operation is not.
    return "base" if path in ("openai", "v1", "api") else "operation"


def shape_of(value: str) -> str:
    """Describe a value so that the description **survives redaction**.

    This exists because of a bug found by asking why a passing test passed. The
    preflight's evidence was the credential value itself; every credential is
    registered with the redactor the moment it is captured; so the published
    finding read *"this endpoint is an operation URL — evidence:
    `[REDACTED:Endpoint]`"*. The redactor was doing its job exactly right and the
    finding was still worthless, because a reviewer could neither verify it nor
    act on it without going back to the live lab.

    So evidence must be **structural, not verbatim**. For a URL the defect lives
    entirely in the path -- the host is the identifying part and the path is the
    part that is wrong -- so rendering ``https://<host>/openai/deployments/...``
    keeps the whole argument and discards the secret. It also no longer matches
    the registered value, so the redactor leaves it intact.

    The general rule this encodes: *if masking your evidence destroys your
    finding, you cited the wrong thing.*
    """
    value = value.strip()
    if endpoint_kind(value) != "not-a-url":
        parsed = urlparse(value)
        return f"{parsed.scheme}://<host>{parsed.path or '/'}"
    if not value:
        return "<empty>"
    kinds = []
    if any(c.isdigit() for c in value):
        kinds.append("digits")
    if any(c.isalpha() for c in value):
        kinds.append("letters")
    if any(not c.isalnum() for c in value):
        kinds.append("punctuation")
    return f"<{len(value)} chars, {'+'.join(kinds) or 'unprintable'}>"


def differs_in(shipped: str, issued: str) -> str:
    """Say *which component* of two values disagrees, without printing either.

    The mirror of :func:`shape_of`'s problem. For a mismatch the shape is
    identical on both sides -- two endpoints differing only by host both render
    as ``https://<host>/`` -- so shape alone destroys the finding just as surely
    as redaction did. And printing the hosts is not available: one of them is a
    registered value, and a fragment of a secret slips past a redactor that
    matches whole values.

    So the evidence names the disagreeing component. That is enough to act on --
    the owner knows where to look -- and it reveals nothing.
    """
    a, b = urlparse(shipped.strip()), urlparse(issued.strip())
    if not (a.netloc and b.netloc):
        return "values differ"
    parts = [
        name for name, x, y in (
            ("host", a.netloc, b.netloc),
            ("path", a.path.rstrip("/"), b.path.rstrip("/")),
            ("scheme", a.scheme, b.scheme),
            ("query", a.query, b.query),
        ) if x != y
    ]
    return f"differ in {', '.join(parts)}" if parts else "differ in trailing characters"


def parse_config(text: str) -> dict[str, str]:
    """Parse ``KEY=value`` config, the way a dotenv loader would.

    Tolerant on purpose: this reads *the lab's* file, and the point is to find
    what is wrong with it. A parser that raises on the first oddity would report
    one defect and hide the rest.
    """
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip().removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def check_endpoints(endpoints: dict[str, str]) -> list[Check]:
    """Every URL the lab hands the learner should be usable as handed over."""
    checks = []
    for ref, url in sorted(endpoints.items()):
        kind = endpoint_kind(url)
        if kind == "base":
            checks.append(Check(f"endpoint {ref}", True, "is a base URL", evidence=shape_of(url)))
        elif kind == "operation":
            checks.append(Check(
                f"endpoint {ref}", False,
                "is an operation URL where a base URL is required. An SDK given this "
                "appends its own path, so every call 404s -- and the failure surfaces "
                "far from here.",
                verdict=DEFECT, domain=SETUP, severity="critical", evidence=shape_of(url),
            ))
        else:
            checks.append(Check(
                f"endpoint {ref}", False, "is not a usable URL",
                verdict=DEFECT, domain=SETUP, severity="critical", evidence=shape_of(url),
            ))
    return checks


def check_shipped_config(config: dict[str, str], issued: dict[str, str] | None = None,
                         *, source: str = ".env") -> list[Check]:
    """Check the lab's *own* config file against shape and against what it issued.

    Three failure modes, all seen in the reference run and none visible in the
    lab text:

    * a placeholder nobody replaced;
    * a value of the wrong *shape* -- an operation URL, a non-GUID subscription;
    * a value that contradicts what the Resources tab handed the learner, which
      is the only way to catch a config pointing at a resource from a previous
      lab edition.
    """
    checks: list[Check] = []
    issued = issued or {}

    for key, value in sorted(config.items()):
        if value.strip().lower() in PLACEHOLDERS:
            # Safe to quote verbatim, and necessary: the whole point is *which*
            # placeholder survived. It is drawn from a known list, so it cannot
            # be a secret -- and shape alone ("<14 chars, letters>") would lose
            # the finding.
            checks.append(Check(
                f"{source} {key}", False, "is an unreplaced placeholder",
                verdict=DEFECT, domain=SETUP, severity="major",
                evidence=f"{key}={value!r}",
            ))
            continue
        if key in BASE_URL_KEYS:
            kind = endpoint_kind(value)
            if kind != "base":
                checks.append(Check(
                    f"{source} {key}", False,
                    f"is {'an operation URL' if kind == 'operation' else 'not a URL'} "
                    "where a base URL is required",
                    verdict=DEFECT, domain=SETUP, severity="critical",
                    evidence=f"{key}={shape_of(value)}",
                ))
                continue
        if key in GUID_KEYS and not _GUID.match(value):
            checks.append(Check(
                f"{source} {key}", False, "is not a GUID",
                verdict=DEFECT, domain=SETUP, severity="major",
                evidence=f"{key}={shape_of(value)}",
            ))
            continue
        checks.append(Check(f"{source} {key}", True, "present and well-shaped"))

    for key, expected in sorted(issued.items()):
        if key not in config:
            continue
        actual = config[key]
        if actual and expected and actual.strip() != expected.strip():
            checks.append(Check(
                f"{source} {key} vs Resources tab", False,
                "does not match the value the lab handed the learner. The shipped "
                "config may point at a resource from a previous edition.",
                verdict=DEFECT, domain=SETUP, severity="major",
                evidence=f"{key}: {differs_in(actual, expected)}",
            ))
    return checks


def check_config_paths(loaders: dict[str, str], config_at: str) -> list[Check]:
    """Do the lab's own files agree on where the config lives?

    Sample code that loads ``.env`` from three different relative paths cannot
    all be right, and *disagreement alone is the finding* -- it needs no live
    resolution and no lab session. ``loaders`` maps a file to the path it loads;
    ``config_at`` is where the config actually is, both normalised the same way.
    """
    checks: list[Check] = []
    distinct = {p.replace("\\", "/").strip() for p in loaders.values()}
    want = config_at.replace("\\", "/").strip()

    if len(distinct) > 1:
        checks.append(Check(
            "shipped config path", False,
            f"{len(loaders)} file(s) load the config from {len(distinct)} different "
            "paths, so they cannot all be right",
            verdict=DEFECT, domain=SETUP, severity="critical",
            evidence="; ".join(f"{f} -> {p}" for f, p in sorted(loaders.items())),
        ))
    for source, path in sorted(loaders.items()):
        if path.replace("\\", "/").strip() != want:
            checks.append(Check(
                f"config path in {source}", False,
                f"loads the config from {path!r}, but it is at {config_at!r}",
                verdict=DEFECT, domain=SETUP, severity="critical",
                evidence=f"{source}: {path}",
            ))
        else:
            checks.append(Check(f"config path in {source}", True, "resolves to the config"))
    return checks


def preflight(*, endpoints: dict[str, str] | None = None,
              config: dict[str, str] | None = None,
              issued: dict[str, str] | None = None,
              loaders: dict[str, str] | None = None,
              config_at: str | None = None) -> Preflight:
    """Run every check we have evidence for, and record every one we do not.

    Each argument is optional, and **omitting one is recorded rather than
    ignored**. A preflight run with no shipped config has not established that
    the config is fine; it has established nothing about it, and the report has
    to say which.
    """
    result = Preflight()

    if endpoints:
        for check in check_endpoints(endpoints):
            result.add(check)
    else:
        result.cannot_check(
            "endpoints — no credentials were captured, so nothing the lab hands "
            "the learner was shape-checked"
        )

    if config:
        for check in check_shipped_config(config, issued):
            result.add(check)
        if not issued:
            result.cannot_check(
                "shipped config vs issued values — no captured credentials to "
                "compare against, so a config pointing at a stale resource would pass"
            )
    else:
        result.cannot_check(
            "shipped config — none was read, so placeholder and wrong-shape values "
            "in the lab's own files are unexamined"
        )

    if loaders and config_at:
        for check in check_config_paths(loaders, config_at):
            result.add(check)
    else:
        result.cannot_check(
            "config load paths — sample code was not inspected, so files loading "
            "the config from the wrong place would not be noticed"
        )

    # Named explicitly because it is the one that hurt most, and no amount of
    # shape-checking substitutes for asking the service what it is serving.
    result.cannot_check(
        "identity of deployed models — a deployment *named* `gpt-4o` may serve "
        "something else entirely; this needs a live call, not a name"
    )
    result.cannot_check(
        "resources promised by the instructions — needs a target descriptor to "
        "know what was promised"
    )
    return result
