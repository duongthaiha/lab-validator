"""Turn a signed-in Learning Campus session into a starter target descriptor.

Onboarding a new workshop was, until now, an act of archaeology: open the
catalogue by hand, read IDs out of URLs, and hand-author a TOML file. That is
the step where the person doing it has the least context, so it is exactly the
step worth automating.

The parsing and scaffolding here are deliberately pure -- they take already
extracted DOM records, not a browser -- so the fiddly part is testable without a
live lab session. ``scripts/lab_discover.py`` is the thin shim that supplies the
DOM.

One rule governs the scaffold: **never invent a value.** A descriptor exists to
carry expectations, so a plausible-looking guess is worse than a blank, because
it will be believed. Anything discovery cannot observe is emitted as a commented
``TODO`` naming how to find it, and :mod:`lab_validator.targets` will report the
resulting gaps rather than let a run walk with an invented expectation.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Enrolment",
    "Resolution",
    "slugify",
    "parse_enrolments",
    "resolve",
    "enrolment_from_own_page",
    "scaffold",
    "descriptor_for",
    "LINKS_JS",
    "HREFS_JS",
]

#: Extract every ``(text, href, visible)`` triple on a page.
#:
#: One canonical extractor, because three callers used to carry near-identical
#: copies that had quietly drifted apart in selector, truncation width and
#: whether they reported visibility -- so "the same" enumeration returned
#: different things depending on which script asked. This is the superset:
#: anchors that have an ``href``, text truncated generously, visibility
#: reported. Callers that want less filter it themselves rather than fork the
#: JavaScript again.
LINKS_JS = """() => {
  const seen = new Set(), out = [];
  document.querySelectorAll('a[href]').forEach(e => {
    const text = (e.innerText || e.getAttribute('aria-label') || '').trim();
    const href = e.getAttribute('href');
    if (!href) return;
    const key = text + '\\u0000' + href;
    if (seen.has(key)) return;
    seen.add(key);
    out.push({text: text.slice(0, 120), href,
              visible: !!(e.offsetWidth || e.offsetHeight)});
  });
  return out;
}"""

#: Just the ``href`` values, for cheap presence checks such as "does this tab
#: offer /User/Logout", where the text and visibility are irrelevant.
HREFS_JS = (
    "() => Array.from(document.querySelectorAll('a[href]'))"
    ".map(a => a.getAttribute('href') || '')"
)

#: ``/ClassEnrollment/5928204`` -- the launch entry point for one enrolment.
ENROLMENT_RE = re.compile(r"/ClassEnrollment/(\d+)\b", re.I)
#: ``/Class/763682`` or ``?classId=763682``.
CLASS_RE = re.compile(r"/Class(?:Details)?/(\d+)\b|[?&]classId=(\d+)\b", re.I)
#: ``/LabProfile/79233``, ``labProfileId=79233`` -- the lab *profile* id.
LAB_RE = re.compile(r"/LabProfile/(\d+)\b|[?&]labProfileId=(\d+)\b", re.I)
#: ``/Lab/79233?instructionSetLang=en&classId=763682`` -- the launch link on an
#: enrolment's own page. Anchored on ``/Lab/`` + digits so ``/LabProfile/79233``
#: cannot match it.
LAB_PAGE_RE = re.compile(r"/Lab/(\d+)\b", re.I)


@dataclass(frozen=True)
class Enrolment:
    """One launchable training the signed-in user is enrolled in."""

    enrolment: int
    title: str
    href: str
    class_id: int | None = None
    lab_id: int | None = None

    @property
    def url(self) -> str:
        return f"https://mslearningcampus.com/ClassEnrollment/{self.enrolment}"

    def __str__(self) -> str:
        bits = [f"enrolment {self.enrolment}"]
        if self.class_id:
            bits.append(f"class {self.class_id}")
        if self.lab_id:
            bits.append(f"lab {self.lab_id}")
        return f"{self.title[:58]:60} {'  '.join(bits)}"


def _clean_title(raw: str) -> str:
    """Reduce an anchor's ``innerText`` to the workshop title.

    Two problems, one fix. ``innerText`` on an anchor wrapping a whole card is
    multi-line -- ``"title\\n18 Mar 2026\\nLaunch"`` -- and a raw newline is
    illegal in a TOML basic string, so an unflattened title reaches the scaffold
    and produces a descriptor that will not parse. It also poisons the derived
    slug, and because the merge below prefers the *longest* title, the card blob
    is exactly the variant that wins over the clean title link.

    Taking the first non-empty line fixes both: on a card that is the title, and
    on a plain title link it changes nothing. "Longest wins" then does the right
    thing, because a bare ``Launch`` label loses to a real title.
    """
    for line in raw.splitlines():
        cleaned = re.sub(r"\s+", " ", line).strip()
        if cleaned:
            return cleaned
    return ""


def _first_group(match: re.Match | None) -> int | None:
    if not match:
        return None
    for value in match.groups():
        if value:
            return int(value)
    return None


def slugify(title: str) -> str:
    """A filesystem- and CLI-safe slug for a workshop title.

    Workshop titles carry decoration the slug should not: a ``WorkshopPLUS -``
    prefix, a trailing parenthesised edition date, and accented characters that
    make a filename awkward to type on a different keyboard layout.
    """
    text = unicodedata.normalize("NFKD", title)
    # Normalise dashes *before* the ASCII strip: en/em dashes and the like are
    # not decomposable, so encode(errors="ignore") deletes them outright and the
    # "WorkshopPLUS - " prefix below stops matching.
    text = re.sub(r"[\u2010-\u2015\u2212]", "-", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"^\s*workshop\s*plus\s*[-:]\s*", "", text)
    text = re.sub(r"\([^)]*\)", " ", text)  # edition suffixes
    text = re.sub(r"\b(all\s+modules|lab|labs|training)\b", " ", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return re.sub(r"-{2,}", "-", text) or "untitled"


def parse_enrolments(links: list[dict]) -> list[Enrolment]:
    """Pick the launchable enrolments out of a flat list of anchor records.

    ``links`` is what :data:`LINKS_JS` above returns: dicts with ``text`` and
    ``href``. Several anchors on the page point at the
    same enrolment (title link, a "Launch" button, a thumbnail), so results are
    collapsed by enrolment id and the longest human title wins -- a "Launch"
    label identifies the row but does not name the workshop.
    """
    best: dict[int, Enrolment] = {}
    for link in links:
        href = (link.get("href") or "").strip()
        enrolment = _first_group(ENROLMENT_RE.search(href))
        if enrolment is None:
            continue
        title = _clean_title(link.get("text") or "")
        found = Enrolment(
            enrolment=enrolment,
            title=title,
            href=href,
            class_id=_first_group(CLASS_RE.search(href)),
            lab_id=_first_group(LAB_RE.search(href)),
        )
        prior = best.get(enrolment)
        if prior is None:
            best[enrolment] = found
            continue
        # Merge: keep the most informative title and any id either anchor knew.
        best[enrolment] = Enrolment(
            enrolment=enrolment,
            title=max((prior.title, found.title), key=len),
            href=prior.href or found.href,
            class_id=prior.class_id or found.class_id,
            lab_id=prior.lab_id or found.lab_id,
        )
    return sorted(best.values(), key=lambda e: e.title.lower())


@dataclass(frozen=True)
class Resolution:
    """The answer to "which lab does this URL and name refer to?"

    Three outcomes, and the ambiguous one is deliberately not collapsed into a
    guess. A validator that picks the closest match will, on the day two
    editions of a workshop are enrolled at once, walk the wrong one and report
    81 findings against a lab nobody asked about -- and every one of them will
    look plausible. Naming the candidates and stopping costs one round trip;
    guessing costs the run's credibility.
    """

    enrolment: Enrolment | None
    candidates: list[Enrolment]
    reason: str

    @property
    def ok(self) -> bool:
        return self.enrolment is not None


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def enrolment_from_own_page(enrolment: int, links: list[dict], name: str) -> Enrolment | None:
    """Build the enrolment for a page that *is* that enrolment's page.

    ``/ClassEnrollment/<id>`` is the entry point this module's own
    ``Enrolment.url`` hands out, and the one a human copies from the address
    bar -- but the page does not link to itself, so ``parse_enrolments`` finds
    nothing there and the caller used to refuse the very URL it recommends.

    The evidence that this really is such a page is the launch link,
    ``/Lab/<labId>?...classId=<classId>``. Requiring it means a signed-out page,
    or some unrelated page whose URL merely contains the path, still refuses --
    an enrolment nobody could launch is not one worth returning.
    """
    for link in links:
        href = (link.get("href") or "").strip()
        lab_id = _first_group(LAB_PAGE_RE.search(href))
        if lab_id is None:
            continue
        observed = _clean_title(link.get("text") or "")
        return Enrolment(
            enrolment=enrolment,
            # The link text names the lab; --name is the fallback, since here it
            # is only a label -- the URL already did the disambiguating.
            title=observed or _clean_title(name),
            href=href,
            class_id=_first_group(CLASS_RE.search(href)),
            lab_id=lab_id,
        )
    return None


def resolve(links: list[dict], url: str, name: str) -> Resolution:
    """Pick the one enrolment a ``--url`` + ``--name`` pair identifies.

    The URL is trusted first: if it names an enrolment id outright -- which the
    ``/ClassEnrollment/<id>`` entry point does -- then the learner has already
    disambiguated and the name is only a label. Otherwise the URL was a
    catalogue or landing page, and the name has to do the work.

    Name matching goes exact, then unique-substring, and stops. Fuzzy scoring is
    deliberately absent: it turns "no match" into "some match", and this
    function's most valuable answer is that it could not tell.
    """
    enrolments = parse_enrolments(links)

    # Trusting the URL has to come *before* refusing for want of links on the
    # page, or the trust is not real: an enrolment's own page lists no
    # enrolments, so the check below would reject it before this branch ran.
    from_url = _first_group(ENROLMENT_RE.search(url))
    if from_url is not None:
        exact = [e for e in enrolments if e.enrolment == from_url]
        if exact:
            return Resolution(exact[0], exact, f"the URL names enrolment {from_url}")
        standing = enrolment_from_own_page(from_url, links, name)
        if standing is not None:
            return Resolution(
                standing, [standing],
                f"the URL names enrolment {from_url}, and this is its own page",
            )
        if not enrolments:
            return Resolution(
                None, [],
                f"the URL names enrolment {from_url}, but the page offers no lab to "
                "launch -- the session may be signed out",
            )
        return Resolution(
            None,
            enrolments,
            f"the URL names enrolment {from_url}, which is not on this page -- "
            "the session may be signed out, or the enrolment may belong to another account",
        )

    if not enrolments:
        return Resolution(None, [], "no launchable enrolment found on that page")

    wanted = _norm(name)
    if not wanted:
        return Resolution(None, enrolments, "no --name given, and the URL names no enrolment")

    exact = [e for e in enrolments if _norm(e.title) == wanted]
    if len(exact) == 1:
        return Resolution(exact[0], exact, "exact title match")
    if len(exact) > 1:
        return Resolution(None, exact, f"{len(exact)} enrolments share that exact title")

    partial = [e for e in enrolments if wanted in _norm(e.title)]
    if len(partial) == 1:
        return Resolution(partial[0], partial, "unique partial title match")
    if len(partial) > 1:
        return Resolution(None, partial, f"{len(partial)} enrolments match that name")

    return Resolution(None, enrolments, f"no enrolment matches {name!r}")


def _todo(key: str, how: str) -> str:
    return f"# TODO {key}: {how}"

def scaffold(enrolment: Enrolment, slug: str | None = None) -> str:
    """Render a starter ``targets/<slug>.toml`` from what discovery observed.

    Observed values are written as real keys. Everything else is a commented
    TODO carrying the instruction for finding it, so the file never asserts an
    expectation nobody checked.
    """
    slug = slug or slugify(enrolment.title)
    lines = [
        "# Target descriptor for one Skillable lab.",
        "#",
        "# Generated by scripts/lab_discover.py --scaffold. Every value below was",
        "# OBSERVED; every TODO is a value discovery could not see. Fill the TODOs in",
        "# from the running lab, then re-check with:",
        f"#     python scripts/lab_run.py --check-target {slug}",
        "#",
        "# Do not guess. An invented expectation is worse than a missing one, because",
        "# a run will believe it and report a divergence that is really a typo here.",
        "",
        f'slug = "{slug}"',
        f'name = "{_escape(enrolment.title)}"',
        "",
        "[lab]",
    ]
    if enrolment.lab_id:
        lines.append(f"id = {enrolment.lab_id}")
    else:
        lines.append(_todo("id", "lab profile id -- the number in the lab-client URL"))
    if enrolment.class_id:
        lines.append(f"class_id = {enrolment.class_id}")
    else:
        lines.append(_todo("class_id", "from the /Class/<id> link on the enrolment page"))
    lines += [
        f"enrollment = {enrolment.enrolment}",
        _todo("edition", 'the "(YYYYMMDD)" edition string shown on the enrolment page'),
        _todo("duration_hours", "the lab clock's starting value, in hours"),
        f'enrollment_url = "{enrolment.url}"',
        "",
        "[environment]",
        _todo("kind", 'e.g. ["virtualization", "cloud-slice"] -- what the lab hands out'),
        _todo("cloud", 'e.g. "azure", if the lab includes a cloud slice'),
        _todo("credential_hours", "how long cloud credentials last before a refresh"),
        _todo("vm_user", "the signed-in account on the jumpbox"),
        _todo("lab_files", "path to the lab files on the VM"),
        "",
        "[expect]",
        "# Resource names usually carry a per-instance number, so match on prefix.",
        _todo("region", "the region the instructions tell the learner to pick"),
        _todo("resource_group", "resource group name, or its stable prefix"),
        _todo("models", "models the instructions tell the learner to deploy"),
        "",
        "[risks]",
        "# Structural dependencies worth re-asserting every run: one break, many",
        "# broken segments. Add them as you find them.",
        "",
        "# Full human-fidelity execution is the default. Anything under [deferrals] is",
        "# deliberately not attempted and MUST carry a justification that survives",
        "# review; convenience is not a justification.",
        "[deferrals]",
        "",
    ]
    return "\n".join(lines)


#: TOML basic strings permit only tab among the control characters, and require
#: these to be escaped. Anything else in C0/C1 becomes a \uXXXX escape.
_TOML_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\b": "\\b",
    "\t": "\\t",
    "\n": "\\n",
    "\f": "\\f",
    "\r": "\\r",
}


def _escape(value: str) -> str:
    """Escape a string for a TOML basic string.

    Titles come from `innerText`, so they can carry anything the page carries.
    An unescaped control character makes the whole descriptor unparseable, which
    turns a cosmetic oddity in a lab title into a file nobody can load.
    """
    out = []
    for ch in value:
        if ch in _TOML_ESCAPES:
            out.append(_TOML_ESCAPES[ch])
        elif ord(ch) < 0x20 or ord(ch) == 0x7F:
            out.append(f"\\u{ord(ch):04X}")
        else:
            out.append(ch)
    return "".join(out)


def descriptor_for(enrolment: Enrolment, targets_dir: Path) -> str | None:
    """Slug of an existing descriptor for this enrolment, or ``None``.

    Matched on **observed identity** (``lab.enrollment``, else ``lab.id``), not
    on the derived slug. A curated descriptor's slug is usually hand-shortened --
    this repo's own ``azure-ai-platform`` versus the derived
    ``azure-ai-platform-and-services`` -- so a name-based check reports an
    already-onboarded lab as new and then writes a second, blank descriptor
    beside the curated one.
    """
    from .targets import Target, TargetError  # local: avoids an import cycle at module load

    for slug in Target.available(targets_dir):
        try:
            target = Target.inspect(slug, root=targets_dir)
        except TargetError:
            continue  # a broken descriptor is someone else's problem, not a match
        lab = target.lab if isinstance(target.lab, dict) else {}
        if lab.get("enrollment") == enrolment.enrolment:
            return slug
        if enrolment.lab_id is not None and lab.get("id") == enrolment.lab_id:
            return slug
    return None


def write_scaffold(
    enrolment: Enrolment,
    targets_dir: Path,
    slug: str | None = None,
    overwrite: bool = False,
) -> Path:
    """Write the scaffold, refusing to clobber a descriptor someone has curated."""
    existing = descriptor_for(enrolment, targets_dir)
    if existing and not overwrite:
        raise FileExistsError(
            f"targets/{existing}.toml already describes enrolment {enrolment.enrolment}. "
            "Pass --overwrite to replace it, but note that a curated descriptor holds "
            "findings a scaffold cannot regenerate."
        )
    slug = slug or existing or slugify(enrolment.title)
    path = targets_dir / f"{slug}.toml"
    if path.exists() and not overwrite:
        raise FileExistsError(
            f"{path} already exists. Pass --overwrite to replace it, but note that "
            "a curated descriptor holds findings a scaffold cannot regenerate."
        )
    targets_dir.mkdir(parents=True, exist_ok=True)
    path.write_text(scaffold(enrolment, slug), encoding="utf-8")
    return path
