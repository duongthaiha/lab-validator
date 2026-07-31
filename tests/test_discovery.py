"""Tests for the discovery core.

Discovery's parsing is exercised here against DOM records shaped like the ones
``LINKS_JS`` returns, so the fiddly part is verified without a lab session --
which is the whole reason it was split away from the browser.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.discovery import (  # noqa: E402
    Enrolment,
    descriptor_for,
    parse_enrolments,
    resolve,
    scaffold,
    slugify,
    write_scaffold,
)
from lab_validator.targets import Target, TargetError  # noqa: E402

# --- slugify -------------------------------------------------------------


@pytest.mark.parametrize(
    "title,expected",
    [
        ("WorkshopPLUS - Azure AI Platform and Services", "azure-ai-platform-and-services"),
        ("WorkshopPLUS – Azure Kubernetes Service", "azure-kubernetes-service"),
        (
            "Azure AI: Platform and Services, All Modules (20260318)",
            "azure-ai-platform-and-services",
        ),
        ("  Spaced   Out  ", "spaced-out"),
        ("!!!", "untitled"),
    ],
)
def test_slugify(title, expected):
    assert slugify(title) == expected


def test_slugify_strips_accents_not_meaning():
    assert slugify("Sécurité Azure") == "securite-azure"


# --- parse_enrolments ----------------------------------------------------


def test_parses_an_enrolment_from_an_anchor():
    links = [{"text": "WorkshopPLUS - Azure AI", "href": "/ClassEnrollment/5928204"}]
    (e,) = parse_enrolments(links)
    assert e.enrolment == 5928204
    assert e.url == "https://mslearningcampus.com/ClassEnrollment/5928204"


def test_ignores_unrelated_links():
    links = [
        {"text": "Home", "href": "/Pages/ms-learningcampus"},
        {"text": "Sign out", "href": "/User/Logout"},
    ]
    assert parse_enrolments(links) == []


def test_collapses_duplicate_anchors_and_keeps_the_human_title():
    """A row has several anchors; 'Launch' identifies it but does not name it."""
    links = [
        {"text": "Launch", "href": "/ClassEnrollment/5928204"},
        {"text": "WorkshopPLUS - Azure AI Platform", "href": "/ClassEnrollment/5928204"},
        {"text": "", "href": "/ClassEnrollment/5928204"},
    ]
    (e,) = parse_enrolments(links)
    assert e.title == "WorkshopPLUS - Azure AI Platform"


def test_merges_ids_discovered_on_different_anchors():
    links = [
        {"text": "Course", "href": "/ClassEnrollment/5928204?classId=763682"},
        {"text": "Lab", "href": "/ClassEnrollment/5928204/LabProfile/79233"},
    ]
    (e,) = parse_enrolments(links)
    assert (e.class_id, e.lab_id) == (763682, 79233)


def test_sorted_by_title():
    links = [
        {"text": "Zebra", "href": "/ClassEnrollment/2"},
        {"text": "alpha", "href": "/ClassEnrollment/1"},
    ]
    assert [e.title for e in parse_enrolments(links)] == ["alpha", "Zebra"]


def test_absolute_urls_parse_too():
    links = [{"text": "X", "href": "https://mslearningcampus.com/ClassEnrollment/77"}]
    assert parse_enrolments(links)[0].enrolment == 77


# --- scaffold ------------------------------------------------------------


def test_scaffold_is_valid_toml():
    e = Enrolment(enrolment=1, title="WorkshopPLUS - Demo", href="/ClassEnrollment/1")
    tomllib.loads(scaffold(e))  # raises if not


def test_scaffold_records_only_what_was_observed():
    """The central rule: never invent a value."""
    e = Enrolment(enrolment=1, title="Demo", href="/ClassEnrollment/1")
    data = tomllib.loads(scaffold(e))
    assert data["lab"]["enrollment"] == 1
    # unobserved ids must be absent, not zero or empty
    assert "id" not in data["lab"]
    assert "class_id" not in data["lab"]
    assert "region" not in data.get("expect", {})


def test_scaffold_writes_observed_ids_when_known():
    e = Enrolment(enrolment=1, title="Demo", href="/x", class_id=22, lab_id=33)
    data = tomllib.loads(scaffold(e))
    assert (data["lab"]["class_id"], data["lab"]["id"]) == (22, 33)


def test_scaffold_leaves_a_todo_for_every_unobserved_value():
    e = Enrolment(enrolment=1, title="Demo", href="/x")
    todos = [ln for ln in scaffold(e).splitlines() if ln.startswith("# TODO ")]
    keys = {ln.split()[2].rstrip(":") for ln in todos}
    assert {"id", "class_id", "region", "models", "vm_user"} <= keys


def test_scaffold_escapes_quotes_in_a_title():
    e = Enrolment(enrolment=1, title='The "Real" Workshop', href="/x")
    assert tomllib.loads(scaffold(e))["name"] == 'The "Real" Workshop'


def test_a_fresh_scaffold_does_not_load_as_runnable(tmp_path):
    """Incomplete by design: it must not pass as something a run can rely on."""
    e = Enrolment(enrolment=1, title="Demo", href="/x")
    write_scaffold(e, tmp_path, slug="demo")
    with pytest.raises(TargetError, match="lab.id"):
        Target.load("demo", root=tmp_path)


def test_inspect_reports_a_scaffold_gaps_instead_of_raising(tmp_path):
    """Onboarding needs the list of what is missing, not an exception."""
    e = Enrolment(enrolment=1, title="Demo", href="/x")
    write_scaffold(e, tmp_path, slug="demo")
    target = Target.inspect("demo", root=tmp_path)
    assert target.slug == "demo"
    assert any(p.where == "lab.id" for p in target.problems)


def test_inspect_still_raises_on_a_genuine_io_fault(tmp_path):
    """An unparseable or absent file is not 'an incomplete descriptor'."""
    with pytest.raises(TargetError, match="No target descriptor"):
        Target.inspect("nope", root=tmp_path)
    (tmp_path / "bad.toml").write_text("this is not = = toml", encoding="utf-8")
    with pytest.raises(TargetError, match="not valid TOML"):
        Target.inspect("bad", root=tmp_path)


def test_write_scaffold_refuses_to_clobber_the_same_slug(tmp_path):
    e = Enrolment(enrolment=1, title="Demo", href="/x")
    write_scaffold(e, tmp_path, slug="demo")
    with pytest.raises(FileExistsError):
        write_scaffold(e, tmp_path, slug="demo")
    write_scaffold(e, tmp_path, slug="demo", overwrite=True)  # explicit is fine


def test_multiline_card_text_reduces_to_the_title(tmp_path):
    """`innerText` on a card anchor is multi-line and the longest-title merge
    makes that blob win. Unflattened it produces a descriptor that won't parse,
    and even flattened it poisons the title and slug with 'Launch' and a date."""
    links = [
        {"text": "Launch", "href": "/ClassEnrollment/1"},
        {
            "text": "WorkshopPLUS - Azure AI Platform and Services\n18 Mar 2026\nLaunch",
            "href": "/ClassEnrollment/1",
        },
    ]
    (e,) = parse_enrolments(links)
    assert e.title == "WorkshopPLUS - Azure AI Platform and Services"
    assert slugify(e.title) == "azure-ai-platform-and-services"
    tomllib.loads(scaffold(e))  # the original regression: it must still parse


def test_leading_blank_lines_do_not_blank_the_title():
    links = [{"text": "\n\n  WorkshopPLUS - Demo  \nLaunch", "href": "/ClassEnrollment/1"}]
    assert parse_enrolments(links)[0].title == "WorkshopPLUS - Demo"


@pytest.mark.parametrize("ch", ["\n", "\r", "\t", "\x00", "\x1b", "\x7f", "\\", '"'])
def test_scaffold_survives_control_characters_in_a_title(ch):
    e = Enrolment(enrolment=1, title=f"Demo{ch}Workshop", href="/x")
    assert tomllib.loads(scaffold(e))["name"] == f"Demo{ch}Workshop"


def test_write_scaffold_matches_a_curated_descriptor_by_identity(tmp_path):
    """A curated slug is hand-shortened, so a name-based guard misses it and
    writes a second, blank descriptor for a lab that is already onboarded."""
    (tmp_path / "azure-ai-platform.toml").write_text(
        'slug = "azure-ai-platform"\nname = "Curated"\n\n[lab]\nid = 79233\nenrollment = 5928204\n',
        encoding="utf-8",
    )
    e = Enrolment(
        enrolment=5928204,
        title="WorkshopPLUS - Azure AI Platform and Services",
        href="/x",
        lab_id=79233,
    )
    assert slugify(e.title) != "azure-ai-platform"  # the derived slug differs
    assert descriptor_for(e, tmp_path) == "azure-ai-platform"
    with pytest.raises(FileExistsError, match="already describes enrolment"):
        write_scaffold(e, tmp_path)
    assert not (tmp_path / "azure-ai-platform-and-services.toml").exists()


def test_descriptor_for_ignores_an_unrelated_or_broken_descriptor(tmp_path):
    (tmp_path / "other.toml").write_text(
        'slug = "other"\nname = "Other"\n\n[lab]\nid = 1\nenrollment = 2\n', encoding="utf-8"
    )
    (tmp_path / "broken.toml").write_text("not = = toml", encoding="utf-8")
    e = Enrolment(enrolment=999, title="Demo", href="/x")
    assert descriptor_for(e, tmp_path) is None


# --- resolve: URL + name -> one lab --------------------------------------
#
# The contract is `walk --url ... --name ...`, so this is the very first thing
# that happens in a run. Getting it wrong walks the wrong lab and reports every
# finding against the wrong content, plausibly.

CATALOGUE = [
    {"text": "WorkshopPLUS - Azure AI Platform and Services",
     "href": "/ClassEnrollment/5928204"},
    {"text": "Launch", "href": "/ClassEnrollment/5928204"},
    {"text": "WorkshopPLUS - Azure Kubernetes Service", "href": "/ClassEnrollment/6100001"},
]


def test_a_url_that_names_an_enrolment_wins_over_the_name():
    """The learner already disambiguated by pasting that URL."""
    r = resolve(CATALOGUE, "https://mslearningcampus.com/ClassEnrollment/6100001", "Azure AI")
    assert r.ok
    assert r.enrolment.enrolment == 6100001


def test_a_catalogue_url_falls_back_to_the_name():
    r = resolve(CATALOGUE, "https://mslearningcampus.com/Pages/ms-learningcampus",
                "WorkshopPLUS - Azure AI Platform and Services")
    assert r.ok
    assert r.enrolment.enrolment == 5928204
    assert r.reason == "exact title match"


def test_a_partial_name_resolves_when_it_is_unique():
    r = resolve(CATALOGUE, "https://mslearningcampus.com/", "kubernetes")
    assert r.ok
    assert r.enrolment.enrolment == 6100001


def test_an_ambiguous_name_names_the_candidates_and_stops():
    """Never guess. Two editions enrolled at once is the normal case, and the
    closest match would be walked with total confidence."""
    links = [
        {"text": "WorkshopPLUS - Azure AI Platform (20250101)", "href": "/ClassEnrollment/1"},
        {"text": "WorkshopPLUS - Azure AI Platform (20260301)", "href": "/ClassEnrollment/2"},
    ]
    r = resolve(links, "https://mslearningcampus.com/", "Azure AI Platform")
    assert not r.ok
    assert len(r.candidates) == 2
    assert "2 enrolments match" in r.reason


def test_a_name_that_matches_nothing_says_so():
    r = resolve(CATALOGUE, "https://mslearningcampus.com/", "Power Platform Fundamentals")
    assert not r.ok
    assert r.candidates, "the reachable enrolments are still worth printing"
    assert "no enrolment matches" in r.reason


def test_a_signed_out_page_is_distinguishable_from_a_bad_name():
    """Both fail, but only one is fixed by signing in, so they must not read
    the same."""
    r = resolve([], "https://mslearningcampus.com/", "anything")
    assert not r.ok
    assert "no launchable enrolment" in r.reason


def test_an_enrolment_id_absent_from_the_page_is_not_silently_replaced():
    r = resolve(CATALOGUE, "https://mslearningcampus.com/ClassEnrollment/999", "Azure AI")
    assert not r.ok
    assert "not on this page" in r.reason


# --- an enrolment's own page ----------------------------------------------
#
# `/ClassEnrollment/<id>` is what `Enrolment.url` hands out and what a human
# copies from the address bar -- and that page does not link to *itself*, so
# `parse_enrolments` finds nothing on it. Three live runs died here: the tool
# refused the very URL its own output recommends. The URL-trusting branch has
# to run before the empty-page refusal, or trusting the URL is not real.

#: The enrolment's own page, as observed live: no /ClassEnrollment/ anchors at
#: all, and one link to the lab it launches.
OWN_PAGE = [
    {"text": "Home", "href": "/"},
    {"text": "Azure AI: Platform and Services",
     "href": "/Lab/79233?instructionSetLang=en&classId=763682"},
]


def test_an_enrolments_own_page_resolves_to_that_enrolment():
    r = resolve(OWN_PAGE, "https://mslearningcampus.com/ClassEnrollment/5928204",
                "WorkshopPLUS - Azure AI Platform and Services")
    assert r.ok, r.reason
    assert r.enrolment.enrolment == 5928204
    assert r.enrolment.lab_id == 79233
    assert r.enrolment.class_id == 763682
    assert "its own page" in r.reason


def test_the_lab_link_names_the_lab_rather_than_the_name_we_were_given():
    """--name only had to disambiguate, and the URL already did that. What the
    page calls the lab is the observation; --name is the caller's label."""
    r = resolve(OWN_PAGE, "https://mslearningcampus.com/ClassEnrollment/5928204",
                "whatever the human typed")
    assert r.enrolment.title == "Azure AI: Platform and Services"


def test_a_signed_out_enrolment_page_refuses_rather_than_inventing_one():
    """Signed out, the page still has the enrolment id in the URL but offers no
    lab. Returning an enrolment nobody can launch would fail later and further
    away, where the cause is no longer visible."""
    r = resolve([{"text": "Sign in", "href": "/User/Login"}],
                "https://mslearningcampus.com/ClassEnrollment/5928204", "Azure AI")
    assert not r.ok
    assert "no lab to launch" in r.reason
    assert "signed out" in r.reason


def test_a_url_shaped_like_an_enrolment_but_with_no_lab_link_refuses():
    """The id in the URL is not on its own evidence that this is that
    enrolment's page."""
    r = resolve([{"text": "Some article", "href": "/Blog/1"}],
                "https://mslearningcampus.com/ClassEnrollment/5928204", "Azure AI")
    assert not r.ok


def test_an_enrolment_listed_on_the_page_still_wins_over_the_own_page_path():
    """Both branches can match; the parsed enrolment carries more than a lab
    link does, so the order between them must not drift."""
    links = CATALOGUE + [{"text": "Azure AI", "href": "/Lab/79233?classId=763682"}]
    r = resolve(links, "https://mslearningcampus.com/ClassEnrollment/5928204", "Azure AI")
    assert r.ok
    assert r.reason == "the URL names enrolment 5928204"


# --- Target.from_url: the descriptor stops being a precondition -----------


def test_from_url_synthesises_a_target_with_no_descriptor(tmp_path):
    """A brand-new lab must be walkable the moment someone pastes a URL. The
    walk is what produces the expectations a descriptor would carry."""
    t = Target.from_url("https://mslearningcampus.com/ClassEnrollment/5928204",
                        "WorkshopPLUS - Azure AI Platform and Services", root=tmp_path)
    assert not t.is_enriched
    assert t.slug == "azure-ai-platform-and-services"
    assert t.lab["enrollment"] == 5928204
    assert t.enrollment_url == "https://mslearningcampus.com/ClassEnrollment/5928204"


def test_from_url_reuses_a_curated_descriptor_matched_on_identity(tmp_path):
    """Curated slugs are hand-shortened, so matching by name would miss the
    descriptor it should have found and silently downgrade the run."""
    (tmp_path / "azure-ai-platform.toml").write_text(
        'slug = "azure-ai-platform"\nname = "Azure AI Platform"\n\n'
        "[lab]\nid = 79233\nenrollment = 5928204\n\n"
        '[expect]\nregion = "East US 2"\n',
        encoding="utf-8",
    )
    t = Target.from_url("https://mslearningcampus.com/ClassEnrollment/5928204",
                        "WorkshopPLUS - Azure AI Platform and Services", root=tmp_path)
    assert t.is_enriched
    assert t.slug == "azure-ai-platform"
    assert t.expect["region"] == "East US 2"


def test_an_unenriched_target_reports_what_it_cannot_check(tmp_path):
    """Missing enrichment weakens a run; it must not silently weaken it."""
    t = Target.from_url("https://mslearningcampus.com/ClassEnrollment/1", "New Lab",
                        root=tmp_path)
    gaps = t.enrichment_gaps()
    assert any("region" in g for g in gaps)
    assert any("models" in g for g in gaps)


def test_from_url_ignores_a_broken_descriptor(tmp_path):
    (tmp_path / "broken.toml").write_text("not = = toml", encoding="utf-8")
    t = Target.from_url("https://mslearningcampus.com/ClassEnrollment/1", "New Lab",
                        root=tmp_path)
    assert not t.is_enriched
