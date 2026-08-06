"""Playwright browser session management for Microsoft Learning Campus.

Microsoft Learning Campus authenticates through Entra ID / MSA (which enforces
MFA) and Skillable layers Device Registration on top, so a stored username and
password cannot log the validator in. Instead we use Playwright's documented
``storageState`` pattern — https://playwright.dev/docs/auth — capturing a real
interactive sign-in once and replaying the resulting session.

The saved state is encrypted at rest with Windows DPAPI. Playwright warns that
a storageState file contains cookies and headers capable of impersonating the
account, so it is treated as a password-equivalent secret throughout.

The DPAPI layer used to be its own module (`secrets_store.py`). It had exactly
one caller -- this file -- and the split invited the question "which of these
two modules owns the session file?" when the answer was always "both, jointly".
It now lives here, above the session code that uses it.
"""

from __future__ import annotations

import datetime as _dt
import json
import platform
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import LEARNING_CAMPUS_STATE, REPO_ROOT

# Application-specific entropy. Mixed into DPAPI so that another process running
# as the same user cannot decrypt these blobs without also knowing this value.
_ENTROPY = b"lab-validator/v1"

_IS_WINDOWS = platform.system() == "Windows"


class SecretStoreError(RuntimeError):
    """Raised when a secret cannot be protected or recovered."""


def _require_dpapi():
    if not _IS_WINDOWS:
        raise SecretStoreError(
            "DPAPI-encrypted secret files are Windows-only. On Linux/macOS run "
            "the validator with secrets injected as environment variables."
        )
    try:
        import win32crypt  # type: ignore[import-not-found]
    except ImportError as exc:  # pragma: no cover - depends on install
        raise SecretStoreError(
            "pywin32 is required for encrypted secret storage. Install it with:\n"
            "    pip install pywin32"
        ) from exc
    return win32crypt


def protect(data: bytes) -> bytes:
    """Encrypt ``data`` against the current Windows user account."""
    win32crypt = _require_dpapi()
    return win32crypt.CryptProtectData(data, "lab-validator", _ENTROPY, None, None, 0)


def unprotect(blob: bytes) -> bytes:
    """Decrypt a blob previously produced by :func:`protect`."""
    win32crypt = _require_dpapi()
    try:
        _description, plaintext = win32crypt.CryptUnprotectData(
            blob, _ENTROPY, None, None, 0
        )
    except Exception as exc:  # pragma: no cover - depends on OS state
        raise SecretStoreError(
            "Could not decrypt the secret file. DPAPI blobs are bound to the "
            "Windows user and machine that created them — if you changed "
            "machine or user profile, re-run: python scripts/bootstrap_auth.py"
        ) from exc
    return plaintext


def _harden(path: Path) -> None:
    """Best-effort: strip group/other permissions from a secret file."""
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def write_secret_json(path: Path, payload: Any) -> Path:
    """Serialise ``payload`` to JSON, encrypt it, and write it to ``path``."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blob = protect(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    path.write_bytes(blob)
    _harden(path)
    return path


def read_secret_json(path: Path) -> Any:
    """Read and decrypt a JSON payload written by :func:`write_secret_json`."""
    path = Path(path)
    if not path.exists():
        raise SecretStoreError(
            f"No secret file at {path}. Create it with:\n"
            "    python scripts/bootstrap_auth.py"
        )
    return json.loads(unprotect(path.read_bytes()).decode("utf-8"))


def assert_not_tracked(path: Path, repo_root: Path) -> None:
    """Fail loudly if a secret path is tracked by git.

    Cheap insurance against a mis-edited .gitignore.
    """
    path = Path(path)
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", str(path)],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
    except FileNotFoundError:  # git not installed
        return
    if result.returncode == 0:
        raise SecretStoreError(
            f"SECURITY: {path} is tracked by git. Remove it immediately:\n"
            f"    git rm --cached {path}\n"
            "then rotate the credential — assume it is compromised."
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
