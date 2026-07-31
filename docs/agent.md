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

The two stall stops both end with the same sentence, and it is the important
one: *sections already walked keep their reports; the rest are unknown, not
correct.* A partial walk is a partial answer, never a clean bill of health.

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

`--run <folder>` drives a run that already exists instead of starting one, so an
interrupted walk resumes rather than restarting:

```powershell
lab-validator auto --run runs/2026-07-31T1448Z
```

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
```

Read the coverage table before the findings. A section with no findings may not
have been checked, and the report distinguishes the two — an absent finding is
never evidence of correctness.

The learner-path ledger is worth a second look on an agent-driven run. Where the
walk acted by a faster route than a learner has, the report says which controls
were never exercised, so "the button works" stays a claim with evidence behind
it rather than an assumption.

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

- `auto` has never been run against a **real lab**. The synthetic smoke run
  proved the SDK wiring; the `--url` path through `cmd_walk` into the agent, the
  sign-in gate and Launch automation in `launch.py`, and
  `LabClient.scroll_instructions()` have not been exercised end to end.
- Everything above the SDK boundary — the loop, both stall guards, the deny
  branch, redaction, prompt construction, credential threading — is covered by
  tests and by the smoke run.

The first live `auto --url` run is the highest-value thing left to do, and needs
a human present to sign in.
