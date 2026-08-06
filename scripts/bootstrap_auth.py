"""One-time interactive sign-in to Microsoft Learning Campus.

Opens a real, visible Chromium window. You sign in by hand — including MFA and
any Skillable device-registration email challenge. When you confirm you are
signed in, the browser session is captured and encrypted to your Windows
account with DPAPI, so subsequent validator runs never need your password.

    python scripts/bootstrap_auth.py            # sign in and save
    python scripts/bootstrap_auth.py --status   # report on the saved session
    python scripts/bootstrap_auth.py --clear    # delete the saved session

Re-run whenever the session expires (typically every few days to a few weeks,
depending on tenant Conditional Access policy).

Orientation
-----------
Role:     operator-facing shim over `auth`: one-time interactive sign-in.
Entry:    `main`, `bootstrap`
Talks to: auth, config
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.auth import inspect_session, save_storage_state  # noqa: E402
from lab_validator.config import (  # noqa: E402
    LEARNING_CAMPUS_STATE,
    get_settings,
)

BANNER = "=" * 74


async def bootstrap(start_url: str, keep_open: bool) -> int:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print(
            "Playwright is not installed. Run:\n"
            "    pip install -e .[dev]\n"
            "    python -m playwright install chromium",
            file=sys.stderr,
        )
        return 2

    print(BANNER)
    print("Microsoft Learning Campus — interactive sign-in")
    print(BANNER)
    print(f"Opening: {start_url}\n")
    print("In the browser window that appears:")
    print("  1. Sign in with your Microsoft account (complete MFA).")
    print("  2. Clear any Skillable device-registration email challenge.")
    print("  3. Navigate to your labs list so the session is fully established.")
    print("  4. Come back here and press ENTER.\n")
    print("Your password is never read, stored, or transmitted by this script.\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False, args=["--start-maximized"])
        context = await browser.new_context(
            viewport=None,
            locale="en-GB",
            timezone_id="Europe/London",
        )
        page = await context.new_page()
        await page.goto(start_url, wait_until="domcontentloaded")

        await asyncio.get_running_loop().run_in_executor(
            None, input, "Press ENTER once you are signed in… "
        )

        current = page.url
        state = await context.storage_state()

        cookie_count = len(state.get("cookies", []))
        if cookie_count == 0:
            print("\nNo cookies were captured — sign-in did not complete.", file=sys.stderr)
            if not keep_open:
                await browser.close()
            return 1

        path = save_storage_state(state)
        if not keep_open:
            await browser.close()

    print(f"\nLanded on: {current}")
    print(f"Saved {cookie_count} cookies, DPAPI-encrypted, to:\n    {path}")
    print(f"\nSession status: {inspect_session().describe()}")
    print("\nThis file is gitignored and bound to your Windows account.")
    print("Treat it as a password: it can impersonate you until it expires.")
    return 0


def cmd_status() -> int:
    health = inspect_session()
    print(f"Path   : {LEARNING_CAMPUS_STATE}")
    print(f"Status : {health.describe()}")
    if health.origins:
        print("Origins:")
        for origin in health.origins:
            print(f"  - {origin}")
    return 0 if health.usable else 1


def cmd_clear() -> int:
    if LEARNING_CAMPUS_STATE.exists():
        LEARNING_CAMPUS_STATE.unlink()
        print(f"Deleted {LEARNING_CAMPUS_STATE}")
    else:
        print("Nothing to delete.")
    return 0


def main() -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--status", action="store_true", help="report on the saved session")
    parser.add_argument("--clear", action="store_true", help="delete the saved session")
    parser.add_argument(
        "--url",
        default=settings.learning_campus_url,
        help="sign-in start URL (default: %(default)s)",
    )
    parser.add_argument(
        "--keep-open",
        action="store_true",
        help="leave the browser open after saving (useful for DOM reconnaissance)",
    )
    args = parser.parse_args()

    if args.status:
        return cmd_status()
    if args.clear:
        return cmd_clear()
    return asyncio.run(bootstrap(args.url, args.keep_open))


if __name__ == "__main__":
    raise SystemExit(main())
