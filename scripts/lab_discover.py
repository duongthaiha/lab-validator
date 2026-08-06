"""Discover launchable labs in a signed-in Learning Campus session.

This is the onboarding entry point for a new workshop:

    python scripts/lab_discover.py --list
    python scripts/lab_discover.py --scaffold 5928204
    python scripts/lab_run.py --check-target <slug>

It reads the catalogue with the session that is already in the attached
browser. It never signs in and never handles a password: TMS auth is a
memory-only cookie behind an interactive challenge, so a human does that once
and the agent attaches afterwards.

Orientation
-----------
Role:     operator-facing shim over `discovery`: list enrolments, scaffold a target.
Entry:    `main`, `cmd_list`, `cmd_scaffold`
Talks to: browser, discovery, targets
"""

from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

#: `--help` is read by operators; the Orientation block is written for
#: developers reading the file. argparse also reflows whatever it is handed, so
#: leaving the block in turned a formatted table into a paragraph of mush. Cut
#: it off -- `test_operator_help_never_shows_the_developer_block` fails if this
#: stops working.
HELP_DOC = __doc__.split("\nOrientation\n")[0].strip()

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
    script_main,
)
from lab_validator.discovery import (  # noqa: E402
    HREFS_JS,
    LINKS_JS,
    Enrolment,
    descriptor_for,
    parse_enrolments,
    slugify,
    write_scaffold,
)
from lab_validator.targets import Target, TargetError  # noqa: E402

CAMPUS = "https://mslearningcampus.com"
#: The public landing page. The training list is NOT at a fixed path -- it is
#: user-scoped (`/User/CurrentTraining/<userId>`), so it is resolved by following
#: the "My Training" link from here rather than guessed.
#:
#: Note for anyone tempted to hardcode `/User/Dashboard`: it exists and redirects
#: to /User/Login when signed out, which looks exactly like the right page. It
#: still redirects to login when signed *in*. "Exists behind auth" is not the
#: same as "is the page you want" -- follow the nav instead.
HOME_URL = f"{CAMPUS}/Pages/ms-learningcampus"
TRAINING_HREF = re.compile(r"/User/CurrentTraining/\d+", re.I)
TARGETS_DIR = REPO_ROOT / "targets"


async def session_page(context):
    """Return a tab that actually holds a Learning Campus session, or ``None``.

    Tabs in the attached browser do **not** necessarily share a cookie jar. Edge
    can have windows belonging to different profiles open at once, and
    ``connect_over_cdp`` reports them all under a single context -- so
    ``context.pages[0]`` can bounce to /User/Login while a fully signed-in tab
    sits right beside it. Observed live on 2026-07-30: page 0 redirected to
    login, page 1 held the enrolment list, one reported context.

    A `/User/Logout` anchor is the marker: the nav only offers it to a signed-in
    user, and unlike a URL redirect it survives being read from a cached page.
    """
    for page in context.pages:
        if "mslearningcampus.com" not in page.url:
            continue
        try:
            hrefs = await page.evaluate(HREFS_JS)
        except Exception as exc:  # noqa: BLE001,S112 - a closing tab is simply not the one
            print(f"   (skipping {page.url[:60]}: {type(exc).__name__})")
            continue
        if any("/User/Logout" in href for href in hrefs):
            return page
    return None


class NotSignedIn(BrowserError):
    """The attached browser has no Learning Campus session."""


class PageNotFound(BrowserError):
    """The URL we asked for does not exist on this tenant."""


SIGNIN_HELP = (
    "Not signed in.\n"
    f"  Sign in by hand at {CAMPUS}/User/Login in the attached browser,\n"
    "  then re-run this command. TMS has no SSO and its session cookie is\n"
    "  memory-only, so there is no unattended path -- by design."
)


async def collect(port: int, url: str | None) -> tuple[list[Enrolment], str]:
    """Find the training list and parse out the enrolments.

    With no ``url``, the list is located by following the "My Training" link
    from the public home page, because its path carries the signed-in user's id
    and therefore cannot be hardcoded.

    Three outcomes are deliberately kept apart, because they need three
    different actions and collapsing them into "no enrolments found" sends the
    reader looking for the wrong problem: not signed in, page does not exist,
    and signed in with genuinely nothing enrolled.
    """
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, port)
        try:
            page = await session_page(context)
            if page is None:
                raise NotSignedIn(SIGNIN_HELP)
            await page.bring_to_front()

            async def visit(target: str) -> None:
                await page.goto(target, wait_until="domcontentloaded")
                try:
                    await page.wait_for_load_state("networkidle", timeout=15000)
                except Exception as exc:  # noqa: BLE001 - long-polling pages never settle
                    print(f"   (no networkidle: {type(exc).__name__}; reading the DOM anyway)")
                await page.wait_for_timeout(1200)
                if "/Error/NotFound" in page.url:
                    raise PageNotFound(
                        f"{target} does not exist on this tenant "
                        f"(redirected to {page.url}).\n"
                        "  Pass --url with the page that lists your trainings."
                    )
                if "/User/Login" in page.url:
                    raise NotSignedIn(SIGNIN_HELP)

            if url:
                await visit(url)
            else:
                # The training list is user-scoped, so follow the nav rather than
                # guessing a path. Skip the hop if we are already on it.
                if not TRAINING_HREF.search(page.url):
                    links = await page.evaluate(LINKS_JS)
                    hrefs = [
                        link["href"] for link in links
                        if link.get("href") and TRAINING_HREF.search(link["href"])
                    ]
                    if not hrefs:
                        raise PageNotFound(
                            f"Signed in, but no 'My Training' link on {page.url}.\n"
                            "  Pass --url with the page that lists your trainings."
                        )
                    await visit(urljoin(CAMPUS, hrefs[0]))

            links = await page.evaluate(LINKS_JS)
            return parse_enrolments(links), page.url
        finally:
            await browser.close()


def cmd_list(args) -> int:
    enrolments, url = asyncio.run(collect(args.port, args.url))
    if not enrolments:
        print(f"Signed in, but no enrolments are linked from {url}")
        print("  If your trainings live on another page, pass --url to point at it.")
        return 1
    print(f"{len(enrolments)} enrolment(s) at {url}\n")
    any_known = False
    for e in enrolments:
        # Match on identity, not on the derived slug: a curated descriptor is
        # usually named more tersely than its workshop title.
        existing = descriptor_for(e, TARGETS_DIR)
        any_known = any_known or bool(existing)
        note = "  (already onboarded)" if existing else ""
        print(f" {'*' if existing else ' '} {e}")
        print(f"     slug: {existing or slugify(e.title)}{note}")
    if any_known:
        print("\n* = a descriptor already exists in targets/")
    print(f"\nScaffold one with:\n    python {rel(__file__)} --scaffold <enrolment>")
    return 0


def cmd_scaffold(args) -> int:
    enrolments, url = asyncio.run(collect(args.port, args.url))
    # "No enrolments on this page" and "that enrolment is not yours" are
    # different problems with different fixes; saying the second when the first
    # is true sends the reader to inspect their account instead of the page.
    if not enrolments:
        print(f"Signed in, but no enrolments are linked from {url}", file=sys.stderr)
        print("  If your trainings live on another page, pass --url.", file=sys.stderr)
        return 1
    match = next((e for e in enrolments if e.enrolment == args.scaffold), None)
    if match is None:
        print(f"No enrolment {args.scaffold} in this account. Found:", file=sys.stderr)
        for e in enrolments:
            print(f"  {e.enrolment}  {e.title[:60]}", file=sys.stderr)
        return 1

    try:
        path = write_scaffold(match, TARGETS_DIR, slug=args.slug, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(exc, file=sys.stderr)
        return 1

    slug = path.stem
    print(f"Wrote {path.relative_to(REPO_ROOT)}")
    # Inspect, not load: a fresh scaffold is *meant* to be incomplete, and the
    # list of what is missing is the useful output here, not an exception.
    try:
        target = Target.inspect(slug, root=TARGETS_DIR)
    except TargetError as exc:
        # The scaffold wrote something unloadable -- that is a bug here, not in
        # the user's input, so say so plainly rather than dying in a traceback.
        print(f"\nBUG: the generated descriptor does not load:\n{exc}", file=sys.stderr)
        return 1
    todos = [
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith("# TODO ")
    ]
    print(f"\n{len(todos)} value(s) still need filling in:")
    for line in todos:
        print(f"  {line[2:]}")
    if target.problems:
        print("\nValidator says:")
        for p in target.problems:
            print(f"  {p}")
    print(f"\nWhen done:\n    python scripts/lab_run.py --check-target {slug}")
    return 0


def rel(path: str) -> str:
    return str(Path(path).resolve().relative_to(REPO_ROOT)).replace("\\", "/")


@script_main
def main() -> int:
    p = argparse.ArgumentParser(
        description="Discover launchable labs and scaffold a target descriptor.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=HELP_DOC,
    )
    p.add_argument("--list", action="store_true", help="list enrolments (default)")
    p.add_argument(
        "--scaffold",
        type=int,
        metavar="ENROLMENT",
        help="write targets/<slug>.toml for this enrolment id",
    )
    p.add_argument("--slug", help="override the generated slug")
    p.add_argument("--overwrite", action="store_true", help="replace an existing descriptor")
    p.add_argument("--url", help="read enrolments from this page instead of following My Training")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    if args.scaffold is not None:
        return cmd_scaffold(args)
    return cmd_list(args)


if __name__ == "__main__":
    raise SystemExit(main())
