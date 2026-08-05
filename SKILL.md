---
name: lab-validator
description: "Walk a hands-on lab (Microsoft Learning Campus / Skillable) as a simulated learner in a real browser, doing what the instructions say, and report every place reality has drifted from the text — retired models, renamed UI, moved features, dead links, defective sample code — and every place the lab environment itself is broken. The human signs in once; the agent does the rest. Triggers: 'validate this lab', 'walk this lab', 'lab gap analysis', 'check whether these lab instructions still work', 'has this lab drifted', 'test this Skillable lab', 'simulate a learner doing this lab'."
compatibility: Requires Windows, Python 3.11+, browser UI, network access, and a human sign-in.
---
# Lab Validator

Drive a browser through a hands-on lab the way a learner would, and produce a
gap analysis: an evidence-backed list of every place the instructions no longer
match the product, plus a verdict on whether a learner can finish at all.

**This is a differ, not a test runner.** There is no pass/fail suite to go
green. The deliverable is a report someone can act on, and the durable asset is
the recorded trace of what was observed.

## When to use
- Someone hands you a Learning Campus / Skillable URL and asks "validate this lab"

## When *not* to use
- To check a single factual claim ("is `gpt-4-32k` retired?"). Query the Azure
  model-lifecycle API directly — a whole lab walk is hours and this is seconds.
- To fix the lab. This reports; it does not edit lab content.

## Prerequisites
- The `lab-validator` CLI: run `python scripts/install_runtime.py` from a portable extraction, or `pip install -e ".[dev]"` from a clone.
- A browser profile the tooling can attach to (see Step 1). **Edge 136+ refuses
  `--remote-debugging-port` on the default profile**, so a dedicated clone is required.
- **A human available for exactly one gesture: the sign-in.** It is hardware-bound
  (Windows Hello / FIDO) and deliberately un-automatable. Everything after it is not.
- The lab URL and title.

## How this skill reaches you

The CLI owns browser automation, persisted state, evidence, and reports; this
skill supplies operating and judgement rules. Installed with
`lab-validator install-skill`, or unpacked from `package-skill` into any
Agent Skills-compatible harness, it recognizes a user's validation request and
drives the commands below. The repository copy is authoritative, and only
task-scoped run evidence advances the walk.

**You sequence the walk.** `lab-validator next` reads the run folder and says
which move is due and why; run the command it names, then ask again. The
refusals live in the CLI: it will not let you advance past a task with no
verdict.

## What your harness must guarantee

Four rules used to be enforced by a bundled autonomous driver. It is gone, so
they are yours to honour. The incidents behind them are in
`references/harness-traps.md` under *The harness contract*.

1. **Stay on the learner's path.** Act through `step --do` and the documented
   commands. Do not repair the lab from a shell, the product's API or the file
   system behind the VM: a lab you fixed reports as working while the learner
   following the text still cannot finish it. Read-only oracles are fine;
   anything that *changes* the lab must be a control the learner has.
2. **Evidence is progress; your transcript is not.** Only a trace record scoped
   to a task anchor counts. Ask `lab-validator next` after acting — if the
   outstanding tasks did not change, nothing happened.
3. **Stop rather than grind.** Three turns that change nothing, the same move
   returning unchanged, or *Lab Closed*: stop and say so. The run resumes from
   disk; a stuck loop burns lab clock and writes trace nobody can use.
4. **Never echo raw output into a prompt.** Credentials are requested by label
   (`cred:SCOPE/LABEL`) and sign-ins by role (`signin:vm`, `signin:portal`)
   precisely so no value has to pass through you.

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

## Step 4 — Review what was captured, then choose what to walk

The whole lab is expensive, so `walk` stops here — instructions segmented,
credentials captured, nothing spent yet — and shows what it got.

**Show the human what was captured and get an explicit selection before walking
anything.** Put the section table in front of them — number, title, task count —
with the preflight verdict and any structural anomaly. This is the last gate
where being wrong is still free; everything after it spends lab clock. Scope
picked by inference yields a confident report about sections nobody agreed to
walk, and the reader cannot tell that from the real thing. Silence is not
approval.

```powershell
lab-validator scope --run <run folder>                     # print the review, change nothing
lab-validator scope --run <run folder> --sections 4-6      # narrow it
```

**Type the numbers from the review's `#` column** — `4`, `1,4,7`, `4-6`, or
`all`. This is not a convenience: section ids do not exist until the lab has
been captured, so on a first run there is nothing else you could type. The
number printed on a row always selects that row.

Ids work too once you know them (`s04`, or an unambiguous prefix), but a range
*between* ids needs `s04..s06` — ids contain hyphens (`s04-deploy-models`), so
`s04-s06` is indistinguishable from one. Anything unknown or ambiguous is
refused by name rather than guessed: a typo that silently selected nothing, or a
different section, would produce a clean report about a lab nobody looked at.

**What to select.** Scope to the sections the question is actually about:

| The question | Scope |
| --- | --- |
| "we edited section 4, did we break it?" | that section and anything downstream of it |
| "is this lab still fit to teach?" | everything — there is no shortcut to that answer |
| "the learner said lab 10 fails" | that section, plus the setup sections it depends on |
| "is the environment even right?" | Step 3's preflight alone may answer it |

Dependencies matter more than they look. Section 10 failing because section 4
never created the resource is a **setup** finding about section 4, and you will
misattribute it to section 10 if you did not walk section 4.

**What this costs you, and what you must not do about it.** A scoped run answers
a narrower question, and the report says so: `**Scoped run.**` sits beside the
verdict, coverage counts against the selection, and unselected sections get their
own warning — kept separate from *never reached*, because a walk that ran out of
road and a decision somebody made are different facts.

> A scoped run **can never answer YES** to "can a learner complete this lab".
> Do not write that it can, in any summary you produce. You looked at three
> sections out of twenty-three; you know nothing about the other twenty, and
> "no findings" there means nobody looked, not that they are fine.

Re-scoping only widens. `scope` refuses to un-walk a section that is `done`,
`blocked` or `in_progress` and tells you which it refused: walked sections are
evidence, and a narrower scope must never erase them. After widening, the
existing `gap-analysis.md` is stale — re-run the report at Step 9.

`<run>/review.md` holds the full review: preflight verdict, structural anomalies,
the section table, and credentials **by label, scope and shape only**. It never
contains a credential value, because it is a text artefact somebody will paste
into a bug.

## Step 5 — Read what the lab actually asks for, before doing anything

```powershell
lab-validator next                            # what to do now, and why
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

## Step 6 — Do the work, in the learner's path

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

### Signing in: name the login, never the credential

A lab issues several credentials, and more than one of them is called
`Username` / `Password`. They are all strings; only one opens the screen in
front of you. Do not choose between them.

```powershell
lab-validator step --segment s04 --label vm-signin `
  --do signin:vm --do until:quiet:4000 --do shot
```

| Use | When the screen is |
| --- | --- |
| `signin:vm` | the machine's own login — a Windows lock screen, an RDP prompt |
| `signin:portal` | a cloud sign-in — Azure, Entra, Microsoft 365 |
| `signin:portal/username` | the account page that precedes the password page |
| `signin:portal/tap` | *Enter Temporary Access Pass* — where the lab issues one |

`signin:ROLE` types the **password** by default, because both flows end at a
password box. Add `/username` for the account field. Entra often demands a
**Temporary Access Pass** right after the username, offering a password only
behind a *Use your password instead* link; `signin:portal/tap` matches that
screen wherever the lab issues one.

Judge the login from **what you can see**, not from what the task says you are
doing. A step titled "Sign in to the Azure portal" begins on the VM's lock screen
if the VM is locked, and the correct first move is `signin:vm`. The tool resolves
the credential from the lab's own scopes; if two could match, it refuses and
names them — supply the role it could not work out, never a credential.

**The VM login always comes first.** Everything you can reach — browser, portal,
terminal — is inside the VM, so `signin:portal` is refused until `signin:vm` has
run. Nothing is typed by a refused sign-in. Do not work around it by typing the
password another way; go and unlock the machine.

**A sign-in reports `DEFERRED`, never `PASS` — so read the screen afterwards.**
Not caution: on a Windows console an accepted sign-in and a rejected one are
the same flat blue with the same avatar and the same account name, differing by
one line of text, and the accepted one can measure as *less* changed than the
rejected one. So always follow a sign-in with a capture, and say what you see:

```powershell
lab-validator step --segment s04 --label vm-signin `
  --do signin:vm --do until:quiet:4000 --do shot
```

A password box still showing, or "The password is incorrect", means it failed.
Say so, and try the other login — do not repeat the same one. Treating the
`DEFERRED` as a pass and moving on is how four steps of work get recorded
against a screen nobody ever got past.

Guessing here is not a harmless retry. The wrong password produces "the
password is incorrect", which is indistinguishable from a genuine credential
defect, so a guess does not just fail — it manufactures a false finding about
the lab.

**A sign-in the instructions never mention is itself a finding.** Labs commonly
document the cloud login and say nothing about the machine login the learner
meets first. Record it (`LAB004`, minor, `domain=instruction`) and carry on.

## Step 7 — Record a verdict for each instruction

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
| --- | --- |
| `--verdict` | *What kind* of defect — see `references/taxonomy.md` |
| `--domain` | *Who fixes it* — `instruction`, `setup`, or `undetermined` |
| `--note` | *Why you believe it* — the evidence, quoted |

Record `PASS` for things you verified correct, with the same rigour. **A report
with no positive evidence cannot distinguish "verified correct" from "never
reached"**, and a reader will assume the flattering one.

## Step 8 — Finish the section and move on

```powershell
lab-validator run --finish done        # or: blocked / partial
lab-validator next                     # confirms the section is really done
```

`next` will not let you leave a section with a task nobody judged, and it names
which ones. That refusal is the point: the failure mode being prevented is a
task quietly skipped inside a section that then reports clean.

Section reports are written **as the walk happens**, not at the end. A
multi-hour unattended walk *will* be interrupted, and a run that dies with all
its findings unwritten has produced nothing. `next` reads only the run folder,
so resuming an interrupted walk is the same command as continuing a live one.

## Step 9 — Report

```powershell
lab-validator run --report
```

Produces `runs/<ts>/gap-analysis.md` plus one report per section, following the
[output template](assets/gap-analysis-template.md): completability, blockers,
coverage, findings grouped by owner, verified steps, and audit history.

Retract anything that does not survive re-checking:

```powershell
lab-validator run --retract <seq> --note "Re-checked on a fresh instance; the menu is present. Withdrawn."
```

---

## If you are told the screen is not changing

You will sometimes see this after a capture:

```
NOTHING YOU HAVE DONE IN THE LAST 3 CAPTURES HAS CHANGED THE SCREEN. 5 input
action(s) were sent (key:ctrl+l, type:https://portal.azure.com, key:Return, ...)
and every time the screen stayed within its own idle noise.
```

**Stop and look at the most recent screenshot before doing anything else.** Do
not repeat the action, do not try the same thing at different coordinates, and
do not send more keys. This is the moment to spend a `shot` on looking rather
than on trying.

The likely reasons, in the order they have actually occurred:

1. **You are acting on the wrong surface.** The commonest by far. You are typing
   a URL, but there is no browser window open — just a desktop. Open the
   application first, from the taskbar or the Start menu.
2. **Nothing has focus**, or the wrong control does. Click the target, then type.
3. **Your coordinates are landing on empty space** — wallpaper, a margin, a gap
   between controls. A click on bare desktop changes nothing, and correctly
   reports success.
4. **The console is genuinely not repainting.** Real, but the rarest, and it
   looks identical to the other three from the number alone.

**This is not a lab defect. Do not record a finding for it.** A screen that will
not move is a fact about the harness or about what you are doing, not about the
lab's instructions. Filing it as one blames the lab for your own aim.

The measurement cannot tell you which of the four it is — that is why you are
being sent to the screenshot instead of being given an answer. A previous
version of this warning did name a cause, chose "the console has frozen", and
was wrong: the screenshot showed a healthy desktop with a working clock.

---

## If the lab closes while you are walking it

A Skillable lab that ends **keeps its tab, its title, its `/LabClient/<guid>`
URL and all three of its frames.** Only the top-level text changes, to *Lab
Closed*. Every identity check still passes, so this looks like nothing at all.

Any step run against a closed lab now refuses:

```
!! The lab client says: 'Lab Closed'. Instance <id> has ended, so nothing
   observed from here is evidence about the lab.
```

It records one `BLOCKED` step and exits **4**. Stop on it immediately.

**Do not file findings about what you saw after this.** A lab that has ended is
not a defect in the lab: the instruction pane that will not scroll is dead, not
broken, and the wait that never completed had nothing to wait for. Sections
already walked keep their reports; **the rest are unknown, not correct.**

Ask the human to launch the lab again, then resume the same run:

```powershell
lab-validator next --run <run folder>
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
11. **Act through the learner's controls; look through anything.** A capability
    that *acts* on the lab UI by any route the learner does not have proves only
    that your route works. Reading state is never a bypass. Where the fast route
    is the better tool, use it — and exercise its learner-path equivalent at
    least once, so the ledger can say the control works rather than assume it.

### Deciding the domain

| Ask | If yes | Domain |
| --- | --- | --- |
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
| --- | --- |
| `references/judgement.md` | The full principles, with the incidents that produced them. Platform-agnostic — this is the part that generalises past any one lab platform. |
| `references/taxonomy.md` | Every verdict code, its domain and severity, and how to choose between neighbours. |
| `references/skillable-mechanics.md` | Frames, `window.api.v1`, the Resources tab, the lab clock, Launch gating. |
| `references/harness-traps.md` | The expensive mistakes: notebook execution, false success signals, PowerShell encoding, typed-line limits, window focus. |
