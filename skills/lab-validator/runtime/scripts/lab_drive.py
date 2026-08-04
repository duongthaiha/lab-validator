"""Drive a running lab: inspect state, read instructions, control the VM.

Examples
--------
    python scripts/lab_drive.py --state
    python scripts/lab_drive.py --screen
    python scripts/lab_drive.py --page 1
    python scripts/lab_drive.py --creds
    python scripts/lab_drive.py --click 512,384 --screen
    python scripts/lab_drive.py --type "notepad" --key Enter --screen
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from playwright.async_api import async_playwright  # noqa: E402

from lab_validator.browser import (  # noqa: E402
    DEFAULT_CDP_PORT,
    BrowserError,
    attached_context,
)
from lab_validator.labclient import LabClient  # noqa: E402

SHOT_DIR = Path(__file__).resolve().parents[1] / "artifacts" / "vm"


async def run(args) -> int:
    async with async_playwright() as pw:
        browser, context = await attached_context(pw, args.port)
        try:
            lab = LabClient.find(context)
            await lab.page.bring_to_front()

            if args.state:
                status = await lab.connection_status()
                print(f"instance : {lab.instance_id}")
                print(f"remaining: {await lab.minutes_remaining()} min")
                print(f"page     : {await lab.page_index()}")
                print(f"env      : {json.dumps(status)}")
                print(f"frames   : {[f.name or '(top)' for f in lab.page.frames]}")

            if args.creds:
                creds = await lab.credentials()
                print(f"{'scope':<22} {'label':<14} value (redacted)")
                print("-" * 62)
                for c in creds:
                    print(f"{c.scope[:21]:<22} {c.label[:13]:<14} {c.redacted()}")
                await lab.show_instructions()

            if args.page is not None:
                await lab.goto_page(args.page)
                text = await lab.instructions_text()
                actual = await lab.page_index()
                print(f"--- instruction page {actual} ({len(text)} chars) ---")
                print(text[: args.chars])

            if args.click:
                x, y = (int(v) for v in args.click.split(","))
                await lab.click(x, y)
                print(f"clicked VM ({x}, {y})")

            if args.focus:
                await lab.focus_vm()
                print("focused VM canvas")

            if args.type:
                await lab.type(args.type)
                print(f"typed {len(args.type)} chars into the VM")

            if args.type_cred:
                value = await lab.credential_value(args.type_cred)
                await lab.type(value)
                print(f"typed credential {args.type_cred!r} into the VM ({len(value)} chars)")

            if args.key:
                await lab.key(*args.key)
                print(f"pressed {', '.join(args.key)}")

            if args.wait:
                await lab.page.wait_for_timeout(args.wait)

            if args.screen:
                stamp = dt.datetime.now().strftime("%H%M%S")
                out = await lab.screen(SHOT_DIR / f"{args.label or 'vm'}-{stamp}.png")
                print(f"-> {out}")
            return 0
        finally:
            await browser.close()


def main() -> int:
    p = argparse.ArgumentParser(description="Drive a running Skillable lab.")
    p.add_argument("--state", action="store_true", help="show lab and env state")
    p.add_argument("--creds", action="store_true", help="list credentials (redacted)")
    p.add_argument("--page", type=int, help="go to an instruction page and print it")
    p.add_argument("--chars", type=int, default=4000, help="chars of page text to print")
    p.add_argument("--screen", action="store_true", help="capture the VM screen")
    p.add_argument("--label", help="filename label for --screen")
    p.add_argument("--click", metavar="X,Y", help="click at VM coordinates")
    p.add_argument("--focus", action="store_true", help="click the centre of the VM")
    p.add_argument("--type", metavar="TEXT", help="send text into the VM")
    p.add_argument(
        "--type-cred",
        metavar="SCOPE/LABEL",
        help="send a Resources-tab credential into the VM without printing it "
        "(e.g. 'Azure Portal/Password')",
    )
    p.add_argument("--key", nargs="+", metavar="KEY", help="press keys, in order")
    p.add_argument("--wait", type=int, default=0, help="ms to wait before --screen")
    p.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
    args = p.parse_args()

    if not any(
        [args.state, args.creds, args.page is not None, args.screen, args.click,
         args.focus, args.type, args.type_cred, args.key]
    ):
        args.state = True

    try:
        return asyncio.run(run(args))
    except BrowserError as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
