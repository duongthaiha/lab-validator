"""Settings the tool actually reads.

This was once a `pydantic-settings` model with fourteen fields covering a
Skillable Connect API, a Skillable TMS API, Azure subscription/tenant ids and a
headless/log-level/artifact-retention runtime block. Exactly one of them was
ever read: `learning_campus_url`. The rest described an integration the tool
does not have -- it drives a real browser rather than calling Skillable's API --
so they were a config surface promising capabilities that did not exist, plus a
dependency to install for the privilege.

What remains is one setting, still overridable from the environment or a `.env`
file the same way, and the two paths for the encrypted Learning Campus session.
`get_settings` keeps its name and its `.learning_campus_url` attribute so the
three call sites did not have to change.

Orientation
-----------
Role:     the one setting the tool reads, plus the paths of the encrypted session.
Entry:    `get_settings`, `Settings`, `LEARNING_CAMPUS_STATE`
Talks to: paths
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from .paths import REPO_ROOT

#: DPAPI-encrypted Playwright storageState for Microsoft Learning Campus.
AUTH_DIR = REPO_ROOT / ".auth"
LEARNING_CAMPUS_STATE = AUTH_DIR / "mslearningcampus.state.enc"

DEFAULT_LEARNING_CAMPUS_URL = "https://mslearningcampus.com/Pages/ms-learningcampus"


def _dotenv(name: str) -> str | None:
    """Read one key from `.env`, if there is one.

    Deliberately not a parser: `.env` here carries a single optional URL, and a
    real environment variable wins anyway. Quoting and interpolation are not
    supported because nothing in the file needs them.
    """
    path = REPO_ROOT / ".env"
    if not path.is_file():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == name:
            return value.strip().strip("'\"") or None
    return None


@dataclass(frozen=True)
class Settings:
    learning_campus_url: str = DEFAULT_LEARNING_CAMPUS_URL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    url = os.environ.get("LV_LEARNING_CAMPUS_URL") or _dotenv("LV_LEARNING_CAMPUS_URL")
    return Settings(learning_campus_url=url or DEFAULT_LEARNING_CAMPUS_URL)
