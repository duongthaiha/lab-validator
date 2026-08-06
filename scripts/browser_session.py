"""Drive an already-signed-in browser.

    python scripts/browser_session.py --launch        # start the debug browser
    python scripts/browser_session.py --status        # is it reachable? what's open?
    python scripts/browser_session.py --shot          # screenshot the active tab
    python scripts/browser_session.py --goto <url>    # navigate the active tab
    python scripts/browser_session.py --probe         # Skillable lab-client recon

No password is ever stored. You sign in by hand in the debug browser once; the
dedicated profile keeps you signed in, and Skillable's device registration sees
a stable browser fingerprint on every subsequent run.

Orientation
-----------
Role:     operator-facing shim over `browser`: attach to a signed-in browser and recon it.
Entry:    `main`, `cmd_links`, `cmd_probe`, `DUMP_JS`
Talks to: browser, config, discovery
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    PROFILE_DIR,
    attached_context,
    browser_is_running,
    cdp_endpoint,
    clone_profile,
    find_browser,
    launch_debug_browser,
    list_profiles,
    port_is_open,
    resolve_profile,
    script_main,
)
from lab_validator.config import REPO_ROOT, get_settings  # noqa: E402
from lab_validator.discovery import LINKS_JS  # noqa: E402

SHOT_DIR = REPO_ROOT / "artifacts" / "recon"

# Read-only reconnaissance of the Skillable lab client's supported JS API.
# https://docs.skillable.com/docs/lab-client-api-for-lab-delivery-customization
PROBE_JS = """() => {
  const out = {
    url: location.href,
    title: document.title,
    hasApi: typeof window.api !== 'undefined',
    apiVersions: [],
    v1Methods: [],
    frames: [...document.querySelectorAll('iframe')].map(f => ({
      id: f.id, name: f.name, src: (f.src || '').slice(0, 200),
    })),
    canvases: [...document.querySelectorAll('canvas')].map(c => ({
      id: c.id, cls: c.className, w: c.width, h: c.height,
      box: c.getBoundingClientRect().toJSON(),
    })),
    videos: document.querySelectorAll('video').length,
  };
  if (out.hasApi) {
    try { out.apiVersions = Object.keys(window.api); } catch (e) { out.apiErr = String(e); }
    if (window.api.v1) {
      const seen = new Set();
      let o = window.api.v1;
      while (o && o !== Object.prototype) {
        Object.getOwnPropertyNames(o).forEach(k => seen.add(k));
        o = Object.getPrototypeOf(o);
      }
      out.v1Methods = [...seen].filter(k => k !== 'constructor').sort();
    }
  }
  return out;
}"""


async def _with_context(port, fn):
    from playwright.async_api import async_playwright

    async with async_playwright() as pw:
        browser, context = await attached_context(pw, port)
        try:
            return await fn(context)
        finally:
            # Detach only. Never close a browser the user is working in.
            await browser.close()


def cmd_list_profiles(args) -> int:
    profiles = list_profiles(args.browser)
    print(f"{args.browser} profiles on this machine:\n")
    print(f"  {'DIRECTORY':<12} {'NAME':<20} ACCOUNT")
    for p in profiles:
        cookies = p.path / "Network" / "Cookies"
        size = f"{cookies.stat().st_size // 1024} KB" if cookies.exists() else "-"
        print(f"  {p.directory:<12} {p.name:<20} {p.account:<45} {size}")
    print("\nClone the one that's signed into Learning Campus:")
    print('    python scripts/browser_session.py --launch --profile "<account or name>"')
    return 0


def cmd_launch(args) -> int:
    settings = get_settings()
    browser = find_browser(args.browser)
    url = args.goto or settings.learning_campus_url
    profile_directory = "Default"

    if args.profile:
        source = resolve_profile(args.profile, args.browser)
        print(f"Source profile : {source.name}  ({source.account})")
        print(f"               : {source.path}")

        already_cloned = (PROFILE_DIR / source.directory / "Network" / "Cookies").exists()
        if already_cloned and not args.refresh_profile:
            print("Clone          : reusing existing clone (--refresh-profile to re-copy)")
        else:
            if browser_is_running(args.browser):
                print(
                    f"\n  Note: {args.browser} is running. Cookies usually copy cleanly, "
                    "but if\n  the clone turns out signed-out, close all "
                    f"{args.browser} windows and re-run\n  with --refresh-profile.\n"
                )
            print("Clone          : copying session files (caches, history, "
                  "IndexedDB and saved passwords are skipped)…")
            dest, size = clone_profile(source, args.browser, full=args.full_profile)
            print(f"               : {size / 1024 / 1024:.0f} MB -> {dest}")
        profile_directory = source.directory

    print(f"\nBrowser : {browser.name} ({browser.path})")
    print(f"Profile : {PROFILE_DIR}\\{profile_directory}")
    print(f"CDP     : {cdp_endpoint(args.port)}")
    print(f"Opening : {url}\n")

    launch_debug_browser(args.port, args.browser, url, PROFILE_DIR, profile_directory)

    import time

    for _ in range(60):
        if port_is_open(args.port):
            break
        time.sleep(0.5)
    else:
        print("Browser did not open the debug port in time.", file=sys.stderr)
        return 1

    print("Debug port is live.")
    if not args.profile:
        print("\nThis profile is new — sign in now (MFA, device-registration email).")
        print("You only ever have to do this once; the profile keeps you signed in.")
    print("\nLeave this browser open. Then run:")
    print("    python scripts/browser_session.py --status")
    return 0


def cmd_signin(args) -> int:
    """Walk the Learning Campus sign-in chooser as far as automation can go.

    Stops at any interactive challenge (Windows Hello / FIDO, authenticator
    approval, one-time code). Those are hardware- or human-bound by design and
    must be completed by hand in the visible browser — after which the session
    persists in the cloned profile.
    """
    settings = get_settings()
    method = args.signin  # "msa" or "entra"
    label = "Microsoft Account" if method == "msa" else "Entra ID"
    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def _flow(context):
        page = context.pages[args.tab] if context.pages else await context.new_page()
        await page.bring_to_front()

        async def settle(ms=2500):
            try:
                await page.wait_for_load_state("networkidle", timeout=20000)
            except Exception as exc:
                # Long-polling auth pages often never reach networkidle.
                print(f"   (no networkidle: {type(exc).__name__})")
            await page.wait_for_timeout(ms)

        async def shot(name):
            path = SHOT_DIR / f"signin-{name}.png"
            await page.screenshot(path=str(path))
            print(f"    {page.url[:100]}")
            print(f"    -> {path}")

        if "mslearningcampus" not in page.url:
            await page.goto(settings.learning_campus_url, wait_until="domcontentloaded")
            await settle(1500)

        # Step 1 — the header "Login" link, if we are not already on /User/Login.
        if "/User/Login" not in page.url:
            print("1. Login link")
            try:
                await page.get_by_role("link", name="Login").first.click(timeout=10000)
                await settle(1500)
            except Exception as exc:
                print(f"   skipped ({type(exc).__name__})")

        # Step 2 — the hero "Sign In" button opens the method chooser.
        print(f"2. Sign In -> {label}")
        try:
            await page.get_by_role("link", name="Sign In").or_(
                page.get_by_role("button", name="Sign In")
            ).first.click(timeout=10000)
            await settle(1500)
        except Exception as exc:
            print(f"   skipped ({type(exc).__name__})")

        # Step 3 — pick the identity provider.
        try:
            await page.get_by_text(label, exact=True).first.click(timeout=10000)
        except Exception as exc:
            print(f"   chooser not found ({type(exc).__name__})")
        for _ in range(3):
            await settle(2500)

        await shot(method)

        signed_in = "mslearningcampus.com" in page.url and "/User/Login" not in page.url
        print(f"\n   title: {await page.title()}")
        if signed_in:
            print("\n   Signed in. The session now persists in the cloned profile.")
        else:
            print(
                "\n   Stopped at an interactive challenge. Complete it by hand in the\n"
                "   browser window (it is already focused), then run:\n"
                "       python scripts/browser_session.py --status"
            )
        return 0 if signed_in else 3

    return asyncio.run(_with_context(args.port, _flow))


DUMP_JS = """() => {
  const describe = e => ({
    tag: e.tagName,
    type: e.getAttribute('type'),
    text: (e.innerText || e.value || '').trim().slice(0, 60),
    id: e.id || null,
    cls: (e.className || '').toString().slice(0, 80),
    disabled: e.disabled ?? null,
    visible: !!(e.offsetWidth || e.offsetHeight),
    data: Object.fromEntries([...e.attributes]
            .filter(a => a.name.startsWith('data-') || a.name === 'onclick')
            .map(a => [a.name, a.value.slice(0, 120)])),
  });
  return {
    title: document.title,
    url: location.href,
    forms: [...document.querySelectorAll('form')].map(f => ({
      action: f.getAttribute('action'),
      method: f.getAttribute('method'),
      inputs: [...f.querySelectorAll('input,select,textarea')].map(describe),
    })),
    controls: [...document.querySelectorAll(
      'button,input[type=button],input[type=submit],[role=button],[onclick]')]
      .map(describe),
    frames: [...document.querySelectorAll('iframe')].map(f => ({
      src: f.getAttribute('src'), id: f.id || null,
      w: f.clientWidth, h: f.clientHeight,
    })),
  };
}"""


def cmd_links(args) -> int:
    """Enumerate every (text, href) pair on a tab.

    Dropdown parents in the Learning Campus nav are not reachable by clicking,
    so link enumeration is the reliable way to discover routes.
    """

    async def _links(context):
        page = context.pages[args.tab] if context.pages else await context.new_page()
        # The shared extractor keeps untexted anchors and a generous slice; this
        # view has always shown only labelled links, truncated to 60.
        links = [e for e in await page.evaluate(LINKS_JS) if e["text"]]
        print(f"{await page.title()}\n{page.url}\n")
        for entry in links:
            text = entry["text"][:60]
            if args.filter and args.filter.lower() not in (
                text + entry["href"]
            ).lower():
                continue
            mark = " " if entry["visible"] else "."
            print(f" {mark} {text:<45} {entry['href']}")
        print(f"\n{len(links)} link(s).  '.' = not visible (e.g. collapsed nav)")
        return 0

    return asyncio.run(_with_context(args.port, _links))


def cmd_dump(args) -> int:
    """Dump forms, controls and frames for a tab, as JSON.

    This is what reveals controls that are present but hidden -- e.g. a launch
    button rendered with ``display:none`` but ``disabled === false``.
    """

    async def _dump(context):
        page = context.pages[args.tab] if context.pages else await context.new_page()
        data = await page.evaluate(DUMP_JS)
        text = json.dumps(data, indent=2)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"{data['title']}\n{data['url']}\n -> {out}")
        else:
            print(text)
        return 0

    return asyncio.run(_with_context(args.port, _dump))


def cmd_click(args) -> int:
    """Click an element by its accessible name or visible text, then screenshot."""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%H%M%S")
    target = args.click

    async def _click(context):
        page = context.pages[args.tab] if context.pages else await context.new_page()
        await page.bring_to_front()

        candidates = [
            page.get_by_role("link", name=target, exact=False),
            page.get_by_role("button", name=target, exact=False),
            page.get_by_text(target, exact=False),
        ]
        for locator in candidates:
            try:
                await locator.first.click(timeout=8000)
                break
            except Exception as exc:
                print(f"   (no match: {type(exc).__name__})")
                continue
        else:
            print(f"Nothing clickable matched {target!r}.", file=sys.stderr)
            return 1

        try:
            await page.wait_for_load_state("networkidle", timeout=20000)
        except Exception as exc:
            print(f"(no networkidle: {type(exc).__name__})")
        await page.wait_for_timeout(args.wait)

        out = SHOT_DIR / f"click-{stamp}.png"
        await page.screenshot(path=str(out), full_page=args.full_page)
        print(f"clicked : {target!r}")
        print(f"title   : {await page.title()}")
        print(f"url     : {page.url[:120]}")
        print(f"         -> {out}")
        return 0

    return asyncio.run(_with_context(args.port, _click))


def cmd_status(args) -> int:
    print(f"Profile : {PROFILE_DIR}  ({'exists' if PROFILE_DIR.exists() else 'not created'})")
    print(f"CDP     : {cdp_endpoint(args.port)}")
    if not port_is_open(args.port):
        print("Status  : not reachable — run --launch first")
        return 1

    async def _probe(context):
        pages = context.pages
        print(f"Status  : reachable, {len(pages)} tab(s) open")
        cookies = await context.cookies()
        domains = sorted({c["domain"].lstrip(".") for c in cookies})
        print(f"Cookies : {len(cookies)} across {len(domains)} domains")
        for d in domains:
            if any(k in d for k in ("skillable", "labondemand", "microsoft", "azure", "live")):
                print(f"          · {d}")
        print("Tabs:")
        for i, p in enumerate(pages):
            print(f"  [{i}] {(await p.title())[:60]!r}")
            print(f"      {p.url[:110]}")
        return 0

    return asyncio.run(_with_context(args.port, _probe))


def cmd_goto(args) -> int:
    async def _go(context):
        page = context.pages[args.tab] if context.pages else await context.new_page()
        await page.goto(args.goto, wait_until="domcontentloaded")
        await page.bring_to_front()
        print(f"[{args.tab}] {await page.title()}")
        print(f"    {page.url}")
        return 0

    return asyncio.run(_with_context(args.port, _go))


def cmd_shot(args) -> int:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%H%M%S")

    async def _shot(context):
        pages = context.pages
        if not pages:
            print("No tabs open.", file=sys.stderr)
            return 1
        targets = pages if args.all_tabs else [pages[args.tab]]
        for i, page in enumerate(targets):
            idx = i if args.all_tabs else args.tab
            out = SHOT_DIR / f"tab{idx}-{stamp}.png"
            await page.screenshot(path=str(out), full_page=args.full_page)
            print(f"[{idx}] {await page.title()}")
            print(f"     {page.url[:110]}")
            print(f"     -> {out}")
        return 0

    return asyncio.run(_with_context(args.port, _shot))


def cmd_probe(args) -> int:
    SHOT_DIR.mkdir(parents=True, exist_ok=True)

    async def _probe(context):
        pages = context.pages
        if not pages:
            print("No tabs open.", file=sys.stderr)
            return 1
        report = []
        for i, page in enumerate(pages):
            try:
                info = await page.evaluate(PROBE_JS)
            except Exception as exc:
                info = {"url": page.url, "error": str(exc)[:200]}
            info["tabIndex"] = i
            report.append(info)

            print(f"\n[{i}] {info.get('title', '?')[:70]}")
            print(f"    {info.get('url', '')[:110]}")
            if "error" in info:
                print(f"    probe failed: {info['error']}")
                continue
            print(f"    window.api present : {info['hasApi']}")
            if info["hasApi"]:
                print(f"    api versions       : {info['apiVersions']}")
                print(f"    v1 methods ({len(info['v1Methods'])}):")
                for m in info["v1Methods"]:
                    print(f"      · {m}")
            print(f"    iframes: {len(info['frames'])}  canvases: {len(info['canvases'])}"
                  f"  videos: {info['videos']}")
            for f in info["frames"][:6]:
                print(f"      iframe id={f['id']!r} src={f['src'][:80]}")
            for c in info["canvases"][:4]:
                print(f"      canvas id={c['id']!r} cls={c['cls'][:40]!r} "
                      f"{c['w']}x{c['h']}")

        out = SHOT_DIR / "probe.json"
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"\nFull probe written to {out}")
        return 0

    return asyncio.run(_with_context(args.port, _probe))


@script_main
def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--launch", action="store_true", help="start the debug browser")
    p.add_argument("--list-profiles", action="store_true", help="show real browser profiles")
    p.add_argument(
        "--profile",
        metavar="NAME",
        help="clone a real profile by account, display name, or directory "
        '(e.g. --profile "haduong@microsoft.com")',
    )
    p.add_argument(
        "--refresh-profile",
        action="store_true",
        help="re-copy the source profile even if a clone already exists",
    )
    p.add_argument(
        "--full-profile",
        action="store_true",
        help="mirror the entire source profile rather than just session files "
        "(much larger; only needed if a lean clone comes up signed out)",
    )
    p.add_argument("--status", action="store_true", help="show reachability and open tabs")
    p.add_argument(
        "--signin",
        choices=["msa", "entra"],
        help="drive the Learning Campus sign-in chooser; 'msa' for a personal "
        "Microsoft Account, 'entra' for a work/school account",
    )
    p.add_argument("--shot", action="store_true", help="screenshot a tab")
    p.add_argument("--probe", action="store_true", help="probe for the Skillable lab client API")
    p.add_argument("--goto", metavar="URL", help="navigate a tab")
    p.add_argument("--click", metavar="TEXT", help="click by accessible name or text")
    p.add_argument("--links", action="store_true", help="enumerate (text, href) pairs")
    p.add_argument("--dump", action="store_true", help="dump forms/controls/frames as JSON")
    p.add_argument("--filter", metavar="TEXT", help="substring filter for --links")
    p.add_argument("--out", metavar="PATH", help="write --dump JSON to a file")
    p.add_argument("--wait", type=int, default=2500, help="ms to settle after a click")
    p.add_argument("--tab", type=int, default=0, help="tab index (default 0)")
    p.add_argument("--all-tabs", action="store_true", help="apply to every tab")
    p.add_argument("--full-page", action="store_true", help="full-page screenshot")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    p.add_argument("--browser", choices=["edge", "chrome"], default="edge")
    args = p.parse_args()

    if args.list_profiles:
        return cmd_list_profiles(args)
    if args.launch:
        return cmd_launch(args)
    if args.signin:
        return cmd_signin(args)
    if args.probe:
        return cmd_probe(args)
    if args.shot:
        return cmd_shot(args)
    if args.goto:
        return cmd_goto(args)
    if args.click:
        return cmd_click(args)
    if args.links:
        return cmd_links(args)
    if args.dump:
        return cmd_dump(args)
    return cmd_status(args)


if __name__ == "__main__":
    raise SystemExit(main())
