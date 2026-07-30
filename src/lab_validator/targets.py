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

__all__ = ["Target", "TargetError", "Problem"]

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGETS_DIR = REPO_ROOT / "targets"

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
    path: Path
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
