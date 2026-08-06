"""Screenshot storage.

A full walk generates thousands of frames, and a raw 2000x1472 PNG of the VM is
~3.4 MB. Keeping those would cost tens of gigabytes per run and, more
immediately, they are too large for an agent to read back.

Evidence frames are therefore stored as high-quality JPEG at native resolution:
still legible enough to read portal labels and notebook tracebacks, roughly a
tenth of the size. Heartbeat frames exist only to prove liveness during a long
wait, so they downscale hard.

A separate `view/` copy is written for frames the agent needs to inspect, sized
to fit the reader's limit. Evidence and inspection have different constraints
and conflating them means one of them loses.

Orientation
-----------
Role:     stores evidence frames, and the smaller copies an agent can read back.
Entry:    `save_evidence`, `save_view`, `stability`
Talks to: nothing
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageChops

#: Mean per-pixel greyscale difference below which two frames count as the
#: same screen. Measured against a blinking caret on an otherwise idle portal
#: page, which sits near 0.05; a spinner or a page transition is orders above.
QUIET_THRESHOLD = 0.6

EVIDENCE_QUALITY = 82
VIEW_WIDTH = 1400
VIEW_QUALITY = 72
HEARTBEAT_WIDTH = 900
HEARTBEAT_QUALITY = 55


def _open(png: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(png))
    return img.convert("RGB") if img.mode not in ("RGB", "L") else img


def _resize(img: Image.Image, width: int) -> Image.Image:
    if img.width <= width:
        return img
    height = round(img.height * width / img.width)
    return img.resize((width, height), Image.LANCZOS)


def stability(a: bytes | None, b: bytes | None, width: int = 320) -> float:
    """Mean absolute pixel difference between two frames, 0.0 = identical.

    Byte equality is the obvious test and it is wrong here. The lab console
    re-encodes its framebuffer, and a focused text box blinks a caret roughly
    twice a second, so two visually identical frames rarely compare equal. A
    probe built on equality then waits forever on a page that finished minutes
    ago and reports a timeout as if the lab were at fault.

    Comparing downscaled greyscale means a caret or a repaint artefact moves
    the number by a fraction of a unit while any real UI change moves it by
    several, which is the distinction the probe actually needs.
    """
    if a is None or b is None:
        return 255.0
    ga = _resize(_open(a).convert("L"), width)
    gb = _resize(_open(b).convert("L"), width)
    if ga.size != gb.size:
        return 255.0
    diff = ImageChops.difference(ga, gb)
    histogram = diff.histogram()
    total = sum(i * n for i, n in enumerate(histogram))
    return total / max(1, ga.width * ga.height)


def save_evidence(png: bytes, path: Path, heartbeat: bool = False) -> Path:
    """Write a frame, returning the path actually written (extension may change)."""
    img = _open(png)
    out = path.with_suffix(".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    if heartbeat:
        _resize(img, HEARTBEAT_WIDTH).save(
            out, "JPEG", quality=HEARTBEAT_QUALITY, optimize=True
        )
    else:
        img.save(out, "JPEG", quality=EVIDENCE_QUALITY, optimize=True)
    return out


def save_view(png: bytes, path: Path, width: int = VIEW_WIDTH) -> Path:
    """Write a reader-sized copy under `view/` next to the evidence folder."""
    out = path.parent.parent / "view" / (path.stem + ".jpg")
    out.parent.mkdir(parents=True, exist_ok=True)
    _resize(_open(png), width).save(out, "JPEG", quality=VIEW_QUALITY, optimize=True)
    return out
