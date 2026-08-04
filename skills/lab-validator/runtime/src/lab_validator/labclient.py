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


def instance_id_of(url: str) -> str:
    """The lab instance GUID carried in a lab-client URL, or ``?``."""
    m = re.search(r"/LabClient/([0-9a-f-]{36})", url)
    return m.group(1) if m else "?"


class LabClosed(BrowserError):
    """The lab client is still open, but the lab behind it has ended."""


#: What the product puts on the page when a lab instance ends, and where each
#: wording came from. Provenance is recorded because the project's rule is not
#: to invent: a guessed marker that fires is a confident claim resting on
#: nothing, and a reader has no way to tell the two apart from the tuple alone.
#:
#: Observed live: the tab stays open, keeps its title, keeps its
#: ``/LabClient/<guid>`` URL and still lists the console and instructions frames
#: -- and shows "Lab Closed / Your lab has been closed." with a Close Window
#: button.
#:
#: This is what a learner sees, which is the point. Everything the tool checked
#: to identify the lab (tab present, URL right, instance id right, frames
#: present) remained true after the lab ended, so the walk carried on: it filed
#: a *major* defect saying the instruction pane would not scroll -- the pane was
#: dead, not defective -- and recorded three PASS steps for work done against
#: nothing. Identity was never the problem here; liveness was.
MARKER_PROVENANCE: dict[str, str] = {
    "lab closed": "observed — the heading on the ended lab, 2026-07-31",
    "your lab has been closed": "observed — the body text beneath it, 2026-07-31",
    # A guess. Kept because the cost of a miss is high (the walk carries on
    # against nothing) and the cost of a false match is low (this reads the
    # client's own chrome, not the lab's prose). Labelled so nobody later
    # mistakes it for something the product was seen to say.
    "this lab has ended": "unverified — a plausible variant, never seen",
}

CLOSED_MARKERS = tuple(MARKER_PROVENANCE)


async def closed_reason(page) -> str | None:
    """What the *top-level* client says, if it says the lab has ended.

    Read from the main frame only. The instructions frame carries the lab's own
    prose, which can say anything at all -- including "lab closed" -- and using
    it here would let a lab's own text end its own walk.

    A page that cannot be read at all is not reported as closed: an unreadable
    page is a different failure with a different fix, and guessing between them
    would produce exactly the confident wrong answer this check exists to stop.

    Blind spot, stated: this only recognises wordings in ``MARKER_PROVENANCE``.
    A lab that ends with words nobody has seen will not be caught here, and the
    walk will carry on exactly as it did before this check existed.
    """
    try:
        text = await page.main_frame.inner_text("body")
    except Exception:  # noqa: BLE001 - a dead page is not evidence of closure
        return None
    lowered = " ".join(text.lower().split())
    for marker in CLOSED_MARKERS:
        if marker in lowered:
            return text.strip().splitlines()[0].strip() if text.strip() else marker
    return None


#: Sub-pixel layout rounding routinely makes scrollHeight exceed clientHeight by
#: a pixel or two on content that visibly fits.
SCROLL_SLACK = 4


@dataclass(frozen=True)
class Scrolled:
    """What a learner's scroll of the instruction pane actually did.

    Three outcomes need telling apart and the old ``int`` return could only
    tell two. A section short enough to fit its pane *cannot* scroll and is not
    defective; a pane whose content overflows but will not move is the defect
    worth reporting. Collapsing them files a major finding against every short
    section in the lab -- which is precisely what the first live run did.
    """

    before: int
    after: int
    #: how much content sits beyond the scroller's viewport, in pixels
    overflow: int
    #: what was measured, so a wrong guess at the scroller shows up in the
    #: evidence instead of hiding inside a verdict
    where: str
    #: whether the text under a fixed point in the pane changed
    view_changed: bool

    @property
    def moved(self) -> bool:
        """The learner's own criterion: did the pane show something new?

        Offset *or* view, because either alone can lie. A pane can scroll an
        inner element whose offset we failed to find, and a pane can report an
        offset change while rendering nothing new.
        """
        return self.after != self.before or self.view_changed

    @property
    def scrollable(self) -> bool:
        return self.overflow > SCROLL_SLACK

    @property
    def stuck(self) -> bool:
        """There is more to read, and the learner cannot reach it."""
        return self.scrollable and not self.moved

    def describe(self) -> str:
        if self.stuck:
            return (
                f"instruction pane did not scroll: {self.where} stayed at "
                f"scrollTop {self.before} with {self.overflow}px of content below "
                "the fold, and the view did not change. A learner reading this "
                "section by hand would be stuck."
            )
        if not self.scrollable:
            return f"nothing to scroll: {self.where} holds no content beyond its viewport"
        return (
            f"{self.where} scrolled {self.before} -> {self.after} "
            f"of {self.overflow}px"
        )


#: Find the element the pane actually scrolls, mark it so the wheel can be aimed
#: at it, and sample what the learner can see. Two things this replaces were
#: both wrong in the same direction -- silently reporting a healthy pane as
#: broken. ``document.scrollingElement`` is only the scroller when the document
#: itself scrolls, and a pane built as a ``div`` with ``overflow-y: auto``
#: leaves it pinned at 0 forever; and hovering the frame's ``body`` aims the
#: wheel at ``body``'s box, which on this product is a 101px strip *above* the
#: instruction pane, so the wheel went to the tab bar.
_SCROLL_PROBE = """() => {
  const slack = __SLACK__;
  const scrollers = [...document.querySelectorAll('*')].filter(el => {
    const style = getComputedStyle(el);
    return /auto|scroll/.test(style.overflowY)
        && el.scrollHeight - el.clientHeight > slack;
  });
  const doc = document.scrollingElement;
  // The pane with the most content beyond its viewport is the one holding the
  // instructions: chrome and toolbars overflow by a little, content by a lot.
  scrollers.sort((a, b) =>
    (b.scrollHeight - b.clientHeight) - (a.scrollHeight - a.clientHeight));
  const el = scrollers[0] || doc;
  document.querySelectorAll('[data-lv-scroller]')
    .forEach(e => e.removeAttribute('data-lv-scroller'));
  el.setAttribute('data-lv-scroller', '1');
  const box = (el === doc)
    ? {left: 0, top: 0, width: innerWidth, height: innerHeight}
    : el.getBoundingClientRect();
  const seen = document.elementFromPoint(
    Math.round(box.left + box.width / 2),
    Math.round(box.top + box.height / 2));
  const name = (el === doc) ? 'document'
    : el.tagName.toLowerCase()
      + (el.id ? '#' + el.id : '')
      + ((typeof el.className === 'string' && el.className.trim())
         ? '.' + el.className.trim().split(/\\s+/).join('.') : '');
  return {
    top: Math.round(el.scrollTop),
    overflow: Math.round(el.scrollHeight - el.clientHeight),
    where: name,
    seen: (seen ? seen.textContent || '' : '').replace(/\\s+/g, ' ').trim().slice(0, 160),
  };
}""".replace("__SLACK__", str(SCROLL_SLACK))

_UNMARK_SCROLLER = (
    "() => document.querySelectorAll('[data-lv-scroller]')"
    ".forEach(e => e.removeAttribute('data-lv-scroller'))"
)


class LabClient:
    """A live Skillable lab instance."""

    def __init__(self, page: Page):
        self.page = page

    # ---- discovery -----------------------------------------------------

    @classmethod
    def candidates(cls, context) -> list[Page]:
        return [p for p in context.pages if "/LabClient/" in p.url]

    @classmethod
    def find(cls, context, *, instance_id: str | None = None, known=()) -> LabClient:
        """The one lab client this run is about -- or a refusal naming the rest.

        Position is not identity. This used to return ``pages[0]``, and the
        surrounding guidance deliberately leaves an old lab tab open so a
        re-run can pick it up, so "first tab" could easily be *a different
        lab* -- which would answer every question fluently and wrongly. A
        wrong answer that is indistinguishable from a right one is the worst
        thing a validator can produce, so ambiguity is refused rather than
        resolved by guessing.

        ``instance_id`` pins an exact instance. ``known`` is the set of
        lab-client URLs that existed *before* Launch was clicked; anything
        outside it is the tab that Launch just opened.
        """
        pages = cls.candidates(context)
        if instance_id:
            pinned = [p for p in pages if instance_id in p.url]
            if not pinned:
                raise BrowserError(
                    f"No lab client tab for instance {instance_id}. "
                    f"Open tabs: {cls._describe(pages)}."
                )
            pages = pinned
        elif known:
            fresh = [p for p in pages if p.url not in set(known)]
            if fresh:
                pages = fresh
        if not pages:
            raise BrowserError("No lab client tab found. Launch the lab first, then retry.")
        if len(pages) > 1:
            raise BrowserError(
                f"{len(pages)} lab client tabs are open ({cls._describe(pages)}) and "
                "nothing says which one this run is about. Close the ones you are not "
                "using, or pass the instance id. Guessing here would read a different "
                "lab's instructions and report them as this lab's."
            )
        return cls(pages[0])

    @staticmethod
    def _describe(pages) -> str:
        return ", ".join(instance_id_of(p.url) for p in pages) or "none"

    @property
    def instance_id(self) -> str:
        return instance_id_of(self.page.url)

    async def ensure_open(self) -> None:
        """Refuse to act on a lab that has ended.

        Called before anything is recorded, because a step taken after the lab
        closed is not weak evidence -- it is evidence of nothing at all, written
        into a trace that reads exactly like evidence of something.
        """
        reason = await closed_reason(self.page)
        if reason is None:
            return
        raise LabClosed(
            f"The lab client says: {reason!r}. Instance {self.instance_id} has "
            "ended, so nothing observed from here is evidence about the lab. "
            "Sections already walked keep their reports; the rest are unknown, "
            "not correct. Launch the lab again to continue."
        )

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

    async def scroll_instructions(self, delta: int = 600) -> Scrolled:
        """Scroll the instruction pane the way a learner does, and say what happened.

        :meth:`goto_page` is faster and exact, and that is the problem: it pages
        the pane through the API without ever touching the pane's own
        navigation, so a broken scroll or a pager that silently skips content is
        invisible to a walk that only uses it. This is the control that closes
        that hole -- a real wheel event on the real element.

        Returns a :class:`Scrolled`, not an offset. The offset alone cannot tell
        "there was nothing to scroll" from "the pane would not move", and only
        one of those is a defect.
        """
        pane = self.instructions
        first = await pane.evaluate(_SCROLL_PROBE)
        try:
            await self._wheel_over_scroller(pane, delta)
            await self.page.wait_for_timeout(400)
            second = await pane.evaluate(_SCROLL_PROBE)
        finally:
            await pane.evaluate(_UNMARK_SCROLLER)
        return Scrolled(
            before=first["top"],
            after=second["top"],
            # The larger of the two: a pane that scrolls can report a smaller
            # overflow once lazily-rendered content settles, and understating it
            # would turn a real defect into "nothing to scroll".
            overflow=max(first["overflow"], second["overflow"]),
            where=second["where"] or first["where"],
            view_changed=first["seen"] != second["seen"],
        )

    async def _wheel_over_scroller(self, pane: Frame, delta: int) -> None:
        """Put the pointer inside the scroller, then turn the wheel.

        A wheel event goes to whatever is under the pointer, so aiming is the
        whole job. ``bounding_box()`` reports page coordinates, which is what
        ``page.mouse`` wants, and the vertical offset is clamped so a pane taller
        than the window is still aimed at somewhere visible.
        """
        box = await pane.locator("[data-lv-scroller]").first.bounding_box()
        if box is None:
            # Nothing measurable to aim at. Turning the wheel anyway would put
            # the event somewhere arbitrary and the result would be read as
            # evidence, so decline and let the caller see an unmoved pane.
            return
        await self.page.mouse.move(
            box["x"] + box["width"] / 2,
            box["y"] + min(box["height"], 400) / 2,
        )
        await self.page.mouse.wheel(0, delta)

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

    async def wheel(self, x: int, y: int, delta: int = 400) -> None:
        """Scroll the VM under VM-screen coordinates.

        Notebook outputs, portal blades and log panes routinely exceed one
        screen, so without a wheel the validator can only ever observe the
        first fold and would report "absent" for anything below it.
        """
        box = await self._canvas_box()
        res_w, res_h = await self.resolution()
        await self.page.mouse.move(
            box["x"] + x * box["width"] / res_w, box["y"] + y * box["height"] / res_h
        )
        await self.page.mouse.wheel(0, delta)
        await self.page.wait_for_timeout(500)

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

        60 ms/char was enough for browser fields but not for a PowerShell
        console, where PSReadLine re-highlights the whole line on every
        keystroke; a 165-character command still split across a continuation
        prompt. 110 ms/char covers the slowest surface seen so far.
        """
        await self.console.evaluate(
            "async (t) => await window.api.v1.sendTextToEnvironment(t)", text
        )
        await self.page.wait_for_timeout(1500 + 110 * len(text))

    #: Playwright spells modifiers out; the shorthand a human reaches for on a
    #: keyboard is what ends up in a --do list, so accept both.
    _KEY_ALIASES = {
        "ctrl": "Control",
        "cmd": "Meta",
        "win": "Meta",
        "esc": "Escape",
        "del": "Delete",
        "ins": "Insert",
        "pgup": "PageUp",
        "pgdn": "PageDown",
        "return": "Enter",
        "space": " ",
        "up": "ArrowUp",
        "down": "ArrowDown",
        "left": "ArrowLeft",
        "right": "ArrowRight",
    }

    @classmethod
    def normalise_key(cls, key: str) -> str:
        """Map a key or chord to Playwright's spelling.

        An unrecognised modifier raises deep inside Playwright mid-step, which
        aborts a walk after some actions have already been applied. Normalising
        up front keeps that class of typo from reaching the VM at all.
        """
        parts = [p.strip() for p in key.split("+") if p.strip()]
        if not parts:
            raise BrowserError(f"Empty key: {key!r}")
        out = []
        for part in parts:
            mapped = cls._KEY_ALIASES.get(part.lower(), part)
            out.append(mapped if len(mapped) > 1 else mapped)
        return "+".join(out)

    async def key(self, *keys: str, delay: int = 400) -> None:
        for k in keys:
            await self.page.keyboard.press(self.normalise_key(k))
            await self.page.wait_for_timeout(delay)
