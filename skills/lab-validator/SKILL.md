---
name: lab-validator
description: "Walk a hands-on lab (Microsoft Learning Campus / Skillable) as a simulated learner in a real browser, doing what the instructions say, and report every place reality has drifted from the text — retired models, renamed UI, moved features, dead links, defective sample code — and every place the lab environment itself is broken. The human signs in once; the agent does the rest. Triggers: 'validate this lab', 'walk this lab', 'lab gap analysis', 'check whether these lab instructions still work', 'has this lab drifted', 'test this Skillable lab', 'simulate a learner doing this lab'."
---

# Lab Validator

Drive a browser through a hands-on lab the way a learner would, and produce a
gap analysis: an evidence-backed list of every place the instructions no longer
match the product, plus a verdict on whether a learner can finish at all.

**This is a differ, not a test runner.** There is no pass/fail suite to go
green. The deliverable is a report someone can act on, and the durable asset is
the recorded trace of what was observed.

## When to use
- A lab is about to be delivered and nobody has walked it since the last product release.
- A learner or trainer reports "step 12 doesn't work" and you need the full picture.
- A model, SKU or portal blade was retired and you need to know which labs it breaks.
- Someone hands you a Learning Campus / Skillable URL and asks "is this still good?"

## When *not* to use
- To check a single factual claim ("is `gpt-4-32k` retired?"). Query the Azure
  model-lifecycle API directly — a whole lab walk is hours and this is seconds.
- To fix the lab. This reports; it does not edit lab content.

## Prerequisites
- A clone of the `lab-validator` repo, installed: `pip install -e ".[dev]"`.
- A browser profile the tooling can attach to (see Step 1). **Edge 136+ refuses
  `--remote-debugging-port` on the default profile**, so a dedicated clone is required.
- **A human available for exactly one gesture: the sign-in.** It is hardware-bound
  (Windows Hello / FIDO) and deliberately un-automatable. Everything after it is not.
- The lab URL and the lab's title.

---

## Step 1 — Attach to a browser

```powershell
lab-validator session --list-profiles
lab-validator session --launch --profile "<your profile>"
```

This clones the named profile (allow-list only, ~6 MB rather than ~1.6 GB) and
starts it with CDP enabled. Leave it running for the whole walk.

> **Never force-restart this browser mid-run.** The platform session is
> memory-only and the lab-client URL returns *Access Denied* when loaded
> directly, so a restart costs a human sign-in and can end the run.

## Step 2 — Start the walk

```powershell
lab-validator walk --url "https://mslearningcampus.com/ClassEnrollment/<id>" `
                   --name "<the lab's exact title>"
```

`walk` navigates, **blocks until the human has signed in** (15 min budget, with
heartbeats), resolves the URL and name to exactly one enrolment, clicks Launch,
waits for the lab client to actually answer, extracts and segments the
instructions, opens the run folder, and captures the lab's own credentials.

Two behaviours to expect and not "fix":

- **Ambiguity stops the run.** If `--name` matches more than one enrolment it
  prints candidates and exits 2. Walking the wrong lab yields a report full of
  findings that all look plausible — the worst possible output.
- **`LAUNCH NEEDED` is not an error.** The Launch control is countdown-gated and
  sometimes `display:none`. Ask the human to click it; the run waits.

If the lab is already open in the browser, use `lab-validator run --start` instead.

## Step 3 — Read the setup preflight before you trust anything

`walk` runs an environment check as segment 0 and writes `<run>/preflight.md`.
Read it. It is checking the class of defect that otherwise gets found late and
misattributed: endpoints of the wrong *kind*, unreplaced placeholders, a shipped
config that disagrees with what the Resources tab just issued.

- **Failures do not stop the run** — they make every later failure attributable.
  Record them as findings with `domain=setup`, then carry on.
- **A clean preflight is not a pass.** Its last section lists what it could not
  check — model identity, promised resources, VM baseline. Those remain open
  questions and belong in the coverage table, not in silence.

## Step 4 — Read what the lab actually asks for, before doing anything

```powershell
lab-validator next                            # what to do now, and why
lab-validator run --next                      # the next unwalked section
lab-validator text --segment s04 --tasks      # the numbered tasks in it
lab-validator text --segment s04              # the full text
```

`next` is the loop. Ask it after every step; it reads the run folder and nothing
else, so it is also how you resume a walk that was interrupted. It will not let
you advance past a task nobody judged, and when it stops it tells you what is
still unaccounted for.

It also names the lab-issued values each task is asking for, so you do not have
to spot them:

```
task: #4-set-the-values   [api key -> Azure/API Key; endpoint -> Azure/Endpoint]
task: #5-sign-in          [username -> NOT ISSUED by this lab]
```

Type a satisfied one with `--do 'cred:Azure/API Key'` — never by hand, and never
by pasting the value into a note. **An ask marked `NOT ISSUED` is a finding**
(`LAB002`, `domain=setup`): the instruction wants something this lab never handed
out, which is the learner's dead end, not yours.

Read the whole section first. Do **not** work from the task list alone —
prerequisites, warnings and "if you see X, do Y" notes live in the prose, and
missing one produces a false finding.

Reading by API is a **bypass**: it is faster and exact, but it cannot see a
broken instructions pane. Scroll it the way a learner does at least once per
run, so the pager's blind spot is closed by observation rather than by
assumption:

```powershell
lab-validator step --segment s04 --label read-instructions --do read
```

If the pane does not move, that is a `LAB003 / domain=setup` finding recorded
automatically — the lab is unreadable, which gates everything after it.

## Step 5 — Do the work, in the learner's path

```powershell
lab-validator step --segment s04 --label deploy-gpt4o `
  --do click:820,410 --do 'type:gpt-4o' --do key:Enter `
  --do until:quiet:4000 --do shot
```

Actions run **in the order given**, so a click that must land before typing does.

**Interaction rule: act through the learner's path, observe through the API.**
Click visible controls and type into focused fields. Use `window.api.v1` for
navigation bookkeeping and reading state — never to perform an action the
learner is told to perform by hand. A broken scroll, a dead button, an input
that rejects paste: none of those are visible to a validator that shortcuts.

Every action is recorded against the capability it used, and the run report
names any bypass whose learner-path equivalent was never exercised. Treat that
list as coverage, not as a scolding: it says which controls the run has no
opinion about.

**Do the work; do not check reachability.** Reaching the page that contains the
button proves nothing. Press the button and read the artifact it was supposed to
produce. The most dangerous lab defects are steps that *succeed while failing*.

## Step 6 — Record a verdict for each instruction

```powershell
lab-validator step --segment s04 --label task2-deploy --verdict LAB001 `
  --domain setup --severity critical `
  --ref "#2-deploy-gpt-4o-model" `
  --note "Task 2 says 'leave the defaults and click Deploy'. Deployment is refused: 'ServiceModelDeprecating ... cannot be used for new deployments'. Third independent observation, on a fresh lab instance and a new subscription, so this is not a stale environment."
```

`--ref` anchors the finding to the instruction it disputes, so a reader can go
straight to the text in question.

**Use the task's own anchor, not the section's.** Coverage is counted per task,
and a section reference is refused — one would vouch for every task under it,
which is how a section reports clean with a task nobody did. `lab-validator
text --segment s04 --tasks` prints the anchors. If you keep being asked for
tasks you believe you did, this is why, and `next` will say so.

Every finding needs three things (see `references/judgement.md`):

| Field | Question it answers |
|---|---|
| `--verdict` | *What kind* of defect — see `references/taxonomy.md` |
| `--domain` | *Who fixes it* — `instruction`, `setup`, or `undetermined` |
| `--note` | *Why you believe it* — the evidence, quoted |

Record `PASS` for things you verified correct, with the same rigour. **A report
with no positive evidence cannot distinguish "verified correct" from "never
reached"**, and a reader will assume the flattering one.

## Step 7 — Finish the section and move on

```powershell
lab-validator run --finish done        # or: blocked / partial
lab-validator run --status
lab-validator run --next
```

Section reports are written **as the walk happens**, not at the end. A
multi-hour unattended walk *will* be interrupted, and a run that dies with all
its findings unwritten has produced nothing.

## Step 8 — Report

```powershell
lab-validator run --report
```

Produces `runs/<ts>/gap-analysis.md` plus one report per section. It opens with
the question that matters — **can a learner complete this lab: yes / no /
partially** — names the blocking findings, then coverage, then findings grouped
by who fixes them.

Retract anything that does not survive re-checking:

```powershell
lab-validator run --retract <seq> --note "Re-checked on a fresh instance; the menu is present. Withdrawn."
```

---

## The judgement, in one page

The mechanics above are the easy part. These are the rules that decide whether
the report is worth reading. Full versions with the incidents that produced them
are in `references/judgement.md`.

1. **A defect needs an oracle or a repeated observation.** Never a single
   transient. A previous run withdrew 6 of 36 findings; every one came from
   trusting something seen once.
2. **"X is missing" is a measurement, not a glance.** Negative claims need
   exhaustive evidence — you searched, and here is where.
3. **A green tick is not an observation.** Read the artifact the step was meant
   to produce. Cells that succeed while doing nothing are the worst defect class
   precisely because they hide every other defect.
4. **Record what was not reached as loudly as what failed.** Coverage goes at
   the top, before any finding.
5. **Blocked is a status, not a finding.** The blocker is the finding; keep
   reading past it. One lab sat as a single line — *blocked* — for two runs;
   re-opening it produced six further defects **and corrected the blocker's own
   factual claim**. Never let a section end at `BLOCKED` with one finding.
6. **Re-verify a blocker's factual claim before publishing it.** An overstated
   finding costs more credibility than a missing one, because it is exactly what
   a lab author will check first and use to dismiss the rest.
7. **Say which side is wrong, or say you cannot tell.** `undetermined` is a
   first-class answer, but it must name **the evidence that would settle it**.
   Guessing sends the defect to the wrong owner, who correctly rejects it — and
   the finding dies.
8. **Match on identity, not on a derived name.** A deployment *named* `gpt-4o`
   may serve something else entirely. Ask what a thing *is*, not what it is called.
9. **Never invent an expectation.** Emit what was observed; leave the rest
   blank. A plausible guess will be believed, and the run will report a
   divergence that is really a typo in your own descriptor.
10. **Keep distinct failures distinct.** *Not signed in*, *page does not exist*
    and *signed in with nothing there* need three different messages, because
    they need three different actions.

### Deciding the domain

| Ask | If yes | Domain |
|---|---|---|
| Would editing the lab text alone fix this? | the text names a dead model, a renamed blade, a moved menu, a dead link | `instruction` |
| Would the text be correct if the environment were built properly? | a resource was never provisioned, shipped config is wrong, credentials fail, the image serves something other than it claims | `setup` |
| Could either be true and you have not distinguished them? | — | `undetermined`, **and name the experiment that would decide** |

The two most damaging findings in the reference walk were **setup** defects, and
neither announced itself: an image shipping deployments *named* `gpt-4o` that
actually served a different model, and a `.env` wrong in two independent ways.
Both read, at first, as five unrelated bugs in five unrelated labs.

---

## Reference files

| File | Contents |
|---|---|
| `references/judgement.md` | The full principles, with the incidents that produced them. Platform-agnostic — this is the part that generalises past any one lab platform. |
| `references/taxonomy.md` | Every verdict code, its domain and severity, and how to choose between neighbours. |
| `references/skillable-mechanics.md` | Frames, `window.api.v1`, the Resources tab, the lab clock, Launch gating. |
| `references/harness-traps.md` | The expensive mistakes: notebook execution, false success signals, PowerShell encoding, typed-line limits, window focus. |
