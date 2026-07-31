"""Tests for recognising when an instruction asks for a lab-issued value.

The asymmetry drives every test here. A **missed** ask stops the walk and a
human notices. An **invented** ask types a credential into whatever happens to
be focused, and nobody notices until it appears in a screenshot. So there are
more tests about not firing than about firing, and the negative cases are the
ones worth reading.
"""

from __future__ import annotations

import pytest

from lab_validator.asks import Ask, asks_in
from lab_validator.labclient import Credential
from lab_validator.vault import Vault

LABELS = {
    "username": ("Azure/Username",),
    "password": ("Azure/Password",),
    "subscription id": ("Azure/Subscription ID",),
    "resource group": ("Azure/Resource Group",),
    "endpoint": ("Azure/Endpoint",),
}


# --- it fires when it should ------------------------------------------------


@pytest.mark.parametrize("text,term", [
    ("Sign in with the username from the Resources tab.", "username"),
    ("Enter the password shown in the Resources tab.", "password"),
    ("Paste your subscription ID into the field.", "subscription id"),
    ("Use the resource group listed on the Resources tab.", "resource group"),
    ("Replace <endpoint> with the endpoint from the portal.", "endpoint"),
    ("Type the username, then select Next.", "username"),
    ("Specify the region for your deployment.", "region"),
])
def test_an_instruction_asking_for_a_value_is_recognised(text, term):
    terms = {a.term for a in asks_in(text, LABELS)}
    assert term in terms


def test_a_recognised_ask_resolves_to_a_typeable_action():
    (ask,) = asks_in("Sign in with the username from the Resources tab.", LABELS)
    assert ask.satisfied
    assert ask.ref == "Azure/Username"
    assert ask.action() == "cred:Azure/Username"


def test_several_values_in_one_sentence_are_all_found():
    asks = asks_in("Enter the username and password from the Resources tab.", LABELS)
    assert {a.term for a in asks} == {"username", "password"}
    assert all(a.satisfied for a in asks)


def test_the_sentence_is_kept_so_the_decision_is_reviewable():
    (ask,) = asks_in("Now enter the password to continue.", LABELS)
    assert ask.sentence == "Now enter the password to continue."


# --- it does NOT fire when it should not ------------------------------------


@pytest.mark.parametrize("text", [
    # Prose about a credential is not a request for one.
    "The password policy requires twelve characters.",
    "Your subscription includes a monthly credit.",
    "The endpoint is regional and cannot be changed later.",
    "A resource group is a logical container for related resources.",
    "This lab issues a username for each learner.",
])
def test_prose_about_a_credential_is_not_a_request_for_one(text):
    assert asks_in(text, LABELS) == []


@pytest.mark.parametrize("text", [
    "You do not need to enter a password.",
    "Do not type the subscription ID here.",
    "No need to provide a username at this step.",
    "Leave the password blank and select Next.",
    "You will not be asked to enter the endpoint.",
])
def test_a_negated_instruction_never_produces_an_ask(text):
    """Acting on the reverse of an instruction is worse than not acting."""
    assert asks_in(text, LABELS) == []


def test_a_cue_in_one_sentence_does_not_leak_into_the_next():
    """Sentence-scoped, or a page with any 'enter' anywhere types everything."""
    text = "Select Enter to continue. A password is a shared secret."
    assert asks_in(text, LABELS) == []


def test_a_negation_in_one_sentence_does_not_suppress_a_real_ask_in_another():
    text = "You do not need to enter a password. Now enter the username."
    terms = {a.term for a in asks_in(text, LABELS)}
    assert terms == {"username"}


# --- longest-match: typing the wrong secret is the failure mode -------------


def test_subscription_id_is_not_consumed_by_subscription():
    (ask,) = asks_in("Paste the subscription ID into the terminal.", LABELS)
    assert ask.term == "subscription id"
    assert ask.ref == "Azure/Subscription ID"


def test_user_name_written_as_two_words_still_resolves():
    (ask,) = asks_in("Enter the user name from the Resources tab.", LABELS)
    assert ask.ref == "Azure/Username"


def test_a_term_is_not_matched_inside_a_longer_word():
    """'allocation' contains 'location' and is not a request for a region."""
    assert asks_in("Use the allocation settings shown here.", LABELS) == []


def test_repeated_asks_for_the_same_value_collapse():
    text = ("Enter the password. Then enter the password again. "
            "Finally, type the password once more.")
    asks = asks_in(text, LABELS)
    assert len(asks) == 1


# --- the finding: an ask the environment cannot satisfy ---------------------


def test_asking_for_a_value_the_lab_never_issued_is_unsatisfied_not_silent():
    """A stale instruction survives an edition where provisioning changed.

    The learner reads it, goes looking, finds nothing, and blames themselves.
    This is the machine-readable version of that.
    """
    (ask,) = asks_in("Copy the resource group from the Resources tab.",
                     {"username": ("Azure/Username",)})
    assert ask.term == "resource group"
    assert not ask.satisfied
    assert ask.ref is None
    assert ask.action() is None
    assert "NOT ISSUED" in str(ask)


def test_with_nothing_captured_asks_are_reported_unsatisfied_not_absent():
    """An empty list would claim the text asked for nothing, which is a lie."""
    asks = asks_in("Sign in with the username and password.", None)
    assert {a.term for a in asks} == {"username", "password"}
    assert not any(a.satisfied for a in asks)


def test_the_matcher_never_needs_a_secret_to_do_its_job():
    """Resolution is on labels only; the value never enters the decision."""
    labels = Vault.capture([
        Credential(scope="Azure", label="Password", value="Sup3rSecret!value"),
    ]).label_index()
    assert "Sup3rSecret!value" not in str(labels)
    (ask,) = asks_in("Enter the password.", labels)
    assert ask.ref == "Azure/Password"
    assert "Sup3rSecret!value" not in str(ask)


# --- the vault join ---------------------------------------------------------


def test_a_vault_answers_directly_what_an_instruction_is_asking_for():
    vault = Vault.capture([
        Credential(scope="Azure", label="Username", value="learner@lab.example"),
        Credential(scope="Azure", label="Password", value="Sup3rSecret!value"),
    ])
    asks = vault.asks_in("Sign in with the username and password from the Resources tab.")
    assert [a.action() for a in asks] == ["cred:Azure/Username", "cred:Azure/Password"]


def test_the_label_index_exposes_labels_and_never_values():
    vault = Vault.capture([
        Credential(scope="Azure", label="Password", value="Sup3rSecret!value"),
    ])
    index = vault.label_index()
    assert index == {"password": ("Azure/Password",)}


def test_matching_is_on_the_label_the_environment_used():
    """Never on a name derived from the instruction (principle 11)."""
    vault = Vault.capture([
        Credential(scope="Lab", label="Admin Username", value="admin@lab.example"),
    ])
    (ask,) = vault.asks_in("Enter the username to sign in.")
    assert ask.ref == "Lab/Admin Username"
    assert ask.label == "admin username"


def test_an_ask_is_hashable_and_comparable_so_it_can_be_deduped_by_callers():
    a = Ask(term="password", sentence="Enter the password.", ref="Azure/Password")
    b = Ask(term="password", sentence="Enter the password.", ref="Azure/Password")
    assert a == b
    assert len({a, b}) == 1


# --- one label, two credentials ---------------------------------------------


def test_an_ask_that_two_credentials_fit_types_nothing():
    """Ambiguity must not resolve. Typing either is a coin toss with a secret."""
    vault = Vault.capture([
        Credential(scope="Azure Portal", label="Password", value="P0rtalSecret!23"),
        Credential(scope="Machine credentials", label="Password", value="M4chineSecret"),
    ])
    (ask,) = vault.asks_in("Enter the password from the Resources tab.")

    assert ask.ambiguous
    assert not ask.satisfied
    assert ask.action() is None, "an ambiguous ask must produce no keystrokes"


def test_an_ambiguous_ask_is_not_reported_as_a_missing_credential():
    """Two different facts. One is a lab defect; the other is our own limit."""
    vault = Vault.capture([
        Credential(scope="Azure Portal", label="Password", value="P0rtalSecret!23"),
        Credential(scope="Machine credentials", label="Password", value="M4chineSecret"),
    ])
    (ask,) = vault.asks_in("Enter the password from the Resources tab.")

    assert "NOT ISSUED" not in str(ask)
    assert "AMBIGUOUS" in str(ask)
    assert "Azure Portal/Password" in str(ask)
    assert "Machine credentials/Password" in str(ask)


def test_the_old_flat_mapping_is_refused_rather_than_iterated():
    """A bare string iterates per character and resolves to plausible nonsense.

    Found by running the suite mid-change: a stale caller produced the ask
    ``username -> AMBIGUOUS, could be any of: c, r, e, d, -, 1``. Every part of
    that looks like a working reference.
    """
    with pytest.raises(TypeError, match="is a string"):
        asks_in("Enter the password.", {"password": "Azure/Password"})
