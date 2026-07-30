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
