# lab-validator — working notes for agents

Read this before changing anything. This repo has an unusual number of
self-guarding tests; most of them exist because the failure they describe
already happened once.

## What this is

A Python tool that walks a Microsoft Learning Campus (Skillable) hands-on lab
as a simulated learner in a real browser and produces an evidence-backed **gap
analysis** — every place the instructions have drifted from the live product,
and every place the lab environment itself is broken. A human signs in once;
the tool does the rest.

Two faces over one engine:

| Face | What it is | Lives in |
|---|---|---|
| **CLI** | The execution engine. Drives the browser, records the trace, renders reports. | `src/lab_validator/`, `scripts/` |
| **Agent skill** | The judgement layer. Tells a model *how* to walk a lab and *what counts* as a finding. | `SKILL.md`, `references/`, `assets/` |

The skill never re-implements the CLI — it calls it. Keep that boundary.

## Running things

Windows, PowerShell, Python ≥ 3.11. The package is installed editable into
`.venv`, so `import lab_validator` works without `PYTHONPATH`. The
`lab-validator` console script is **not** on `PATH` in a fresh shell — either
use `.venv\Scripts\lab-validator.exe` or:

```powershell
python -m lab_validator.cli <command>
```

The two commands that must pass before you call anything done:

```powershell
python -m pytest -q          # 907 tests, ~13s, no network
python -m ruff check .
```

Everything is offline and hermetic. If a test wants a browser or a live lab,
it is wrong — fix the test, not the environment.

## Layout

```
src/lab_validator/     the engine (cli, walkloop, report, runlog, browser, agent, …)
scripts/lab_*.py       operator-facing shims; each keeps its own main()
SKILL.md               the skill body — this repository *is* the skill
references/*.md        loaded into a model's context on demand
assets/                the gap-analysis output template
evals/                 skill-quality evals; results go in ../lab-validator-workspace/
tests/                 pytest; one file per module, all offline
targets/*.toml         lab descriptors
docs/                  approach.md (the reasoning), solution.md, cli.md
runs/, artifacts/      generated, gitignored, may contain lab credentials
```

`cli.py` is a **dispatcher, not a rewrite**. `COMMANDS` delegates to
`scripts/`; `BUILTINS` is implemented in-process. Both are kept as data because
the help epilog, the dispatcher and the tests all read them — hardcoding the
list anywhere rots it silently.

## Trip-wires

These will fail on you if you skip them. They are not noise.

**Editing `SKILL.md`, `references/`, `assets/`, `src/`, `scripts/` or
`pyproject.toml`** → re-install, or
`test_the_installed_copy_has_not_drifted_from_the_repo` fails:

```powershell
python -m lab_validator.cli install-skill
```

The repository *is* the skill. `install-skill` and `package-skill` are two
writers over one curated file list — `_skill_files()` in `cli.py` — so the
installed copy, the archive and the repo cannot disagree about what the skill
contains. There is no staging step to keep fresh.

The list is explicit rather than "everything here", because the flip side of
publishing straight from the repo is **over-inclusion**: a careless glob ships
`tests/`, `docs/` or whatever a tool has just written into the working tree, and
an archive full of the wrong files still extracts and loads perfectly well.
`test_the_package_ships_nothing_the_repository_only_needs` is the guard. Adding
a new runtime file means adding it to `SKILL_CONTENTS` or `SKILL_SCRIPTS`, and
`install-skill --dry-run` shows exactly what would be published.

**`SKILL.md` has a hard 500-line budget** (progressive disclosure).
It currently sits around 495. Adding a section means moving one out to
`references/`.

**Docs are tested against the code.** `tests/test_skill.py` scrapes every
`lab-validator <cmd> --flag` out of `SKILL.md`, `README.md` and `docs/cli.md`
and checks it against the real argparse surface. It also checks:

- every verdict code and domain named in the docs exists in `taxonomy.py`
- every file in `references/` and `assets/` is linked, and every link resolves
- the README's *Layout* block lists every module and script, and nothing that
  no longer exists
- every test cited by name in the docs is still called that
- every `--sections` expression printed in the docs actually parses

So: rename a module, add a CLI flag, or delete a test, and you must update the
prose in the same change.

**Adding a new skill file** → link it from `SKILL.md`, or the orphan test fails.

**Spec conformance.** The skill is a valid [Agent Skills](https://agentskills.io/specification)
package. If you change its frontmatter or structure, re-validate:

```powershell
pip install skills-ref            # installs a console script named `agentskills`
agentskills validate C:\Git\lab-validator   # needs an absolute path, not `.`
```

## Evaluating the skill

Test cases live in `evals/evals.json`; `evals/README.md` explains the loop.
Read it before changing `SKILL.md` in any way that alters judgement.

The one thing to understand up front: **evals here never touch a live lab.**
Not because it would be slow, but because two live runs do not see the same lab
— environments drift between reservations, and detecting that drift is what
this tool is *for*. A with/without delta measured across two live runs is partly
measuring the skill and partly measuring the lab moving underneath it. So the
input is a recorded walk (`evals/files/drifted-walk/`) with the observations
already made, identical for every run and every version.

That fixture is synthetic and every trap in it is planted deliberately — a
transient that must *not* be reported, a deployment whose name and served model
disagree, a notebook cell green with nothing behind it. `tests/test_evals.py`
asserts the traps are still there, because a fixture edited down to clean
observations still parses, still grades, and still reports the skill as working.

`evals/` is repository-only: not published by `install-skill` or
`package-skill`, and the over-inclusion guard enforces it.

## The report is the product

`src/lab_validator/report.py` renders the gap analysis, and
`assets/gap-analysis-template.md` is the template that
documents that output. **They must not drift.** Change the renderer and you
change the template in the same commit, and vice versa.

Structural rules the renderer holds to:

- Findings are numbered **globally, severity-ordered**, and the number is
  stable — it is the same in the routing block, the summary table and the
  finding's own heading. A finding that changes number between runs cannot be
  tracked.
- The run-level report groups finding bodies **lab by lab** (`### {lab}` →
  `#### {n}.`); a section report does not, because one section is one lab.
- The report publishes *absences* as loudly as failures: sections never
  reached, checks the preflight could not make, learner controls left untested.
  A run that omits them reads cleaner than it was.

## House style

- **Docstrings and comments explain *why*, and usually name the failure that
  motivated the code.** "Written as its own term rather than left to fall out
  of `done != total`: that arithmetic happens to be right today, and a
  coincidence is not a guarantee." Match that register — it is the repo's
  main defence against someone helpfully deleting a guard.
- Do not add comments that restate the code.
- Test names are sentences: `test_unfinished_section_does_not_read_as_clean`.
  Their docstrings say what a reader would wrongly conclude without them.
- Line length 100. Ruff `E,F,I,UP,B,S` with `S101/S603/S607` ignored.
- Commit messages are imperative and describe the *behavioural* change, not the
  files touched: "Refuse the sign-in verdict the pixels cannot settle".

### The Orientation block

Every module under `src/lab_validator/` and `scripts/` ends its docstring with:

```
Orientation
-----------
Role:     renders the trace into gap-analysis.md; the last stage of a walk.
Entry:    `render_section`, `render_run`, `Finding`
Talks to: taxonomy, runlog, scope, learnerpath
```

It exists because the prose above it answers *why this module exists* and
deliberately never answers *what do I call, and what does it talk to* — which
is what someone reading the file for the first time needs first.

Two rules, both enforced by `tests/test_docstrings.py`:

- **It is strictly additive, and it goes last.** Never reword, reorder or
  summarise the prose above it to make room. The first screen of `console.py`
  is the story of the bug that module exists to catch; a metadata table above
  that pushes the most valuable paragraph in the repo below the fold.
- **It may not lie.** Every name under `Entry:` must resolve to a real
  module-level definition and every name under `Talks to:` to a real import, so
  a rename cannot leave the docstring reading plausibly and pointing nowhere.

`Entry:` names the two-to-four things a caller actually uses. It is not an API
dump — `cli.py` names `main` and its dispatch tables, not thirty parsers.

## Safety

Lab runs handle real credentials. `pre-commit` blocks `.env`, `.auth/`, HAR
files, Playwright traces and storage-state JSON, and runs gitleaks. Install it:
`pre-commit install`.

- Never commit anything under `runs/`, `artifacts/`, `.auth/`,
  `.browser-profile/`.
- Never paste `@lab.MaskedTextBox` / `CloudPortalCredential` values into code,
  tests, docs or commit messages.
- `.env.example` is the only `.env*` file that belongs in git.

## Where to read more

| Question | File |
|---|---|
| Why is it built this way? | `docs/approach.md` (long; the reasoning of record) |
| How do the pieces fit? | `docs/solution.md` |
| What can the CLI do? | `docs/cli.md` |
| What must a harness driving this guarantee? | `references/harness-traps.md` |
| What does the output look like? | `docs/gapanalysis.md` (real example) |
| How should a model judge a lab? | `skills/lab-validator/SKILL.md` + `references/` |

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->
