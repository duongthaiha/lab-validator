#!/usr/bin/env python3
"""Install the lab-validator CLI that ships alongside this skill.

Works identically from a clone and from an extracted `.skill` archive, because
in both cases the skill root is the project root -- that is the point of the
repository *being* the skill.
"""

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
        "--skip-browser",
        action="store_true",
        help="do not install the Playwright Chromium browser",
    )
    args = parser.parse_args()

    skill_root = Path(__file__).resolve().parents[1]
    if not (skill_root / "pyproject.toml").is_file():
        parser.error(f"{skill_root} does not look like a lab-validator skill: no pyproject.toml")

    subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(skill_root)],
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
