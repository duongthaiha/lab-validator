"""Playwright browser session management for Microsoft Learning Campus.

Microsoft Learning Campus authenticates through Entra ID / MSA (which enforces
MFA) and Skillable layers Device Registration on top, so a stored username and
password cannot log the validator in. Instead we use Playwright's documented
``storageState`` pattern — https://playwright.dev/docs/auth — capturing a real
interactive sign-in once and replaying the resulting session.

The saved state is encrypted at rest with Windows DPAPI. Playwright warns that
a storageState file contains cookies and headers capable of impersonating the
account, so it is treated as a password-equivalent secret throughout.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import LEARNING_CAMPUS_STATE, REPO_ROOT, get_settings
from .secrets_store import (
    SecretStoreError,
    assert_not_tracked,
    read_secret_json,
    write_secret_json,
)

#: Refuse to use a session whose cookies expire within this window.
_MIN_REMAINING = _dt.timedelta(minutes=10)


@dataclass(frozen=True)
class SessionHealth:
    """Summary of a stored session, safe to log (contains no secret values)."""

    exists: bool
    cookie_count: int
    origins: tuple[str, ...]
    earliest_expiry: _dt.datetime | None
    usable: bool
    reason: str

    def describe(self) -> str:
        if not self.exists:
            return "no saved session"
        expiry = (
            self.earliest_expiry.isoformat(timespec="minutes")
            if self.earliest_expiry
            else "session-only"
        )
        return (
            f"{self.cookie_count} cookies across {len(self.origins)} origins, "
            f"earliest expiry {expiry} — {self.reason}"
        )


def _earliest_expiry(state: dict[str, Any]) -> _dt.datetime | None:
    stamps = [
        c["expires"]
        for c in state.get("cookies", [])
        # Playwright uses -1 for session cookies
        if isinstance(c.get("expires"), (int, float)) and c["expires"] > 0
    ]
    if not stamps:
        return None
    return _dt.datetime.fromtimestamp(min(stamps), tz=_dt.UTC)


def save_storage_state(state: dict[str, Any], path: Path = LEARNING_CAMPUS_STATE) -> Path:
    """Encrypt and persist a Playwright ``storageState`` payload."""
    assert_not_tracked(path, REPO_ROOT)
    return write_secret_json(path, state)


def load_storage_state(path: Path = LEARNING_CAMPUS_STATE) -> dict[str, Any]:
    """Decrypt the stored session, raising if it is missing or expired."""
    state = read_secret_json(path)
    health = inspect_session(path)
    if not health.usable:
        raise SecretStoreError(
            f"Stored session is not usable ({health.reason}). Refresh it with:\n"
            "    python scripts/bootstrap_auth.py"
        )
    return state


def inspect_session(path: Path = LEARNING_CAMPUS_STATE) -> SessionHealth:
    """Report on the stored session without raising. Safe for status commands."""
    path = Path(path)
    if not path.exists():
        return SessionHealth(False, 0, (), None, False, "not bootstrapped")

    try:
        state = read_secret_json(path)
    except SecretStoreError as exc:
        return SessionHealth(True, 0, (), None, False, f"undecryptable: {exc}")

    cookies = state.get("cookies", [])
    origins = tuple(o.get("origin", "") for o in state.get("origins", []))
    expiry = _earliest_expiry(state)

    if not cookies:
        return SessionHealth(True, 0, origins, expiry, False, "no cookies captured")

    now = _dt.datetime.now(_dt.UTC)
    if expiry is not None and expiry - now < _MIN_REMAINING:
        return SessionHealth(True, len(cookies), origins, expiry, False, "expired or expiring")

    return SessionHealth(True, len(cookies), origins, expiry, True, "ok")


async def new_authenticated_context(browser, **kwargs):
    """Create a Playwright ``BrowserContext`` carrying the saved session.

    Extra keyword arguments are forwarded to ``browser.new_context``.
    """
    settings = get_settings()
    context = await browser.new_context(
        storage_state=load_storage_state(),
        locale=kwargs.pop("locale", "en-GB"),
        timezone_id=kwargs.pop("timezone_id", "Europe/London"),
        viewport=kwargs.pop("viewport", {"width": 1600, "height": 900}),
        **kwargs,
    )
    context.set_default_timeout(30_000)
    _ = settings  # reserved for future per-run configuration
    return context
