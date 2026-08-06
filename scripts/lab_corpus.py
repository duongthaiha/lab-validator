"""Extract and inspect a lab's instruction outline.

    python scripts/lab_corpus.py --extract          # from the live lab
    python scripts/lab_corpus.py --segments         # show derived segments
    python scripts/lab_corpus.py --anomalies        # structural problems
    python scripts/lab_corpus.py --section s07      # print one section

Orientation
-----------
Role:     operator-facing shim over `corpus`: extract and inspect the instruction outline.
Entry:    `main`, `do_extract`, `load`
Talks to: browser, corpus, labclient, paths
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
    script_main,
)
from lab_validator.corpus import Outline, extract  # noqa: E402
from lab_validator.labclient import LabClient  # noqa: E402
from lab_validator.paths import MARKDOWN, OUTLINE  # noqa: E402


async def do_extract(port: int) -> Outline:
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, port)
        try:
            lab = LabClient.find(context)
            outline = await extract(lab.instructions)
            outline.save(OUTLINE)
            MARKDOWN.write_text(outline.to_markdown(), encoding="utf-8")
            print(f"instance : {lab.instance_id}")
            print(f"headings : {len(outline.headings)}")
            print(f"toc      : {len(outline.toc)} in-page links")
            print(f"sections : {len(outline.sections())}")
            print(f"-> {OUTLINE}")
            print(f"-> {MARKDOWN}  ({len(outline.to_markdown()):,} chars)")
            return outline
        finally:
            await browser.close()


def load() -> Outline:
    if not OUTLINE.exists():
        raise BrowserError(f"No outline at {OUTLINE}. Run with --extract first.")
    return Outline.load(OUTLINE)


@script_main
def main() -> int:
    p = argparse.ArgumentParser(description="Inspect a lab's instruction outline.")
    p.add_argument("--extract", action="store_true", help="read from the live lab")
    p.add_argument("--segments", action="store_true", help="list derived segments")
    p.add_argument("--anomalies", action="store_true", help="list structural problems")
    p.add_argument("--outline", action="store_true", help="print the heading tree")
    p.add_argument("--section", metavar="ID", help="print one section by segment id or anchor")
    p.add_argument("--tasks", action="store_true", help="with --section, list tasks only")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    outline = asyncio.run(do_extract(args.port)) if args.extract else load()

    if args.outline:
        for h in outline.headings:
            if h.level <= 3:
                print(f"{'  ' * (h.level - 1)}h{h.level} {h.text[:70]}  [{h.id[:40]}]")

    if args.segments:
        segments = outline.segments()
        print(f"{'id':<34} {'module':<26} title")
        print("-" * 100)
        for s in segments:
            print(f"{s.id:<34} {(s.module or '-')[:25]:<26} {s.title[:38]}")
        print(f"\n{len(segments)} segments")

    if args.anomalies:
        found = outline.anomalies()
        for a in found:
            print(f"[{a.code}] {a.severity:<8} {a.message}")
        print(f"\n{len(found)} structural anomalies")

    if args.section:
        needle = args.section.lstrip("#")
        match = None
        for seg in outline.segments():
            if needle in (seg.id, (seg.anchor or "").lstrip("#")) or seg.id.startswith(needle):
                match = outline.section_by_anchor((seg.anchor or "").lstrip("#"))
                break
        if match is None:
            match = outline.by_id(needle)
        if match is None:
            print(f"no section matching {args.section!r}", file=sys.stderr)
            return 1
        if args.tasks:
            for t in outline.tasks(match):
                print(f"  {t.text}")
        else:
            print(outline.section_text(match))

    if not any([args.extract, args.segments, args.anomalies, args.outline, args.section]):
        print(f"{len(outline.headings)} headings, {len(outline.sections())} sections")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
