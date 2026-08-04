# The agent that walks the lab

`lab-validator auto` walks a lab unattended. You sign in; it does the rest and
stops with a reason.

This document is for the moment *after* you start it — when it has stopped and
you need to know what that meant, when you want to know what it was and was not
allowed to do before you trust its report, or when you want to change it. For
how to run a validation at all, read the [README](../README.md). For why the
engine refuses the things it refuses, read [`approach.md`](approach.md) §2.19.

```powershell
lab-validator auto --url "<lab url>" --name "<lab title>"
```

Needs the optional extra (`pip install -e .[agent]`) and an authenticated
`copilot` CLI. Without either it stops before touching the lab and says which is
missing.

## The contract: sequencing is Python's, judgement is the model's

```
open / read / report / advance   ->  executed directly; no model is consulted
perform / assess                 ->  one scoped model turn, then ask the loop again
```

Both halves come from the same `walkloop.next_move` a human gets from
`lab-validator next`. `auto` is not a second implementation of the walk; it is
the same loop with the PERFORM moves answered by a model instead of a person.

The split is the whole design. `next_move`'s refusals were each paid for by a
wrong report — it will not advance past a task nobody judged, will not trust a
section report older than its last step, will not call a section read without a
recorded learner scroll. Hand sequencing to a model and every one of those
becomes a *suggestion* it may decline at 3am with nobody watching, while the run
still produces a confident report.

**A mechanical move cannot be skipped, because nothing is asked about it.**

### Where the skill enters

`auto` creates a Copilot SDK session and passes the repository root — which *is*
the skill directory — in `skill_directories`. The skill contributes
the learner-path operating rules, evidence standards, taxonomy, and ownership
judgement used during a model turn. It does not implement the controller.

This repository-local loading path is separate from
`lab-validator install-skill`, which copies the same files into the user's
Copilot skills directory for direct natural-language invocation. An installed
copy is not required for `auto`, and `auto` does not read it. Keeping the
repository copy authoritative means the agent code, skill instructions, and
tests are reviewed together.

The resulting call chain is:

```text
lab-validator auto
  -> cli.cmd_auto
  -> agent.walk_autonomously
  -> walkloop.next_move
  -> mechanical move, or one skill-guided model turn
  -> CLI-backed tool writes evidence
  -> fingerprint persisted run state
  -> walkloop.next_move
```

The model can follow the skill only through the tools registered for that
session. Python hooks reject every other tool, and the controller independently
checks the run folder after the turn. Instructions shape judgement; code
enforces capability and progress.

Three consequences follow, and they are the three things most worth
understanding before you read a report `auto` produced.

**A claim of progress is never believed.** Before and after every model turn the
loop fingerprints the **run folder** — steps recorded for this section, tasks
still without a verdict, section status (`agent.Fingerprint`). An identical
fingerprint means nothing happened, whatever the transcript said. A model
reporting success and a model achieving something read exactly the same; only
the folder can tell them apart.

**The loop applies that scepticism to itself.** `next_move` derives each
mechanical move from state, so a move that worked changes the state that
produced it and the next move differs. The same move coming straight back means
the command did not take. One retry absorbs a transient browser failure; three
identical moves in a row is a stuck run.

**Tools off the learner path are denied, not discouraged.** Not for safety — for
correctness. An agent with a shell will repair a broken deployment and then
report the lab as working, while the learner following the written instructions
still cannot finish it. A confidently wrong report is worse than no report,
because every artefact downstream corroborates it.

## What one move actually looks like

This is a real (one-section) run, unedited:

```
-> driving 2026-07-31T1448Z

  OPEN s01 - next unwalked section: Smoke
    run: 2026-07-31T1448Z  segment: s01  findings this step: 0  lab clock: unknown  -> sections\s01.md
  PERFORM s01 - 5 of 5 task(s) have no verdict yet. These task(s) ask for
    resource group, which this lab did not issue - that is a finding about the
    setup, not a reason to stop.
  ADVANCE s01 - section reported and complete
    run: 2026-07-31T1448Z  segment: s01  findings this step: 0  lab clock: unknown  -> sections\s01.md
  STOP  - all 1 sections have been walked or accounted for

1 model turn(s), 2 mechanical move(s), 0 stall(s). all 1 sections have been walked or accounted for
report: runs\2026-07-31T1448Z\gap-analysis.md
```

Indented one level is the loop's decision and the reason it chose it. Indented
two is what the command said. A `PERFORM` line is the only kind that costs a
model turn, and each one carries a screenshot of the VM taken immediately
before it. A longer walk interleaves `READ` and `REPORT` moves and repeats the
block per section; the shape does not change.

The prompt for a PERFORM move names the exact task anchors still outstanding
(`agent.prompt_for`). It never says "finish the section": a model told to finish
a section decides for itself what finishing means, and task-level coverage
exists precisely so that it does not. Where the loop can see an instruction
asking for a credential, it names the **label** in the move — as above — so the
model can request the value without one ever entering the prompt.

## The five controls, and the three that are withheld

`ALLOWED_TOOLS` *is* the learner path. Each entry is something a human sitting
in front of the lab could do, and there is deliberately no route to the
product's API, the host shell, or the file system behind the VM.

| Tool | What it does | Runs |
| --- | --- | --- |
| `lab_instructions` | the section's instruction text, as written | `text --segment` |
| `lab_tasks` | the task anchors under the section | `text --segment --tasks` |
| `lab_act` | act in the lab VM: click, type, scroll, screenshot | `step --do ...` |
| `lab_record` | one verdict against one task anchor | `step --verdict --ref` |
| `lab_look` | capture the VM and return the image | `step --do shot` |

Every one shells out to the real `lab-validator` rather than importing the
scripts. The CLI is the surface the walk was proven through — it refreshes the
section report after each step, resolves the run folder the same way, applies
the same validation. A second path would have its own bugs and the agent would
be its only caller.

`Tools` has three more methods that the model never sees: `open_segment`,
`close_segment`, `refresh_report`. They move the run through its states, and a
model that can open, close or re-report a section can also skip one. The loop
calls them; nobody asks permission. `test_every_allowed_tool_is_one_the_agent_actually_builds`
asserts set equality between `ALLOWED_TOOLS` and the tools actually registered,
so neither list can quietly grow.

Anything else is refused by `on_pre_tool_use` with a reason naming the five that
remain. Tool output is scrubbed on the way back through the run's `Redactor`,
primed from the vault, so lab-issued credentials never enter the transcript —
and the model asks for one by label (`cred:SCOPE/LABEL`) rather than ever seeing
a value.

### Sign-ins are bound in code, not chosen by the model

`lab_act` takes `signin:vm` and `signin:portal`, and they behave unlike every
other action: **there is no parameter through which the wrong credential can be
requested.** The model names the *login* it can see; `vault.signin()` resolves
the credential from the lab's own scopes.

This is deliberate asymmetry. A lab hands out several rows called `Username`
and `Password` in different scopes, indistinguishable by type and often by
appearance. Given a free choice the model will pick the one its *task* mentions
rather than the one its *screen* wants — which is exactly what happened in the
second live run, thirteen times in a row. See approach.md §2.23.

The prompt therefore lists every credential the lab issued annotated with the
sign-in it serves (`[signin:vm]`, `[signin:portal]`), not just the ones the
instruction text asked for. Labs routinely document the cloud login and never
mention the machine login the learner meets first; a model told about one
family reaches for that family.

**The order is bound too.** `signin:portal` is refused until a `signin:vm` has
run in this walk. Everything the agent can reach — browser, portal, terminal —
is inside the VM, so a cloud sign-in is unreachable until the machine is
unlocked, and the request cannot be correct whatever the screen shows. The
guard reads the run's trace rather than memory, so `auto --run <folder>`
inherits it. This exists because binding the credential fixed only half the
problem: the next live run *did* call `signin:`, and asked for `portal` while
looking at a Windows lock screen, because its task said "Sign in to Azure
Portal".

**A sign-in never records `PASS`.** It records `DEFERRED`, and that is not
caution — it is the only honest verdict available. Measured on this lab's own
frames:

| transition | delta | outcome |
| --- | --- | --- |
| lock screen → *"The password is incorrect"* | 0.80 | **failed** |
| lock screen → *"Welcome"* | 0.23 | **succeeded** |
| lock screen → *"Welcome"* | 1.20 | **succeeded** |

A success can score below a failure, because both screens are the same flat
blue with the same avatar and the same account name and differ by a line of
text. So the delta is measured and written into the note for audit, decides
nothing, and the note names what does settle it: capture the screen and read
it — a password box still showing, or an error message, means it failed.

That division is deliberate. The model reads screens well; it transcribed *"The
password is incorrect. Try again."* correctly on the run that got the
credential wrong. What it cannot do is choose the credential or the order. So
perception stays with the model and binding stays in code.

It records only what it can prove. A screen that moved shows the input landed;
it does **not** show the credential was accepted, because a rejection repaints
too — *"the password is incorrect"* is a repaint. Telling those apart by
magnitude would be an uncalibrated threshold, so the note says so and points at
the next capture. A screen that did not move at all records `BLOCKED`, not a
finding: the keystrokes reached nothing, which is a fact about the console, not
about the lab's credentials.

Roles are resolved by `vault.role_of()`, which refuses a scope matching two
roles or none: `Azure VM credentials` is genuinely both, and picking one would
be a guess with a type signature.

## Why it stopped

Every exit prints a sentence. Match its opening words here.

| It said | What happened | What to do |
| --- | --- | --- |
| `all N sections have been walked or accounted for` | the walk finished | read the report |
| `... but N task(s) ... have no recorded verdict` | finished, but with holes | those tasks are **unknown, not correct** — the report names them |
| `N min left on the lab clock ...` | stopped to reserve write-up time | expected; the report is complete for what was walked |
| `<move> <segment> came back N times and the run did not move on` | a mechanical command is failing silently | the message quotes what that command last printed — that is the diagnosis, not a hint to reproduce it |
| `3 consecutive turns changed nothing in the run folder` | the model is not making progress on a named task | the message names the outstanding task; open that section by hand |
| `reached the N-move ceiling before the lab ended` | budget exhausted | re-run with `--run <folder>` to continue, or raise `--max-turns` |
| `2 model turns in a row outlasted the Ns budget` | the model could not answer twice running | raise `--turn-timeout` if the moves are simply long; the run is resumable with `auto --run <folder>` |
| `all N selected sections are accounted for ... Separately, M were not selected` | a scoped walk finished its scope | expected; the report says `**Scoped run.**` and can never answer YES. Widen with `lab-validator scope --run <folder> --sections ...` and re-run `auto --run <folder>` |
| `The lab has closed.` | the lab instance ended while the walk was still running | **not a tool failure and not a lab defect.** Sections already walked keep their reports; the rest are **unknown, not correct**. Launch the lab again and resume with `auto --run <folder>` |
| `signin:<role> refused: ...` | the vault could not bind that login to exactly one credential pair | **not a guess to fix by retrying.** The message names what it found: no credential for that role, two that match, or half a pair. Check the Resources tab in `credentials.json`; if the lab genuinely issues an ambiguous scope, that is a finding about the lab |
| `signin:<role> refused: these keystrokes go to the VM ...` | a cloud sign-in was requested before the VM was unlocked | **expected, and not a failure.** Nothing was typed. The agent should call `signin:vm` first; if it keeps asking for the portal, the screen it is looking at is a Windows lock screen and its task text is misleading it |

A **single** slow turn is not a stop. It prints `(that turn outlasted its Ns
budget - timeout 1/2; anything it recorded is kept)` and the walk carries on:
the steps that turn recorded are already on disk, and the loop takes its next
move from the run folder rather than from the model's memory, so a long turn
costs time and nothing else. Two in a row is different — that is a model which
cannot answer, and an unattended walk has nobody to notice. Before this
distinction existed the first live run ended in a raw `TimeoutError` traceback
whose last frame was inside the SDK, which read as *the tool crashed* while the
agent had in fact been signing into a portal correctly for fifteen minutes.

The two stall stops both end with the same sentence, and it is the important
one: *sections already walked keep their reports; the rest are unknown, not
correct.* A partial walk is a partial answer, never a clean bill of health.

The closed-lab stop deserves its own note, because it is the one that looks
like nothing. A Skillable lab that ends keeps its tab, its tab title, its
`/LabClient/<guid>` URL and all three of its frames; only the top-level body
text changes, to *Lab Closed*. Every identity check the tool has still passed,
and on the run that found this the walk carried on for four more steps — filing
a **major** finding that the instruction pane would not scroll (the pane was
dead, not defective) and three `PASS` steps for work done against nothing.
Every step now asks whether there is still a lab before it records anything,
and the loop stops on the first refusal rather than grinding out its stall
ceiling. See `docs/approach.md` §2.22.

The commonest cause of the repeat stop, by some distance, is the controller
browser not being there — the first real run stopped on a repeated `READ` with
`Nothing is listening on http://127.0.0.1:9222` quoted three times.

## Why it would not start

`AgentUnavailable` is raised before the lab is touched, and exits `3`.

| Cause | Fix |
| --- | --- |
| SDK not installed | `pip install -e .[agent]`, then check `copilot --version` |
| model name not available | `--model auto` (the default) lets the CLI choose |
| CLI not authenticated | run `copilot`, then `/login` |
| anything else | the original error is passed through verbatim — guessing a cause would be worse than admitting we do not know it |

In all four cases the fallback is the same and is printed with the error: walk
it yourself with `lab-validator next`, which asks the same loop for the same
moves and needs no model at all. The SDK is an optional extra precisely so a
missing one degrades to "walk it by hand" rather than taking the CLI down.

## Budgets, and resuming

An unattended walk that cannot finish should stop rather than spend.

| Flag | Default | Why that number |
| --- | --- | --- |
| `--max-turns` | 200 | mechanical moves and model turns share the ceiling, so a loop that thrashes cannot run forever |
| `--turn-timeout` | 900s | a lab step is not a chat reply; the SDK's own default of 60s is far too short |
| `--model` | `auto` | pinning a model name means eventually validating a lab with a dependency that has itself retired |
| `--sections` | all | the cheapest budget of the four: walking 3 sections of 23 costs a twentieth of the time. Takes the numbers from the review's `#` column (`4`, `1,4,7`, `4-6`) or the section ids (`s04`, `s04..s06` — ids range with `..` because they contain hyphens) |

`--sections` is the one budget that changes what the report *means* rather than
how far it gets, so it is also the one the report announces. A scoped `auto` run
prints `**Scoped run.**` beside the verdict and cannot return YES — see
[Reviewing what you got, and choosing what to walk](../README.md#reviewing-what-you-got-and-choosing-what-to-walk).

Without `--sections`, `auto` walks everything. It never prompts: stdin under the
SDK is not a terminal, and a prompt nobody can answer would hang an unattended
run forever. The manifest records `how: "default"` in that case rather than
`"prompt"`, so a walk nobody scoped is never later read as a walk somebody
approved.

`--run <folder>` drives a run that already exists instead of starting one, so an
interrupted walk resumes rather than restarting:

```powershell
lab-validator auto --run runs/2026-07-31T1448Z
```

To review and narrow first, then let the agent walk only what you chose:

```powershell
lab-validator scope --run runs/2026-07-31T1448Z                    # read the review
lab-validator auto  --run runs/2026-07-31T1448Z --sections 4-6
```

`scope` is worth running before `auto` for a reason beyond the review itself:
section ids are only knowable *after* a lab has been captured, so on a first run
there is nothing you could put in `--sections` yet. `scope` prints them — with a
`#` column whose numbers `--sections` also accepts.

Without `--run`, `auto` starts a walk and then identifies the run it just made
by **set difference** against what existed before — not by taking the newest
folder. Clock skew and a parallel walk are exactly the cases where "latest"
quietly hands you somebody else's lab.

## Reading what it produced

Nothing about the output is special to `auto`. It is the same run folder, the
same per-section reports written as the walk happens, the same roll-up:

```
runs/<timestamp>/gap-analysis.md      roll-up, links to every section report
runs/<timestamp>/sections/<id>.md     one report per section
runs/<timestamp>/images/              numbered evidence
runs/<timestamp>/trace.jsonl          append-only, one record per step
runs/<timestamp>/debug.jsonl          what each action did to the screen
```

Read the coverage table before the findings. A section with no findings may not
have been checked, and the report distinguishes the two — an absent finding is
never evidence of correctness.

The learner-path ledger is worth a second look on an agent-driven run. Where the
walk acted by a faster route than a learner has, the report says which controls
were never exercised, so "the button works" stays a claim with evidence behind
it rather than an assumption.

`debug.jsonl` is deliberately **not** part of the trace. The trace is what the
report is built from and what a human is asked to believe; padding it with
per-action pixel deltas would make the evidence harder to read in order to make
debugging easier. Read it with `lab-validator debug --run <folder>`, which also
works on runs recorded before the file existed, by measuring the images on disk.

### When the walk is doing things and nothing is happening

The one to know about, because it looks like progress. A live run recorded
`PASS` on step after step while typing URLs at a Windows desktop with no browser
open. Every action was dispatched, so every action succeeded; none of them was
*the screen changed*.

After three captures where input went in and nothing came back, the tool now
tells the model exactly that, names the actions that achieved nothing, and sends
it to look at the screen. It also lists what a still screen can mean — wrong
surface, wrong focus, wrong coordinates, dead console — and **picks none of
them**, because from a delta alone they are indistinguishable. The first version
of this feature did pick one, said the console had frozen, and was wrong.

It is an observation, never a verdict: the walk is not stopped and no finding is
recorded. A screen that will not move is a fact about the harness or about the
walk, not about the lab's instructions.

```powershell
lab-validator debug --run runs/<timestamp> --stuck    # only the ineffective actions
```

## Changing it

**Before adding a tool, ask what it makes reachable.** The deny list is not a
security boundary; it is the reason the report can be believed. A tool that lets
the agent reach a result by a route the learner does not have converts a finding
into a success, silently. If you add one, add it to `ALLOWED_TOOLS` in the same
change — the set-equality test will fail otherwise, which is the point.

Put constraints in the **tool description**, not only in the prompt or the
skill. A description is read at the moment of choosing and competes with
nothing; a rule in the prompt competes with everything else in the context. The
verdict codes are generated into `RecordP.verdict`'s description from
`taxonomy.py` by `_verdict_menu()` for exactly this reason, and are never
transcribed.

**Mutation-test every guard you touch.** Break it deliberately, confirm a test
fails, restore. Two tests in this file were found vacuous that way — one
asserted a key that is always present, another passed by luck of alphabetical
ordering. Both looked fine. If a mutation does not change the test outcome, the
test is decoration.

Two footguns specific to this module:

- `from __future__ import annotations` makes type hints strings, and the SDK's
  `define_tool` resolves them with `get_type_hints` against **module** globals.
  Parameter models must stay at module scope. Declared inside `build_tools`,
  every tool fails to register with `NameError` — and nothing evaluates the
  annotation until a session actually starts, so the test suite stays green.
- `drive()` takes `ask` as an injected callable so the loop is testable with no
  SDK and no browser. Keep it that way, and keep `_do_mechanical` calling only
  `Tools` methods — a second route to the run folder is a route that cannot be
  substituted in a test.

## Verifying a change without a lab

Every test in `tests/test_agent.py` injects a fake `ask` and never reaches the
SDK, which is exactly why none of them noticed that no tool could register at
all. **A seam that is always stubbed is a seam nobody has tested.**

So there is a smoke run: it builds a one-section run from whatever corpus is on
disk, records the learner scroll the loop insists on, and drives `auto` against
it with no lab and no browser — session start, tool registration, hook shape,
one real model turn, one recorded finding.

```powershell
python scripts/agent_smoke.py --drive
```

> **Hold the model constant when you are comparing.** `--drive` defaults to
> `auto`, so Copilot picks the model, and the pick moves with the prompt.
> Adding five lines of *unrelated* text to the Rules block was measured
> flipping this fixture from a clean walk to three stalls; the same edit under
> a pinned model walked cleanly both ways. So after editing the prompt, run
> `--drive --model <name>` on your version *and* on the one you started from
> before concluding anything. An unpinned stall prints a note saying exactly
> this, because the natural reading — "my change broke it" — is wrong often
> enough to cost an afternoon.

Run it after any change to the SDK half of `agent.py`, and after any SDK
upgrade.

It has now found five defects, and the fifth arrived on the run that packaged
it: `_cli` told the child process to write UTF-8 while decoding with the
parent's locale codec, so one em-dash in an instruction killed subprocess's
reader thread and `stdout` arrived **empty**. Empty, not an error — the tool
returned "" and the model judged a section it had never seen. With it fixed the
same fixture recorded a `LAB002` instruction defect it could only find by
reading, so the bug had been suppressing the cheapest and most reliable class of
finding this project has.

The script creates its own run and primes only the run it created; it takes no
argument naming an existing one, because that priming step records a scroll the
walk did not really take — honest in a fixture, evidence-destroying anywhere
else. Fixtures are stamped in the manifest and swept on the next invocation.

`lab_act` will fail during the smoke run, because there is no lab client. That
is useful rather than a nuisance: a tool erroring is precisely what a blocked
lab looks like, and the correct outcome is a `BLOCKED` finding recorded against
the task — with the tasks that depended on it `DEFERRED` rather than lazily
blamed on the same cause.

## What is still unproven

Stated plainly, because this project's whole argument is that unverified is not
the same as working:

- `auto` has now been run against a **real lab**, and that run is what produced
  the timeout stop above and the corrected learner scroll. `walk --url` is proven
  end to end: enrolment resolution, Launch (which turns out to be two-stage —
  `/Setup/<guid>` self-advances to `/LabClient/<guid>` after ~4 minutes),
  credential capture, preflight, review, scoping and the first agent moves.
- **A section completing under `auto` against a real lab** is the piece still
  outstanding. The runs so far ended on budget, not on error.
- Everything above the SDK boundary — the loop, both stall guards, the timeout
  guard, the deny branch, redaction, prompt construction, credential threading —
  is covered by tests and by the smoke run.

The five defects the first live run exposed, and why none of the 600-odd tests
could see them, are written up in
[approach.md §2.21](approach.md#221-the-first-live-run-a-tool-that-invents-defects-is-worse-than-one-that-finds-none).
The headline is worth repeating here: the tool filed a confident `major` finding
about the *product* that was not true. Verify a first-run code path's first
finding before publishing it.
