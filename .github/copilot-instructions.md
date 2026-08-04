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
| **Agent skill** | The judgement layer. Tells a model *how* to walk a lab and *what counts* as a finding. | `skills/lab-validator/` |

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
python -m pytest -q          # 817 tests, ~13s, no network
python -m ruff check .
```

Everything is offline and hermetic. If a test wants a browser or a live lab,
it is wrong — fix the test, not the environment.

## Layout

```
src/lab_validator/     the engine (cli, walkloop, report, runlog, browser, agent, …)
scripts/lab_*.py       operator-facing shims; each keeps its own main()
skills/lab-validator/  SKILL.md + references/ + assets/ + scripts/ + runtime/
tests/                 pytest; one file per module, all offline
targets/*.toml         lab descriptors
docs/                  approach.md (the reasoning), solution.md, cli.md, agent.md
runs/, artifacts/      generated, gitignored, may contain lab credentials
```

`cli.py` is a **dispatcher, not a rewrite**. `COMMANDS` delegates to
`scripts/`; `BUILTINS` is implemented in-process. Both are kept as data because
the help epilog, the dispatcher and the tests all read them — hardcoding the
list anywhere rots it silently.

## Trip-wires

These will fail on you if you skip them. They are not noise.

**Editing anything under `skills/lab-validator/`** → re-install, or
`test_the_installed_copy_has_not_drifted_from_the_repo` fails:

```powershell
python -m lab_validator.cli install-skill
```

**Editing anything under `src/` or `scripts/`** → re-stage the bundled runtime,
or the packaging tests fail:

```powershell
python -m lab_validator.cli prepare-skill    # then install-skill
```

`prepare-skill` stages a clean copy into `skills/lab-validator/runtime/` for
inspection; `package-skill` zips the visible skill tree and **refuses** if the
staging is stale or contains generated files (`__pycache__/`, `*.egg-info/`).
Never hand-edit `runtime/` — it is output.

**`SKILL.md` has a hard 500-line budget** (progressive disclosure).
It currently sits around 495. Adding a section means moving one out to
`references/`.

**Docs are tested against the code.** `tests/test_skill.py` scrapes every
`lab-validator <cmd> --flag` out of `SKILL.md`, `README.md` and `docs/agent.md`
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
agentskills validate skills\lab-validator
```

## The report is the product

`src/lab_validator/report.py` renders the gap analysis, and
`skills/lab-validator/assets/gap-analysis-template.md` is the template that
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
| How does the autonomous walk work? | `docs/agent.md` |
| What does the output look like? | `docs/gapanalysis.md` (real example) |
| How should a model judge a lab? | `skills/lab-validator/SKILL.md` + `references/` |

<!-- mermaid-ai-skills:start -->
## Mermaid Diagrams

When the user asks to create, edit, or visualize a diagram, follow the
instructions in `.github/instructions/mermaid.instructions.md`.
<!-- mermaid-ai-skills:end -->
