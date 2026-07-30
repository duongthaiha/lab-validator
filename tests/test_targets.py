"""Tests for the per-lab target descriptor loader.

These matter more than their size suggests. The descriptor is the whole
generalisation story -- onboarding a new workshop is meant to be "write a TOML
file" -- so the loader's error messages are the product surface for that task.
A silently-ignored typo is the failure mode this file exists to prevent.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lab_validator.targets import Target, TargetError  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]

MINIMAL = """
slug = "demo"
name = "Demo Workshop"

[lab]
id = 12345
enrollment = 999
"""


def write(tmp_path: Path, slug: str, body: str) -> Path:
    path = tmp_path / f"{slug}.toml"
    path.write_text(body, encoding="utf-8")
    return path


def test_loads_minimal_descriptor(tmp_path):
    write(tmp_path, "demo", MINIMAL)
    target = Target.load("demo", root=tmp_path)
    assert target.lab_id == 12345
    assert target.name == "Demo Workshop"
    assert target.problems == []


def test_enrollment_url_is_derived_when_absent(tmp_path):
    write(tmp_path, "demo", MINIMAL)
    target = Target.load("demo", root=tmp_path)
    assert target.enrollment_url == "https://mslearningcampus.com/ClassEnrollment/999"


def test_explicit_enrollment_url_wins(tmp_path):
    write(tmp_path, "demo", MINIMAL + '\nenrollment_url = "https://example.test/x"\n')
    assert Target.load("demo", root=tmp_path).enrollment_url == "https://example.test/x"


def test_missing_file_lists_what_is_available(tmp_path):
    write(tmp_path, "demo", MINIMAL)
    with pytest.raises(TargetError) as exc:
        Target.load("nope", root=tmp_path)
    assert "demo" in str(exc.value)


def test_slug_must_match_filename(tmp_path):
    """The trap when a descriptor is created by copying another one."""
    write(tmp_path, "renamed", MINIMAL)
    with pytest.raises(TargetError, match="must match"):
        Target.load("renamed", root=tmp_path)


def test_missing_lab_id_is_an_error(tmp_path):
    write(tmp_path, "demo", 'slug = "demo"\nname = "D"\n\n[lab]\nclass_id = 1\n')
    with pytest.raises(TargetError, match="lab.id"):
        Target.load("demo", root=tmp_path)


def test_unknown_key_warns_but_still_loads(tmp_path):
    """Forward compatibility: a stray key must not block a run."""
    write(tmp_path, "demo", MINIMAL + '\n[expect]\nregoin = "East US 2"\n')
    target = Target.load("demo", root=tmp_path)
    warnings = [p for p in target.problems if p.level == "warning"]
    assert any(p.where == "expect.regoin" for p in warnings)
    assert "region" in str(warnings[0])  # the message suggests the real key


def test_strict_mode_promotes_warnings_to_failure(tmp_path):
    write(tmp_path, "demo", MINIMAL + '\n[expect]\nregoin = "East US 2"\n')
    with pytest.raises(TargetError, match="regoin"):
        Target.load("demo", root=tmp_path, strict=True)


def test_deferral_without_justification_is_an_error(tmp_path):
    write(tmp_path, "demo", MINIMAL + '\n[deferrals]\nlab09_redteam = ""\n')
    with pytest.raises(TargetError, match="justification"):
        Target.load("demo", root=tmp_path)


def test_deferrals_as_a_scalar_is_reported_not_crashed(tmp_path):
    """A plausible onboarding mistake must produce a complaint, not a traceback."""
    write(tmp_path, "demo", 'slug = "demo"\nname = "D"\ndeferrals = "none yet"\n\n[lab]\nid = 1\n')
    with pytest.raises(TargetError, match="must be a table"):
        Target.load("demo", root=tmp_path)


def test_unknown_top_level_scalar_is_reported(tmp_path):
    """The classic slip: a [lab] key written outside the table. It would read as
    None at the point of use, which is the silent failure this loader prevents."""
    body = MINIMAL.replace("[lab]", 'enrollment_url = "https://example.test/x"\n\n[lab]')
    write(tmp_path, "demo", body)
    target = Target.load("demo", root=tmp_path)
    assert any(p.where == "enrollment_url" for p in target.problems)
    # and it genuinely did not take effect
    assert target.enrollment_url == "https://mslearningcampus.com/ClassEnrollment/999"


def test_unknown_top_level_scalar_fails_strict(tmp_path):
    body = MINIMAL.replace("[lab]", 'modles = ["gpt-4o"]\n\n[lab]')
    write(tmp_path, "demo", body)
    with pytest.raises(TargetError, match="modles"):
        Target.load("demo", root=tmp_path, strict=True)


# --- value types ---------------------------------------------------------


def test_a_string_where_a_list_belongs_is_an_error(tmp_path):
    """The likeliest slip here. list() would silently make six model names out
    of one, which is precisely the invented expectation this module prevents."""
    write(tmp_path, "demo", MINIMAL + '\n[expect]\nmodels = "gpt-4o"\n')
    with pytest.raises(TargetError, match="expect.models: must be a array"):
        Target.load("demo", root=tmp_path)
    target = Target.inspect("demo", root=tmp_path)
    assert target.models == ["g", "p", "t", "-", "4", "o"]  # why it must be caught


def test_a_list_where_a_string_belongs_is_an_error(tmp_path):
    write(tmp_path, "demo", MINIMAL + '\n[expect]\nregion = ["East US 2"]\n')
    with pytest.raises(TargetError, match="expect.region: must be a string"):
        Target.load("demo", root=tmp_path)


def test_a_string_where_an_integer_belongs_is_an_error(tmp_path):
    write(tmp_path, "demo", 'slug = "demo"\nname = "D"\n\n[lab]\nid = "79233"\n')
    with pytest.raises(TargetError, match="lab.id: must be a integer"):
        Target.load("demo", root=tmp_path)


def test_a_boolean_is_not_accepted_as_an_integer(tmp_path):
    """bool subclasses int, so a plain isinstance check would let this through."""
    write(tmp_path, "demo", MINIMAL + "\n[environment]\ncredential_hours = true\n")
    with pytest.raises(TargetError, match="environment.credential_hours"):
        Target.load("demo", root=tmp_path)


def test_correct_types_raise_nothing(tmp_path):
    write(
        tmp_path,
        "demo",
        MINIMAL
        + '\nedition = "x (20260318)"\nduration_hours = 96\n'
        + '\n[environment]\nkind = ["virtualization"]\ncredential_hours = 8\n'
        + '\n[expect]\nregion = "East US 2"\nmodels = ["gpt-4o"]\n',
    )
    target = Target.load("demo", root=tmp_path, strict=True)
    assert target.models == ["gpt-4o"]


def test_risks_as_a_scalar_is_reported(tmp_path):
    body = MINIMAL.replace("[lab]", 'risks = "none yet"\n\n[lab]')
    write(tmp_path, "demo", body)
    with pytest.raises(TargetError, match="risks: must be a table"):
        Target.load("demo", root=tmp_path)


# --- file encoding -------------------------------------------------------


def test_a_utf8_bom_loads_rather_than_faking_a_syntax_error(tmp_path):
    """Notepad and PowerShell 5.1 write a BOM by default. Under plain utf-8 it
    surfaces as 'Invalid statement at line 1' -- a syntax error that isn't there."""
    (tmp_path / "demo.toml").write_text(MINIMAL, encoding="utf-8-sig")
    assert Target.load("demo", root=tmp_path).lab_id == 12345


def test_a_non_utf8_file_names_the_real_cause(tmp_path):
    """PowerShell 5.1 '>' redirection writes UTF-16; the UnicodeDecodeError used
    to escape TargetError entirely and surface as a traceback naming no file."""
    (tmp_path / "demo.toml").write_text(MINIMAL, encoding="utf-16")
    with pytest.raises(TargetError, match="not UTF-8"):
        Target.load("demo", root=tmp_path)
    with pytest.raises(TargetError, match="not UTF-8"):
        Target.inspect("demo", root=tmp_path)


def test_deferral_with_justification_loads(tmp_path):
    body = MINIMAL + '\n[deferrals]\nlab09 = "Scan needs 45 min; instance expires first."\n'
    write(tmp_path, "demo", body)
    target = Target.load("demo", root=tmp_path)
    assert "lab09" in target.deferrals


def test_invalid_toml_names_the_file(tmp_path):
    write(tmp_path, "demo", "slug = = broken")
    with pytest.raises(TargetError, match="not valid TOML"):
        Target.load("demo", root=tmp_path)


def test_shipped_descriptor_is_valid():
    """The real descriptor must pass its own validator, strictly."""
    target = Target.load("azure-ai-platform", root=REPO_ROOT / "targets", strict=True)
    assert target.lab_id == 79233
    assert "gpt-4o" in target.models
