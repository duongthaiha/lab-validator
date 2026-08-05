# Lab Validator

Validates Microsoft Learning Campus hands-on lab instructions against live
product state, and reports where a lab has drifted from reality — retired
models, renamed navigation, moved features, stale screenshots.

Learning Campus is a **Skillable TMS** tenant hosted for Microsoft, so the
validator drives the platform's supported APIs rather than scraping the UI.

**Current findings:** [`docs/gapanalysis.md`](docs/gapanalysis.md) — the
learner-facing gap list for *WorkshopPLUS: Azure AI Platform and Services*,
including how much of the lab has actually been walked. Read the coverage table
first: an absence of findings in a module means *not yet checked*, not *correct*.

**Status.** Run 005 completed the corpus: **all 23 sections walked**, executing the work
rather than checking reachability — 5,880+ recorded steps, 111 heartbeats, 980+ evidence
images, **220+ standing findings**, 7 withdrawn on re-check. 20 sections completed and 3
remain blocked by a defect. The headline result is unchanged and now fully evidenced:
**the workshop cannot currently be completed by any learner** (gap `G-08`), compounded by
a silent model substitution (`G-30`) and a `.env` file that is wrong in two independent
ways (`G-70`, `G-71`). Findings are in [`docs/gapanalysis.md`](docs/gapanalysis.md);
engineering lessons are in [`docs/approach.md`](docs/approach.md) §2.8–§2.10.

## Quick start

Everything after step 2 is automated; step 2 is the only one that needs a human.

```powershell
# 1. a browser to attach to -- opens once, you keep it running
lab-validator session --launch --profile "<your Edge profile>"

# 2. sign in to mslearningcampus.com by hand, in that window

# 3. ask which labs you can actually launch. Do not guess a URL.
lab-validator discover --list

# 4. walk it, with an agent
lab-validator auto --url "<the URL step 3 printed>" --name "<the title step 3 printed>" --max-turns 40 --turn-timeout 900
```

Step 3 prints something like:

```
1 enrolment(s) at https://mslearningcampus.com/User/CurrentTraining/3399370

 * WorkshopPLUS - Azure AI Platform and Services                enrolment 5928204
     slug: azure-ai-platform  (already onboarded)
```

so step 4 becomes:

```powershell
lab-validator auto --url "https://mslearningcampus.com/User/CurrentTraining/3399370" --name "WorkshopPLUS - Azure AI Platform and Services" --max-turns 40 --turn-timeout 900
```

**Why step 3 exists, and why it is not optional.** Learning Campus URLs are not
guessable, and two plausible ones do not work. The catalogue root
(`mslearningcampus.com/Pages/ms-learningcampus`) carries no enrolment at all and
is correctly refused with *"no launchable enrolment found on that page"*. A
`/ClassEnrollment/<id>` form — which this README itself recommended until the
day this section was written — resolves to nothing either. `discover --list`
reads the page with your signed-in session and prints what is launchable
**now**, which is the only answer that cannot go stale.

Then `auto` launches the lab, waits for the client, extracts the instructions,
captures the lab's own credentials — and **stops to ask which sections to
walk**, because validating 23 sections takes hours:

```
Which sections should I walk?  'all' | '4' | '1,4,7' | '4-6' | '?' to re-print the review  [Enter = all]
```

Pass `--sections 4-6` to skip the prompt entirely.
The report lands at `runs/<timestamp>/gap-analysis.md`, and is rewritten after
every step — a run you interrupt is still a run you can read.

**If it says the lab has closed**, that is the tool refusing to invent: a
Skillable lab that has ended keeps its tab, title and URL, so nothing else would
have noticed. Relaunch the lab and resume the same run with
`lab-validator auto --run runs/<timestamp>`.

**If nothing seems to be happening**, ask:

```powershell
lab-validator debug --run runs/<timestamp> --stuck
```

That lists every action that changed nothing on screen, so
`26 of 33 input intervals changed nothing` is a fact rather than an
impression. It works on runs recorded before this feature existed, because it
measures the screenshots already on disk. See
[Reading a run back](#reading-a-run-back--why-nothing-is-happening).

**What of this is proven.** Steps 1–3 and the resolution of that URL were run
against the live tenant on 2026-07-31. `auto` walking a section to completion
has not yet been observed end to end — the one run that got that far ended when
the lab itself closed. Treat step 4 as the documented path, not a demonstrated
one, and see [`docs/agent.md`](docs/agent.md) for what each stop message means.

## Guidance — choose the document for the question

The guidance is deliberately split, because "how do I run this" and "is what I
just saw a defect" are not the same question and get read at different moments.
This README is the quick start and operator journey; it is not the canonical
reference for every command or the agent's internal contract. Pick by the
question, not by reading all five:

| Question | Read |
| --- | --- |
| How does the whole solution fit together? | [`docs/solution.md`](docs/solution.md) |
| What commands and options does the CLI provide? | [`docs/cli.md`](docs/cli.md) |
| How do I run a validation from nothing? | this README, [Running a validation](#running-a-validation) |
| What do I do *next*, mid-walk? | don't read — ask: `lab-validator next` |
| Is this observation a defect? Whose? What evidence do I need? | [`references/judgement.md`](references/judgement.md) |
| What are the steps of a walk, in order? | [`SKILL.md`](SKILL.md) |
| The agent stopped — why? What was it allowed to do? How do I change it? | [`docs/agent.md`](docs/agent.md) |
| Why is the engine built this way, and what went wrong before? | [`docs/approach.md`](docs/approach.md) |

The boundaries between them are deliberate. `docs/solution.md` explains how the
parts cooperate, `docs/cli.md` describes the executable surface, `docs/agent.md`
describes the autonomous controller, and `SKILL.md` tells a Copilot agent how to
operate and judge a walk. If two documents appear to disagree about a command,
the real parser and its CLI drift tests are authoritative.

`judgement.md` is the one worth reading even if you never run this tool. Each of
its principles was paid for by a wrong finding — a defect claimed on one
observation, a blocker reported without re-checking, a whole section skipped
because a report file happened to exist. They are written with no platform
nouns, so they transfer to any "walk a documented procedure and report where it
diverges" problem.

## Credentials — read this first

**This project never stores your Learning Campus password.** Sign-in goes
through Entra ID / MSA with MFA, and Skillable adds device registration on top,
so a stored password could not log in even if we kept one.

### Preferred: attach to a browser you're already signed into

A dedicated Edge/Chrome profile under `.browser-profile/`, cloned from one of
your real Edge profiles, that **you sign into by hand once**. Playwright then
attaches to it over CDP.

```powershell
python scripts/browser_session.py --list-profiles          # see your Edge profiles
python scripts/browser_session.py --launch --profile "Profile 2"
python scripts/browser_session.py --signin msa             # walk the sign-in chooser
python scripts/browser_session.py --status                 # confirm it's reachable
```

`--signin` drives the Learning Campus chooser as far as it can and stops at the
interactive challenge. Both Entra ID and personal Microsoft Accounts land on a
**Windows Hello / FIDO passkey** prompt, which is hardware-bound and cannot be
automated — by design. You complete that one gesture in the visible window and
the session then persists in the profile for every subsequent run.

Why this is the best option:

- **Zero credentials stored** — not even an encrypted session file.
- **MFA is never re-prompted** — the profile persists.
- **Skillable device registration stays satisfied.** Registration keys off a
  browser-cookie GUID plus IP and geolocation
  ([docs](https://docs.skillable.com/docs/device-registration)). Reusing one
  profile means the same fingerprint every run, so no email challenge.
- The browser is visible, so you can watch or take over at any point.

Notes:

- Chrome/Edge 136+ refuse `--remote-debugging-port` on the *default* profile,
  which is why a dedicated profile directory is required.
- The clone is an allow-list copy (cookies, preferences, local storage): ~6 MB
  versus ~1.6 GB for a full mirror. Saved passwords are deliberately not copied.
  Use `--full-profile` only if you need a complete mirror.

### Fallback: encrypted session capture (headless CI)

Where no interactive profile exists, capture a Playwright `storageState` and
encrypt it to your Windows account with DPAPI:

```powershell
python scripts/bootstrap_auth.py            # sign in, capture, encrypt
python scripts/bootstrap_auth.py --status
python scripts/bootstrap_auth.py --clear
```

### The other two credentials

| Credential | Where it lives | How it gets there |
|---|---|---|
| Skillable API key | `.env` locally · GitHub Actions secret in CI | Copy `.env.example` → `.env` |
| Azure access for model/lifecycle oracles | Nothing stored | `az login` locally · OIDC federation in CI |

Rules:

- `.env`, `.auth/`, `.browser-profile/`, `artifacts/`, `*.har`, `trace.zip`,
  `test-results/` are all gitignored **and** blocked by a pre-commit hook.
  Playwright traces embed cookies, request headers and response bodies — they
  are as sensitive as the password itself.
- A `storageState` file can impersonate your account until it expires
  ([Playwright docs](https://playwright.dev/docs/auth)). Treat it accordingly.
- Config uses `pydantic.SecretStr`, so printing settings shows `**********`.
- DPAPI blobs are bound to your Windows user *and* machine. Copying `.auth/`
  to another machine yields an unreadable file — by design.

## Driving the browser

```powershell
python scripts/browser_session.py --goto <url>    # navigate a tab
python scripts/browser_session.py --links         # enumerate (text, href) pairs
python scripts/browser_session.py --click <text>  # click by accessible name or text
python scripts/browser_session.py --dump          # forms/controls/frames as JSON
python scripts/browser_session.py --shot          # screenshot → artifacts/recon/
python scripts/browser_session.py --probe         # detect window.api.v1, iframes, canvases
python scripts/browser_session.py --all-tabs      # applies to every tab
```

`--probe` is the reconnaissance command: it reports whether the Skillable
[Lab Client API](https://docs.skillable.com/docs/lab-client-api-for-lab-delivery-customization)
is exposed on the page, enumerates `window.api.v1` methods, and records iframe
and `<canvas>` geometry — which is what distinguishes a DOM-automatable Cloud
Slice lab from a pixel-only virtualization lab.

`--links` and `--dump` exist because the two things you most need during recon
are *"what can I reach from here"* and *"what is on this page that I can't
see"*. The Learning Campus nav is built from dropdown parents whose children are
`display:none`, so clicking a visible nav label does nothing — link enumeration
is the only reliable way to discover routes. Likewise `--dump` surfaces controls
that exist but are hidden, such as a lab launch button gated by a client-side
countdown rather than a server-side lock.

## Running a validation

A run is a folder of evidence: an append-only trace, numbered screenshots and a
manifest recording how far the walk got. Segments are resumable checkpoints, so
a run that ends early is still worth reading.

### The whole thing, end to end

```powershell
lab-validator session --launch --profile "<your profile>"   # 1. a browser to attach to
lab-validator walk --url "<lab url>" --name "<lab title>"    # 2. you sign in; it does the rest

# 3. repeat until it says stop:
lab-validator next                                           # what to do now, and why
lab-validator step --segment s01 --ref <task-anchor> `       #    do it, record what you saw
  --do click:820,410 --do shot --verdict PASS
lab-validator run --finish done                              #    when a section is complete

lab-validator run --report                                   # 4. runs/<ts>/gap-analysis.md
```

Step 3 is a loop and step 2 is the only one needing a human. If the walk dies at
section 9 of 23, re-running `lab-validator next` picks up exactly where it
stopped and the nine finished section reports are already on disk.

### Start from a URL

One command starts a run on any lab, including one this repo has never seen.
The human's only job is the sign-in gesture — everything after it is automated.

```powershell
lab-validator discover --list                     # what can I actually launch?
lab-validator walk --url "https://mslearningcampus.com/User/CurrentTraining/3399370" `
                   --name "WorkshopPLUS - Azure AI Platform and Services"
```

`walk` navigates to the URL, **blocks until you have signed in** (15 minutes by
default, with a heartbeat so an unattended run survives a coffee break),
resolves the URL and name to exactly one enrolment, clicks Launch, waits for the
lab client to actually answer, extracts and segments the instructions, opens the
run folder, and captures the lab's own credentials into a run-scoped vault.

Two things it deliberately does **not** do:

- **It never guesses which lab you meant.** If `--name` matches more than one
  enrolment, it prints the candidates and stops. Walking the wrong lab produces
  a report full of findings that all look plausible.
- **It never dies on Launch.** The control is countdown-gated and sometimes
  hidden, so if it cannot be clicked the run says `LAUNCH NEEDED`, asks you to
  click it, and waits.

A descriptor in `targets/` is **optional enrichment**, not a precondition.
Without one you still get every *observation-based* finding — broken links,
defective sample code, missing UI, dead models. With one you additionally get
*expectation-based* findings ("the lab promised region X and I did not find
it"). A run with no descriptor says so, loudly, in both the console and the
manifest; silence there would read as "nothing was expected and nothing was
missing", which is the opposite of the truth.

### Before anything else: the preflight

`walk` runs a **preflight as segment 0** — it reads the lab's own Resources tab
and any config the lab shipped, and checks they agree *before* the walk spends
an hour discovering they don't. The two most expensive findings in run 003 were
of exactly this kind, and both were invisible in the lab text.

It is deliberately **non-fatal**: a preflight that halts the run on a check it
could not perform would convert a small unknown into no report at all. Instead
it publishes **its own blind spots** — every check it could not complete is
listed in the report's Coverage section, next to the sections never reached.
A check that quietly skipped would read as a check that passed.

### Walking it: ask the loop what to do

```powershell
lab-validator next          # what to do now, and why
```

This is the part of a walk that is genuinely mechanical, and the only part worth
automating: deciding what comes next and **refusing to advance past work nobody
did**. Everything else — what an instruction means, whether the screen matches
it, which side is at fault — needs judgement and stays with you.

```
NEXT: PERFORM  [s08]
  why: 2 of 5 task(s) have no verdict yet
  task: #3-deploy-the-model   [username -> VM/Username; password -> VM/Password]
  task: #4-run-the-notebook
```

Four properties are worth knowing, because each exists to prevent a specific
way a walk goes quietly wrong:

- **Coverage is counted in tasks, not sections.** A section is a heading; a task
  is a thing the instructions told a learner to do. The failure mode of the
  reference walk was *a task skipped inside a section that then reported clean*,
  and only task-level bookkeeping can see it. So a step must name the task it
  answers (`--ref 3-deploy-the-model`), and a **section** reference is explicitly
  rejected as coverage — one would vouch for every task beneath it.
- **It is a pure function of the run folder.** Resuming a killed walk is the same
  command as continuing a live one. A multi-hour unattended walk *will* be
  interrupted, and a loop whose position lives in memory cannot survive that.
- **It names the credentials a task is asking for** — resolved from the vault by
  **label only**, so a move can be printed or logged without leaking anything.
  A task asking for something the lab never issued is a *finding*, not an error:
  that's a learner's dead end.
- **`why` is load-bearing.** When a walk stops, the sentence explaining what the
  loop believed at the time is the most useful thing in the folder.

Two refusals you will meet, both intentional:

| It says | Because |
|---|---|
| still asking for a task you believe you did | your `--ref` named a *section*; `lab-validator text --segment s08 --tasks` prints the real anchors |
| asking you to REPORT a section you already reported | a finding was recorded *after* that report was written, so the report on disk no longer says what the run knows |

### Or let an agent walk it: `auto`

```powershell
lab-validator auto --url "<lab url>" --name "<lab title>"   # sign in, then leave it
```

Same loop, same refusals — the only difference is who answers the PERFORM moves.
`auto` needs the optional extra (`pip install -e .[agent]`) and an authenticated
`copilot`; without either it fails saying so and points you back at
`lab-validator next`, which needs no model at all.

**Python keeps the sequencing; the model only supplies judgement.** That split is
the whole design:

```
open / read / report / advance   →  executed directly, no model consulted
perform / assess                 →  one scoped model turn, then ask the loop again
```

The loop's refusals were each paid for by a wrong report, and a model that owned
sequencing would turn every one of them into a suggestion it could quietly
ignore. So it is never asked. Three consequences worth knowing:

- **A model's claim of progress is never believed.** Before and after every turn
  the run folder is fingerprinted — steps recorded, tasks still unjudged, section
  status. Identical fingerprint means nothing happened, whatever the transcript
  says. Three of those in a row stops the walk and says which task was
  outstanding.
- **The loop applies that scepticism to itself too.** A mechanical move that comes
  back unchanged three times is a command failing silently, not a move worth
  repeating; it stops and tells you what to run by hand.
- **Tools outside the learner's path are denied, not discouraged.** A shell would
  let the agent repair a broken deployment and then report the lab as working
  while the learner still cannot finish it — a confidently wrong answer, which is
  worse than no answer. Tool output is scrubbed through the run's redactor on the
  way back, so lab-issued credentials never enter the transcript.

Budgets are explicit, because an unattended walk that cannot finish should stop
rather than spend: `--max-turns` (default 200) and `--turn-timeout` (default 900s,
since a lab step is not a chat reply). `--run <folder>` drives a run that already
exists, so an interrupted walk resumes instead of restarting.

**[`docs/agent.md`](docs/agent.md) is the rest of it** — what each stop message
means and what to do about it, the five controls the model gets and the three
withheld from it, how to change the agent without making its report unbelievable,
and how to verify a change with no lab at all.

### Act through the learner's controls

A capability that *acts* on the lab by a route the learner does not have proves
only that your route works. Reading state is never a bypass — look through
anything you like. But where you act by a faster route, the run records it, and
the report prints a **ledger** of which learner-path controls were never
exercised. "The button works" is then a claim with evidence behind it rather
than an assumption.

### Reviewing what you got, and choosing what to walk

Walking 23 sections took 6 217 steps and about a day. Nobody wants to pay that
to re-check one section they just edited. So after the capture — instructions
segmented, credentials in the vault, preflight done — `walk` stops and shows you
what it found before it spends anything.

```
WorkshopPLUS - Azure AI Platform and Services
run:  runs/2026-07-30T0749Z        review: runs/2026-07-30T0749Z/review.md
preflight: 2 failed of 9 checks    credentials: 4 captured

  |  # | id                     | section                   | tasks |
  |  1 | s01-deploy-models      | Deploy models             |     6 |
  |  2 | s02-bing-connections   | Bing connections          |     4 |
  | ...
  | 22 | s22-semantic-kernel    | Semantic Kernel & AutoGen |     ? |

Which sections should I walk?  'all' | '4' | '1,4,7' | '4-6' | '?' to
re-print the review  [Enter = all]
```

**Type the numbers in the `#` column.** That is the whole point of the prompt:
until you have signed in and the lab has been captured, the section ids do not
exist yet, so `--sections s04-deploy-models` is not something you could have
typed in advance. The numbers are on screen in front of you, and the number
printed on a row always selects that row.

Ids work too, once you know them — from the review, or from a previous run:

```powershell
lab-validator walk --url "<lab url>" --name "<lab title>" --sections 4-6
lab-validator auto --url "<lab url>" --name "<lab title>" --sections all
lab-validator walk --url "<lab url>" --name "<lab title>" --sections s04..s06
```

A range between *numbers* may be written `4-6` or `4..6`. A range between *ids*
must use `..` — `s04-s06` is indistinguishable from an id like
`s04-deploy-models`, so it is refused with a hint rather than guessed at. Get
anything wrong and it tells you: a typo that silently selects nothing, or
silently selects a different section, would be far worse than a refusal.

You can also review an existing run without walking it, or widen a run later:

```powershell
lab-validator scope --run runs/2026-07-30T0749Z                    # read-only
lab-validator scope --run runs/2026-07-30T0749Z --sections 1,4-6
```

Re-scoping only ever **widens**. A section already walked is evidence, so
`scope` refuses to un-walk `done`, `blocked` or `in_progress` and says which it
refused. `runs/<ts>/review.md` holds the full version — credentials by label,
scope and shape only, never values, because it is a text artefact you may well
paste into a bug.

**The half that matters more than the selection.** A scoped run reports a
different fact from a full one, and it says so:

- `**Scoped run.**` sits next to the completability verdict, and a scoped run
  **can never answer YES** — it did not look at the rest.
- Coverage counts against what you chose (`3 of 3 selected sections completed`)
  and names what you didn't (`20 of 23 sections were not selected`).
- Unselected sections get their own warning, kept separate from *never reached*.
  Never reached is a walk that ran out of road; not selected is a decision
  somebody made. Same ignorance, different cause, different thing to do.

No prompt appears when stdin is not a terminal — CI and unattended `auto` runs
walk everything, as they always did, and the manifest records that nobody was
asked rather than implying somebody approved.

### The rest of the commands

`lab-validator` is a front door over the scripts, which all still work directly.

```powershell
lab-validator                                        # what exists
lab-validator run --targets                          # list lab descriptors
lab-validator run --check-target <slug>              # validate one strictly
lab-validator run --start                            # new run from an already-open lab
lab-validator run --status                           # progress and verdict counts
lab-validator run --report                           # roll-up + every section report
lab-validator run --retract <seq> --note "…"         # withdraw a finding
lab-validator text --segment s08 --tasks             # what the lab asks for here
```

Individual steps are driven with an **ordered** action list, so a click that
must land before typing actually does:

```powershell
lab-validator step --segment s08 --label deploy `
  --do click:820,410 --do 'type:gpt-5-mini' --do key:Enter `
  --do until:quiet:4000 --do shot
```

Probes are lab-client conditions (`connected`, `quiet:MS`), not screen text —
there is no OCR here. Long operations poll with a budget and emit heartbeats, so
a wait is visible in the trace and a crash mid-wait is resumable.

**Each section reports on itself, as the walk happens.** Every step refreshes
`runs/<ts>/sections/<segment-id>.md`, so a run that dies at section 9 of 23
still leaves nine finished, publishable reports rather than one roll-up that
was never written. `gap-analysis.md` is the roll-up and links to each of them.
Reports are rendered from the trace each time, never appended to — which is why
a retraction removes a finding cleanly instead of needing an erratum.

Every report opens with the question a reader actually has — **can a learner
complete this: YES / NO / PARTIALLY / UNKNOWN** — followed by the blockers and
their evidence, before coverage and before the findings list. A blocked run has
found the most important thing there is to find, so it must not read as a run
that failed to finish. Absence of evidence is never a YES: if any section went
unwalked the answer is UNKNOWN, because unreached content is unknown rather
than correct.

Findings carry two independent axes. The `LABnnn` **code** says what kind of
defect it is; the **domain** says who has to fix it:

| Domain | Meaning | Owner |
|---|---|---|
| `instruction` | the text is wrong — retired model, renamed blade, dead link | lab author |
| `setup` | the text is right, the environment cannot deliver it | lab profile / image / subscription owner |
| `undetermined` | the evidence does not yet settle which side is wrong | needs one more observation |

They have to be orthogonal because the same code falls both ways: a missing
resource is a *setup* defect if the lab should have provisioned it, and an
*instruction* defect if the text names a SKU that never existed. This is not
academic — the two most damaging findings in run 003 were setup defects with
innocent instructions (deployments *named* `gpt-4o` that serve `gpt-5-mini`; a
shipped `.env` wrong in two ways, breaking five labs). Neither is visible in
the lab text. `undetermined` is a first-class value and the correct default:
guessing wrong sends a defect to an owner who correctly rejects it, and then it
dies.

```powershell
python scripts/lab_step.py --segment s08 --note "the shipped .env points at an operation URL" `
  --verdict LAB009 --severity major --domain setup
```

The codes themselves live in one module, `src/lab_validator/taxonomy.py`, with a
test asserting every finding code has a name, a definition and a default
severity — because they previously lived in three places that disagreed, and 40
findings rendered with no name at all while nothing failed.

`--retract` matters as much as the rest: run 003 withdrew 6 of 36 findings. A
validator that never withdraws anything is not checking itself.

## Reading a run back — "why is nothing happening?"

A live walk once did **sixty-five actions against a Windows desktop with no
browser open** and was told `PASS` every single time. It typed
`https://portal.azure.com`, pressed `ctrl+l`, `/` and `g`, and clicked at
(500,60), (700,72) and (640,50) — all into bare wallpaper. Every action was
genuinely dispatched, so every action was genuinely a success, and not one of
them was *the screen changed*.

Every capture now measures what the actions before it did to the screen:

```powershell
lab-validator debug --run runs/2026-08-02T0025Z --stuck --tail 6
```

```
capture                                     delta  effect     actions
0053-s00-create-microsoft-type-after-cli    0.000  NO CHANGE  type:Microsoft Foundry, wait:2000, shot
0054-s00-create-microsoft-ai-azure-shot     0.005  NO CHANGE  page:1, focus, key:ctrl+l, type:https://ai.azure.com/, ...
0056-s00-create-microsoft-look              0.000  NO CHANGE  page:0, wait:2000, click:840,400, wait:3000, dialog, shot

26 of 33 input intervals changed nothing on screen.
```

| flag | what it does |
| --- | --- |
| `--stuck` | only the actions that changed nothing — the shape of a stuck walk |
| `--tail N` | only the last N captures; the usual question is *what was it doing when it stopped* |
| `--out FILE` | also write the report to a file |

**It works on runs recorded before any of this existed**, by measuring the
images already on disk. That is deliberate: the run you need to explain is
always one that already happened, and asking someone to re-run it with a flag
on is asking them to reproduce a thing they could not explain in the first
place. For the same reason `debug.jsonl` is written **always**, not on request —
you never know in advance which run will be the one that goes wrong. `--debug`
on `step` only controls what is *printed* as it happens.

Live, the agent is told the same thing. After three captures where input went in
and nothing came back, the tool says so and tells it to look at the screen
before doing anything else.

**What it will not tell you is why.** The first version of this feature measured
that run, found twenty-four byte-identical frames, and concluded the console had
frozen — with a stop, and a message telling the user to reconnect the lab. Then
somebody opened the last screenshot: a healthy Windows desktop with the clock
reading 5:39 PM. The numbers were all correct and the story built on them was
invented. So the report lists the candidate causes and picks none of them, and
it ends by telling you to go and look at the frame. A still screen is a fact
about the harness or about the walk — **it is never recorded as a lab defect.**

Scale, on the one console measured, so a number means something:

| transition | delta |
| --- | --- |
| click on empty wallpaper | 0.0 |
| clock digit / caret blink | 0.002–0.005 |
| `Tab` moving a desktop focus ring | 0.28 |
| typing into a lock screen | 0.52 |
| lock screen giving way to the desktop | 94.75 |

Which is why nothing is compared against a constant: a run measures its own idle
noise from the intervals where nothing was sent, and judges an action against
that.

## Adding another lab

Everything lab-specific is data in `targets/<slug>.toml` — ids, expected
resources, region, risks, justified deferrals. Structure is **not** listed there;
segments and tasks are derived from the instructions by `corpus.py`, so they stay
correct when the lab author edits content.

Start from discovery rather than hand-authoring the file:

```powershell
python scripts/lab_discover.py --list              # enrolments in the signed-in session
python scripts/lab_discover.py --scaffold 5928204  # writes targets/<slug>.toml
python scripts/lab_run.py --check-target <slug>    # what still needs filling in
```

The scaffold writes only values it **observed**, and leaves a `# TODO` naming how
to find each one it couldn't. That asymmetry is deliberate: an invented
expectation is worse than a missing one, because a run will believe it and report
a divergence that is really a typo in the descriptor.

A freshly scaffolded descriptor is therefore *incomplete by design* and will not
load as runnable until the TODOs are filled in — `--check-target` lists exactly
which.

If walking a new workshop needs a code change, that is a bug in the engine, not
a gap in the descriptor.

While only one descriptor exists, `--target` can be omitted and every command
infers it. Add a second descriptor and the engine stops guessing: `--target`
becomes required rather than silently defaulting to whichever lab came first.

## Using it as an agent skill

The executable and the skill are different parts of the same solution:

- **The CLI is the engine.** It attaches to the browser, persists the run,
  chooses the next legal move, records evidence, and renders reports.
- **The skill is the operating and judgement contract.** It tells Copilot how to
  follow that engine without bypassing the learner path, and how to decide when
  an observation is a finding.

The repository *is* the skill: `SKILL.md`, `references/` and `assets/` sit at the
root beside the code they drive. Install it when you want Copilot to recognize
requests such as "validate this lab" and drive the CLI workflow directly:

```powershell
lab-validator install-skill              # copies it to ~/.copilot/skills
lab-validator install-skill --dry-run    # show what would be written
```

To share the same skill with another Agent Skills-compatible harness, build one
portable archive:

```powershell
lab-validator package-skill
# dist\lab-validator.skill
```

Both commands publish the same curated subset of the repository, so the
installed copy and the archive are byte-identical and neither can go stale. The
`.skill` file is a ZIP archive with `lab-validator/SKILL.md`, its references and
assets, and the complete CLI Python runtime under one root directory. Import it
using the receiving harness's skill installer, or extract it into that harness's
skills directory. Then install the bundled runtime:

```powershell
python <skills-dir>\lab-validator\scripts\install_runtime.py
```

That installs the CLI, agent extra, and Playwright Chromium. Use
`--without-agent` or `--skip-browser` for a smaller manual-only setup. Browser
profiles, credentials, and run evidence are never bundled. A SHA-256 digest is
printed when the package is built so the file can be verified after transfer.

`lab-validator auto` does not depend on that installed copy. It starts a Copilot
SDK session and loads the repository skill directly, then exposes only five
learner-visible CLI-backed tools. Python still owns sequencing, section state,
coverage checks, and report generation; the model supplies the `PERFORM` and
`ASSESS` judgement. See [How Lab Validator works](docs/solution.md) for the full
interaction and [The agent that walks the lab](docs/agent.md) for controls and
stop behavior.

The repo copy is the source of truth; the installed copy is a deployment of it.
A test asserts the two have not drifted, and another parses every command out of
**both `SKILL.md` and this README** and checks it against the real argument
parser — documentation that teaches a renamed flag doesn't produce a helpful
error, it produces a run that dies partway through a lab with a human waiting.

`references/judgement.md` is written with **no platform nouns**, so it transfers
to any "walk a documented procedure and report where it diverges" problem.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"         # also puts `lab-validator` on PATH
python -m playwright install chromium

Copy-Item .env.example .env     # then fill in LV_SKILLABLE_API_KEY
pre-commit install              # blocks credentials from reaching git

python scripts/browser_session.py --list-profiles
python scripts/browser_session.py --launch --profile "<your profile>"
```

```powershell
pytest -q            # unit tests (no lab or browser required)
ruff check src scripts tests
```

## Layout

```
docs/approach.md                    architecture, findings and reuse guide
docs/solution.md                    concise end-to-end solution architecture
docs/cli.md                         CLI workflows, commands, options and recovery
docs/agent.md                       the autonomous walker: stops, limits, changing it
docs/gapanalysis.md                 learner-facing gaps found in the target lab
SKILL.md                            the agent skill — the walk, step by step
references/*.md                     judgement, taxonomy, traps, Skillable mechanics
assets/gap-analysis-template.md     the shape of the report a walk produces
evals/                              skill quality evals — see evals/README.md
targets/<slug>.toml                 per-lab descriptor — data only, no code

scripts/lab_run.py                  start/status/report a validation run
scripts/lab_step.py                 ordered actions; every verb becomes evidence
scripts/lab_text.py                 print a section's instructions from the corpus
scripts/lab_corpus.py               inspect the segmented instruction corpus
scripts/lab_discover.py             list enrolments; scaffold a target descriptor
scripts/browser_session.py          attach to a signed-in browser; recon commands
scripts/lab_drive.py                drive a running lab: instructions, creds, VM
scripts/bootstrap_auth.py           fallback: sign-in → encrypted session
scripts/agent_smoke.py              exercise the agent's SDK wiring with no lab
scripts/install_runtime.py          install the CLI from an extracted skill archive

src/lab_validator/cli.py            `lab-validator` front door; the walk command
src/lab_validator/walkloop.py       what to do next, and the refusals that matter
src/lab_validator/scope.py          review, then choose which sections to walk
src/lab_validator/agent.py          `auto`: the loop driven by a model, on a leash
src/lab_validator/runlog.py         run folder, append-only trace, resume, redaction
src/lab_validator/taxonomy.py       verdict codes and the instruction/setup domain axis
src/lab_validator/corpus.py         instruction segmenter and structural checks
src/lab_validator/report.py         trace → per-section reports + roll-up
src/lab_validator/preflight.py      check the environment before walking it
src/lab_validator/launch.py         sign-in gate, Launch automation, lab-client wait
src/lab_validator/vault.py          run-scoped credential vault, captured once at start
src/lab_validator/asks.py           which instruction is asking for which credential
src/lab_validator/learnerpath.py    which learner controls a run never exercised
src/lab_validator/targets.py        target descriptor loader and validator
src/lab_validator/discovery.py      enrolment parsing, URL→lab resolution, scaffolding
src/lab_validator/imaging.py        screenshot capture, downscaled view copies
src/lab_validator/console.py        what each action did to the screen; the debug log
src/lab_validator/debugread.py      read a finished run back and explain it
src/lab_validator/browser.py        CDP launch/attach, profile management
src/lab_validator/labclient.py      lab frames, window.api.v1, VM screen/click/type
src/lab_validator/config.py         typed settings, SecretStr-backed
src/lab_validator/secrets_store.py  DPAPI protect/unprotect helpers
src/lab_validator/auth.py           storageState load/save, session health

runs/<timestamp>/                   gitignored — screenshots contain live API keys
  trace.jsonl                       append-only, one record per step
  images/                           numbered evidence captures
  sections/<segment-id>.md          each section's own report, written as it is walked
  gap-analysis.md                   roll-up, links to every section report
```

## Design

See the research report for the full architecture. In brief — *oracle-first,
API-second, DOM-third, vision-last*:

1. **Static claim checking.** Parse a lab's IDLx instruction source, extract
   claims (model, region, SKU, API version, portal label), and cross-check them
   against authoritative APIs. This catches every "model retired" defect with no
   browser at all.
2. **Instrumented launch.** Launch via the Skillable Connect LAB API, drive the
   lab client's supported `window.api.v1` surface, and read back the lab
   author's own automated-activity results.
3. **Cloud Slice DOM automation.** Azure portal labs open a second window with a
   full DOM, so Playwright locators work.
4. **Canvas vision.** Only for virtualization labs, where the VM is delivered as
   pixels over a WebSocket.