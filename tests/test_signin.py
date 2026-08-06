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
import re
import sys
from pathlib import Path

import pytest
from PIL import Image

from lab_validator.imaging import stability
from lab_validator.labclient import Credential
from lab_validator.runlog import Redactor, Run, Segment
from lab_validator.vault import Vault

ROOT = Path(__file__).resolve().parents[1]

#: Frames from the run that recorded PASS for a rejected sign-in. Kept as a
#: regression fixture: synthetic frames cannot reproduce the overlap that made
#: the threshold impossible, because the real ones differ by a line of text.
REAL = ROOT / "runs" / "2026-08-01T0948Z" / "images"

#: The reference walk, which contains a *successful* VM sign-in: the lock screen
#: followed by the "Welcome" screen. Needed because the failing run never got
#: one, and a single class of frame cannot show an overlap.
REF = ROOT / "runs" / "2026-07-30T0749Z" / "images"


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


def _unlocked(run: Run) -> Run:
    """Satisfy the ordering guard, the way a real walk does.

    `signin:portal` is refused until the VM has been signed in to, so any test
    about the portal path has to get there legitimately rather than by editing
    the trace.
    """
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))]), "vm")
    return run


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
    run = _unlocked(_run_with_vault(tmp_path))
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
    run = _unlocked(_run_with_vault(tmp_path))
    lab = FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))])
    _signin(run, lab, "portal/username")
    assert lab.typed == ["learner@example.invalid"]


# --- the order is not a parameter either -----------------------------------


def test_portal_before_vm_is_refused_without_typing_anything(tmp_path):
    """The defect the second live run showed, after the first fix.

    Binding the credential to the role fixed only half of it. The model *did*
    call `signin:`, and still asked for `portal` while looking at a Windows
    lock screen captioned `Admin` with a password box on it -- because its task
    said "sign in to the Azure portal".

    These keystrokes go to the VM. A cloud sign-in inside the VM's browser is
    unreachable until the machine is unlocked, so this request cannot be
    correct whatever the screen shows, and no amount of looking at the screen
    is needed to know that.
    """
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112))])
    module = _lab_step()
    with pytest.raises(module.Stop) as exc:
        _signin(run, lab, "portal")
    assert lab.typed == [], "a refused sign-in must not have typed"
    assert "signin:vm" in str(exc.value), "the refusal must name the move to make"


def test_the_vm_sign_in_itself_is_never_blocked_by_the_ordering_guard(tmp_path):
    """Otherwise nothing could ever go first."""
    run = _run_with_vault(tmp_path)
    lab = FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))])
    _signin(run, lab, "vm")
    assert lab.typed == ["VmSecret9"]


def test_the_ordering_guard_reads_the_trace_so_a_resumed_run_inherits_it(tmp_path):
    """`auto --run <folder>` rebuilds from disk; this must not be the one fact
    that resets.

    A fresh `Run` object over the same folder still knows the VM was signed in
    to, because the guard reads `trace.jsonl` rather than memory.
    """
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))]), "vm")

    resumed = Run.open(run.dir)
    lab = FakeLab([_frame((8, 64, 112)), _frame((250, 250, 250))])
    _signin(resumed, lab, "portal")
    assert lab.typed == ["PortalSecret1!"]


def test_only_a_vm_sign_in_satisfies_the_guard_not_any_sign_in(tmp_path):
    """The guard must not be satisfied by the thing it exists to prevent.

    Today `startswith("signin:")` would behave identically, because a non-vm
    sign-in cannot reach the trace without a vm one preceding it -- but that
    argument is circular: it holds only while this very guard holds. So the
    trace is seeded directly, bypassing `do_signin`, and the refusal must
    survive it. Otherwise a later exemption for some third role would quietly
    unlock the guard for every role at once.
    """
    run = _run_with_vault(tmp_path)
    run.step(
        "s00",
        action="signin:portal/password",
        surface="vm",
        verdict="DEFERRED",
        severity=None,
        note="seeded, not performed",
    )
    lab = FakeLab([_frame((8, 64, 112))])
    module = _lab_step()
    with pytest.raises(module.Stop):
        _signin(run, lab, "portal")
    assert lab.typed == []


# --- the verdict does not come from the pixels -----------------------------
#
# Measured on real frames from this lab:
#
#     lock screen -> "The password is incorrect"   0.80   FAILED
#     lock screen -> "Welcome"                     0.23   SUCCEEDED
#     lock screen -> "Welcome"                     1.20   SUCCEEDED
#
# A success can score below a failure. Both screens are the same flat blue with
# the same avatar and the same account name; the only difference is one line of
# text. No threshold separates those populations, so the action must not try.


def test_a_sign_in_never_claims_pass_however_much_the_screen_moved(tmp_path):
    """Whatever the delta, the outcome is not established here.

    The previous version passed at delta > 0.6 and recorded PASS for a real
    rejection that measured 0.80.
    """
    run = _run_with_vault(tmp_path)
    for before, after in [
        (_frame((8, 64, 112)), _frame((8, 64, 112))),           # nothing moved
        (_frame((8, 64, 112)), _frame((8, 64, 112), noise=3)),  # a caret's worth
        (_frame((8, 64, 112)), _frame((250, 250, 250))),        # whole screen
    ]:
        _signin(run, FakeLab([before, after]), "vm")
        assert _last_step(run)["verdict"] != "PASS"


def test_a_sign_in_defers_rather_than_guessing(tmp_path):
    """DEFERRED, not BLOCKED and not a finding.

    The action was performed; its outcome is settled by a screenshot. Calling
    it BLOCKED would claim it failed, and calling it a finding would blame the
    lab for something not yet observed.
    """
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((250, 250, 250))]), "vm")
    step = _last_step(run)
    assert step["verdict"] == "DEFERRED"
    assert not step.get("severity")


def test_the_note_says_the_delta_cannot_settle_it_and_what_can(tmp_path):
    """A deferral that does not say who settles it is just a shrug.

    The `or` this used to contain made it vacuous: truncating the note to
    "capture the screen." satisfied the alternative and left the reader with an
    instruction and no way to act on it. Both halves are required -- go and
    look, *and* here is what you are looking for.
    """
    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((250, 250, 250))]), "vm")
    note = _last_step(run)["note"].lower()
    assert "cannot tell" in note, "it must say the measurement is not the answer"
    assert "read it" in note, "it must say to go and look"
    assert "password box" in note and "failed" in note, (
        "it must say what a failure looks like -- 'go and look' with no idea "
        "what at is how thirteen wrong passwords got typed in the first place"
    )


def test_the_real_failed_sign_in_frames_do_not_produce_a_pass(tmp_path):
    """Regression, against the actual frames from the run that got it wrong.

    Not synthetic: these are the lock screen and the "The password is
    incorrect. Try again." screen that the tool recorded as PASS.
    """
    lock = REAL / "0004-s00-create-microsoft-screen-state.jpg"
    err = REAL / "0005-s00-create-microsoft-after-signin.jpg"
    if not (lock.exists() and err.exists()):
        pytest.skip("evidence run not present")

    run = _run_with_vault(tmp_path)
    _signin(run, FakeLab([lock.read_bytes(), err.read_bytes()]), "vm")
    assert _last_step(run)["verdict"] != "PASS"


def test_the_measured_delta_is_recorded_as_a_number_not_just_the_word(tmp_path):
    """The delta decides nothing, so it must at least be *auditable*.

    Two ways this test has been vacuous. The first version only exercised the
    unchanged path, so deleting the delta from the moved path left it green.
    The second asserted the word "delta", which survives in the note's own
    explanation of why the delta cannot settle anything -- so removing the
    measurement still passed. It has to look for the number.
    """
    for frames in [
        [_frame((8, 64, 112)), _frame((8, 64, 112))],
        [_frame((8, 64, 112)), _frame((250, 250, 250))],
    ]:
        run = _run_with_vault(tmp_path / str(id(frames)))
        _signin(run, FakeLab(frames), "vm")
        note = _last_step(run)["note"]
        assert re.search(r"delta \d+\.\d", note), f"no measurement in: {note}"


def test_success_and_failure_frames_overlap_so_no_threshold_can_exist(tmp_path):
    """The measurement that closed this question, kept as a test.

    Someone will eventually look at `signin:` returning DEFERRED every time and
    think a threshold would be tidier. It would not: these are the real frames,
    and a successful sign-in scores *below* a failed one.

        lock -> "The password is incorrect"   0.80   FAILED
        lock -> "Welcome"                     0.23   SUCCEEDED

    Both screens are the same flat blue with the same avatar and the same
    account name. The only difference is a line of text, and mean pixel
    difference cannot read text.
    """
    lock = REAL / "0004-s00-create-microsoft-screen-state.jpg"
    err = REAL / "0005-s00-create-microsoft-after-signin.jpg"
    welcome = REF / "0003-s00-create-microsoft-desktop.jpg"
    login = REF / "0002-s00-create-microsoft-login.jpg"
    if not all(p.exists() for p in (lock, err, welcome, login)):
        pytest.skip("evidence runs not present")

    failed = stability(lock.read_bytes(), err.read_bytes())
    succeeded = stability(login.read_bytes(), welcome.read_bytes())

    assert succeeded < failed, (
        f"a successful sign-in ({succeeded:.2f}) must still measure below a failed "
        f"one ({failed:.2f}) -- if this ever stops being true, re-open the question "
        "of whether a threshold is possible, but do not assume it"
    )


# --- secrets never reach the trace -----------------------------------------


def test_both_passwords_are_masked_afterwards_not_just_the_one_typed(tmp_path):
    """Tests the redactor on the *resumed* path, which is where this can fail.

    Two false starts are worth recording, because both looked fine.

    The first version asserted neither password appears in `trace.jsonl`. It
    passes with masking disabled entirely, because the note only holds a scope
    and a label -- the secrets were never written, so masking was never
    exercised.

    The second asserted the redactor masks both after `do_signin`. It also
    passed unconditionally, because the fixture built its vault with
    `Vault.capture(..., redactor=run.redactor)`, which registers at capture
    time. The test could not tell whether `do_signin` had done anything.

    So this one throws the primed redactor away first, which is exactly what
    `auto --run <folder>` does: a resumed run rebuilds its Run object, loads
    the vault from disk, and until `Vault.load` took a redactor it would type
    a password nothing had been told to mask.
    """
    run = _run_with_vault(tmp_path)
    run.redactor = Redactor()
    assert run.redactor.scrub(TWO_SIGNINS[3][2]) == TWO_SIGNINS[3][2], (
        "the fixture must start unprimed or this proves nothing"
    )

    _signin(run, FakeLab([_frame((8, 64, 112)), _frame((30, 30, 30))]), "vm")

    leak = f"used {TWO_SIGNINS[3][2]} after rejecting {TWO_SIGNINS[1][2]}"
    masked = run.redactor.scrub(leak)
    assert TWO_SIGNINS[3][2] not in masked, "the credential it typed is not masked"
    assert TWO_SIGNINS[1][2] not in masked, "the credential it rejected is not masked"


def test_no_password_reaches_the_trace(tmp_path):
    """Kept as a floor, and honest about being weaker than it looks.

    This passes for the wrong reason today -- the note holds no values at all.
    It is here to fail if someone puts one there, not as evidence the redactor
    works; that is the test above.
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


def test_a_cred_ref_on_a_resumed_run_primes_the_redactor(tmp_path):
    """`cred:` hands back a secret to type. On a resumed run, nothing had
    registered it.

    Same defect as the sign-in path and a wider blast radius: every `cred:` ref
    in every step goes through here, and the value is returned to be typed. A
    walk resumed with `auto --run <folder>` would type it with the writer
    unable to mask it, so any later step quoting the field -- an error toast, a
    tool result -- would print a live secret into the trace.
    """
    run = _run_with_vault(tmp_path)
    run.redactor = Redactor()
    secret = TWO_SIGNINS[3][2]
    assert run.redactor.scrub(secret) == secret, "fixture must start unprimed"

    module = _lab_step()
    value = asyncio.run(
        module.resolve_credential(FakeLab([_frame((8, 64, 112))]), run, "vm/password")
    )

    assert value == secret, "the ref must still resolve"
    assert secret not in run.redactor.scrub(f"leaked {secret}")


# --- the action vocabulary ----------------------------------------------------
#
# Written after a live walk stopped here: `SKILL.md` Step 6 tells the reader to
# sign in with `--do signin:vm`, and `lab_step.py --help` did not list a
# `signin:` action at all. The action worked -- the dispatcher had always
# handled it -- so nothing failed loudly. It simply read as unsupported to
# anyone who checked the help first, which is what a careful operator does.
# `scroll:` was missing the same way.
#
# The doc guards in test_skill.py scrape `lab-validator <cmd> --flag`, so a
# `--do` value drifting from the dispatcher was invisible to all of them.


def test_every_action_the_dispatcher_handles_is_in_the_help():
    """`--help` is the doc nobody has to go looking for, so it drifts first.

    An action missing here is worse than an undocumented feature: the operator
    concludes the capability is absent and reaches for a bypass instead -- which
    is exactly the behaviour the learner-path rule exists to prevent.
    """
    # The engine's own table, not a scrape of it: the dispatch used to be an
    # if/elif chain that could only be read as text, and the regex that read it
    # went stale the moment the chain became a dict.
    handled = set(_lab_step().ACTIONS)

    documented = set(re.findall(r"^  (\w+)[: \[]", _lab_step().HELP, re.M))

    missing = sorted(handled - documented)
    assert not missing, (
        f"lab_step.py handles --do actions its own --help never mentions: {missing}"
    )


def test_the_help_does_not_promise_an_action_that_does_not_exist():
    """The other direction, and the more dangerous one.

    A documented action that no longer dispatches fails mid-walk, against a
    running lab clock, with a human waiting.
    """
    handled = set(_lab_step().ACTIONS)

    documented = set(re.findall(r"^  (\w+)[: \[]", _lab_step().HELP, re.M))
    # `until` probes are listed in the same indented style but are arguments to
    # an action, not actions; they are checked by their own tests.
    probes = {"connected", "quiet"}

    phantom = sorted(documented - handled - probes)
    assert not phantom, (
        f"--help offers --do actions the dispatcher does not handle: {phantom}"
    )
