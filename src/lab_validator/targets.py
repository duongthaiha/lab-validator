"""Per-lab target descriptors.

Everything lab-specific is data in ``targets/<slug>.toml``; the engine is generic.
That split only holds if the data is *validated*, because a data-driven design
trades one failure mode for another: a typo in a descriptor key does not raise,
it silently reads as ``None`` and the run quietly walks with a missing
expectation. Onboarding a new workshop is the moment that bites, and it is
exactly when the person doing it has the least context to debug it.

So this module exists to turn a descriptor into either a typed object or a
precise complaint naming the file, the key and the fix.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from . import paths

__all__ = ["Target", "TargetError", "Problem"]

REPO_ROOT = paths.REPO_ROOT
TARGETS_DIR = paths.TARGETS

# Declared shape: key -> expected type. Unknown keys are reported rather than
# ignored (in a file whose whole job is to carry expectations, a key nobody reads
# is a silent bug), and so are wrong types -- `models = "gpt-4o"` is the likeliest
# authoring slip here, and `list()` would silently turn it into six single-letter
# model names. A wrong type is an invented expectation, which is the exact failure
# this module exists to prevent.
STR, INT, LIST = str, int, list
SCHEMA: dict[str, dict[str, type | tuple[type, ...]]] = {
    "lab": {
        "id": INT,
        "class_id": INT,
        "enrollment": INT,
        "edition": STR,
        "duration_hours": (INT, float),
        "enrollment_url": STR,
    },
    "environment": {
        "kind": (STR, LIST),
        "cloud": STR,
        "credential_hours": (INT, float),
        "vm_user": STR,
        "lab_files": STR,
    },
    "expect": {
        "region": STR,
        "region_slug": STR,
        "resource_group": STR,
        "project": STR,
        "resource_prefixes": LIST,
        "models": LIST,
    },
}
# Free-form tables: the keys are author-chosen labels, so only the values are checked.
FREE_TABLES = {"risks", "deferrals"}


def _type_name(expected: type | tuple[type, ...]) -> str:
    names = {str: "string", int: "integer", float: "number", list: "array", dict: "table"}
    if isinstance(expected, tuple):
        return " or ".join(dict.fromkeys(names.get(t, t.__name__) for t in expected))
    return names.get(expected, expected.__name__)


class TargetError(Exception):
    """A descriptor could not be loaded, or failed validation in strict mode."""


@dataclass(frozen=True)
class Problem:
    """One validation complaint."""

    level: str  # "error" | "warning"
    where: str  # dotted path into the descriptor
    message: str

    def __str__(self) -> str:
        return f"[{self.level}] {self.where}: {self.message}"


@dataclass
class Target:
    """A validated per-lab descriptor.

    The raw table stays reachable through :attr:`data` so a descriptor can carry
    a key this loader has not learned about yet without the run failing --
    forward compatibility matters more here than strictness, because the
    descriptor is edited by whoever onboards a lab, not by whoever ships the
    engine.
    """

    slug: str
    path: Path | None
    data: dict
    problems: list[Problem] = field(default_factory=list)

    # ---- loading --------------------------------------------------------

    @classmethod
    def _read(cls, slug: str, root: Path | None = None) -> Target:
        """Read and validate, attaching problems without judging them."""
        root = root or TARGETS_DIR
        path = root / f"{slug}.toml"
        if not path.exists():
            known = ", ".join(cls.available(root)) or "none"
            raise TargetError(f"No target descriptor at {path}\nAvailable targets: {known}")
        try:
            # utf-8-sig, not utf-8: Notepad and PowerShell 5.1 both write a BOM
            # by default, and a BOM under plain utf-8 surfaces as "Invalid
            # statement (at line 1, column 1)" -- which sends whoever is
            # onboarding hunting a syntax error that does not exist.
            data = tomllib.loads(path.read_text(encoding="utf-8-sig"))
        except tomllib.TOMLDecodeError as exc:
            raise TargetError(f"{path} is not valid TOML: {exc}") from exc
        except (UnicodeDecodeError, LookupError) as exc:
            raise TargetError(
                f"{path} is not UTF-8 text ({exc}).\n"
                "  Descriptors must be UTF-8. PowerShell 5.1 writes UTF-16 for '>' "
                "redirection;\n  use Set-Content -Encoding utf8, or re-save the file as UTF-8."
            ) from exc

        target = cls(slug=slug, path=path, data=data)
        target.problems = target.validate()
        return target

    @classmethod
    def load(cls, slug: str, root: Path | None = None, strict: bool = False) -> Target:
        """Read ``targets/<slug>.toml`` as something a run can rely on.

        ``strict`` turns warnings into failures. Off by default so a run is
        never blocked by a cosmetic descriptor issue; on in tests and in the
        onboarding command, where the point is to catch it.

        Use :meth:`inspect` instead when the descriptor is *expected* to be
        incomplete -- a freshly scaffolded one, say -- and the problems are the
        answer rather than an error.
        """
        target = cls._read(slug, root)
        errors = [p for p in target.problems if p.level == "error"]
        fatal = target.problems if strict else errors
        if fatal:
            joined = "\n  ".join(str(p) for p in fatal)
            raise TargetError(f"{target.path} failed validation:\n  {joined}")
        return target

    @classmethod
    def inspect(cls, slug: str, root: Path | None = None) -> Target:
        """Read a descriptor for *reporting*, never raising on its contents.

        A descriptor being incomplete is the normal state during onboarding, and
        answering "what is still missing?" with an exception would make the
        onboarding command useless at exactly the moment it is needed. Genuine
        I/O faults -- no such file, unparseable TOML -- still raise, because
        those are not descriptions of an incomplete descriptor.
        """
        return cls._read(slug, root)

    @staticmethod
    def available(root: Path | None = None) -> list[str]:
        """Slugs of every descriptor on disk, for discovery and error messages."""
        root = root or TARGETS_DIR
        if not root.is_dir():
            return []
        return sorted(p.stem for p in root.glob("*.toml"))

    @staticmethod
    def default(root: Path | None = None) -> str:
        """The slug to use when the caller did not name one.

        Deliberately *not* a constant. Baking a slug into the engine is how a
        validator quietly becomes a single-lab script: the default keeps working
        for the lab it was written against, so nobody notices it is there until
        a second lab exists and silently runs against the first one's
        descriptor.

        So: one descriptor on disk means there is no ambiguity to resolve and it
        is used. Any other number is a question only the caller can answer, and
        is raised as one.
        """
        slugs = Target.available(root)
        if len(slugs) == 1:
            return slugs[0]
        if not slugs:
            raise TargetError(
                f"no target descriptors in {root or TARGETS_DIR}. "
                "Create one with: python scripts/lab_discover.py --scaffold <enrolment>"
            )
        raise TargetError(
            "several target descriptors exist, so --target is required: "
            + ", ".join(slugs)
        )

    # ---- starting from a URL instead of a descriptor ---------------------

    @classmethod
    def from_url(cls, url: str, name: str, root: Path | None = None) -> Target:
        """Build a target from nothing but a lab URL and a human name.

        This inverts the descriptor's role. Requiring ``targets/<slug>.toml``
        before a run can start makes onboarding the gate: a brand-new lab cannot
        be walked until somebody hand-authors expectations for a lab nobody has
        walked yet, which is the wrong order. The walk is what *produces* those
        expectations.

        So the descriptor becomes **optional enrichment**:

        * without one, a run still yields every *observation-based* finding --
          broken links, defective sample code, missing UI, undocumented steps,
          a model the portal refuses to deploy;
        * with one, it additionally yields *expectation-based* findings -- "the
          lab promised region X / model Y and I did not find it".

        A descriptor already on disk is matched on **observed identity** (the
        enrolment or lab id parsed out of the URL), never on the derived slug:
        curated slugs are hand-shortened, so a name match would miss the very
        descriptor it should have found and silently downgrade the run.
        """
        from .discovery import ENROLMENT_RE, LAB_RE, _first_group, slugify

        enrolment = _first_group(ENROLMENT_RE.search(url))
        lab_id = _first_group(LAB_RE.search(url))

        for slug in cls.available(root):
            try:
                candidate = cls.inspect(slug, root=root)
            except TargetError:
                continue  # a broken descriptor is someone else's problem, not a match
            lab = candidate.lab
            if enrolment is not None and lab.get("enrollment") == enrolment:
                return candidate
            if lab_id is not None and lab.get("id") == lab_id:
                return candidate

        lab: dict = {"enrollment_url": url}
        if enrolment is not None:
            lab["enrollment"] = enrolment
        if lab_id is not None:
            lab["id"] = lab_id
        return cls(
            slug=slugify(name),
            path=None,
            data={"slug": slugify(name), "name": name, "lab": lab},
        )

    @property
    def is_enriched(self) -> bool:
        """Is this target backed by a curated descriptor on disk?

        The distinction has to reach the report. A run with no descriptor cannot
        make expectation-based findings at all, and a coverage table that does
        not say so invites the reader to treat "nothing expected was missing" as
        "everything expected was there".
        """
        return self.path is not None

    def enrichment_gaps(self) -> list[str]:
        """Checks that are unavailable because nothing declared an expectation.

        Reported, not raised. Missing enrichment weakens a run; it does not
        invalidate it, and a run that refuses to start is worth less than one
        that starts and says what it could not check.
        """
        gaps: list[str] = []
        expect = self.expect
        if not expect.get("region"):
            gaps.append("region -- cannot tell whether the lab landed where the text says")
        if not expect.get("models"):
            gaps.append("models -- cannot tell whether the promised deployments exist")
        if not expect.get("resource_group") and not expect.get("resource_prefixes"):
            gaps.append("resource naming -- cannot tell a missing resource from a renamed one")
        if not self.environment.get("lab_files"):
            gaps.append("lab_files -- cannot check the shipped sample code in place")
        if not self.risks:
            gaps.append("risks -- no structural dependency is re-asserted each run")
        return gaps


    # ---- validation -----------------------------------------------------

    def validate(self) -> list[Problem]:
        problems: list[Problem] = []
        data = self.data

        if not data.get("name"):
            problems.append(Problem("error", "name", "required -- the human-readable lab title"))

        declared = data.get("slug")
        if not declared:
            problems.append(Problem("error", "slug", "required"))
        elif declared != self.slug:
            problems.append(
                Problem(
                    "error",
                    "slug",
                    f"is {declared!r} but the file is {self.slug}.toml -- "
                    "they must match, or --target will load a different lab than it names",
                )
            )

        lab = data.get("lab")
        if not isinstance(lab, dict):
            problems.append(Problem("error", "lab", "required table"))
        elif lab.get("id") is None:
            problems.append(Problem("error", "lab.id", "required -- the Skillable lab profile id"))

        for table, allowed in SCHEMA.items():
            section = data.get(table)
            if section is None:
                continue
            if not isinstance(section, dict):
                problems.append(Problem("error", table, "must be a table"))
                continue
            for key in sorted(set(section) - set(allowed)):
                problems.append(
                    Problem(
                        "warning",
                        f"{table}.{key}",
                        f"not a known key; nothing reads it. Expected one of: "
                        f"{', '.join(sorted(allowed))}",
                    )
                )
            for key, expected in sorted(allowed.items()):
                if key not in section:
                    continue
                value = section[key]
                # bool is an int subclass; a flag where a count belongs is a bug.
                if isinstance(value, bool) and expected is not bool:
                    ok = False
                else:
                    ok = isinstance(value, expected)
                if not ok:
                    problems.append(
                        Problem(
                            "error",
                            f"{table}.{key}",
                            f"must be a {_type_name(expected)}, not "
                            f"{_type_name(type(value))} -- got {value!r}",
                        )
                    )

        # `risks` is free-form in its keys, but it is still a table of prose. A
        # scalar here makes the property return a str, so anything that later
        # iterates it walks characters.
        risks = data.get("risks")
        if risks is not None and not isinstance(risks, dict):
            problems.append(Problem("error", "risks", 'must be a table of name = "description"'))

        # A deferral is a promise not to do work, so it has to carry a reason
        # that survives review. An empty one is how "we skipped it" becomes
        # invisible in the report.
        deferrals = data.get("deferrals")
        if deferrals is not None and not isinstance(deferrals, dict):
            problems.append(
                Problem("error", "deferrals", 'must be a table of name = "justification"')
            )
            deferrals = None
        for name, reason in (deferrals or {}).items():
            if not isinstance(reason, str) or not reason.strip():
                problems.append(
                    Problem(
                        "error",
                        f"deferrals.{name}",
                        "needs a written justification -- convenience is not one",
                    )
                )

        # Scalars are reported as well as tables. A key at the top level that
        # belongs inside one -- `enrollment_url` outside [lab], say -- reads as
        # None at the point of use, which is exactly the silent failure this
        # loader exists to prevent.
        for key in sorted(set(data) - set(SCHEMA) - FREE_TABLES - {"slug", "name"}):
            kind = "table" if isinstance(data.get(key), dict) else "key"
            problems.append(Problem("warning", key, f"unknown top-level {kind}; nothing reads it"))

        return problems

    # ---- typed access ---------------------------------------------------

    @property
    def name(self) -> str:
        return self.data.get("name", self.slug)

    @property
    def lab(self) -> dict:
        return self.data.get("lab", {})

    @property
    def environment(self) -> dict:
        return self.data.get("environment", {})

    @property
    def expect(self) -> dict:
        return self.data.get("expect", {})

    @property
    def risks(self) -> dict[str, str]:
        return self.data.get("risks", {})

    @property
    def deferrals(self) -> dict[str, str]:
        return self.data.get("deferrals", {})

    @property
    def lab_id(self) -> int | None:
        return self.lab.get("id")

    @property
    def enrollment_url(self) -> str | None:
        """Where a human signs in to launch this lab.

        Worth surfacing: the lab client is not directly addressable, so this URL
        is the only entry point when a session has to be re-established.
        """
        url = self.lab.get("enrollment_url")
        if url:
            return url
        enrollment = self.lab.get("enrollment")
        if enrollment:
            return f"https://mslearningcampus.com/ClassEnrollment/{enrollment}"
        return None

    @property
    def models(self) -> list[str]:
        return list(self.expect.get("models", []))

    @property
    def resource_prefixes(self) -> list[str]:
        return list(self.expect.get("resource_prefixes", []))

    @property
    def credential_hours(self) -> int | None:
        return self.environment.get("credential_hours")

    def summary(self) -> str:
        lines = [
            f"target      : {self.slug}",
            f"name        : {self.name}",
            f"lab id      : {self.lab_id}",
            f"enrollment  : {self.enrollment_url}",
            f"region      : {self.expect.get('region')}",
            f"models      : {', '.join(self.models) or '-'}",
            f"prefixes    : {', '.join(self.resource_prefixes) or '-'}",
            f"deferrals   : {len(self.deferrals)}",
        ]
        if self.problems:
            lines.append("problems    :")
            lines += [f"  {p}" for p in self.problems]
        return "\n".join(lines)
