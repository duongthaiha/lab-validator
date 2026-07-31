"""Tests for the run-scoped credential vault.

The lab hands out credentials once and the instructions refer back to them for
hours. Two properties matter and are tested here: that capturing a credential
*always* teaches the redactor to mask it (so the two cannot drift apart), and
that a live secret can only ever be written into the one gitignored tree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.labclient import Credential  # noqa: E402
from lab_validator.runlog import Redactor  # noqa: E402
from lab_validator.vault import Vault, VaultError, classify  # noqa: E402

# Invented, not copied from a run. Real ids belong only in `runs/`, which is
# gitignored precisely so that a committed fixture can never become a leak.
SUB_ID = "00000000-1111-2222-3333-444444444444"

ROWS = [
    Credential("Azure Portal", "Username", "learner@labtenant.onmicrosoft.com"),
    Credential("Azure Portal", "Password", "Sup3rSecret!Passw0rd"),
    Credential("Azure Portal", "Subscription ID", SUB_ID),
    Credential("Azure OpenAI", "Endpoint", "https://ai-foundry-example.openai.azure.com/"),
    Credential("Azure OpenAI", "Key", "abcdef0123456789abcdef0123456789"),
    Credential("Virtual Machine", "User", "Admin"),
]


def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "runs" / "2026-07-31T1200Z"
    d.mkdir(parents=True)
    return d


# --- capture and masking are one action ------------------------------------


def test_capturing_a_credential_also_teaches_the_redactor_to_mask_it():
    """Registering happens inside capture on purpose. If it were the caller's
    job there would be a path that captures without masking, and it would be
    found by reading a secret in a committed report."""
    redactor = Redactor()
    Vault.capture(ROWS, redactor)
    assert len(redactor) >= 4
    masked = redactor.text(f"signed in as learner with {SUB_ID}")
    assert SUB_ID not in masked
    assert "[REDACTED:Subscription ID]" in masked


def test_short_values_are_not_registered_as_secrets():
    """Masking a 5-character value corrupts ordinary prose in the trace."""
    redactor = Redactor()
    Vault.capture([Credential("VM", "User", "Admin")], redactor)
    assert redactor.text("the Admin account") == "the Admin account"


def test_capture_works_without_a_redactor():
    assert len(Vault.capture(ROWS)) == 6


# --- lookup ----------------------------------------------------------------


def test_lookup_by_scope_and_label():
    v = Vault.capture(ROWS)
    assert v.value("Azure Portal/Password") == "Sup3rSecret!Passw0rd"


def test_lookup_is_case_insensitive_and_tolerates_loose_wording():
    """Instructions name credentials loosely -- "your subscription" -- and an
    exact-only lookup fails on wording rather than on substance."""
    v = Vault.capture(ROWS)
    assert v.value("subscription") == SUB_ID


def test_an_ambiguous_loose_match_is_not_guessed():
    """Two scopes both have a "Key"-ish field; picking one would type the wrong
    secret into the right box and blame the lab for the failure."""
    v = Vault.capture([
        Credential("A", "Access Key", "aaaaaaaaaaaaaaaa"),
        Credential("B", "Account Key", "bbbbbbbbbbbbbbbb"),
    ])
    with pytest.raises(VaultError):
        v.value("key")
    assert v.value("A/Access Key") == "aaaaaaaaaaaaaaaa"


def test_a_missing_credential_raises_and_names_what_exists():
    """Returning None would let an agent type nothing into a password box and
    then report a login defect that is entirely its own."""
    v = Vault.capture(ROWS)
    with pytest.raises(VaultError, match="No credential"):
        v.value("Azure Portal/Tenant ID")
    try:
        v.value("Nope")
    except VaultError as exc:
        assert "Azure Portal/Username" in str(exc)


# --- credentials as data ---------------------------------------------------


def test_shape_classification():
    assert classify(SUB_ID) == "guid"
    assert classify("https://x.openai.azure.com/") == "url"
    assert classify("learner@labtenant.onmicrosoft.com") == "email"
    assert classify("Sup3rSecret!") == "text"


def test_subscription_id_needs_both_the_label_and_the_shape():
    """A lab that labels a field "Subscription" and puts a display name in it
    would otherwise yield an id no Azure call accepts, and the failures would
    be blamed on the instructions."""
    assert Vault.capture(ROWS).subscription_id() == SUB_ID
    misleading = Vault.capture([Credential("Azure", "Subscription", "Skillable Sandbox")])
    assert misleading.subscription_id() is None


def test_endpoints_are_exposed_for_comparison_against_shipped_config():
    """This is the left-hand side of the comparison that catches a shipped
    .env pointing somewhere else."""
    ends = Vault.capture(ROWS).endpoints()
    assert ends["Azure OpenAI/Endpoint"] == "https://ai-foundry-example.openai.azure.com/"
    assert len(ends) == 1


# --- reporting -------------------------------------------------------------


def test_redacted_rows_carry_no_secret():
    rows = Vault.capture(ROWS).redacted_rows()
    blob = json.dumps(rows)
    assert SUB_ID not in blob
    assert "Sup3rSecret!Passw0rd" not in blob
    assert "Subscription ID" in blob
    assert "guid" in blob


# --- persistence -----------------------------------------------------------


def test_saving_and_reloading_round_trips(tmp_path):
    d = run_dir(tmp_path)
    Vault.capture(ROWS).save(d)
    again = Vault.load(d)
    assert again is not None
    assert again.value("Azure Portal/Password") == "Sup3rSecret!Passw0rd"


def test_the_saved_file_warns_what_it_holds(tmp_path):
    d = run_dir(tmp_path)
    path = Vault.capture(ROWS).save(d)
    assert "gitignored" in json.loads(path.read_text(encoding="utf-8"))["_warning"]


def test_writing_outside_runs_is_refused(tmp_path):
    """A guard, not a convention. "Do not write secrets outside runs/" holds
    until someone adds a debug flag at 2am."""
    with pytest.raises(VaultError, match="refusing to write"):
        Vault.capture(ROWS).save(tmp_path / "somewhere-else")


def test_loading_a_run_that_has_no_vault_is_not_an_error(tmp_path):
    """Resuming a run started before vaults existed is normal."""
    assert Vault.load(run_dir(tmp_path)) is None


def test_runs_is_gitignored():
    """The whole secrets position rests on this one line, so assert it."""
    ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text(encoding="utf-8")
    assert any(line.strip() == "runs/" for line in ignore.splitlines())


# --- two sign-ins, two credential families ----------------------------------
#
# Every test below is here because a real walk typed the Azure password into a
# Windows lock screen, thirteen times, and reported the lab as broken. The lab
# was fine. Both families were captured correctly; the tool could not keep them
# apart, and nothing about that failure was visible until a human watched it.

TWO_SIGNINS = [
    Credential("Azure Portal", "Username", "learner@labtenant.onmicrosoft.com"),
    Credential("Azure Portal", "Password", "P0rtalSecret!23"),
    Credential("Machine credentials", "Username", "Admin"),
    Credential("Machine credentials", "Password", "M4chineSecret"),
]


def test_a_label_carried_by_two_scopes_keeps_both():
    """The original defect. Two of eight credentials became unreachable.

    ``label_index`` was a dict comprehension keyed on the label, so the second
    "Password" overwrote the first and the survivor was decided by the order of
    the Resources tab.
    """
    index = Vault.capture(TWO_SIGNINS).label_index()
    assert index["password"] == ("Azure Portal/Password", "Machine credentials/Password")
    assert index["username"] == ("Azure Portal/Username", "Machine credentials/Username")


def test_an_unscoped_reference_to_a_duplicated_label_refuses():
    """Returning the first match is selecting by position (principle 13)."""
    with pytest.raises(VaultError, match="ambiguous"):
        Vault.capture(TWO_SIGNINS).value("password")


def test_the_ambiguity_refusal_names_both_candidates():
    """A refusal that does not say what to type instead just stops the walk."""
    with pytest.raises(VaultError) as exc:
        Vault.capture(TWO_SIGNINS).value("password")
    assert "Azure Portal/Password" in str(exc.value)
    assert "Machine credentials/Password" in str(exc.value)


def test_a_sign_in_resolves_to_its_own_scope_and_never_the_other():
    """The property the whole role table exists for."""
    vault = Vault.capture(TWO_SIGNINS)

    vm_user, vm_pass = vault.signin("vm")
    portal_user, portal_pass = vault.signin("portal")

    assert (vm_user.value, vm_pass.value) == ("Admin", "M4chineSecret")
    assert portal_pass.value == "P0rtalSecret!23"
    assert vm_pass.value != portal_pass.value
    assert portal_user.value.endswith("onmicrosoft.com")


def test_a_role_reference_types_the_machine_password_not_the_portal_one():
    """`vm/password` is the ref the agent uses; it must be unmistakable."""
    vault = Vault.capture(TWO_SIGNINS)
    assert vault.value("vm/password") == "M4chineSecret"
    assert vault.value("portal/password") == "P0rtalSecret!23"
    assert vault.value("vm/username") == "Admin"


def test_a_scope_naming_two_roles_is_refused_rather_than_picked():
    """"Azure VM credentials" is both. Choosing either would be a guess."""
    from lab_validator.vault import role_of

    assert role_of("Azure VM credentials") is None
    assert role_of("Machine credentials") == "vm"
    assert role_of("Azure Portal") == "portal"
    assert role_of("Open AI Endpoint") is None


def test_a_sign_in_the_lab_never_issued_refuses_and_says_what_it_did_issue():
    vault = Vault.capture([Credential("Azure Portal", "Password", "P0rtalSecret!23")])
    with pytest.raises(VaultError) as exc:
        vault.signin("vm")
    assert "portal" in str(exc.value)


def test_half_a_credential_pair_refuses_rather_than_signing_in_with_one():
    """A username typed into a password box fails exactly like a bad password."""
    vault = Vault.capture([Credential("Machine credentials", "Password", "M4chineSecret")])
    with pytest.raises(VaultError, match="missing its username"):
        vault.signin("vm")


def test_an_unknown_sign_in_names_the_ones_that_exist():
    with pytest.raises(VaultError, match="Unknown sign-in"):
        Vault.capture(TWO_SIGNINS).signin("database")


def test_load_primes_the_redactor_it_is_given(tmp_path):
    """The resumed-run guarantee, asserted directly.

    `capture` has registered with the redactor since it was written, on the
    grounds that there must be no way to take a credential without teaching the
    writer to mask it. `load` did not, and `load` is the one that runs on every
    resumed step from seven call sites -- so `auto --run <folder>` could type a
    password nothing had been told about.
    """
    d = run_dir(tmp_path)
    Vault.capture(ROWS).save(d)

    fresh = Redactor()
    Vault.load(d, redactor=fresh)

    # Only values the redactor will accept. A short one such as `Admin` is
    # dropped on purpose -- masking a 5-character common word corrupts far more
    # text than it protects -- and asserting otherwise would make this test
    # describe a policy the project deliberately does not have.
    maskable = [r for r in ROWS if len(r.value) >= Redactor.min_length]
    assert maskable, "the fixture has nothing long enough to mask"
    for row in maskable:
        assert row.value not in fresh.scrub(f"leaked {row.value} here")


def test_load_without_a_redactor_still_works(tmp_path):
    """Read-only callers exist -- `scope` reviews a run without typing anything.

    Requiring a redactor would make the safe path harder than the unsafe one.
    """
    d = run_dir(tmp_path)
    Vault.capture(ROWS).save(d)
    assert Vault.load(d) is not None
