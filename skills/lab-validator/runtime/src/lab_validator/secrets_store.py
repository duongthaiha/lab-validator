"""Encrypted local secret storage.

On Windows, secrets are protected with DPAPI (``CryptProtectData``). The
resulting blob is bound to the current Windows user *and* machine, so there is
no master password to manage and a copied file is useless to an attacker.

This is a **local developer** mechanism. In CI, inject secrets as environment
variables from GitHub Actions secrets or Key Vault and never write them to disk.
"""

from __future__ import annotations

import json
import platform
import stat
import subprocess
from pathlib import Path
from typing import Any

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


def redact(value: str | None, keep: int = 4) -> str:
    """Render a secret safely for logs: ``abcd…(28 more)``."""
    if not value:
        return "<unset>"
    if len(value) <= keep:
        return "*" * len(value)
    return f"{value[:keep]}…({len(value) - keep} more)"


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
