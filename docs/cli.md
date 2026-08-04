# CLI reference

`lab-validator` is the supported front door for discovery, capture, walking,
debugging, and reporting. Run `lab-validator` to list commands and
`lab-validator <command> --help` for the current options.

## Installation

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m playwright install chromium
```

Autonomous walking also needs the Copilot SDK extra and an authenticated
GitHub Copilot CLI:

```powershell
pip install -e ".[agent]"
copilot
# use /login if the CLI is not already authenticated
```

## How the front door is assembled

The package entry point is `lab_validator.cli:main`. It provides one command
surface over two implementation styles:

- `walk`, `auto`, `scope`, `next`, `debug`, `install-skill` and `package-skill`
  are orchestration commands implemented in
  `src/lab_validator/cli.py`;
- `run`, `step`, `text`, `corpus`, `discover`, `drive`, `session`, and `auth`
  delegate to the established scripts under `scripts/`.

The dispatcher does not duplicate those scripts. It imports their `main()`
functions and passes through the remaining arguments, so the standalone scripts
and the `lab-validator` front door use the same implementation. Run
`lab-validator` for the command list and `lab-validator <command> --help` for the
parser-backed options.

The commands share a persisted run folder. `walk` captures and scopes a lab,
`next` selects the next legal move, `step` records learner actions and verdicts,
and `run --report` renders the trace. `auto` drives that same sequence; it does
not maintain a separate agent-only run format.

## Typical workflows

Choose the workflow by who will answer the judgement moves:

| Need | Workflow |
| --- | --- |
| A human will perform and assess each task | `walk`, then repeat `next`, `text`, and `step` |
| Copilot should perform and assess tasks | `auto --url ...` |
| Capture now and decide later | `walk`, then `auto --run ...` or the manual loop |
| Continue an interrupted run | `next --run ...` or `auto --run ...` |
| Let Copilot recognize a natural-language validation request | `install-skill`, then invoke the installed skill |

Start the browser once, sign in manually, discover the live enrolment, and let
the autonomous agent walk it:

```powershell
lab-validator session --launch --profile "<Edge profile>"
lab-validator discover --list
lab-validator auto --url "<URL printed by discover>" --name "<exact lab title>"
```

Capture first and walk manually:

```powershell
lab-validator walk --url "<lab URL>" --name "<exact lab title>"
lab-validator next --run runs\<timestamp>
lab-validator text --run runs\<timestamp> --segment s01 --tasks
lab-validator step --run runs\<timestamp> --segment s01 --ref <task-anchor> `
  --do shot --note "What the learner observed" --verdict PASS
lab-validator run --run runs\<timestamp> --report
```

Resume an interrupted autonomous run:

```powershell
lab-validator auto --run runs\<timestamp>
```

Manual and autonomous walking use the same deterministic controller and
artifacts. Switching from `next`/`step` to `auto --run` does not restart the lab
or discard recorded evidence.

## Command summary

| Command | Purpose |
| --- | --- |
| `walk` | Sign-in gate, resolve and launch a lab, capture instructions/credentials, run preflight, create and scope a run |
| `auto` | Start or resume a run and answer judgement moves with the constrained agent |
| `scope` | Review captured sections; optionally widen the selected scope |
| `next` | Print the next deterministic move and its reason |
| `debug` | Explain what recorded actions changed on screen |
| `run` | Start, inspect, finish, retract, and render runs |
| `step` | Execute ordered learner actions and append evidence/verdicts |
| `text` | Print a section or its task anchors from the saved corpus |
| `corpus` | Extract or inspect the instruction outline and anomalies |
| `discover` | List signed-in enrolments or scaffold a target descriptor |
| `drive` | Low-level Skillable instructions, credentials, and VM controls |
| `session` | Create/attach browser profiles and inspect tabs |
| `auth` | Manage the encrypted storage-state fallback |
| `install-skill` | Install the repository's judgement skill for Copilot |
| `package-skill` | Build one portable `.skill` archive for another agent harness |

## Primary commands

### `walk`

```powershell
lab-validator walk --url <url> [--name <title>] [--sections <selection>] `
  [--agent <name>] [--signin-budget <seconds>] `
  [--launch-budget <seconds>] [--client-budget <seconds>] [--port <number>]
```

`--url` is required. `--name` disambiguates pages containing several
enrolments. `--sections` accepts `all`, row numbers (`4`, `1,4,7`, `4-6`), IDs
(`s04`), or an ID range (`s04..s06`). If omitted in a terminal, the command
prints a review and prompts; non-interactive runs select all sections.

The command creates a run but does not perform its tasks. Continue with `next`
or `auto --run`.

### `auto`

```powershell
lab-validator auto --url <url> [walk options] [agent options]
lab-validator auto --run <folder> [--sections <selection>] [agent options]
```

Agent options:

| Option | Default | Meaning |
| --- | --- | --- |
| `--model` | `auto` | Copilot model; `auto` avoids pinning a retiring name |
| `--max-turns` | `200` | Shared ceiling for model and mechanical moves |
| `--turn-timeout` | `900` | Seconds allowed for one model turn |
| `--runs` | `runs` | Root used when a new run is created |

With `--run`, `auto` resumes the persisted state. Without it, `--url` is
required and `auto` first performs the complete `walk` capture flow. The command
exits before touching a lab if the optional SDK is unavailable.

### `scope`

```powershell
lab-validator scope [--run <folder> | --runs <root>]
lab-validator scope --run <folder> --sections <selection>
```

Without `--sections`, this is read-only and writes/prints `review.md`. With a
selection it can widen the run, but it cannot remove in-progress or completed
evidence. Re-render `gap-analysis.md` after changing scope.

### `next`

```powershell
lab-validator next [--run <folder> | --runs <root>] [--minutes <remaining>]
```

Prints progress plus the next `OPEN`, `READ`, `PERFORM`, `ASSESS`, `REPORT`,
`ADVANCE`, or `STOP` move. `--minutes` lets the controller enforce its reporting
reserve. If neither run option is supplied, the latest run under `./runs` is
used.

### `step`

```powershell
lab-validator step --segment <id> [--run <folder>] [--label <name>] `
  [--do <action> ...] [--note <text> --verdict <value> --ref <task-anchor>] `
  [--severity <level>] [--domain instruction|setup|undetermined]
```

Repeat `--do` to preserve action order. Common actions are:

| Action | Effect |
| --- | --- |
| `click:X,Y`, `dblclick:X,Y`, `move:X,Y` | Pointer input in VM coordinates |
| `focus` | Focus the VM console |
| `type:TEXT`, `key:KEY` | Keyboard input |
| `cred:SCOPE/LABEL` | Type a vault credential without exposing its value |
| `signin:vm`, `signin:portal` | Use the role-bound machine or cloud sign-in |
| `wait:MS`, `until:connected`, `until:quiet:MS` | Wait for a condition |
| `shot` | Capture evidence |
| `dialog` | Read/dismiss the Skillable client dialog |
| `read`, `page:N` | Read/position the learner instruction pane |

Use `--start-segment` and `--end-segment done|blocked|skipped` only in a manual
walk; `auto` performs these transitions mechanically. A verdict must use the
numbered task's anchor from `text --tasks`, not the containing section anchor.

### `run`

```powershell
lab-validator run --status [--run <folder>]
lab-validator run --report [--run <folder>]
lab-validator run --finish <status> [--run <folder>]
lab-validator run --retract <sequence> --note <reason> [--run <folder>]
lab-validator run --targets
lab-validator run --check-target <slug>
```

`--report` regenerates section reports and `gap-analysis.md` from the trace.
`--retract` withdraws a finding without rewriting append-only history.
`--start` remains available for creating a run from an already-open lab;
normally `walk` is the safer end-to-end entry point.

### `debug`

```powershell
lab-validator debug [--run <folder> | --runs <root>] `
  [--tail <count>] [--stuck] [--out <path>]
```

Reads `debug.jsonl` or reconstructs screen deltas from saved screenshots.
`--stuck` shows only actions that caused no visible change. The result is a
diagnostic observation, not an automatic defect verdict.

## Supporting commands

### `text` and `corpus`

```powershell
lab-validator text --segment <id-or-prefix> [--run <folder>] [--tasks]
lab-validator corpus --extract
lab-validator corpus --segments
lab-validator corpus --anomalies
lab-validator corpus --outline
lab-validator corpus --section <id-or-anchor> [--tasks]
```

`text` reads the immutable corpus associated with a run. `corpus` inspects or
refreshes the shared instruction capture and is mainly useful during
development and diagnosis.

### `discover`

```powershell
lab-validator discover --list [--url <training-page>]
lab-validator discover --scaffold <enrolment-id> [--slug <slug>] [--overwrite]
```

Discovery uses the attached signed-in browser. Scaffolding writes only observed
target metadata and leaves unresolved expectations explicit.

### `session`

```powershell
lab-validator session --list-profiles
lab-validator session --launch --profile "<profile>"
lab-validator session --status
lab-validator session --signin msa
lab-validator session --goto <url>
lab-validator session --links
lab-validator session --dump
lab-validator session --probe
lab-validator session --shot
```

Use `--tab`, `--all-tabs`, `--port`, and `--browser edge|chrome` to select the
attachment target. The dedicated profile must remain open while walking.

### `drive`

```powershell
lab-validator drive --state
lab-validator drive --creds
lab-validator drive --page <number>
lab-validator drive --screen [--label <name>]
lab-validator drive --click X,Y
lab-validator drive --type <text>
lab-validator drive --type-cred <scope/label>
lab-validator drive --key <key> [<key> ...]
```

This is the low-level diagnostic surface. Prefer `step` during a validation
because it records ordered actions as evidence and refreshes reports.

### `auth`

```powershell
lab-validator auth
lab-validator auth --status
lab-validator auth --clear
```

This manages the DPAPI-encrypted Playwright storage-state fallback. The preferred
interactive path is the attached dedicated browser profile.

### `install-skill`

```powershell
lab-validator install-skill [--into <skills-directory>] [--dry-run]
```

Copies the skill — `SKILL.md`, `references/`, `assets/` and the CLI runtime that
backs them — into the Copilot skills directory. The repository copy remains the
source of truth. This installed copy is for direct Copilot skill
invocation. `lab-validator auto` instead loads the repository skill directly
through the Copilot SDK, so installing the skill is not an `auto` prerequisite.

The skill does not replace the executable: it teaches Copilot when and how to
call the CLI and how to judge observations. Browser control, run transitions,
evidence validation, and reporting remain enforced by Python.

### `package-skill`

```powershell
lab-validator package-skill
lab-validator package-skill --out <path\lab-validator.skill>
```

The repository *is* the skill, so packaging is a publish rather than a stage:
`install-skill` and `package-skill` are two writers over one curated file list,
which is why the installed copy and the archive are byte-identical and neither
can drift from the code. To see exactly what will be published without building
anything, run `lab-validator install-skill --dry-run`.

The default package output is `dist\lab-validator.skill`. `package-skill`
validates the frontmatter, the progressive-disclosure limit, and that every
referenced file resolves; it refuses symlinks rather than following them out of
the tree. The deterministic ZIP-format archive prints its SHA-256 digest for
transfer verification.

The archive contains one top-level `lab-validator` directory:

```text
lab-validator/
  SKILL.md
  references/
  assets/
  scripts/
    install_runtime.py
    lab_*.py
  src/lab_validator/
  targets/
  pyproject.toml
```

Repository-only material — `tests/`, `docs/`, `README.md`, git metadata — is
never published.

Use the receiving agent harness's `.skill` import command where available.
Otherwise, extract the archive into its configured skills directory; `.skill` is
a ZIP file with a different extension. Then install its bundled runtime:

```powershell
python <skills-dir>\lab-validator\scripts\install_runtime.py
```

The installer installs the local Python project with the agent extra and then
installs Playwright Chromium. Pass `--without-agent` for a manual-only CLI or
`--skip-browser` when the browser is already provisioned. Python 3.11+ is still
required. The archive intentionally excludes browser profiles, credentials,
run evidence, test fixtures, and development tooling.

## Generated artifacts

Each run is independently resumable and auditable:

| Path | Purpose |
| --- | --- |
| `run.json` | Manifest, selected scope, corpus identity, and section state |
| `outline.json` | Immutable task outline captured for this run |
| `trace.jsonl` | Append-only learner actions, evidence, and verdicts |
| `debug.jsonl` | Measured screen change for recorded actions |
| `credentials.json` | Run-scoped credential vault; gitignored and redacted |
| `images/` | Numbered screenshots used as evidence |
| `sections/*.md` | Current per-section reports |
| `gap-analysis.md` | Coverage-aware roll-up and completability verdict |

Commands select an explicit `--run`, a `--runs` root, or the latest unambiguous
run according to their parser. If selection is ambiguous, the CLI refuses to
guess.

## Exit and recovery behavior

Argument and run-selection errors return a non-zero exit and name the ambiguity
instead of guessing. Agent startup failures explain whether the SDK, model, or
Copilot authentication is missing. Operational stops preserve the run folder;
resume with `next --run` or `auto --run`. Read the coverage table before treating
an absence of findings as success.
