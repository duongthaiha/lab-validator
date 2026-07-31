"""One entry point: ``lab-validator``.

Until now every capability was a separate script under ``scripts/``, which is a
fine shape for building an engine and a poor one for handing it to someone else:
there is no single thing to run, no discoverable list of what exists, and the
order the scripts must be used in lives only in a README.

So this is a dispatcher, not a rewrite. The scripts keep their own ``main()``
and keep working exactly as they did -- ``python scripts/lab_run.py --report``
is still valid -- and this adds a front door over the top. The one genuinely new
command is :func:`cmd_walk`, which is the contract the whole capability was
asked for:

    lab-validator walk --url "<lab url>" --name "<lab name>"

The human signs in. The machine does everything else.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

#: sub-command -> script filename. Kept as data so the list is the help text.
COMMANDS = {
    "run": ("lab_run.py", "start, inspect and report on a validation run"),
    "step": ("lab_step.py", "drive one step, recording it as trace evidence"),
    "text": ("lab_text.py", "read the instruction corpus for a section"),
    "corpus": ("lab_corpus.py", "extract and segment the instruction document"),
    "discover": ("lab_discover.py", "list enrolments and scaffold a descriptor"),
    "drive": ("lab_drive.py", "low-level VM console control"),
    "session": ("browser_session.py", "browser profile, attach, sign-in helpers"),
    "auth": ("bootstrap_auth.py", "prepare the dedicated browser profile"),
}


#: sub-commands implemented here rather than delegated to a script. Kept as data
#: because three places need the list — the help epilog, the dispatcher's error
#: path, and the test that checks the skill only documents real commands — and a
#: hardcoded copy in any of them silently rots the moment a command is added.
BUILTINS = {
    "walk": "start a run from a lab URL (the human signs in)",
    "auto": "walk the whole lab with an agent (the human only signs in)",
    "next": "what the walk loop says to do now, and why",
    "install-skill": "copy skills/lab-validator into ~/.copilot/skills",
}


def _load(script: str):
    """Import a script by path so the dispatcher does not duplicate its logic.

    Path-based rather than a package import because the scripts deliberately
    live outside the package: they are the operator-facing shims, and folding
    them in would make the package depend on argparse surfaces that exist for
    humans rather than for callers.
    """
    path = SCRIPTS / script
    if not path.exists():
        raise SystemExit(
            f"{path} is missing. The CLI dispatches to the scripts in the checkout, "
            "so it must be run from a clone rather than an installed wheel."
        )
    spec = importlib.util.spec_from_file_location(f"_labcli_{path.stem}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _delegate(script: str, argv: list[str]) -> int:
    module = _load(script)
    saved = sys.argv
    sys.argv = [str(SCRIPTS / script), *argv]
    try:
        return module.main()
    finally:
        sys.argv = saved


# ---- walk ----------------------------------------------------------------


async def _walk(args) -> int:
    from playwright.async_api import async_playwright

    from .browser import attached_context
    from .corpus import extract
    from .discovery import resolve
    from .labclient import LabClient
    from .launch import await_lab_client, click_launch, ensure_signed_in, signed_out
    from .preflight import preflight
    from .runlog import Run
    from .targets import Target
    from .vault import Vault

    links_js = _load("browser_session.py").LINKS_JS

    async with async_playwright() as pw:
        browser, context = await attached_context(pw, args.port)
        try:
            page = context.pages[0] if context.pages else await context.new_page()
            await page.bring_to_front()

            print(f"url       : {args.url}")
            await page.goto(args.url, wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)

            # 1. The sign-in gate. The human's job, permanently.
            async def is_signed_in():
                try:
                    has_login = await page.get_by_role(
                        "link", name="Sign In"
                    ).or_(page.get_by_role("button", name="Sign In")).count() > 0
                    return not signed_out(page.url, has_login)
                except Exception:  # noqa: BLE001 - mid-navigation, try again
                    return False

            await ensure_signed_in(is_signed_in, budget_s=args.signin_budget)

            # 2. URL + name -> exactly one enrolment. Never guess.
            links = await page.evaluate(links_js)
            found = resolve(links, args.url, args.name or "")
            if not found.ok:
                print(f"\ncould not identify the lab: {found.reason}", file=sys.stderr)
                if found.candidates:
                    print("\nreachable enrolments:", file=sys.stderr)
                    for e in found.candidates:
                        print(f"  {e}", file=sys.stderr)
                    print(
                        "\nRe-run with --name matching one of these exactly, or pass its "
                        "/ClassEnrollment/<id> URL directly.",
                        file=sys.stderr,
                    )
                return 2
            enrolment = found.enrolment
            print(f"lab       : {enrolment.title}")
            print(f"            enrolment {enrolment.enrolment} ({found.reason})")

            target = Target.from_url(enrolment.url, enrolment.title, root=ROOT / "targets")
            print(f"descriptor: {target.slug}"
                  + ("" if target.is_enriched else " (synthesised -- none on disk)"))

            # 3. Launch. Automated, with a human fallback that is not a failure.
            if enrolment.url not in page.url:
                await page.goto(enrolment.url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2500)
            # Whatever lab tabs exist now predate this launch, so the tab that
            # Launch opens can be told apart from one left over from an
            # earlier lab. The guidance deliberately leaves those open.
            known = [p.url for p in LabClient.candidates(context)]
            if known:
                print(f"note      : {len(known)} lab client tab(s) already open; ignoring them")
            outcome = await click_launch(page, budget_s=args.launch_budget)
            if outcome.needs_human:
                print(f"\n  LAUNCH NEEDED — {outcome.reason}")
                print("  Click Launch yourself in the browser window. I will wait.")
            lab = await await_lab_client(context, budget_s=args.client_budget, known=known)
            print(f"instance  : {lab.instance_id}")

            # 4. Instructions.
            outline = await extract(lab.instructions)
            artifacts = ROOT / "artifacts" / "instructions"
            artifacts.mkdir(parents=True, exist_ok=True)
            outline.save(artifacts / "outline.json")
            (artifacts / "outline.md").write_text(outline.to_markdown(), encoding="utf-8")

            run = Run.create(
                ROOT / "runs",
                target.name,
                lab=target.lab,
                instance=lab.instance_id,
                corpus=artifacts / "outline.md",
                agent=args.agent,
                segments=outline.segments(),
            )
            # A second copy inside the run, because artifacts/ is shared and the
            # next walk overwrites it. Without this, asking an old run what to do
            # next would read a *different lab's* tasks and answer confidently.
            # Run folders are evidence; evidence that depends on a mutable file
            # somewhere else is not evidence.
            outline.save(run.dir / "outline.json")
            run.manifest["targetSlug"] = target.slug
            run.manifest["targetEnriched"] = target.is_enriched
            run.manifest["enrichmentGaps"] = target.enrichment_gaps()
            run.manifest["entryUrl"] = args.url
            run.manifest["labMinutesAtStart"] = await lab.minutes_remaining()
            run.manifest["structuralAnomalies"] = [
                {"code": a.code, "severity": a.severity, "message": a.message}
                for a in outline.anomalies()
            ]
            run._save()

            # 5. Credentials: captured once, masked at the writer, kept as data.
            vault = None
            try:
                vault = Vault.capture(await lab.credentials(), run.redactor)
                vault.save(run.dir)
                await lab.show_instructions()
                print(f"vault     : {len(vault)} credential(s) captured (gitignored)")
            except Exception as exc:  # noqa: BLE001 - a missing tab must not end the run
                run.log(f"credential capture skipped: {type(exc).__name__}: {exc}")
                print(f"vault     : none — {type(exc).__name__}; reuse falls back to the tab")

            # 6. Segment 0: check the environment before walking it.
            #
            # The most damaging defects in the reference run were setup defects
            # found late, after their failures had already been misattributed to
            # unrelated causes across several sections. Running this first does
            # not prevent them; it makes every later failure attributable.
            #
            # It never stops the run. A blocked lab is the most valuable thing a
            # walk can find, and finding it early must not cost the rest.
            checks = preflight(endpoints=vault.endpoints() if vault else None)
            (run.dir / "preflight.md").write_text(
                run.redactor.scrub(checks.to_markdown()), encoding="utf-8"
            )
            run.manifest["preflight"] = {
                "checks": len(checks.checks),
                "failures": [
                    {"name": c.name, "verdict": c.verdict, "domain": c.domain,
                     "severity": c.severity, "detail": c.detail}
                    for c in checks.failures
                ],
                "unchecked": checks.unchecked,
            }
            run._save()
            if checks.failures:
                print(f"preflight : {len(checks.failures)} SETUP DEFECT(S) before section 1")
                for check in checks.failures:
                    print(f"            - {check.name}: {check.detail.splitlines()[0]}")
                print("            the walk continues; later failures are now attributable")
            else:
                print(f"preflight : {len(checks.checks)} check(s), clean "
                      f"({len(checks.unchecked)} thing(s) it could not check)")

            print(f"run       : {run.dir}")
            print(f"lab clock : {run.manifest['labMinutesAtStart']} min")
            print(f"segments  : {len(outline.segments())}")
            print(f"anomalies : {len(outline.anomalies())} structural")
            if not target.is_enriched:
                print("\n  No descriptor on disk, so this run makes OBSERVATION-based")
                print("  findings only. It cannot check any of:")
                for gap in target.enrichment_gaps():
                    print(f"    - {gap}")
            print("\nnext: lab-validator run --next")
            return 0
        finally:
            await browser.close()


def cmd_walk(args) -> int:
    return asyncio.run(_walk(args))


def cmd_auto(args) -> int:
    """Sign in, then let an agent do the lab.

    Sequencing is *not* delegated. ``agent.drive`` calls the same
    ``walkloop.next_move`` a human would, executes the mechanical moves itself,
    and asks a model only where judgement is required -- so every refusal the
    loop makes still holds when nobody is watching. See ``agent.py``.
    """
    from .agent import AgentUnavailable, walk_autonomously
    from .runlog import Run

    runs_root = Path(args.runs or "runs")

    if args.run:
        run_dir = Path(args.run)
    else:
        # Which run is this? Record what existed before walking, so the new one
        # is identified by *not having been there*, rather than by being newest.
        # Position is not identity, and a clock skew or a parallel walk is
        # exactly the case where "latest" quietly returns somebody else's lab.
        before = {p.resolve() for p in runs_root.glob("*") if p.is_dir()}
        rc = cmd_walk(args)
        if rc != 0:
            return rc
        fresh = sorted({p.resolve() for p in runs_root.glob("*") if p.is_dir()} - before)
        if len(fresh) != 1:
            print(
                f"expected exactly one new run under {runs_root}, found {len(fresh)}: "
                f"{[p.name for p in fresh]}. Re-run with --run <folder> to say which.",
                file=sys.stderr,
            )
            return 2
        run_dir = fresh[0]

    print(f"\n-> driving {run_dir.name}\n")
    try:
        progress = walk_autonomously(
            run_dir,
            model=args.model,
            max_turns=args.max_turns,
            turn_timeout=args.turn_timeout,
        )
    except AgentUnavailable as exc:
        print(str(exc), file=sys.stderr)
        return 3

    print(f"\n{progress.summary()}")
    run = Run.open(run_dir)
    print(f"report: {run.dir / 'gap-analysis.md'}")
    return 0


# ---- skill install -------------------------------------------------------


def cmd_install_skill(args) -> int:
    """Copy the repo's skill into the agent's skills directory.

    The repo copy is the source of truth: a skill living only in
    ``~/.copilot/skills`` is unreviewable, unversioned, and lost with the
    machine. This makes deploying it one command, which is what stops the two
    copies drifting -- and a test asserts they have not.
    """
    source = ROOT / "skills" / "lab-validator"
    if not source.is_dir():
        print(f"{source} is missing", file=sys.stderr)
        return 1
    dest = Path(args.into).expanduser() if args.into else Path.home() / ".copilot" / "skills"
    dest = dest / "lab-validator"

    copied = []
    for path in sorted(source.rglob("*")):
        if path.is_dir():
            continue
        target = dest / path.relative_to(source)
        if args.dry_run:
            copied.append(target)
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
        copied.append(target)

    verb = "would install" if args.dry_run else "installed"
    print(f"{verb} {len(copied)} file(s) into {dest}")
    for path in copied:
        print(f"  {path.relative_to(dest)}")
    return 0


# ---- next: what the loop says to do now ----------------------------------


def _outline_for(run) -> tuple[object | None, str]:
    """The outline this run was walked against, or nothing, with the reason.

    Preference order matters more than it looks. The run-local copy is evidence;
    the shared ``artifacts/`` copy is a mutable file that the *next* walk
    overwrites. Reading the shared copy for an older run would enumerate a
    different lab's tasks and answer with complete confidence, which is worse
    than answering nothing — so the fallback is only taken when the manifest's
    recorded hash still matches what is on disk.
    """
    import hashlib

    from .corpus import Outline

    local = run.dir / "outline.json"
    if local.exists():
        return Outline.load(local), ""

    corpus = run.manifest.get("corpus") or {}
    recorded, path = corpus.get("sha256"), corpus.get("path")
    if not (recorded and path):
        return None, "this run recorded no corpus, so task coverage cannot be checked"
    shared = Path(path)
    sibling = shared.with_name("outline.json")
    if not (shared.exists() and sibling.exists()):
        return None, f"the corpus this run used is gone from {shared.parent}"
    actual = hashlib.sha256(shared.read_bytes()).hexdigest()
    if actual != recorded:
        return None, (
            f"{shared.name} has changed since this run walked it (hash mismatch), "
            "so it now describes a different lab. Refusing to enumerate tasks from it."
        )
    return Outline.load(sibling), ""


def cmd_next(args) -> int:
    """Print the next move, decided from the run folder alone.

    This is the walk loop's whole interface. It is a separate command rather
    than a daemon because the step it decides needs judgement to carry out, and
    judgement is the one part that cannot be packaged. Deciding *what* comes
    next, and refusing to advance past a task nobody judged, can be.
    """
    from .runlog import Run
    from .vault import Vault
    from .walkloop import describe, next_move

    runs_root = Path(args.runs or "runs")
    run = Run.open(Path(args.run)) if args.run else Run.latest(runs_root)
    if run is None:
        print(f"no run found under {runs_root}", file=sys.stderr)
        return 2

    outline, why_not = _outline_for(run)
    if outline is None:
        print(f"note: {why_not}")

    # Labels only. The vault's values stay in the vault; what the loop needs is
    # the ability to say "this task wants the admin password", not the password.
    labels = None
    with contextlib.suppress(Exception):
        labels = Vault.load(run.dir).label_index()

    move = next_move(run, outline, minutes_remaining=args.minutes, labels=labels)
    print(describe(run, outline))
    print()
    print(f"NEXT: {move.action.upper()}" + (f"  [{move.segment_id}]" if move.segment_id else ""))
    print(f"  why: {move.why}")
    for ref in move.tasks:
        asked = (move.detail.get("asks") or {}).get(ref)
        print(f"  task: #{ref}" + (f"   [{'; '.join(asked)}]" if asked else ""))
    if move.detail:
        print(f"  {move.detail}")
    return 0


# ---- entry point ---------------------------------------------------------


def _console_utf8() -> None:
    """Stop a lab's own title from killing the run.

    Windows consoles default to cp1252, and Skillable titles are full of
    en-dashes -- "WorkshopPLUS - Azure AI Platform" is the exception, not the
    rule. Printing one raises ``UnicodeEncodeError`` *mid-line*, which takes
    down whatever was in progress. For a tool whose entire job is walking labs
    whose titles it has never seen, that is not an edge case.

    ``errors="replace"`` is deliberate: a mangled character in a console echo
    costs nothing, because the artefacts on disk are written separately and are
    real UTF-8. Losing an hour-long walk to a dash costs a great deal.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        with contextlib.suppress(Exception):
            reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    _console_utf8()
    parser = argparse.ArgumentParser(
        prog="lab-validator",
        description="Walk a Skillable lab as a learner and report where it has drifted.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join(
            ["commands:"]
            + [f"  {name:<14}{help}" for name, help in BUILTINS.items()]
            + [f"  {name:<14}{help}" for name, (_, help) in COMMANDS.items()]
        ),
    )
    parser.add_argument("command", nargs="?",
                        help="one of: " + ", ".join([*BUILTINS, *COMMANDS]))
    parser.add_argument("rest", nargs=argparse.REMAINDER)
    args, _ = parser.parse_known_args()

    if args.command is None:
        parser.print_help()
        return 0

    if args.command == "walk":
        from .browser import DEFAULT_CDP_PORT

        w = argparse.ArgumentParser(prog="lab-validator walk")
        w.add_argument("--url", required=True, help="the lab or catalogue URL")
        w.add_argument("--name", help="the lab's title, to disambiguate the URL")
        w.add_argument("--agent", default="lab-validator", help="who is walking")
        w.add_argument("--signin-budget", type=float, default=900.0,
                       help="seconds to wait for a human to sign in")
        w.add_argument("--launch-budget", type=float, default=180.0,
                       help="seconds to wait for Launch to become clickable")
        w.add_argument("--client-budget", type=float, default=300.0,
                       help="seconds to wait for the lab client to answer")
        w.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
        return cmd_walk(w.parse_args(args.rest))

    if args.command == "auto":
        from .agent import DEFAULT_MODEL, DEFAULT_TURN_TIMEOUT
        from .browser import DEFAULT_CDP_PORT

        a = argparse.ArgumentParser(prog="lab-validator auto")
        a.add_argument("--url", help="the lab or catalogue URL")
        a.add_argument("--name", help="the lab's title, to disambiguate the URL")
        a.add_argument("--run", help="drive an existing run instead of starting one")
        a.add_argument("--runs", help="runs root (default: ./runs)")
        a.add_argument("--model", default=DEFAULT_MODEL, help="model to drive with")
        a.add_argument("--max-turns", type=int, default=200,
                       help="ceiling on moves, so a stuck walk cannot run forever")
        a.add_argument("--turn-timeout", type=float, default=DEFAULT_TURN_TIMEOUT,
                       help="seconds one model turn may take")
        a.add_argument("--agent", default="lab-validator", help="who is walking")
        a.add_argument("--signin-budget", type=float, default=900.0,
                       help="seconds to wait for a human to sign in")
        a.add_argument("--launch-budget", type=float, default=180.0,
                       help="seconds to wait for Launch to become clickable")
        a.add_argument("--client-budget", type=float, default=300.0,
                       help="seconds to wait for the lab client to answer")
        a.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
        parsed = a.parse_args(args.rest)
        if not parsed.run and not parsed.url:
            a.error("--url is required unless --run names an existing run")
        return cmd_auto(parsed)

    if args.command == "next":
        n = argparse.ArgumentParser(prog="lab-validator next")
        n.add_argument("--run", help="run folder (default: the most recent)")
        n.add_argument("--runs", help="runs root (default: ./runs)")
        n.add_argument("--minutes", type=int,
                       help="lab minutes remaining, so the loop can reserve write-up time")
        return cmd_next(n.parse_args(args.rest))

    if args.command == "install-skill":
        s = argparse.ArgumentParser(prog="lab-validator install-skill")
        s.add_argument("--into", help="skills directory (default: ~/.copilot/skills)")
        s.add_argument("--dry-run", action="store_true", help="list what would be written")
        return cmd_install_skill(s.parse_args(args.rest))

    if args.command in COMMANDS:
        return _delegate(COMMANDS[args.command][0], args.rest)

    parser.print_help(sys.stderr)
    print(f"\nunknown command {args.command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
