"""Browser session management.

Two ways to get an authenticated browser, in order of preference:

1. **Persistent profile** (default). A dedicated Edge/Chrome profile under
   ``.browser-profile/`` that you sign into by hand *once*. Cookies persist, so
   MFA is never re-prompted, and Skillable's device registration sees the same
   browser fingerprint on every run — no email challenge.

2. **CDP attach.** Connect to a browser already listening on a debug port. Note
   that Chrome/Edge 136+ refuse ``--remote-debugging-port`` when running on the
   *default* user-data-dir, so the browser must have been started explicitly
   with a separate profile (which is what option 1 does).

Neither stores a password. This is the preferred alternative to
``scripts/bootstrap_auth.py``; that script remains useful for headless CI where
no interactive profile exists.
"""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT

#: Dedicated browser profile. Gitignored — contains live session cookies.
PROFILE_DIR = REPO_ROOT / ".browser-profile"

DEFAULT_CDP_PORT = 9222

#: How long to wait for the CDP handshake before giving up. Playwright's default
#: is 180 s, which turns a wedged target into a three-minute stall on every step.
#: A healthy attach completes in a second or two, so fail fast and let the caller
#: retry or reset the browser.
ATTACH_TIMEOUT_MS = 45_000

#: Edge ships Copilot surfaces that materialise as ``edge://discover-chat-v2``
#: and ``edge://newtab`` ``browser_ui`` targets plus prerendered
#: ``copilot.microsoft.com`` iframes. They cannot be closed over CDP
#: (``/json/close`` silently no-ops on them), and once present,
#: ``connect_over_cdp`` blocks forever auto-attaching to them. Suppressing them
#: at launch is the only reliable fix. ``EdgeSyncPromotion`` additionally keeps
#: the profile clone from re-syncing over the copied session. Unknown feature
#: names are ignored by the browser, so this list is safe to over-specify.
SUPPRESSED_EDGE_FEATURES = (
    "EdgeSyncPromotion",
    "msEdgeCopilot",
    "msCopilotSidebar",
    "EdgeDiscoverChat",
    "EdgeCopilotPrerender",
    "msWebAssist",
    "msUndersideButton",
)

_EDGE_PATHS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
)
_CHROME_PATHS = (
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)

#: Where each browser keeps its real profiles.
_USER_DATA_ROOTS = {
    "edge": Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Edge" / "User Data",
    "chrome": Path(os.environ.get("LOCALAPPDATA", "")) / "Google" / "Chrome" / "User Data",
}

#: Caches and ephemeral state — large, and irrelevant to authentication.
_CLONE_EXCLUDE = {
    "Cache",
    "Code Cache",
    "GPUCache",
    "DawnCache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "GrShaderCache",
    "ShaderCache",
    "Service Worker",
    "Application Cache",
    "File System",
    "optimization_guide_model_store",
    "component_crx_cache",
    "extensions_crx_cache",
    "Crashpad",
    "BrowserMetrics",
    "Safe Browsing",
    "segmentation_platform",
}

#: Minimal set that carries a signed-in session. Everything else in a real
#: profile (history, IndexedDB, WebStorage, extensions, saved passwords) is
#: irrelevant to authentication and is deliberately left behind — it keeps the
#: clone small and avoids copying credentials we have no use for.
_CLONE_INCLUDE = (
    "Network/Cookies",
    "Network/Cookies-journal",
    "Preferences",
    "Secure Preferences",
    "Local Storage",
    "Trust Tokens",
)

#: Removing these avoids a "restore pages?" prompt in the cloned profile.
_CLONE_DROP_FILES = {
    "Last Session",
    "Last Tabs",
    "Current Session",
    "Current Tabs",
}


class BrowserError(RuntimeError):
    """Raised when a browser cannot be launched or reached."""


@dataclass(frozen=True)
class BrowserInfo:
    name: str
    path: Path


@dataclass(frozen=True)
class ProfileInfo:
    """A real browser profile discovered on this machine."""

    directory: str  # e.g. "Default", "Profile 9"
    name: str  # display name, e.g. "ExternalEntra2"
    account: str  # signed-in account, e.g. "haduong@microsoft.com"
    path: Path

    def matches(self, needle: str) -> bool:
        n = needle.casefold()
        return n in (
            self.directory.casefold(),
            self.name.casefold(),
            self.account.casefold(),
        ) or n in self.account.casefold()

    def describe(self) -> str:
        return f"{self.directory:<10} {self.name:<18} {self.account}"


def user_data_root(browser: str = "edge") -> Path:
    root = _USER_DATA_ROOTS.get(browser)
    if root is None or not root.exists():
        raise BrowserError(f"No {browser} User Data directory found at {root}.")
    return root


def list_profiles(browser: str = "edge") -> list[ProfileInfo]:
    """Enumerate real profiles from the browser's ``Local State``."""
    root = user_data_root(browser)
    local_state = root / "Local State"
    if not local_state.exists():
        raise BrowserError(f"No Local State file at {local_state}.")

    cache = (
        json.loads(local_state.read_text(encoding="utf-8", errors="replace"))
        .get("profile", {})
        .get("info_cache", {})
    )
    profiles = [
        ProfileInfo(
            directory=directory,
            name=meta.get("name", directory),
            account=meta.get("user_name", ""),
            path=root / directory,
        )
        for directory, meta in cache.items()
        if (root / directory).exists()
    ]
    return sorted(profiles, key=lambda p: (p.directory != "Default", p.directory))


def resolve_profile(needle: str, browser: str = "edge") -> ProfileInfo:
    """Find one profile by directory, display name, or account address."""
    profiles = list_profiles(browser)
    matches = [p for p in profiles if p.matches(needle)]
    if not matches:
        listing = "\n".join(f"    {p.describe()}" for p in profiles)
        raise BrowserError(
            f"No {browser} profile matches {needle!r}. Available:\n{listing}"
        )
    if len(matches) > 1:
        listing = "\n".join(f"    {p.describe()}" for p in matches)
        raise BrowserError(f"{needle!r} is ambiguous — matches:\n{listing}")
    return matches[0]


def _copy_tree(src: Path, dest: Path) -> int:
    """Copy a whole profile directory, skipping caches. Returns bytes copied."""
    copied = 0
    for item in src.iterdir():
        if item.name in _CLONE_EXCLUDE or item.name in _CLONE_DROP_FILES:
            continue
        target = dest / item.name
        try:
            if item.is_dir():
                shutil.copytree(
                    item,
                    target,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*_CLONE_EXCLUDE),
                    ignore_dangling_symlinks=True,
                )
                copied += sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            else:
                shutil.copy2(item, target)
                copied += target.stat().st_size
        except (PermissionError, OSError):
            # Files locked by a running browser are skipped; cookies normally
            # copy fine because SQLite readers do not take exclusive locks.
            continue
    return copied


def _copy_minimal(src: Path, dest: Path) -> int:
    """Copy only the files that carry a signed-in session."""
    copied = 0
    for rel in _CLONE_INCLUDE:
        item = src / rel
        if not item.exists():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
                copied += sum(f.stat().st_size for f in target.rglob("*") if f.is_file())
            else:
                shutil.copy2(item, target)
                copied += target.stat().st_size
        except (PermissionError, OSError):
            # Locked by a running browser; SQLite readers do not take
            # exclusive locks, so cookies normally still copy cleanly.
            continue
    return copied


def clone_profile(
    profile: ProfileInfo,
    browser: str = "edge",
    dest_root: Path = PROFILE_DIR,
    overwrite: bool = True,
    full: bool = False,
) -> tuple[Path, int]:
    """Copy a real browser profile into the validator's own user-data dir.

    Chrome/Edge 136+ refuse ``--remote-debugging-port`` against the *default*
    user-data directory, so the profile must be cloned somewhere else rather
    than driven in place. ``Local State`` is copied too: it holds the
    DPAPI-protected key that decrypts the cookie database, and that key is
    bound to the current Windows user, so the clone only works for you on this
    machine.

    By default only session-bearing files are copied (tens of MB). Pass
    ``full=True`` to mirror the whole profile minus caches (can be gigabytes).

    Returns ``(destination, bytes_copied)``.
    """
    root = user_data_root(browser)
    dest_root = Path(dest_root)
    dest_profile = dest_root / profile.directory

    if overwrite and dest_profile.exists():
        shutil.rmtree(dest_profile, ignore_errors=True)
    dest_profile.mkdir(parents=True, exist_ok=True)

    # The cookie encryption key lives here, not in the profile folder.
    shutil.copy2(root / "Local State", dest_root / "Local State")

    copier = _copy_tree if full else _copy_minimal
    return dest_profile, copier(profile.path, dest_profile)


def browser_is_running(browser: str = "edge") -> bool:
    exe = "msedge.exe" if browser == "edge" else "chrome.exe"
    try:
        out = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {exe}", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return exe.lower() in out.lower()


def find_browser(prefer: str = "edge") -> BrowserInfo:
    """Locate an installed Chromium-family browser."""
    order = (
        (("edge", _EDGE_PATHS), ("chrome", _CHROME_PATHS))
        if prefer == "edge"
        else (("chrome", _CHROME_PATHS), ("edge", _EDGE_PATHS))
    )
    for name, candidates in order:
        for path in candidates:
            if path.exists():
                return BrowserInfo(name, path)
        found = shutil.which(f"{name}.exe") or shutil.which(name)
        if found:
            return BrowserInfo(name, Path(found))
    raise BrowserError("No Microsoft Edge or Google Chrome installation found.")


def port_is_open(port: int = DEFAULT_CDP_PORT, host: str = "127.0.0.1") -> bool:
    """True if something is listening on the CDP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.75)
        return sock.connect_ex((host, port)) == 0


def cdp_endpoint(port: int = DEFAULT_CDP_PORT) -> str:
    return f"http://127.0.0.1:{port}"


def launch_debug_browser(
    port: int = DEFAULT_CDP_PORT,
    prefer: str = "edge",
    start_url: str | None = None,
    profile_dir: Path = PROFILE_DIR,
    profile_directory: str = "Default",
) -> subprocess.Popen:
    """Start a browser with a dedicated profile and a CDP debug port.

    ``profile_directory`` selects which profile *inside* ``profile_dir`` to use,
    matching the layout of a real browser user-data directory. The profile
    persists between runs, so you sign in once and stay signed in.
    """
    if port_is_open(port):
        raise BrowserError(
            f"Port {port} is already in use — a debug browser is likely already "
            f"running. Attach to it instead, or pass a different --port."
        )

    browser = find_browser(prefer)
    profile_dir.mkdir(parents=True, exist_ok=True)

    args = [
        str(browser.path),
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        f"--profile-directory={profile_directory}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        # Skillable lab launches use window.open and third-party cookies.
        "--disable-popup-blocking",
        # Keep the clone from re-syncing over the copied session, and keep Edge's
        # built-in Copilot surfaces out of the target list. Those appear as
        # unclosable ``edge://`` browser_ui targets plus prerendered
        # copilot.microsoft.com iframes, and Playwright's connect_over_cdp hangs
        # indefinitely trying to auto-attach to them.
        "--disable-features=" + ",".join(SUPPRESSED_EDGE_FEATURES),
    ]
    if start_url:
        args.append(start_url)

    proc = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=(
            subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
        ),
    )
    return proc


async def attach(playwright, port: int = DEFAULT_CDP_PORT):
    """Attach Playwright to a running debug browser over CDP.

    Returns the ``Browser``. Use ``browser.contexts[0]`` to reach the existing,
    already-signed-in context rather than creating a fresh anonymous one.
    """
    if not port_is_open(port):
        raise BrowserError(
            f"Nothing is listening on {cdp_endpoint(port)}.\n"
            "Start the debug browser first:\n"
            "    python scripts/browser_session.py --launch"
        )
    return await playwright.chromium.connect_over_cdp(
        cdp_endpoint(port), timeout=ATTACH_TIMEOUT_MS
    )


async def attached_context(playwright, port: int = DEFAULT_CDP_PORT):
    """Attach and return ``(browser, context)`` for the live signed-in profile."""
    browser = await attach(playwright, port)
    if not browser.contexts:
        raise BrowserError(
            "Debug browser has no open context. Open a tab in it and retry."
        )
    context = browser.contexts[0]
    context.set_default_timeout(30_000)
    return browser, context
