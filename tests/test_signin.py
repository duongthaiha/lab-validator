"""What `signin:` may claim, and what it must refuse to claim.

The action exists because a model given a free choice between two credentials
that are both called `Password` picks the one its *task* mentions rather than
the one its *screen* wants. So the tests below are less about the happy path
than about the two ways this action can lie: by believing the keystrokes it
sent, and by reading a repaint as an acceptance.
"""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest
from PIL import Image

from lab_validator.imaging import QUIET_THRESHOLD
from lab_validator.labclient import Credential
from lab_validator.runlog import Run, Segment
from lab_validator.vault import Vault

ROOT = Path(__file__).resolve().parents[1]


def _lab_step():
    """Import `scripts/lab_step.py` as a module.

    It is a script, not a package member, and every other test reads it as
    text. These tests need to *run* `do_signin`, because the defect they guard
    against (comparing frames by byte equality) is invisible to source reading
    once the call looks reasonable.
    """
    if "lab_step" in sys.modules:
        return sys.modules["lab_step"]
    spec = importlib.util.spec_from_file_location("lab_step", ROOT / "scripts" / "lab_step.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["lab_step"] = module
    spec.loader.exec_module(module)
    return module


TWO_SIGNINS = [
    ("Azure Portal", "Username", "learner@example.invalid"),
    ("Azure Portal", "Password", "PortalSecret1!"),
    ("Machine credentials", "Username", "Admin"),
    ("Machine credentials", "Password", "VmSecret9"),
]


def _frame(colour: tuple[int, int, int], noise: int = 0) -> bytes:
    """A JPEG the size the console produces, optionally with a speck moved.

    `noise` stands in for what a real console does between two identical
    screens: re-encode, blink a caret. It changes the bytes and must not change
    the verdict.
    """
    img = Image.new("RGB", (320, 240), colour)
    for i in range(noise):
        img.putpixel((i, 0), (255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=82)
    return buf.getvalue()


class FakeLab:
    """A console that returns the frames it is told to, in order."""

    def __init__(self, frames: list[bytes]) -> None:
        self._frames = list(frames)
        self.typed: list[str] = []
        self.keys: list[str] = []

    async def screen_bytes(self) -> bytes:
        return self._frames.pop(0) if len(self._frames) > 1 else self._frames[0]

    async def type(self, text: str) -> None:
        self.typed.append(text)

    async def key(self, name: str) -> None:
        self.keys.append(name)


def _run_with_vault(tmp_path: Path, rows=TWO_SIGNINS) -> Run:
    """Write the vault through `Vault.save`, never by hand.

    A hand-rolled `credentials.json` would let this whole file keep passing
    after the on-disk shape changed, which is the wrong way round: these tests
    are meant to fail when the thing they describe stops being true.
    """
    run = Run.create(
        tmp_path / "runs", "Signin Fixture", lab={"id": 1}, instance="i", agent="t",
        segments=[Segment(id="s00", title="Setup", anchor="setup")],
    )
    vault = Vault.capture(
        [Credential(scope=s, label=lbl, value=v) for s, lbl, v in rows],
        redactor=run.redactor,
    )
    vault.save(run.dir)
    return run


def _signin(run: Run, lab: FakeLab, arg: str = "vm") -> int:
    module = _lab_step()
    # No sleeping: the action waits 6s for the screen to settle and the test
    # has no console to wait for.
    original = asyncio.sleep

    async def _instant(_seconds):
        await original(0)

    module.asyncio.sleep = _instant
    try:
        return asyncio.run(module.do_signin(lab, run, "s00", arg))
    finally:
        module.asyncio.sleep = original


def _last_step(run: Run) -> dict:
    lines = (run.dir / "trace.jsonl").read_text(encoding="utf-8").strip().splitlines()
    return json.loads(lines[-1])


# --- the credential is chosen by role, never by the caller ------------------


def test_signin_vm_types_the_machine_password_not_the_portal_one(tmp_path):
    """The defect this action exists for, in one assertion.

    Both scopes carry a row called `Password`. The lock screen wants the
    9-character one. Nothing in the call names a credential.
    """
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))])
    _signin(run, lab, "vm")
    assert lab.typed == ["VmSecret9"]


def test_signin_portal_types_the_portal_password(tmp_path):
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112)), _frame((250, 250, 250))])
    _signin(run, lab, "portal")
    assert lab.typed == ["PortalSecret1!"]


def test_signin_defaults_to_the_password_field(tmp_path):
    """Both flows end at a password box, so that is the default.

    Typing a username into a password box is visible and harmless; typing the
    other family's secret is neither.
    """
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))])
    _signin(run, lab, "vm")
    assert lab.typed == ["VmSecret9"]
    assert _last_step(run)["action"].endswith("/password")


def test_signin_username_takes_the_account_field_of_the_same_role(tmp_path):
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))])
    _signin(run, lab, "portal/username")
    assert lab.typed == ["learner@example.invalid"]


# --- the verdict is read from the frame, not from the keystrokes -----------


def test_an_unchanged_screen_is_not_a_pass(tmp_path):
    """The whole point of measuring: sending input is not evidence of anything."""
    run = _run_with_vault(tmp_path)
    still = _frame((8, 64, 112))
    _signin(run, FakeLab([still, still]), "vm")
    assert _last_step(run)["verdict"] != "PASS"


def test_re_encoding_noise_does_not_count_as_the_screen_changing(tmp_path):
    """The guard against the guard's own first draft.

    `before != after` on JPEG bytes is true here -- the frames differ by a
    handful of pixels, exactly as a caret blink or a re-encode differs -- so a
    byte comparison would record PASS on a console that did not move. This test
    is the one that fails if anyone reaches for equality again.
    """
    run = _run_with_vault(tmp_path)
    before, after = _frame((8, 64, 112)), _frame((8, 64, 112), noise=3)
    assert before != after, "the fixture must differ by bytes or it proves nothing"
    _signin(run, FakeLab([before, after]), "vm")
    assert _last_step(run)["verdict"] != "PASS"


def test_an_unchanged_screen_records_blocked_and_not_a_finding(tmp_path):
    """Keystrokes reaching nothing is a fact about the console.

    Filing it as a lab defect is 2.22's dead-pane finding again: a real
    observation, correctly made, attributed to the wrong thing.
    """
    run = _run_with_vault(tmp_path)
    still = _frame((8, 64, 112))
    _signin(run, FakeLab([still, still]), "vm")
    step = _last_step(run)
    assert step["verdict"] == "BLOCKED"
    assert not step.get("severity")


def test_a_changed_screen_does_not_claim_the_sign_in_worked(tmp_path):
    """A rejection repaints too.

    "The password is incorrect" is a repaint, so magnitude cannot separate
    success from failure without a threshold nobody calibrated. The note has to
    say what was established and where the rest is settled.
    """
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((250, 250, 250))]), "vm")
    note = _last_step(run)["note"].lower()
    assert "input landed" in note
    assert "not established" in note
    assert "next capture" in note


def test_the_measured_delta_is_recorded(tmp_path):
    """A verdict derived from a number should show the number.

    Otherwise the threshold is unauditable from the trace, and a run sitting
    just under it looks identical to one sitting far below.
    """
    run = _run_with_vault(tmp_path)
    still = _frame((8, 64, 112))
    _signin(run, FakeLab([still, still]), "vm")
    assert "delta" in _last_step(run)["note"].lower()


def test_the_threshold_is_the_one_the_probe_already_calibrated(tmp_path):
    """Not a second opinion about what "the same screen" means.

    A frame pair either side of QUIET_THRESHOLD must land either side of the
    verdict, so the action cannot drift away from the quiet probe's calibration.
    """
    from lab_validator.imaging import stability

    quiet = (_frame((8, 64, 112)), _frame((8, 64, 112), noise=3))
    moved = (_frame((8, 64, 112)), _frame((250, 250, 250)))
    assert stability(*quiet) <= QUIET_THRESHOLD < stability(*moved)

    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab(list(quiet)), "vm")
    assert _last_step(run)["verdict"] == "BLOCKED"

    run2 = _run_with_vault(tmp_path / "second")
    _signin(run2, FakeLab(list(moved)), "vm")
    assert _last_step(run2)["verdict"] == "PASS"


# --- secrets never reach the trace -----------------------------------------


def test_neither_password_appears_in_the_trace(tmp_path):
    """Both are registered with the redactor, not just the one typed.

    A run that masks the credential it used and prints the one it rejected has
    leaked a live secret while looking careful.
    """
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))]), "vm")
    trace = (run.dir / "trace.jsonl").read_text(encoding="utf-8")
    assert "VmSecret9" not in trace
    assert "PortalSecret1!" not in trace


def test_the_note_names_the_scope_it_chose(tmp_path):
    """Which family was used is the first question a wrong sign-in raises."""
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))]), "vm")
    assert "Machine credentials" in _last_step(run)["note"]


# --- refusals name what they could not decide ------------------------------


def test_an_unknown_role_is_refused_before_anything_is_typed(tmp_path):
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112))])
    module = _lab_step()
    with pytest.raises(module.Stop):
        _signin(run, lab, "database")
    assert lab.typed == []


def test_a_role_the_lab_issued_no_credential_for_is_refused(tmp_path):
    """Refuses rather than falling back to the family it does have."""
    run = _run_with_vault(tmp_path, rows=TWO_SIGNINS[:2])
    lab = FakeLab([_frame((8, 64, 112))])
    module = _lab_step()
    with pytest.raises(module.Stop) as exc:
        _signin(run, lab, "vm")
    assert lab.typed == []
    assert "vm" in str(exc.value)


def test_a_run_with_no_vault_says_how_to_get_one(tmp_path):
    """The likeliest cause is a run started outside `walk`, so say that."""
    run = Run.create(
        tmp_path / "runs", "No Vault", lab={"id": 1}, instance="i", agent="t",
        segments=[Segment(id="s00", title="Setup", anchor="setup")],
    )
    module = _lab_step()
    with pytest.raises(module.Stop) as exc:
        _signin(run, FakeLab([_frame((8, 64, 112))]), "vm")
    assert "walk" in str(exc.value)
