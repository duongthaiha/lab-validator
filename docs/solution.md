# How Lab Validator works

Lab Validator walks a Microsoft Learning Campus / Skillable lab as a learner,
records what actually happens, and compares that evidence with the written
instructions. Its output is an evidence-backed gap analysis, not just a test
result.

For operating the tool, see the [CLI reference](cli.md). For what a harness
driving this must guarantee, see
[`references/harness-traps.md`](../references/harness-traps.md).

## End-to-end flow

1. **Attach to a trusted browser.** `lab-validator session` starts or attaches
   to a dedicated Edge/Chrome profile over CDP. A human completes the interactive
   Microsoft sign-in; the validator never stores the Learning Campus password.
2. **Discover and resolve a lab.** `lab-validator discover --list` reads the
   signed-in enrolment page. `walk` resolves the supplied URL and title to exactly
   one enrolment and refuses ambiguous matches.
3. **Launch and identify the live client.** The tool clicks Launch, waits through
   provisioning, and attaches to the new Skillable Lab Client tab. It distinguishes
   the new client from stale tabs by identity, not by "latest tab" position.
4. **Capture the lab definition.** The instruction frame is extracted into a
   heading outline, sections, and numbered tasks. A copy is stored inside the run
   so a resumed run cannot accidentally use a later lab's corpus.
5. **Capture setup evidence.** Lab-issued credentials are placed in a run-scoped,
   gitignored vault and added to the redactor. A non-fatal preflight checks the
   environment before later failures can be misattributed.
6. **Choose scope.** The review lists every section and task count. The operator
   can walk all sections or a selected range; unselected work remains explicitly
   unknown.
7. **Walk task by task.** `walkloop.next_move()` derives the next action solely
   from persisted run state. Each numbered task must receive its own verdict before
   the loop can report and advance the section.
8. **Write reports continuously.** Every step appends evidence to `trace.jsonl`
   and refreshes the current section report. The roll-up is rendered from the
   trace, so interrupted runs remain useful and retracted findings disappear
   cleanly on re-render.

## Architecture

| Layer | Responsibility | Main code |
| --- | --- | --- |
| CLI | One front door; delegates mature commands to their existing scripts | `src/lab_validator/cli.py`, `scripts/` |
| Browser and launch | Profile management, CDP attachment, sign-in gate, enrolment resolution, launch wait | `browser.py`, `launch.py`, `discovery.py` |
| Skillable client | Instruction frame, Resources tab, lab clock, VM canvas input and capture | `labclient.py` |
| Corpus and scope | Parse headings/tasks, detect structural anomalies, select sections | `corpus.py`, `scope.py` |
| Walk controller | Deterministic state machine and coverage refusals | `walkloop.py` |
| Evidence | Append-only trace, screenshots, redaction, resumable manifest | `runlog.py`, `imaging.py`, `console.py` |
| Judgement | Finding taxonomy, ownership domain, learner-path checks | `taxonomy.py`, `learnerpath.py`, skill references |
| Reporting | Per-section reports and the final gap-analysis roll-up | `report.py` |
| Skill | Operating discipline and judgement, for whatever harness drives it | `SKILL.md`, `references/` |

The control-surface preference is **oracle first, API second, DOM third, vision
last**. Authoritative APIs are best for claims such as model availability;
Skillable's supported client API is used for lab state; DOM locators are used
where the learner has a normal web page; pixel coordinates and screenshots are
used only inside the VM canvas.

## How the CLI and skill work together

The CLI and the skill are complementary, not alternative implementations.

| Part | Owns | Does not own |
| --- | --- | --- |
| CLI | Browser attachment, lab launch, persisted run state, deterministic sequencing, evidence validation, redaction, and reporting | Deciding what a learner-visible observation means |
| Skill | Operating discipline, learner-path rules, evidence standards, finding taxonomy, and ownership judgement | Advancing run state, bypassing controls, or declaring coverage complete |
| Harness | Sequencing the loop and answering one scoped `perform` or `assess` decision at a time | Deciding coverage, editing the report directly, or reaching the result off the learner's path |

### The CLI is the executable front door

Installing the package registers `lab-validator = lab_validator.cli:main`.
`cli.py` implements the orchestration commands (`walk`, `scope`, `next`,
`debug`, `install-skill`, and `package-skill`) and dispatches the lower-level
commands (`run`, `step`, `text`, `corpus`, `discover`, `drive`, `session`, and
`auth`) to their existing scripts. This keeps one discoverable command surface
without creating a second implementation of the proven script behavior.

Commands cooperate through the run folder rather than process memory. A typical
manual path is:

```text
session -> discover -> walk -> next -> text/step -> run --report
```

`walk` performs capture and creates the run; it does not execute the numbered
tasks. `next` asks the deterministic controller for the next legal move, and
`step` carries out learner actions or records a task verdict. Because every
decision is derived from disk, the same commands resume safely after a process
or browser interruption.

### The skill can enter the solution in two ways

1. **Installed skill.** `lab-validator install-skill` copies the skill to the
   Copilot skills directory. A user can then ask
   Copilot to validate a lab; `SKILL.md` teaches it the CLI workflow and the
   judgement rules. The repository copy remains the versioned source of truth.
2. **Portable archive.** `lab-validator package-skill` writes a deterministic
   archive from the same curated file list `install-skill` uses — `SKILL.md`,
   references, assets, the CLI source, delegated scripts, packaging metadata and
   target descriptors — for any Agent Skills-compatible harness. Its bundled
   `scripts/install_runtime.py` installs the CLI and browser dependencies after
   extraction; secrets, browser profiles, tests, docs and run evidence are
   excluded.

Either way the harness drives the same commands a human would:

```text
walkloop.next_move()
  -> mechanical move (open/read/report/advance): run the command it names
  -> perform/assess: judgement, against the section text and the current screen
       -> text --segment            read the instructions
       -> text --segment --tasks    the anchors that need verdicts
       -> step --do ...             act in the lab VM, and capture it
       -> step --verdict --ref      one verdict against one task
  -> ask next_move() again; the run folder, not the transcript, says what moved
```

The indirection through the CLI is intentional. A harness gets the same
validation, run selection, trace writing and report refresh paths as a
human-operated walk, and cannot claim progress in prose: only task-scoped
evidence in the trace counts.

There used to be a third way — a bundled autonomous driver, `agent.py`, that
sequenced the loop through a Copilot SDK session and exposed exactly five
learner-visible tools. It was removed when the project became a portable skill:
it pinned the solution to one harness, and the guarantees it enforced are stated
for any harness in `references/harness-traps.md` under *The harness contract*.

### Trust boundaries

- A human completes the hardware-bound Learning Campus sign-in.
- The model receives credential labels, never raw values; role-bound sign-in
  actions resolve the correct vault entry in code.
- Tool output is redacted before it reaches the model transcript.
- Shell, host filesystem, product API, section transitions, and report controls
  are withheld from the model.
- Actions that change the lab must use learner-visible controls. Faster APIs may
  be used as read-only oracles, but not to repair or bypass the documented path.

## The run folder is the source of truth

```text
runs/<timestamp>/
  run.json                    manifest, segment state, scope, corpus identity
  outline.json                immutable task outline used by this run
  trace.jsonl                 append-only evidence records
  debug.jsonl                 per-action screen-change measurements
  credentials.json            run-scoped vault; gitignored and redacted
  images/                     numbered screenshots
  sections/<section-id>.md    current report for each walked section
  gap-analysis.md             roll-up and overall completability verdict
```

Progress does not live only in process memory. The controller reopens this
folder before deciding every move, which makes continuing and resuming the same
operation. A model saying that it completed a task does not count; a correctly
scoped trace record does.

## The deterministic walk loop

The state machine returns one of seven moves:

| Move | Meaning |
| --- | --- |
| `open` | Mark the next selected section in progress |
| `read` | Scroll/read the instructions through the learner-visible pane |
| `perform` | Execute outstanding tasks and record one verdict per task |
| `assess` | A blocker prevents execution; explicitly defer the remaining tasks |
| `report` | Render a section report current through its latest trace record |
| `advance` | Close the reported section as done or blocked |
| `stop` | Scope is complete, time is reserved for reporting, or progress is unsafe |

`open`, `read`, `report`, and `advance` are mechanical. `perform` and `assess`
need judgement. Important refusals are enforced in code:

- a section cannot complete while a numbered task has no verdict;
- a section anchor cannot stand in for all task anchors beneath it;
- a report older than the section's latest evidence must be regenerated;
- an unresolved task outline is reported as unknown, not as an empty section;
- blocked work is still assessed so dependent tasks are explicitly deferred;
- the final lab-clock reserve is protected for writing usable reports.

## What a harness must guarantee

An agent driving this uses the same state machine as the manual
`lab-validator next` workflow. The CLI owns sequencing; the agent is there for
one scoped `perform` or `assess` move at a time, working from the current
section text, the exact outstanding task anchors, a current VM screenshot,
credential labels (never values), and the judgement rules in `SKILL.md`.

Four rules were previously enforced by the removed autonomous driver, and now
have to be honoured by whatever is driving:

| Rule | Why |
| --- | --- |
| Act only through the learner's controls | shell, host filesystem or product API access lets an agent repair or bypass a defect a learner would still encounter |
| Treat the run folder, not the transcript, as progress | trace length, outstanding anchors and section status are the only things that can distinguish doing the work from describing it |
| Stop rather than grind | three unchanged turns, three repeated mechanical moves, two consecutive timeouts, a closed lab, a move ceiling, or the reporting-time reserve — each an explicit, resumable stop |
| Keep raw output out of the prompt | the CLI redacts what it writes; it cannot redact a conversation |

Section transitions and report refreshes are the controller's, driven by
`next`'s mechanical moves rather than chosen. Sign-ins use role-bound actions
(`signin:vm`, `signin:portal`) resolved against the vault in code, so no
component upstream of the CLI chooses between raw passwords. The full version,
with the incidents behind each rule, is in
[`references/harness-traps.md`](../references/harness-traps.md).

## Evidence and verdicts

Every task gets `PASS`, `BLOCKED`, `DEFERRED`, or a `LABnnn` finding code.
Findings also carry an independent ownership domain:

- `instruction`: the written procedure is wrong or stale;
- `setup`: the supplied lab environment cannot deliver the documented path;
- `undetermined`: the available evidence does not yet settle ownership.

`BLOCKED` describes execution state, not a defect by itself. A finding requires
an observed divergence and evidence. Reports therefore distinguish completed,
blocked, deferred, unselected, and never-reached work instead of treating every
absence of findings as success.

## Resume and failure model

Use the existing run folder after interruption:

```powershell
lab-validator next --run runs\<timestamp>
```

Already recorded steps and section reports are retained. The controller derives
the next move from disk and verifies the saved corpus identity before counting
task coverage. Partial coverage is reported as partial or unknown; it is never
promoted to a clean result.
