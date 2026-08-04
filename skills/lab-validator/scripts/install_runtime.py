#!/usr/bin/env python3
"""Install the CLI runtime bundled inside the portable skill archive."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install the lab-validator CLI bundled with this skill."
    )
    parser.add_argument(
        "--without-agent",
        action="store_true",
        help="install the manual CLI without the GitHub Copilot SDK extra",
    )
    parser.add_argument(
        "--skip-browser",
        action="store_true",
        help="do not install the Playwright Chromium browser",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    runtime = skill_root / "runtime"
    if not (runtime / "pyproject.toml").is_file():
        parser.error(
            "this skill has no prepared runtime; run `lab-validator prepare-skill` "
            "in the source checkout before packaging"
        )

    target = str(runtime) + ("" if args.without_agent else "[agent]")
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", target],
        check=True,
    )
    if not args.skip_browser:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )

    print("lab-validator runtime installed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
