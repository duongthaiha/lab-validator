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
