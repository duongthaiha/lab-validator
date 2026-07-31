"""Tests for the setup preflight.

Two things are being guarded here, and the second matters more.

The first is the checks: does an operation URL get caught where a base URL is
required, does an unreplaced placeholder get caught, do disagreeing config paths
get caught. These are the G-70 / G-71 class, reproduced from the real defects.

The second is the *coverage discipline*. The stated risk is that a clean
preflight gets read as "the setup is correct" when the truthful claim is much
narrower. So there are tests asserting that omitting an input is **recorded**
rather than silently skipped, and that the report cannot render without saying
what it did not check. Those tests exist because the failure mode is social, not
technical: nobody misreads a crash, everybody misreads a silent pass.
"""

from __future__ import annotations

import pytest

from lab_validator import taxonomy
from lab_validator.preflight import (
    Check,
    Preflight,
    check_config_paths,
    check_endpoints,
    check_shipped_config,
    differs_in,
    endpoint_kind,
    parse_config,
    preflight,
    shape_of,
)

# --- endpoint_kind: the distinction nobody looks for -----------------------


@pytest.mark.parametrize("url", [
    "https://ai-foundry-000000.openai.azure.com/",
    "https://ai-foundry-000000.openai.azure.com",
    "https://example.cognitiveservices.azure.com/openai",
    "https://example.services.ai.azure.com/api",
])
def test_base_urls_are_recognised(url):
    assert endpoint_kind(url) == "base"


@pytest.mark.parametrize("url", [
    # The exact shape that broke five labs: valid, resolvable, and wrong.
    "https://ai-foundry-000000.openai.azure.com/openai/deployments/gpt-4o/chat/completions",
    "https://example.openai.azure.com/openai/deployments/embed/embeddings",
    "https://example.search.windows.net/indexes/idx/docs",
])
def test_operation_urls_are_caught(url):
    assert endpoint_kind(url) == "operation"


@pytest.mark.parametrize("url", ["", "not a url", "ai-foundry.openai.azure.com", "ftp://x/y"])
def test_non_urls_are_caught(url):
    assert endpoint_kind(url) == "not-a-url"


def test_an_operation_url_is_a_critical_setup_defect():
    """It has to be critical: the failure surfaces far away from the cause."""
    op = "https://x.openai.azure.com/openai/deployments/d/chat/completions"
    (check,) = check_endpoints({"Azure/Endpoint": op})
    assert not check.ok
    assert check.verdict in taxonomy.FINDING_VERDICTS
    assert check.domain == "setup"
    assert check.severity == "critical"
    # Shape-preserving: the path is the whole argument, the host is not.
    assert check.evidence == "https://<host>/openai/deployments/d/chat/completions"


def test_a_base_endpoint_passes_and_carries_its_evidence():
    (check,) = check_endpoints({"Azure/Endpoint": "https://x.openai.azure.com/"})
    assert check.ok
    assert check.evidence == "https://<host>/"


def test_evidence_survives_the_redactor_that_masks_the_value_it_came_from():
    """The bug this whole convention exists for.

    Every captured credential is registered with the redactor, so evidence that
    quoted the value verbatim published as ``[REDACTED:Endpoint]`` -- a finding
    nobody could verify or act on. Masking must cost the secret, not the
    argument.
    """
    from lab_validator.runlog import Redactor

    op = "https://ai-foundry-000000.openai.azure.com/openai/deployments/d/chat/completions"
    redactor = Redactor()
    redactor.add(op, "Endpoint")

    (check,) = check_endpoints({"Azure/Endpoint": op})
    published = redactor.scrub(check.evidence)

    assert "REDACTED" not in published, "the evidence was eaten by the redactor"
    assert "/openai/deployments/d/chat/completions" in published
    assert "ai-foundry-000000" not in published, "and it must not leak the host either"


# --- parse_config: tolerant on purpose -------------------------------------


def test_parse_config_handles_the_shapes_a_lab_actually_ships():
    parsed = parse_config(
        "# comment\n"
        "AZURE_OPENAI_ENDPOINT=https://x.openai.azure.com/\n"
        'AZURE_OPENAI_KEY="quoted"\n'
        "export AZURE_TENANT_ID='exported'\n"
        "  SPACED  =  value  \n"
        "\n"
        "not-a-pair\n"
    )
    assert parsed == {
        "AZURE_OPENAI_ENDPOINT": "https://x.openai.azure.com/",
        "AZURE_OPENAI_KEY": "quoted",
        "AZURE_TENANT_ID": "exported",
        "SPACED": "value",
    }


def test_parse_config_does_not_stop_at_the_first_oddity():
    """A parser that raised would report one defect and hide the rest."""
    parsed = parse_config("BROKEN LINE\nGOOD=value\n=novalue\n")
    assert parsed["GOOD"] == "value"


# --- check_shipped_config: the G-71 class ----------------------------------


def test_shipped_operation_url_is_caught_in_the_config_file():
    checks = check_shipped_config({
        "AZURE_OPENAI_ENDPOINT":
            "https://x.openai.azure.com/openai/deployments/gpt-4o/chat/completions",
    })
    (bad,) = [c for c in checks if not c.ok]
    assert "base URL is required" in bad.detail
    assert bad.severity == "critical"


@pytest.mark.parametrize("value", ["", "<your-endpoint>", "CHANGEME", "your-key", "TODO"])
def test_placeholders_are_caught_whatever_their_case(value):
    checks = check_shipped_config({"AZURE_OPENAI_KEY": value})
    (bad,) = [c for c in checks if not c.ok]
    assert "placeholder" in bad.detail


def test_a_real_key_containing_a_placeholder_word_is_not_flagged():
    """Placeholders match the whole value. A real secret may contain 'xxx'."""
    checks = check_shipped_config({"AZURE_OPENAI_KEY": "abcxxxdef1234567890"})
    assert all(c.ok for c in checks)


def test_a_non_guid_subscription_is_caught():
    checks = check_shipped_config({"AZURE_SUBSCRIPTION_ID": "my-subscription"})
    (bad,) = [c for c in checks if not c.ok]
    assert "not a GUID" in bad.detail


def test_a_guid_subscription_passes():
    checks = check_shipped_config(
        {"AZURE_SUBSCRIPTION_ID": "00000000-1111-2222-3333-444444444444"}
    )
    assert all(c.ok for c in checks)


def test_config_contradicting_the_resources_tab_is_caught():
    """The only way to catch a config left pointing at a previous edition."""
    checks = check_shipped_config(
        {"AZURE_OPENAI_ENDPOINT": "https://old-lab.openai.azure.com/"},
        {"AZURE_OPENAI_ENDPOINT": "https://this-lab.openai.azure.com/"},
    )
    (bad,) = [c for c in checks if not c.ok]
    assert "handed the learner" in bad.detail
    # Shape alone would render both sides identically, so the evidence names the
    # component that disagrees instead -- actionable, and it leaks neither host.
    assert bad.evidence == "AZURE_OPENAI_ENDPOINT: differ in host"


def test_matching_config_and_issued_values_produce_no_finding():
    same = "https://x.openai.azure.com/"
    checks = check_shipped_config({"AZURE_OPENAI_ENDPOINT": same},
                                  {"AZURE_OPENAI_ENDPOINT": same})
    assert all(c.ok for c in checks)


def test_issued_keys_absent_from_the_config_are_not_invented():
    """Never manufacture an expectation the artefact did not make."""
    checks = check_shipped_config({}, {"AZURE_OPENAI_ENDPOINT": "https://x/"})
    assert checks == []


# --- check_config_paths: the G-70 class ------------------------------------


def test_disagreeing_load_paths_are_a_finding_on_their_own():
    """Three files loading from three paths cannot all be right."""
    checks = check_config_paths(
        {"a.ipynb": "../.env", "b.ipynb": "../../.env", "c.ipynb": ".env"},
        config_at="../.env",
    )
    (disagreement,) = [c for c in checks if c.name == "shipped config path"]
    assert not disagreement.ok
    assert "3 different" in disagreement.detail
    assert disagreement.severity == "critical"


def test_each_wrong_loader_is_named_individually():
    checks = check_config_paths({"a.ipynb": "../.env", "b.ipynb": "wrong/.env"},
                                config_at="../.env")
    failed = {c.name for c in checks if not c.ok}
    assert "config path in b.ipynb" in failed
    assert "config path in a.ipynb" not in failed


def test_agreeing_correct_paths_pass():
    checks = check_config_paths({"a.ipynb": "../.env", "b.ipynb": r"..\.env"},
                                config_at="../.env")
    assert all(c.ok for c in checks)


# --- the coverage discipline ------------------------------------------------


def test_omitting_an_input_is_recorded_not_ignored():
    """A preflight with no config has established *nothing* about the config."""
    result = preflight()
    assert result.ok, "no evidence means no findings"
    assert not result.checks
    blob = " ".join(result.unchecked)
    assert "endpoints" in blob
    assert "shipped config" in blob
    assert "config load paths" in blob


def test_the_hardest_check_is_always_declared_unchecked():
    """Shape-checking never establishes what a deployment actually serves."""
    result = preflight(endpoints={"a": "https://x.openai.azure.com/"},
                       config={"K": "v"}, issued={"K": "v"},
                       loaders={"n.ipynb": ".env"}, config_at=".env")
    assert result.ok
    assert any("identity of deployed models" in u for u in result.unchecked)


def test_config_without_issued_values_records_the_weaker_comparison():
    result = preflight(config={"AZURE_OPENAI_KEY": "abc123"})
    assert any("vs issued values" in u for u in result.unchecked)


def test_config_with_issued_values_does_not_record_it():
    result = preflight(config={"K": "v"}, issued={"K": "v"})
    assert not any("vs issued values" in u for u in result.unchecked)


def test_the_report_always_states_what_it_did_not_check():
    """The section that stops a clean preflight reading as 'setup is correct'."""
    md = preflight().to_markdown()
    assert "did *not* check" in md
    assert "the things we knew to check" in md


def test_an_empty_unchecked_list_is_called_out_rather_than_omitted():
    md = Preflight(checks=[Check("x", True, "fine")]).to_markdown()
    assert "did *not* check" in md
    assert "itself suspicious" in md


def test_failures_are_reported_before_passes_and_carry_evidence():
    md = preflight(endpoints={
        "Azure/Endpoint": "https://x.openai.azure.com/openai/deployments/d/chat/completions",
        "Azure/Other": "https://y.openai.azure.com/",
    }).to_markdown()
    assert md.index("**endpoint Azure/Endpoint**") < md.index("Checks that passed")
    assert "evidence:" in md


def test_passes_are_collapsed_but_present():
    """Recorded, because a check that ran is evidence; collapsed, because noise."""
    md = preflight(endpoints={"a": "https://x.openai.azure.com/"}).to_markdown()
    assert "<details>" in md
    assert "1 check(s) ran, clean" in md


# --- taxonomy conformance ---------------------------------------------------


def test_every_preflight_finding_uses_real_taxonomy_values():
    """The preflight must not mint private codes; 8A gave them one home."""
    result = preflight(
        endpoints={"bad": "https://x/openai/deployments/d/chat/completions"},
        config={"AZURE_SUBSCRIPTION_ID": "nope", "AZURE_OPENAI_KEY": "<your-key>"},
        loaders={"a.ipynb": "x/.env", "b.ipynb": "y/.env"},
        config_at="z/.env",
    )
    assert result.failures, "this fixture must produce findings or the test is vacuous"
    for check in result.failures:
        assert check.verdict in taxonomy.FINDING_VERDICTS, check.name
        assert check.domain in taxonomy.DOMAINS, check.name
        assert check.severity in taxonomy.SEVERITIES, check.name


def test_a_failing_preflight_does_not_raise():
    """Principle: it sets the verdict, it does not stop the run."""
    result = preflight(endpoints={"bad": "https://x/openai/deployments/d/chat/completions"})
    assert not result.ok
    assert result.to_markdown()


# --- evidence that survives masking ----------------------------------------


@pytest.mark.parametrize("value,expected", [
    ("https://x.openai.azure.com/openai/deployments/d/chat/completions",
     "https://<host>/openai/deployments/d/chat/completions"),
    ("https://x.openai.azure.com/", "https://<host>/"),
    ("https://x.openai.azure.com", "https://<host>/"),
])
def test_shape_of_keeps_the_path_and_drops_the_host(value, expected):
    assert shape_of(value) == expected


def test_shape_of_a_secret_reveals_nothing_but_still_says_something():
    shape = shape_of("Sup3rSecret!value")
    assert "Sup3rSecret" not in shape
    assert "17 chars" in shape and "digits" in shape and "punctuation" in shape


def test_shape_of_an_empty_value_is_not_silent():
    assert shape_of("") == "<empty>"


@pytest.mark.parametrize("shipped,issued,expected", [
    ("https://a.openai.azure.com/", "https://b.openai.azure.com/", "differ in host"),
    ("https://a.openai.azure.com/x", "https://a.openai.azure.com/y", "differ in path"),
    ("http://a.example.com/", "https://a.example.com/", "differ in scheme"),
    ("https://a.example.com/?v=1", "https://a.example.com/?v=2", "differ in query"),
    ("not-a-url", "other", "values differ"),
])
def test_differs_in_names_the_component_without_printing_it(shipped, issued, expected):
    result = differs_in(shipped, issued)
    assert result == expected
    for secret in (shipped, issued):
        host = secret.split("//")[-1].split("/")[0]
        assert host not in result or host in ("",)


def test_differs_in_reports_every_differing_component():
    assert differs_in("http://a.example.com/x", "https://b.example.com/y") == \
        "differ in host, path, scheme"