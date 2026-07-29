"""Drive a running Skillable lab client: instructions, VM console, and screen capture.

The lab client is a frameset. ``window.api.v1`` is exposed in the *child*
frames -- ``consoleIFrame`` and ``instructionsIFrame`` -- but **not** on the top
frame, so every API call here is routed through a child frame.

Screen capture uses ``api.v1.getEnvironmentScreenDataUrl()`` in preference to a
Playwright screenshot: it returns just the VM framebuffer, with no browser
chrome and no instructions pane, which makes the resulting images far easier to
reason about and much cheaper to look at.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from playwright.async_api import Frame, Page

from .browser import BrowserError


@dataclass
class Credential:
    """One credential row from the lab's Resources tab."""

    scope: str
    label: str
    value: str

    def redacted(self) -> str:
        if len(self.value) <= 4:
            return "*" * len(self.value)
        return f"{self.value[0]}{'*' * (len(self.value) - 2)}{self.value[-1]}"


class LabClient:
    """A live Skillable lab instance."""

    def __init__(self, page: Page):
        self.page = page

    # ---- discovery -----------------------------------------------------

    @classmethod
    def find(cls, context) -> LabClient:
        pages = [p for p in context.pages if "/LabClient/" in p.url]
        if not pages:
            raise BrowserError(
                "No lab client tab found. Launch the lab first, then retry."
            )
        return cls(pages[0])

    @property
    def instance_id(self) -> str:
        m = re.search(r"/LabClient/([0-9a-f-]{36})", self.page.url)
        return m.group(1) if m else "?"

    def _frame(self, marker: str) -> Frame:
        for f in self.page.frames:
            if marker in f.url:
                return f
        raise BrowserError(f"Frame {marker!r} not present in the lab client.")

    @property
    def console(self) -> Frame:
        return self._frame("/VirtualizationClient/")

    @property
    def instructions(self) -> Frame:
        return self._frame("/Instructions/")

    # ---- lab state -----------------------------------------------------

    async def call(self, expr: str, *args):
        """Invoke ``window.api.v1.<expr>`` from the console frame."""
        return await self.console.evaluate(
            f"async (a) => await window.api.v1.{expr}", args[0] if args else None
        )

    async def minutes_remaining(self) -> int:
        return await self.call("getMinutesRemaining()")

    async def connection_status(self) -> dict:
        return await self.call("getEnvironmentConnectionStatus()")

    async def page_index(self) -> int:
        return await self.call("getInstructionsPageIndex()")

    async def goto_page(self, index: int) -> None:
        await self.console.evaluate(
            "async (i) => await window.api.v1.gotoInstructionsPage(i)", index
        )
        await self.page.wait_for_timeout(600)

    async def instructions_text(self) -> str:
        raw = await self.instructions.inner_text("body")
        return re.sub(r"\s*\n\s*", "\n", raw).strip()

    # ---- credentials ---------------------------------------------------

    async def credentials(self) -> list[Credential]:
        """Read the Resources tab. Values are secret -- prefer ``redacted()``."""
        await self.dismiss_dialog()
        await self.instructions.get_by_text("Resources", exact=True).first.click()
        await self.page.wait_for_timeout(1800)
        text = await self.instructions.inner_text("body")

        creds: list[Credential] = []
        scope = "?"
        for line in (line.strip() for line in text.splitlines()):
            if not line:
                continue
            if "\t" not in line:
                if line not in ("Exit Lab", "Instructions", "Resources"):
                    scope = line
                continue
            label, _, value = line.partition("\t")
            creds.append(Credential(scope, label.strip(), value.strip()))
        return creds

    def find_credential(
        self, creds: list[Credential], label: str, scope: str | None = None
    ) -> Credential | None:
        for c in creds:
            if c.label.lower() == label.lower() and (
                scope is None or scope.lower() in c.scope.lower()
            ):
                return c
        return None

    async def credential_value(self, ref: str) -> str:
        """Look up one credential by ``"Scope/Label"`` and return it verbatim.

        Exists so secrets can go straight from the Resources tab into the VM
        without ever being printed, logged, or passed on a command line.
        Restores the Instructions tab afterwards so the caller's view of the
        pane is unchanged.
        """
        scope, _, label = ref.rpartition("/")
        creds = await self.credentials()
        await self.show_instructions()
        match = self.find_credential(creds, label, scope or None)
        if match is None:
            known = ", ".join(f"{c.scope}/{c.label}" for c in creds)
            raise BrowserError(f"No credential {ref!r} on the Resources tab. Have: {known}")
        return match.value

    async def show_instructions(self) -> None:
        await self.dismiss_dialog()
        await self.instructions.get_by_text("Instructions", exact=True).first.click()
        await self.page.wait_for_timeout(1200)

    # ---- modal dialogs -------------------------------------------------

    async def dismiss_dialog(self, accept: bool = False) -> str | None:
        """Close ``#modalDialog`` if it is open, returning its text.

        The lab client raises modals for destructive actions (e.g. refreshing
        cloud credentials). The dialog lives on the *top* frame and swallows
        pointer events for the whole client, so an unhandled one makes every
        subsequent click time out with a misleading "intercepts pointer
        events" error rather than anything that names the real cause.
        """
        dialog = self.page.locator("#modalDialog")
        if not await dialog.count() or not await dialog.is_visible():
            return None
        text = await dialog.inner_text()
        await dialog.get_by_role(
            "button", name="OK" if accept else "Cancel"
        ).first.click()
        await self.page.wait_for_timeout(800)
        return text

    async def type_credential_natively(self, label: str) -> None:
        """Type a credential into the VM using Skillable's own affordance.

        Credential values on the Resources tab are ``span.typeText`` elements;
        clicking one makes the lab client replay it into the remote session.
        Preferring this over :meth:`type` removes our own text injection from
        the trust path -- it is byte-for-byte what a human clicking the field
        would get, so a login failure can no longer be blamed on us.
        """
        await self.dismiss_dialog()
        await self.instructions.get_by_text("Resources", exact=True).first.click()
        await self.page.wait_for_timeout(1500)
        span = self.instructions.locator("span.typeText").filter(has_text=label)
        if not await span.count():
            raise BrowserError(f"No typeText span matching {label!r} on the Resources tab.")
        await span.first.click()
        await self.page.wait_for_timeout(2500)

    # ---- VM interaction ------------------------------------------------

    async def screen(self, path: str | Path) -> Path:
        """Capture the VM framebuffer.

        Screenshots the ``<canvas>`` element itself rather than the iframe, so
        pixel coordinates in the saved image map 1:1 onto VM screen
        coordinates. That property is what makes it safe to read a coordinate
        off an image and feed it straight back into :meth:`click`.
        """
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        await self.console.locator("canvas").first.screenshot(path=str(out))
        return out

    async def screen_bytes(self) -> bytes:
        """Capture the VM framebuffer to memory.

        Used by stability probes, which compare consecutive frames and would
        otherwise litter the run folder with thousands of throwaway PNGs.
        """
        return await self.console.locator("canvas").first.screenshot()

    async def resolution(self) -> tuple[int, int]:
        size = await self.console.evaluate(
            "() => { const c = document.querySelector('canvas');"
            " return [c.width, c.height]; }"
        )
        return (size[0], size[1])

    async def _canvas_box(self) -> dict:
        box = await self.console.locator("canvas").first.bounding_box()
        if not box:
            raise BrowserError("VM canvas has no layout box.")
        frame_box = await self.page.locator("#consoleIFrame").bounding_box()
        return {
            "x": (frame_box["x"] if frame_box else 0) + box["x"],
            "y": (frame_box["y"] if frame_box else 0) + box["y"],
            "width": box["width"],
            "height": box["height"],
        }

    async def click(self, x: int, y: int, *, double: bool = False) -> None:
        """Click at VM-screen coordinates.

        The canvas resolution is read live rather than assumed: it starts at
        1024x768 and is renegotiated once the VM connects, so a hard-coded
        assumption silently mis-aims every click.
        """
        box = await self._canvas_box()
        res_w, res_h = await self.resolution()
        sx = box["width"] / res_w
        sy = box["height"] / res_h
        px, py = box["x"] + x * sx, box["y"] + y * sy
        await self.page.mouse.click(px, py, click_count=2 if double else 1)
        await self.page.wait_for_timeout(500)

    async def move(self, x: int, y: int) -> None:
        """Move the pointer to VM-screen coordinates without clicking.

        Hover reveals menus and tooltips that a click would dismiss, so this is
        how you check a label without changing state.
        """
        box = await self._canvas_box()
        res_w, res_h = await self.resolution()
        await self.page.mouse.move(
            box["x"] + x * box["width"] / res_w, box["y"] + y * box["height"] / res_h
        )
        await self.page.wait_for_timeout(300)

    async def focus_vm(self) -> None:
        box = await self._canvas_box()
        await self.page.mouse.click(
            box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        )
        await self.page.wait_for_timeout(400)

    async def type(self, text: str) -> None:
        """Send text into the VM via the lab API (not synthetic keystrokes).

        The API replays the string keystroke-by-keystroke into the remote
        session and resolves before the VM has consumed it, so the settle
        time has to scale with length. A fixed delay silently truncates
        input: pressing Enter too early submitted only "https:" once.
        """
        await self.console.evaluate(
            "async (t) => await window.api.v1.sendTextToEnvironment(t)", text
        )
        await self.page.wait_for_timeout(1200 + 60 * len(text))

    async def key(self, *keys: str, delay: int = 400) -> None:
        for k in keys:
            await self.page.keyboard.press(k)
            await self.page.wait_for_timeout(delay)
