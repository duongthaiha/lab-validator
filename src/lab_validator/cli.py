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
import hashlib
import importlib.util
import re
import sys
import threading
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"

#: The skill's directory name, which is fixed by the Agent Skills spec rather
#: than by whatever a checkout happens to be called. Deriving it from
#: ``ROOT.name`` would make `package-skill` fail for anyone who cloned into a
#: differently-named folder, which is not a defect in their skill.
SKILL_NAME = "lab-validator"

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
    "scope": "review what was captured and choose which sections to walk",
    "next": "what the walk loop says to do now, and why",
    "debug": "read a finished run back and see what each action did to the screen",
    "install-skill": "copy this skill into ~/.copilot/skills",
    "package-skill": "build a portable .skill archive for other agent harnesses",
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


async def _select_off_the_loop(fn, *args, **kwargs):
    """Run a blocking call in a daemon thread, without freezing this loop.

    The scope prompt waits on ``input()`` for as long as a person takes to read
    the review and decide -- minutes, on a 23-section lab. The caller owns a
    live Playwright connection to the launched lab, and a coroutine that blocks
    services no websocket. The sign-in gate already refuses to block for exactly
    this reason: it polls with ``await sleep`` rather than waiting inline.

    A *daemon* thread rather than ``asyncio.to_thread``: the default executor's
    workers are non-daemon and joined during interpreter shutdown, so a prompt
    nobody ever answers could keep the process alive after Ctrl+C. A daemon
    thread cannot. The only thing lost is a clean join, and there is nothing to
    join -- the answer is already in the run folder or it was never given.
    """
    loop = asyncio.get_running_loop()
    done = loop.create_future()

    def finish(setter, value):
        # ``done`` may already be cancelled if the caller was torn down while
        # the human was still thinking; setting a result on it would raise.
        if not done.done():
            setter(value)

    def work():
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - handed back to the loop
            # Bound to a default argument: ``except ... as exc`` deletes ``exc``
            # when the block ends, so a lambda closing over it would raise
            # NameError on the loop and lose the real error entirely.
            loop.call_soon_threadsafe(
                lambda e=exc: finish(done.set_exception, e)
            )
        else:
            loop.call_soon_threadsafe(
                lambda r=result: finish(done.set_result, r)
            )

    threading.Thread(target=work, name="lab-validator-scope", daemon=True).start()
    return await done


async def _walk(args) -> int:
    from playwright.async_api import async_playwright

    from . import scope
    from .browser import attached_context
    from .corpus import extract
    from .discovery import resolve
    from .labclient import LabClient
    from .launch import (
        SignInTimeout,
        await_lab_client,
        click_launch,
        ensure_signed_in,
        signed_out,
    )
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
            try:
                lab = await await_lab_client(context, budget_s=args.client_budget, known=known)
            except SignInTimeout as exc:
                # Not a crash, and not the user's fault: the lab may simply
                # still be provisioning. A traceback here reads as "the tool
                # broke" and buries the one line that says what to do next.
                print(f"\n  LAB CLIENT NEVER ANSWERED — {exc}", file=sys.stderr)
                print("  Nothing was walked, so nothing is recorded as checked.",
                      file=sys.stderr)
                return 3
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

            # 7. Scope. Everything above is capture; everything below is hours of
            # walking. This is the moment to ask, and it costs the human nothing
            # extra because they are already at the keyboard -- they signed in by
            # hand a few minutes ago.
            #
            # Nothing here can be inferred: only a person knows which sections
            # they just edited. So --sections decides if given, a terminal is
            # asked if there is one, and otherwise everything is walked, which is
            # what this command did before selection existed.
            print()
            try:
                # Off the loop: `select` may block on `input()` for as long as a
                # person takes to read the review and decide, and this coroutine
                # owns the Playwright connection to the launched lab.
                applied = await _select_off_the_loop(
                    scope.select, run, args.sections, outline=outline, vault=vault
                )
            except scope.ScopeError as exc:
                print(f"--sections: {exc}", file=sys.stderr)
                return 2
            except Exception as exc:  # noqa: BLE001 - capture is done; do not lose it
                # Everything expensive already happened. Failing here would throw
                # away a launched lab, an extracted corpus and a captured vault
                # over the step that decides how much of it to walk -- and the
                # fallback is simply the behaviour this command had before
                # selection existed, so it is safe to take.
                run.log(f"scope gate failed: {type(exc).__name__}: {exc}")
                print(f"scope     : {type(exc).__name__}: {exc}")
                print("            ALL sections stay selected; narrow it with "
                      "`lab-validator scope --sections`")
                applied = None
            else:
                print(f"review    : {run.dir / scope.REVIEW_FILENAME}")

            hint = f"lab-validator next --run {run.dir}"
            if applied is not None and applied.not_selected_now:
                print(f"\nnext: {hint}   (scoped; the rest stay unknown)")
            else:
                print(f"\nnext: {hint}")
            print("  keep running `next` until it says stop; it names the one "
                  "legal move and why")
            return 0
        finally:
            await browser.close()


def cmd_walk(args) -> int:
    return asyncio.run(_walk(args))


# ---- the skill: install and package --------------------------------------
#
# This repository *is* the skill. `SKILL.md`, `references/` and `assets/` sit at
# the root beside the code they drive, and the two commands below publish a
# curated subset of it: one to `~/.copilot/skills`, one to a `.skill` archive.
#
# There used to be a staged copy of the runtime under `skills/lab-validator/`,
# which meant every edit to `src/` had to be re-staged before packaging would
# agree with the source. That copy also carried its own `pyproject.toml`, so
# tools looking for a project root treated it as a second project and wrote
# caches into it. Both failures were invisible until a test caught them. There
# is now one tree and one file list.


#: Everything that ships, as globs relative to the repository root. Kept as data
#: because the same list has to drive the installer, the packager and the test
#: that checks nothing else leaked in -- and because the risk has inverted: with
#: the repo as the skill, the mistake to guard against is shipping `tests/`, not
#: forgetting to re-stage.
SKILL_CONTENTS = (
    "SKILL.md",
    ".env.example",
    "pyproject.toml",
    "references/*.md",
    "assets/*.md",
    "src/lab_validator/*.py",
    "targets/*.toml",
)

#: The scripts that ship. Deliberately enumerated rather than `scripts/*.py`: a
#: development harness that expects the test corpus would ship as a command that
#: cannot work from an extracted archive. Only what a delegated command needs.
SKILL_SCRIPTS = ("install_runtime.py",) + tuple(script for script, _ in COMMANDS.values())


def _validate_skill(body: str) -> None:
    """Refuse to publish a skill that a harness would reject on load.

    Every rule here has already been enforced somewhere else -- by a test, or by
    the Agent Skills spec -- and is repeated at publish time because that is the
    last point where the failure is still ours. A harness that cannot parse the
    frontmatter reports a broken skill, not a broken build.
    """
    if not body.startswith("---\n"):
        raise ValueError("SKILL.md has no YAML frontmatter")
    frontmatter_end = body.find("\n---", 4)
    if frontmatter_end < 0:
        raise ValueError("SKILL.md frontmatter is not closed")
    frontmatter = body[4:frontmatter_end]

    name = re.search(r"^name:\s*([a-z0-9-]+)\s*$", frontmatter, re.MULTILINE)
    if not name or name.group(1) != SKILL_NAME:
        raise ValueError(f"SKILL.md name must be {SKILL_NAME!r}")
    if not re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE):
        raise ValueError("SKILL.md frontmatter has no description")
    if len(body.splitlines()) >= 500:
        raise ValueError("SKILL.md must stay under 500 lines")

    for reference in set(re.findall(r"(references|assets)/([a-z0-9-]+\.md)", body)):
        relative = "/".join(reference)
        if not (ROOT / relative).is_file():
            raise ValueError(f"referenced file is missing: {relative}")


def _skill_files() -> dict[str, bytes]:
    """The published skill, as ``relative posix path -> bytes``.

    Bytes rather than text so that what is installed and what is packaged are
    the same octets. Reading as text would let the platform rewrite line endings
    on the way through, and the drift test between the repo and the installed
    copy would then be comparing two things it had itself changed.
    """
    skill = ROOT / "SKILL.md"
    if not skill.is_file():
        raise ValueError(f"{skill} is missing")
    _validate_skill(skill.read_text(encoding="utf-8"))

    paths: list[Path] = []
    for pattern in SKILL_CONTENTS:
        matched = sorted(ROOT.glob(pattern))
        if not matched:
            raise ValueError(f"skill content is missing: {pattern}")
        paths.extend(matched)
    for script in SKILL_SCRIPTS:
        paths.append(SCRIPTS / script)

    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise ValueError("missing: " + ", ".join(str(path) for path in missing))
    links = [path for path in paths if path.is_symlink()]
    if links:
        raise ValueError(
            "skill packages cannot contain symlinks: "
            + ", ".join(path.relative_to(ROOT).as_posix() for path in links)
        )

    entries: dict[str, bytes] = {}
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        if relative == "pyproject.toml":
            # `readme = "README.md"` would make an install from the extracted
            # archive fail outright: the README is repo documentation and is not
            # published, and setuptools treats a missing readme as fatal.
            content = re.sub(rb"^readme\s*=\s*.+\r?\n", b"", content, flags=re.MULTILINE)
        entries[relative] = content
    return entries


def cmd_install_skill(args) -> int:
    """Copy this skill into the agent's skills directory.

    The repo is the source of truth: a skill living only in
    ``~/.copilot/skills`` is unreviewable, unversioned, and lost with the
    machine. This makes deploying it one command, which is what stops the two
    copies drifting -- and a test asserts they have not.
    """
    try:
        entries = _skill_files()
    except ValueError as exc:
        print(f"cannot install skill: {exc}", file=sys.stderr)
        return 2

    dest = Path(args.into).expanduser() if args.into else Path.home() / ".copilot" / "skills"
    dest = dest / SKILL_NAME

    # Prune before writing. An install that only ever adds leaves every file the
    # skill used to have sitting in the destination -- and the debris is not
    # inert: a renamed module leaves the old one importable, and a dropped
    # directory leaves a stale second copy of the engine inside the very skill an
    # agent reads. The destination belongs to this command, so it owns removals
    # too. Restricted to files this command could have written, so pointing
    # `--into` somewhere unfortunate cannot take anything else with it.
    stale = sorted(
        path
        for path in (dest.rglob("*") if dest.exists() else ())
        if path.is_file() and path.relative_to(dest).as_posix() not in entries
    )

    for relative, content in sorted(entries.items()):
        if args.dry_run:
            continue
        target = dest / Path(relative)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    if not args.dry_run:
        for path in stale:
            path.unlink()
        for directory in sorted(
            (p for p in dest.rglob("*") if p.is_dir()),
            key=lambda p: len(p.parts),
            reverse=True,
        ):
            if not any(directory.iterdir()):
                directory.rmdir()

    verb = "would install" if args.dry_run else "installed"
    print(f"{verb} {len(entries)} file(s) into {dest}")
    for relative in sorted(entries):
        print(f"  {relative}")
    if stale:
        removed = "would remove" if args.dry_run else "removed"
        print(f"{removed} {len(stale)} file(s) the skill no longer contains")
        for path in stale:
            print(f"  - {path.relative_to(dest).as_posix()}")
    return 0


def cmd_package_skill(args) -> int:
    """Build the portable archive another harness can extract and load."""
    try:
        entries = _skill_files()
    except ValueError as exc:
        print(f"cannot package skill: {exc}", file=sys.stderr)
        return 2

    output = Path(args.out or "dist/lab-validator.skill").expanduser().resolve()
    if output.suffix != ".skill":
        print("--out must name a .skill file", file=sys.stderr)
        return 2

    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w") as archive:
        # Fixed timestamps and permissions: a rebuild from unchanged sources has
        # to produce an identical file, or "did this archive change?" can only be
        # answered by unpacking it.
        for relative, content in sorted(entries.items()):
            entry = zipfile.ZipInfo(f"{SKILL_NAME}/{relative}", date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, content)

    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"packaged {len(entries)} file(s) into {output}")
    print(f"sha256   : {digest}")
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


def _open_run(args):
    """Open the run named by `--run`, or the latest under `--runs`.

    Returns `(run, exit_code)`; exactly one of them is None.

    `--run` and `--runs` sit next to each other on two commands and mean
    opposite things -- one folder versus the folder of folders -- so pointing
    `--run` at a runs root is the mistake people actually make. It used to exit
    with a `FileNotFoundError` traceback, which reads as a crash rather than as
    a typo. Detect that specific case and name the runs inside it, which is the
    same move `LabClient.find` and `scope.parse` already make: refuse, and say
    what the real candidates were.
    """
    from .runlog import Run

    runs_root = Path(args.runs or "runs")
    if not args.run:
        run = Run.latest(runs_root)
        if run is None:
            print(f"no run found under {runs_root}", file=sys.stderr)
            return None, 2
        return run, None

    path = Path(args.run)
    try:
        return Run.open(path), None
    except FileNotFoundError as exc:
        print(f"{exc}", file=sys.stderr)
        inside = sorted(p.name for p in path.glob("*") if (p / "run.json").is_file())
        if inside:
            print(f"that looks like a runs root. It holds: {', '.join(inside)}",
                  file=sys.stderr)
            print(f"did you mean --run {path / inside[-1]}?", file=sys.stderr)
        return None, 2


def cmd_debug(args) -> int:
    """Read a finished run back and say what each action did to the screen.

    Works on runs recorded before any of this existed, by measuring the images
    on disk. That is the whole point: the run you want to explain is always one
    that already happened, and asking somebody to re-run it with a flag on is
    asking them to reproduce a thing they could not explain in the first place.
    """
    from .debugread import report

    run, code = _open_run(args)
    if run is None:
        return code
    moved = False if args.stuck else None
    try:
        text = report(run.dir, tail=args.tail, moved=moved)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(text)
    if args.out:
        out = Path(args.out)
        out.write_text(text, encoding="utf-8", newline="\n")
        print(f"\nwritten to {out}")
    return 0


def cmd_scope(args) -> int:
    """Review what a run captured, and choose what is worth walking.

    Read-only unless ``--sections`` is given. That default is deliberate: this
    command exists so somebody can *look* before committing hours, and a review
    tool that silently rewrites the thing being reviewed is not one.

    It is also the re-scoping path. A walk that turns up something interesting
    in section 4 is a good reason to add 5 and 6, so this may widen a run at any
    point -- but never narrow one, because a walked section is evidence.
    """
    from . import scope
    from .vault import Vault

    run, code = _open_run(args)
    if run is None:
        return code

    outline, why_not = _outline_for(run)
    vault = None
    with contextlib.suppress(Exception):
        vault = Vault.load(run.dir)

    if not args.sections:
        if outline is None:
            print(f"note: {why_not}")
        path = scope.write_review(run, outline, vault)
        print(scope.review(run, outline, vault))
        print(f"written to {path}")
        print("\nnothing changed. Re-run with --sections to choose.")
        return 0

    try:
        scope.select(run, args.sections, outline=outline, vault=vault, interactive=False)
    except scope.ScopeError as exc:
        print(f"--sections: {exc}", file=sys.stderr)
        return 2

    if (run.dir / "gap-analysis.md").exists():
        # The report on disk was rendered against the old scope, so it now
        # understates or overstates what this run covers. Saying so beats
        # letting somebody read a stale file that looks current.
        print("\nnote: gap-analysis.md predates this scope change; re-render it "
              "before reading it as current.")
    print(f"\nnext: lab-validator next --run {run.dir}")
    return 0


def cmd_next(args) -> int:
    """Print the next move, decided from the run folder alone.

    This is the walk loop's whole interface. It is a separate command rather
    than a daemon because the step it decides needs judgement to carry out, and
    judgement is the one part that cannot be packaged. Deciding *what* comes
    next, and refusing to advance past a task nobody judged, can be.
    """
    from .vault import Vault
    from .walkloop import describe, next_move

    run, code = _open_run(args)
    if run is None:
        return code

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
        from .scope import SECTIONS_HELP

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
        w.add_argument("--sections", help=SECTIONS_HELP)
        w.add_argument("--port", type=int, default=DEFAULT_CDP_PORT)
        return cmd_walk(w.parse_args(args.rest))

    if args.command == "scope":
        from .scope import SECTIONS_HELP

        s = argparse.ArgumentParser(prog="lab-validator scope")
        s.add_argument("--run", help="run folder (default: the most recent)")
        s.add_argument("--runs", help="runs root (default: ./runs)")
        s.add_argument("--sections",
                       help=f"{SECTIONS_HELP}. Omit to review without changing anything.")
        return cmd_scope(s.parse_args(args.rest))

    if args.command == "next":
        n = argparse.ArgumentParser(prog="lab-validator next")
        n.add_argument("--run", help="run folder (default: the most recent)")
        n.add_argument("--runs", help="runs root (default: ./runs)")
        n.add_argument("--minutes", type=int,
                       help="lab minutes remaining, so the loop can reserve write-up time")
        return cmd_next(n.parse_args(args.rest))

    if args.command == "debug":
        d = argparse.ArgumentParser(prog="lab-validator debug")
        d.add_argument("--run", help="run folder (default: the most recent)")
        d.add_argument("--runs", help="runs root (default: ./runs)")
        d.add_argument("--tail", type=int, default=0,
                       help="show only the last N captures (a long run answers "
                            "'what was it doing when it stopped' badly in full)")
        d.add_argument("--stuck", action="store_true",
                       help="show only the actions that changed nothing on screen")
        d.add_argument("--out", help="also write the report to this file")
        return cmd_debug(d.parse_args(args.rest))

    if args.command == "install-skill":
        s = argparse.ArgumentParser(prog="lab-validator install-skill")
        s.add_argument("--into", help="skills directory (default: ~/.copilot/skills)")
        s.add_argument("--dry-run", action="store_true", help="list what would be written")
        return cmd_install_skill(s.parse_args(args.rest))

    if args.command == "package-skill":
        s = argparse.ArgumentParser(prog="lab-validator package-skill")
        s.add_argument(
            "--out",
            help="output .skill file (default: dist/lab-validator.skill)",
        )
        return cmd_package_skill(s.parse_args(args.rest))

    if args.command in COMMANDS:
        return _delegate(COMMANDS[args.command][0], args.rest)

    parser.print_help(sys.stderr)
    print(f"\nunknown command {args.command!r}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
