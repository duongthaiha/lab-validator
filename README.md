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

## Guidance — four documents, four different questions

The guidance is deliberately split, because "how do I run this" and "is what I
just saw a defect" are not the same question and get read at different moments.
Pick by the question, not by reading all four:

| Question | Read |
| --- | --- |
| How do I run a validation from nothing? | this README, [Running a validation](#running-a-validation) |
| What do I do *next*, mid-walk? | don't read — ask: `lab-validator next` |
| Is this observation a defect? Whose? What evidence do I need? | [`skills/lab-validator/references/judgement.md`](skills/lab-validator/references/judgement.md) |
| What are the steps of a walk, in order? | [`skills/lab-validator/SKILL.md`](skills/lab-validator/SKILL.md) |
| Why is the engine built this way, and what went wrong before? | [`docs/approach.md`](docs/approach.md) |

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
lab-validator walk --url "https://mslearningcampus.com/ClassEnrollment/5928204" `
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

### Act through the learner's controls

A capability that *acts* on the lab by a route the learner does not have proves
only that your route works. Reading state is never a bypass — look through
anything you like. But where you act by a faster route, the run records it, and
the report prints a **ledger** of which learner-path controls were never
exercised. "The button works" is then a claim with evidence behind it rather
than an assumption.

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

The judgement that makes a report worth reading — when an observation is a
defect, which side is at fault, what evidence is required, when to withdraw a
finding — is packaged as an agent skill in [`skills/lab-validator/`](skills/lab-validator/).

```powershell
lab-validator install-skill              # copies it to ~/.copilot/skills
lab-validator install-skill --dry-run    # show what would be written
```

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
docs/gapanalysis.md                 learner-facing gaps found in the target lab
skills/lab-validator/               the agent skill — judgement, taxonomy, traps
targets/<slug>.toml                 per-lab descriptor — data only, no code

scripts/lab_run.py                  start/status/report a validation run
scripts/lab_step.py                 ordered actions; every verb becomes evidence
scripts/lab_text.py                 print a section's instructions from the corpus
scripts/lab_corpus.py               inspect the segmented instruction corpus
scripts/lab_discover.py             list enrolments; scaffold a target descriptor
scripts/browser_session.py          attach to a signed-in browser; recon commands
scripts/lab_drive.py                drive a running lab: instructions, creds, VM
scripts/bootstrap_auth.py           fallback: sign-in → encrypted session

src/lab_validator/cli.py            `lab-validator` front door; the walk command
src/lab_validator/runlog.py         run folder, append-only trace, resume, redaction
src/lab_validator/taxonomy.py       verdict codes and the instruction/setup domain axis
src/lab_validator/corpus.py         instruction segmenter and structural checks
src/lab_validator/report.py         trace → per-section reports + roll-up
src/lab_validator/launch.py         sign-in gate, Launch automation, lab-client wait
src/lab_validator/vault.py          run-scoped credential vault, captured once at start
src/lab_validator/targets.py        target descriptor loader and validator
src/lab_validator/discovery.py      enrolment parsing, URL→lab resolution, scaffolding
src/lab_validator/imaging.py        screenshot capture, downscaled view copies
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