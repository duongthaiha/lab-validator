"""An end-to-end exercise of ``walk`` with the browser replaced by fakes.

``_walk`` is the whole contract in one function: URL in, run folder out. It is
also the piece with the worst feedback loop -- every real rehearsal costs a
human sign-in and burns lab clock, so a wiring bug (a property awaited, an
attribute renamed, a coroutine never scheduled) would surface with somebody
sitting watching it. That is precisely the code that deserves fakes.

Only the browser-touching seams are stubbed. ``resolve``, ``Target.from_url``,
``Run.create`` and ``Vault.capture`` run for real, because the wiring *between*
them is what these tests exist to catch.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lab_validator import browser as browser_mod  # noqa: E402
from lab_validator import cli, corpus, launch, taxonomy  # noqa: E402
from lab_validator.labclient import Credential  # noqa: E402

ENROLMENT = 5928204
TITLE = "WorkshopPLUS \u2013 Azure AI Platform and Services"
ENTRY = "https://mslearningcampus.com/Pages/ms-learningcampus"

LINKS = [
    {"href": f"/ClassEnrollment/{ENROLMENT}", "text": TITLE},
    {"href": "/ClassEnrollment/9111111", "text": "WorkshopPLUS - Azure Kubernetes Service"},
]


class FakePage:
    def __init__(self, url=ENTRY):
        self.url = url
        self.visited = []

    async def bring_to_front(self):
        pass

    async def goto(self, url, **_):
        self.visited.append(url)
        self.url = url

    async def wait_for_timeout(self, _ms):
        pass

    async def evaluate(self, _js):
        return LINKS

    def get_by_role(self, *_a, **_k):
        return self

    def or_(self, _other):
        return self

    async def count(self):
        return 0  # no Sign In control => already signed in


class FakeBrowser:
    def __init__(self):
        self.closed = False

    async def close(self):
        self.closed = True


class FakeContext:
    def __init__(self, page):
        self.pages = [page]


class FakeLab:
    instance_id = "0e6f7c2a-fake"
    instructions = object()

    def __init__(self, creds=None, minutes=5721):
        self._creds = creds or [
            Credential(scope="Azure", label="Username", value="user@labtenant.example"),
            Credential(scope="Azure", label="Password", value="Sup3rSecret!value"),
            Credential(scope="Azure", label="Subscription ID",
                       value="8d1f4a2e-0b73-4c19-9f6a-2ab5cd7e1234"),
        ]
        self._minutes = minutes
        self.shown = False

    async def minutes_remaining(self):
        return self._minutes

    async def credentials(self):
        return list(self._creds)

    async def show_instructions(self):
        self.shown = True


class FakeOutline:
    """Real ``Segment`` objects on purpose. Faking them as dicts would let a
    change to the segment contract pass this suite and fail on a live lab."""

    def segments(self):
        from lab_validator.corpus import Heading, Outline

        headings = [
            Heading(order=0, level=1, id="getting-started", text="Getting started"),
            Heading(order=1, level=2, id="sign-in", text="Sign in"),
            Heading(order=2, level=1, id="deploy-a-model", text="Deploy a model"),
            Heading(order=3, level=2, id="pick-a-model", text="Pick a model"),
        ]
        return Outline(title=TITLE, headings=headings).segments()

    def anomalies(self):
        return []

    def save(self, path):
        Path(path).write_text(json.dumps({"segments": 2}), encoding="utf-8")

    def to_markdown(self):
        return "# Getting started\n\nDeploy a model.\n"


class FakePlaywright:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return False


@pytest.fixture
def wired(monkeypatch, tmp_path):
    """Replace only what touches a browser; leave the wiring under test."""
    page = FakePage()
    browser = FakeBrowser()
    context = FakeContext(page)
    lab = FakeLab()
    state = {"page": page, "browser": browser, "context": context, "lab": lab,
             "launch_calls": 0}

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    monkeypatch.setattr(cli, "SCRIPTS", ROOT / "scripts")

    import playwright.async_api as pwapi
    monkeypatch.setattr(pwapi, "async_playwright", lambda: FakePlaywright())

    async def fake_attach(_pw, _port):
        return browser, context

    async def fake_click_launch(_page, **_k):
        state["launch_calls"] += 1
        return launch.LaunchOutcome(True, False, "clicked")

    async def fake_await_client(_ctx, **_k):
        return lab

    async def fake_extract(_frame):
        return FakeOutline()

    monkeypatch.setattr(browser_mod, "attached_context", fake_attach)
    monkeypatch.setattr(launch, "click_launch", fake_click_launch)
    monkeypatch.setattr(launch, "await_lab_client", fake_await_client)
    monkeypatch.setattr(corpus, "extract", fake_extract)
    return state


def walk_args(**over):
    ns = type("N", (), {})()
    ns.url = ENTRY
    ns.name = TITLE
    ns.agent = "test"
    ns.signin_budget = 5.0
    ns.launch_budget = 5.0
    ns.client_budget = 5.0
    ns.port = 9333
    for k, v in over.items():
        setattr(ns, k, v)
    return ns


def latest_run(tmp_path: Path) -> Path:
    runs = sorted((tmp_path / "runs").iterdir())
    assert runs, "walk produced no run folder"
    return runs[-1]


def test_a_url_and_a_name_produce_a_started_run(wired, tmp_path, capsys):
    assert cli.cmd_walk(walk_args()) == 0
    run = latest_run(tmp_path)
    manifest = json.loads((run / "run.json").read_text(encoding="utf-8"))
    assert manifest["instance"] == "0e6f7c2a-fake"
    assert manifest["entryUrl"] == ENTRY
    assert len(manifest["segments"]) == 2


def test_the_walk_navigates_to_the_resolved_enrolment_not_the_entry_url(wired):
    """The URL a human pastes is usually a catalogue page. Launching from it
    would launch nothing."""
    cli.cmd_walk(walk_args())
    assert f"/ClassEnrollment/{ENROLMENT}" in wired["page"].visited[-1]


def test_the_browser_is_released_even_though_the_session_must_survive(wired):
    """close() detaches the CDP client; it does not kill the human's browser --
    which must keep its memory-only TMS cookie."""
    cli.cmd_walk(walk_args())
    assert wired["browser"].closed


def test_credentials_are_captured_once_and_kept_as_data(wired, tmp_path):
    cli.cmd_walk(walk_args())
    from lab_validator.vault import Vault

    vault = Vault.load(latest_run(tmp_path))
    assert vault is not None
    assert vault.subscription_id() == "8d1f4a2e-0b73-4c19-9f6a-2ab5cd7e1234"
    assert vault.value("Username") == "user@labtenant.example"


def test_capturing_credentials_returns_the_learner_to_the_instructions(wired):
    """The Resources tab is a tab. Leaving the lab parked on it means every
    later screenshot is of the wrong pane."""
    cli.cmd_walk(walk_args())
    assert wired["lab"].shown


def test_every_captured_value_is_registered_for_redaction(wired, monkeypatch):
    """Capture and registration have to be the same action. If a value can be
    captured without being registered, the trace leaks the moment somebody adds
    a code path that forgets."""
    from lab_validator.vault import Vault

    seen = {}
    real = Vault.capture

    def spy(creds, redactor):
        vault = real(creds, redactor)
        seen["registered"] = len(redactor)
        seen["captured"] = len(vault)
        return vault

    monkeypatch.setattr(Vault, "capture", staticmethod(spy))
    cli.cmd_walk(walk_args())
    assert seen["captured"] == 3
    assert seen["registered"] >= 3


def test_a_run_with_no_descriptor_says_so_rather_than_implying_coverage(wired, capsys):
    """Silence here would read as "nothing was expected and nothing was
    missing", which is the opposite of the truth."""
    cli.cmd_walk(walk_args())
    out = capsys.readouterr().out
    assert "OBSERVATION-based" in out
    assert "synthesised" in out


def test_the_manifest_records_that_expectations_could_not_be_checked(wired, tmp_path):
    cli.cmd_walk(walk_args())
    manifest = json.loads((latest_run(tmp_path) / "run.json").read_text(encoding="utf-8"))
    assert manifest["targetEnriched"] is False
    assert manifest["enrichmentGaps"], "an un-enriched run must name what it cannot check"


def test_an_ambiguous_name_stops_and_names_the_candidates(wired, capsys):
    """Walking the wrong lab produces findings that all look plausible."""
    assert cli.cmd_walk(walk_args(name="WorkshopPLUS")) == 2
    err = capsys.readouterr().err
    assert "could not identify the lab" in err
    assert str(ENROLMENT) in err


def test_a_name_that_matches_nothing_does_not_fall_back_to_the_first_lab(wired, capsys):
    assert cli.cmd_walk(walk_args(name="WorkshopPLUS - Nonexistent")) == 2
    assert "could not identify" in capsys.readouterr().err


def test_a_launch_that_needs_a_human_is_reported_not_fatal(wired, monkeypatch, capsys):
    async def gated(_page, **_k):
        return launch.LaunchOutcome(False, True, "countdown-gated; Launch is hidden")

    monkeypatch.setattr(launch, "click_launch", gated)
    assert cli.cmd_walk(walk_args()) == 0
    assert "LAUNCH NEEDED" in capsys.readouterr().out


def test_a_missing_resources_tab_costs_the_vault_not_the_run(wired, monkeypatch, tmp_path):
    """Some labs have no Resources tab at all. That is a finding, not a crash."""
    async def no_creds():
        raise RuntimeError("no Resources tab in this lab")

    monkeypatch.setattr(wired["lab"], "credentials", no_creds)
    assert cli.cmd_walk(walk_args()) == 0
    run = latest_run(tmp_path)
    assert "credential capture skipped" in (run / "run.log").read_text(encoding="utf-8")


def test_the_lab_clock_is_recorded_before_any_time_is_spent(wired, tmp_path):
    """Every later "was this slow because the lab expired?" question needs a
    zero point."""
    cli.cmd_walk(walk_args())
    manifest = json.loads((latest_run(tmp_path) / "run.json").read_text(encoding="utf-8"))
    assert manifest["labMinutesAtStart"] == 5721


def test_the_instruction_corpus_is_written_where_the_run_points(wired, tmp_path):
    cli.cmd_walk(walk_args())
    md = tmp_path / "artifacts" / "instructions" / "outline.md"
    assert md.exists()
    manifest = json.loads((latest_run(tmp_path) / "run.json").read_text(encoding="utf-8"))
    assert Path(manifest["corpus"]["path"]).name == "outline.md"


# --- segment 0: the setup preflight ----------------------------------------


def test_the_walk_checks_the_setup_before_it_walks_it(wired, tmp_path, capsys):
    """Segment 0 exists, and its report is written where the run points."""
    assert cli.cmd_walk(walk_args()) == 0
    report = latest_run(tmp_path) / "preflight.md"
    assert report.exists()
    body = report.read_text(encoding="utf-8")
    assert "Setup preflight" in body
    assert "preflight :" in capsys.readouterr().out


def test_a_lab_issued_operation_url_is_caught_before_section_one(wired, tmp_path, capsys):
    """The G-71 class: valid, resolvable, and wrong in a way that fails elsewhere."""
    wired["lab"]._creds.append(Credential(
        scope="Azure", label="Endpoint",
        value="https://ai-foundry-000000.openai.azure.com/openai/deployments/d/chat/completions",
    ))
    assert cli.cmd_walk(walk_args()) == 0, "a setup defect must not fail the run"
    out = capsys.readouterr().out
    assert "SETUP DEFECT" in out
    assert "attributable" in out

    manifest = json.loads((latest_run(tmp_path) / "run.json").read_text(encoding="utf-8"))
    (failure,) = manifest["preflight"]["failures"]
    assert failure["domain"] == "setup"
    assert failure["severity"] == "critical"
    assert failure["verdict"] in taxonomy.FINDING_VERDICTS


def test_a_clean_preflight_still_publishes_what_it_could_not_check(wired, tmp_path):
    """Absence of evidence is the thing this project keeps refusing to call a pass."""
    assert cli.cmd_walk(walk_args()) == 0
    run_dir = latest_run(tmp_path)
    manifest = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    assert not manifest["preflight"]["failures"]
    assert manifest["preflight"]["unchecked"], "a clean pass must still state its limits"
    assert "did *not* check" in (run_dir / "preflight.md").read_text(encoding="utf-8")


def test_the_preflight_report_never_contains_a_captured_secret(wired, tmp_path):
    """It renders credential-derived evidence, so it goes through the redactor.

    And — the half this test was originally missing — the *argument* has to
    survive that. An assertion that only checks a bad thing is absent will pass
    on an empty file; it passed here while the published evidence read
    ``[REDACTED:Endpoint]``, which leaks nothing and proves nothing.
    """
    wired["lab"]._creds.append(Credential(
        scope="Azure", label="Endpoint",
        value="https://ai-foundry-000000.openai.azure.com/openai/deployments/d/chat",
    ))
    assert cli.cmd_walk(walk_args()) == 0
    body = (latest_run(tmp_path) / "preflight.md").read_text(encoding="utf-8")

    assert "Sup3rSecret!value" not in body
    assert "8d1f4a2e-0b73-4c19-9f6a-2ab5cd7e1234" not in body
    assert "ai-foundry-000000" not in body

    assert "/openai/deployments/d/chat" in body, "masking took the finding with it"
    assert "REDACTED" not in body


def test_no_vault_means_the_preflight_reports_a_blind_spot_not_a_pass(
    wired, monkeypatch, tmp_path
):
    """Losing the Resources tab costs coverage, and the report has to say so."""
    async def no_creds():
        raise RuntimeError("Resources tab not reachable")

    monkeypatch.setattr(wired["lab"], "credentials", no_creds)
    assert cli.cmd_walk(walk_args()) == 0
    body = (latest_run(tmp_path) / "preflight.md").read_text(encoding="utf-8")
    assert "no credentials were captured" in body