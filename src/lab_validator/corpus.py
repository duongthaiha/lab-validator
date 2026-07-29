"""Derive a lab's structure from the instructions DOM.

Earlier runs segmented the lab by scraping *rendered text* and looking for a
title line followed by ``Introduction``. That heuristic is fragile and it
demonstrably fails: in the target lab, "Lab 09 - Security" has no
``Introduction`` line, so text-based segmentation silently swallows it into the
previous lab. Segment boundaries that are silently wrong are worse than no
segmentation at all, because every downstream finding is then misattributed.

The instructions frame renders from Markdown, so the DOM already carries the
authoritative outline: ``<h1>``-``<h6>`` elements with slugified ``id``
attributes, plus a table of contents made of in-page ``<a href="#...">`` links.
This module reads that outline directly. It is lab-agnostic -- any Skillable lab
whose instructions are Markdown-rendered will segment correctly with no code
change, which is what makes the validator a product rather than a script.

Structural problems are surfaced as :class:`Anomaly` records rather than being
repaired quietly. A table of contents that points at a missing anchor, or two
entries sharing a label, is exactly the kind of drift the validator exists to
report.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .runlog import Segment

#: Browser-side extractor.
#:
#: Section bodies are sliced with DOM ``Range`` objects rather than by splitting
#: rendered text on heading strings: heading text repeats constantly in this
#: corpus ("Introduction", "Objectives", "Scenario" appear once per lab), so
#: string splitting would mis-slice. A range between two elements cannot.
_EXTRACT_JS = r"""
() => {
  const heads = Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'));
  const out = [];
  for (let i = 0; i < heads.length; i++) {
    const h = heads[i];
    let body = '';
    try {
      const r = document.createRange();
      r.setStartAfter(h);
      if (i + 1 < heads.length) { r.setEndBefore(heads[i + 1]); }
      else { r.setEndAfter(document.body.lastChild); }
      body = r.toString();
    } catch (e) { body = ''; }
    out.push({
      order: i,
      level: parseInt(h.tagName.substring(1), 10),
      id: h.id || '',
      text: (h.innerText || h.textContent || '').trim(),
      body: body.replace(/\u00a0/g, ' ').replace(/[ \t]+\n/g, '\n').trim()
    });
  }
  const toc = Array.from(document.querySelectorAll('a[href^="#"]'))
    .map(a => ({ href: a.getAttribute('href'), text: (a.innerText || '').trim(), el: a }))
    .filter(o => o.href.length > 1);

  // The document's real table of contents is the link list under the "Table of
  // Contents" heading. Other in-page links (per-lab mini-contents, "back to
  // top") are navigation too, but treating them as modules would shred the
  // segment list, so mark which links are the primary contents.
  let tocStart = document.querySelector('#table-of-contents');
  if (!tocStart) {
    tocStart = heads.find(h => /table of contents/i.test(h.innerText || '')) || null;
  }
  let tocEnd = null;
  if (tocStart) {
    const lvl = parseInt(tocStart.tagName.substring(1), 10);
    tocEnd = heads.find(h =>
      h.compareDocumentPosition(tocStart) & Node.DOCUMENT_POSITION_PRECEDING &&
      parseInt(h.tagName.substring(1), 10) <= lvl) || null;
  }
  const inToc = (el) => {
    if (!tocStart) return false;
    const afterStart = tocStart.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_FOLLOWING;
    if (!afterStart) return false;
    if (!tocEnd) return true;
    return !!(tocEnd.compareDocumentPosition(el) & Node.DOCUMENT_POSITION_PRECEDING);
  };
  const tocOut = toc.map(o => ({ href: o.href, text: o.text, primary: inToc(o.el) }));

  const links = Array.from(document.querySelectorAll('a[href^="http"]'))
    .map(a => ({ href: a.getAttribute('href'), text: (a.innerText || '').trim().slice(0, 120) }));
  return {
    title: (document.querySelector('h1') || {}).innerText || '',
    headings: out,
    toc: tocOut,
    links: links,
    ids: Array.from(document.querySelectorAll('[id]')).map(e => e.id).filter(Boolean)
  };
}
"""


@dataclass
class Heading:
    order: int
    level: int
    id: str
    text: str
    body: str = ""

    @property
    def words(self) -> int:
        return len(self.body.split())


@dataclass
class TocLink:
    href: str
    text: str
    primary: bool = False

    @property
    def target(self) -> str:
        return self.href.lstrip("#")


@dataclass
class Anomaly:
    """A structural problem in the instruction content itself."""

    code: str
    message: str
    detail: dict = field(default_factory=dict)
    severity: str = "minor"


@dataclass
class Outline:
    """The parsed structure of one lab's instructions."""

    title: str = ""
    headings: list[Heading] = field(default_factory=list)
    toc: list[TocLink] = field(default_factory=list)
    links: list[dict] = field(default_factory=list)
    ids: list[str] = field(default_factory=list)

    # ---- lookups --------------------------------------------------------

    def by_id(self, anchor: str) -> Heading | None:
        anchor = anchor.lstrip("#")
        for h in self.headings:
            if h.id == anchor:
                return h
        return None

    def contents(self) -> list[TocLink]:
        """The primary table of contents, falling back to all in-page links."""
        primary = [t for t in self.toc if t.primary]
        return primary or self.toc

    def modules(self) -> list[Heading]:
        """Headings targeted by the table of contents, in document order.

        The TOC is the learner's map of the lab, so its targets are the natural
        top-level unit -- but it is written by hand and can point anywhere, so
        resolve through the DOM and keep only what actually exists.
        """
        seen: dict[int, Heading] = {}
        for link in self.contents():
            head = self.by_id(link.target)
            if head is not None and head.text.strip():
                seen.setdefault(head.order, head)
        return [seen[k] for k in sorted(seen)]

    def sections(self) -> list[Heading]:
        """The ``<h1>`` units of work, which are what a learner actually walks."""
        return [h for h in self.headings if h.level == 1 and h.id]

    def module_for(self, head: Heading) -> Heading | None:
        current = None
        for module in self.modules():
            if module.order <= head.order:
                current = module
            else:
                break
        return current

    # ---- the product ----------------------------------------------------

    def segments(self) -> list[Segment]:
        """One resumable checkpoint per ``<h1>`` section.

        ``<h1>`` is the right granularity: it is where the corpus starts a new
        named piece of work ("Setup .env file", "Lab 09 - Security"), which is
        both what a learner would treat as a sitting and small enough that a
        crash loses little.
        """
        sections = self.sections()
        segments: list[Segment] = []
        for i, head in enumerate(sections):
            end = sections[i + 1].order - 1 if i + 1 < len(sections) else len(self.headings) - 1
            module = self.module_for(head)
            segments.append(
                Segment(
                    id=f"s{i:02d}-{_short(head.id)}",
                    title=head.text,
                    module=module.text if module else None,
                    anchor=f"#{head.id}",
                    start_line=head.order,
                    end_line=end,
                )
            )
        return segments

    def tasks(self, section: Heading) -> list[Heading]:
        """The numbered ``<h3>`` steps inside one section."""
        bound = self._section_end(section)
        return [
            h
            for h in self.headings
            if section.order < h.order <= bound and h.level == 3 and re.match(r"^\d+[\.\)]", h.text)
        ]

    def section_headings(self, section: Heading) -> list[Heading]:
        bound = self._section_end(section)
        return [h for h in self.headings if section.order <= h.order <= bound]

    def section_text(self, section: Heading) -> str:
        parts = []
        for h in self.section_headings(section):
            parts.append(f"{'#' * h.level} {h.text}".rstrip())
            if h.body:
                parts.append(h.body)
        return "\n\n".join(parts).strip()

    def _section_end(self, section: Heading) -> int:
        for h in self.headings:
            if h.order > section.order and h.level == 1:
                return h.order - 1
        return len(self.headings) - 1

    # ---- structural checks ---------------------------------------------

    def anomalies(self) -> list[Anomaly]:
        found: list[Anomaly] = []

        for link in self.toc:
            if self.by_id(link.target) is None:
                found.append(
                    Anomaly(
                        "LAB006",
                        f"Table of contents entry {link.text!r} points at "
                        f"{link.href!r}, which does not exist in the document.",
                        {"text": link.text, "href": link.href},
                        "major",
                    )
                )

        # Same visible label, different destinations: the learner cannot tell
        # the entries apart, so one lab looks missing from the contents.
        by_label: dict[str, set[str]] = {}
        for link in self.contents():
            by_label.setdefault(link.text.strip(), set()).add(link.href)
        for label, hrefs in by_label.items():
            if len(hrefs) > 1:
                found.append(
                    Anomaly(
                        "LAB003",
                        f"Table of contents shows {label!r} more than once, "
                        f"linking to different sections: {sorted(hrefs)}. "
                        "One section is effectively unlabelled.",
                        {"label": label, "hrefs": sorted(hrefs)},
                        "major",
                    )
                )

        # A module whose heading level differs from its siblings' will not
        # render or navigate consistently. Compare against what this document
        # actually does rather than an assumed h1: nothing says a lab must use
        # any particular level, only that it should be uniform.
        modules = self.modules()
        if len(modules) > 2:
            levels = [m.level for m in modules]
            usual = max(set(levels), key=levels.count)
            for module in modules:
                if module.level != usual:
                    found.append(
                        Anomaly(
                            "LAB003",
                            f"Section {module.text!r} is an <h{module.level}> "
                            f"while the other {len(modules) - 1} contents entries "
                            f"are <h{usual}>; it is structurally inconsistent.",
                            {"id": module.id, "level": module.level, "usual": usual},
                            "minor",
                        )
                    )

        duplicates = {i for i in self.ids if self.ids.count(i) > 1 and i}
        linked = {link.target for link in self.contents()}
        for dup in sorted(duplicates & linked):
            found.append(
                Anomaly(
                    "LAB006",
                    f"Anchor {dup!r} is used by more than one element and is "
                    "linked from the table of contents; the link can only ever "
                    "reach the first one.",
                    {"id": dup},
                    "major",
                )
            )

        for section in self.sections():
            if not self.tasks(section) and section.id:
                heads = {h.text.strip().lower() for h in self.section_headings(section)}
                if "introduction" in heads:
                    continue
                found.append(
                    Anomaly(
                        "LAB003",
                        f"Section {section.text!r} has neither an Introduction "
                        "heading nor numbered tasks, unlike every other section.",
                        {"id": section.id},
                        "minor",
                    )
                )

        return found

    # ---- persistence ----------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "headings": [asdict(h) for h in self.headings],
            "toc": [asdict(t) for t in self.toc],
            "links": self.links,
            "ids": self.ids,
        }

    def save(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=1, ensure_ascii=False), "utf-8")
        return path

    @classmethod
    def from_dict(cls, data: dict) -> Outline:
        return cls(
            title=data.get("title", ""),
            headings=[Heading(**h) for h in data.get("headings", [])],
            toc=[TocLink(**t) for t in data.get("toc", [])],
            links=data.get("links", []),
            ids=data.get("ids", []),
        )

    @classmethod
    def load(cls, path: Path) -> Outline:
        return cls.from_dict(json.loads(Path(path).read_text("utf-8")))

    def to_markdown(self) -> str:
        parts = []
        for h in self.headings:
            parts.append(f"{'#' * h.level} {h.text}".rstrip())
            if h.body:
                parts.append(h.body)
        return "\n\n".join(parts).strip() + "\n"


async def extract(frame) -> Outline:
    """Read the outline out of a live instructions frame."""
    data = await frame.evaluate(_EXTRACT_JS)
    return Outline.from_dict(data)


def _short(anchor: str, limit: int = 28) -> str:
    out = re.sub(r"[^a-z0-9]+", "-", anchor.lower()).strip("-")
    return out[:limit].rstrip("-") or "section"
