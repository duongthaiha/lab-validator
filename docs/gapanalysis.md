# Gap analysis — WorkshopPLUS: Azure AI Platform and Services

What a learner is told to expect, versus what is actually in front of them.

**Lab** 79233, edition 2026031B · **Validated** 2026-07-29/30 · **Runs** 002 (shallow) + 003 (deep)
**Instruction corpus** 2,264 lines / 109,703 chars · 23 sections across 12 modules

This is the **learner- and author-facing** output. Engineering notes live in
[`docs/approach.md`](approach.md); raw per-run evidence lives in `runs/<timestamp>/`
(gitignored — screenshots contain live API keys).

Resource names and subscription IDs are redacted to `<...>` throughout.

---

## Read this first

> **The workshop cannot currently be completed by any learner.**
>
> Both chat models it requires — `gpt-4o` and `gpt-4o-mini` — **refuse to deploy** on a
> Skillable lab subscription, and so does `gpt-4.1`. This is not a quota problem, not a
> region problem and not transient: it is structural and permanent (**G-08**). Every lab
> that calls a chat model is gated behind a setup step nobody can finish.
>
> Fixing G-08 is the precondition for everything else in this document.

**Suggested order of repair**

| Priority | Fix | Why first |
|---|---|---|
| 1 | **G-08** — retarget off the `gpt-4o` family | Nothing downstream can be validated until this clears. Note that bumping to `gpt-4.1` does **not** work — it is already refused. |
| 2 | **G-22** — validate the replacement against the **Agents** API, not just chat completions | A model can pass Lab 01 Task 3 and still fail Lab 01 Task 4 and all six Lab 02 notebooks. |
| 3 | **G-09, G-11, G-12, G-13, G-24** — the `.env` chain | Five separate defects in one file. Every notebook in the workshop reads it. |
| 4 | **G-21, G-25** — cells that report success while failing | These hide every other defect from the learner. |
| 5 | Everything else | Navigation, labels, typos. |

---

## Coverage — read this before trusting the "no gaps found" areas

| | Sections | Status |
|---|---|---|
| **Walked hands-on**, doing the work — every notebook cell executed, every result inspected | 8 of 23 | Required Lab Setup (all 6 sections) + Lab 01 (both sections) |
| of which **completed** | 7 | |
| of which **blocked** by a defect | 1 | *Deploy models* — see G-08 |
| **Never reached** | 15 of 23 | Labs 02–10, both optional labs |
| **Statically analysed** — model IDs vs the Azure model-lifecycle API, TOC/anchor structure, resource inventory | 23 of 23 | 100 % |

Run 003 recorded **1,569 steps** and **196 heartbeats**, capturing 249 evidence images.
**30 findings stand**; **6 were retracted** after re-checking (see *Withdrawn*).

> **The 15 unwalked sections are unknown, not correct.** No finding below says anything
> about them. Labs 09 and 10 are the largest modules and remain entirely unexercised.
> The run stopped because the lab session was lost to a harness fault, not because the
> corpus was exhausted.

---

## Findings

🔴 critical · 🟠 major · 🔵 minor

| ID | Sev | Module | Gap |
|---|---|---|---|
| **G-08** | 🔴 | Deploy models | **`gpt-4o`, `gpt-4o-mini` and `gpt-4.1` cannot be deployed at all** |
| G-01 | 🔴 | Required Lab Setup | Sign-in needs a Temporary Access Pass; no instruction says so |
| G-09 | 🔴 | Setup `.env` | `CSV_PATH` points at a folder that does not exist — inside a "do not modify" block |
| G-02 | 🟠 | Required Lab Setup | Create-wizard tab list is stale — 8 tabs, not the 4 documented |
| G-03 | 🟠 | Lab 05 – Fine-Tuning | Two model names that do not exist *(static only — not walked)* |
| G-10 | 🟠 | Setup `.env` | "the root folder" is not a path; three divergent `.env.example` copies exist |
| G-11 | 🟠 | Setup `.env` | Step 5 pastes the **embedding** URI into the **chat** variable |
| G-12 | 🟠 | Setup `.env` | Four required `..._ADA_...` variables are never mentioned |
| G-13 | 🟠 | Setup `.env` | `SQL_PWD` is required but no step ever sets it |
| G-17 | 🟠 | Required Lab Setup | Resource inventory does not match: extras present, Vision/Language resources absent |
| G-20 | 🟠 | Setup · requirements | `06-pip-install-requirements.ipynb` is not where the instruction says |
| G-21 | 🟠 | Lab 01 Quick Start | Agent cell **swallows a failed run** — green tick, no output, no error |
| G-22 | 🟠 | Lab 01 / Lab 02 | Agents API rejects the newest models; replacement must be Agents-validated |
| G-24 | 🟠 | Lab 01 Evaluations | Endpoint **shape** in Setup step 4 makes the Relevance evaluator fail 404 |
| G-25 | 🟠 | Lab 01 Evaluations | Cell prints "completed" while one evaluator failed 3 of 3 |
| G-26 | 🟠 | Lab 01 Evaluations | `requirements.txt` floors, not pins → stale SDK → `max_tokens` rejected |
| G-29 | 🟠 | Lab 01 Evaluations | Local and cloud runs share **no metric**, so the promised comparison is impossible |
| G-04 | 🔵 | Deploy models | "Click firstProject inside All resources" — that view never appears |
| G-05 | 🔵 | Contents | Second "Lab 07- RAI" entry is really Lab 08 |
| G-06 | 🔵 | Required Lab Setup | "East US 2" is not in the Recommended region list |
| G-07 | 🔵 | Global | Product naming drifts between three variants |
| G-14 | 🔵 | Setup `.env` | Embedding Target URI documented as `/chat/completions`; it is `/embeddings` |
| G-15 | 🔵 | Setup `.env` | Template host and instruction host disagree |
| G-16 | 🔵 | Lab assets | Typos shipped in `.env.example` and a folder name |
| G-18 | 🔵 | Required Lab Setup | "Azure AI Search" is now branded "AI Search (Foundry IQ)" |
| G-19 | 🔵 | Required Lab Setup | "SQL Servers" is not a label the portal offers; example names are stale |
| G-23 | 🔵 | Contents | Two contents links land on a repeated title, not the lab |
| G-27 | 🔵 | Lab 01 Evaluations | Task 1 describes four activities the notebook does not implement |
| G-28 | 🔵 | Lab 01 Evaluations | Docs claim `InteractiveBrowserCredential`; code uses `DefaultAzureCredential` |
| R-01 | ⚠️ | All labs | Everything depends on the "New Foundry" legacy toggle surviving |
| R-02 | ⚠️ | Several | ~~`gpt-4o` is on a retirement path~~ — **superseded by G-08: it has already arrived** |

---

### G-08 🔴 The workshop's chat models cannot be deployed — by anyone

**The single defect that stops the workshop.** Setup requires four deployments:
`text-embedding-3-large`, `gpt-4o`, `gpt-4o-mini`, `text-embedding-ada-002`.
The two embedding models deploy fine. **Neither chat model will deploy, in any version.**

| Model | Versions tried | Result |
|---|---|---|
| `gpt-4o` | 2024-11-20, 2024-08-06, 2024-05-13 — **all three** | `ServiceModelDeprecating` |
| `gpt-4o-mini` | 2024-07-18 (only version offered) | `ServiceModelDeprecating` |
| `gpt-4.1` | 2025-04-14 | `ServiceModelDeprecating` |

> `The model Format:OpenAI,Name:gpt-4o,Version:2024-11-20 is in deprecating state and
> cannot be used for new deployments.`

**Root cause.** Per Microsoft Learn, *[Foundry Models lifecycle and support policy](https://learn.microsoft.com/en-us/azure/foundry/openai/concepts/model-retirements)*,
a **Deprecated** model remains deployable **only for existing customers**, and "existing"
is decided **per subscription** — has *this* subscription ever deployed *that* model
version. Skillable mints a **fresh subscription for every lab instance**. Therefore every
learner is a new customer, and no learner can ever deploy these models. This is
**structural and permanent**, not a transient or a quota issue.

**Three controls were run to rule out alternative explanations:**

1. **Not the resource.** The resource group contains a second, pre-provisioned Azure
   OpenAI resource (`myopai-<n>`, kind `OpenAI`, West US) that Setup never mentions.
   `gpt-4o` fails there too — different resource kind, different region, identical refusal.
2. **Not the region or the quota.** `gpt-5.6-sol` deploys successfully into the same
   Foundry resource (Global Standard, 250K TPM, East US 2, `Succeeded`,
   lifecycle `GenerallyAvailable`). The subscription **can** deploy chat models.
3. **Not specific to `gpt-4o`.** `gpt-4.1` is refused identically, so the block covers
   *every* OpenAI chat model that has an announced deprecation date.

**What makes it worse.** The model catalog labels all three `gpt-4o` versions
**"Generally available"** with retirement dates in 2026–2027, so nothing warns the learner
before they hit the error. The instructions also tell them to *"make sure the selected
Azure region supports model GPT-4o"* — sending them to debug a region that is not the
problem.

**Fix.** Retarget the workshop onto a model with no announced deprecation.
⚠️ **Bumping to `gpt-4.1` will not work** — it is already refused. Either pick from the
currently deployable set, or arrange for the per-instance subscription to be treated as an
existing customer. **See G-22 before choosing**: chat-completions capability is not
sufficient.

*Evidence: run 003 seq 224, 247, 306, 659, 694, 721.*

### G-01 🔴 The sign-in asks for something the instructions never mention

**Instruction** — *"sign in with your Azure credentials. These credentials are present on
the right hand side under resources tab below Azure Portal."*

**What actually happens.** After the username, Entra does not ask for a password. It shows
**"Enter Temporary Access Pass"**. The Resources tab does carry a `TAP` value — but it sits
*below* a `Password` value, and nothing explains which is used when. A learner following
the text reaches for **Password** first.

Reproduced on two different lab instances, so this is stable behaviour, not a one-off.

**Why it matters.** It is the very first action of the workshop and the instruction points
at the wrong field. There is a *"Use your password instead"* link on that screen, but a
learner has no way to know which path is intended.

**Fix.** *"Sign in with the **Username** and the **TAP** from the Resources tab. The
Password is used for later prompts, not the first sign-in."*

*Evidence: run 003 seq 39; first seen run 002.*

### G-09 🔴 `CSV_PATH` is broken, and the instructions forbid fixing it

`.env.example` declares:

```
CSV_PATH=C:\Users\Admin\Desktop\LABS\Vectors\SQL\movie_quotes.csv
```

There is **no `Vectors` folder anywhere under `LABS`**. The file actually lives at
`C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\SQL\movie_quotes.csv` (66,890 bytes).

**Why it is critical rather than major.** `CSV_PATH` sits inside the block headed
`# Do not modify following section`, and step 1 instructs the learner *"Do not modify the
section that is marked for not to modify"*. So a learner who follows the instruction
**correctly** is left with a broken path, and the Azure SQL vector lab fails with
file-not-found. The instruction and the template actively conspire against the fix.

**Fix.** Correct the path in the template, or move `CSV_PATH` out of the do-not-modify block
and add a step that sets it.

*Evidence: run 003 seq 418.*

### G-02 🟠 The create wizard has eight tabs, not four

**Instruction** — *"we will keep all default values for all the subsequent tabs
(Network, Identity, Encryption, Tags)."*

**What actually happens:**

> Basics | **Storage** | **Inbound Networking** | **Outbound Networking** | Identity | Encryption | Tags | Review + create

**Network** has been split into **Inbound** and **Outbound Networking**, and a **Storage**
tab has been added.

Defaults are still correct so nothing breaks, and the "click Next until Review + create"
guidance still works — but a learner counting tabs against the instruction concludes they
are in the wrong wizard.

**Fix.** Make it version-proof: *"click Next through the remaining tabs, accepting
defaults, until you reach Review + create."*

*Evidence: run 003 seq 66; reproduced from run 002 on a different instance.*

### G-03 🟠 Model names that do not exist

**Line 993** — *"Here choose GPT-4.1-mini or **GPT-4-o-mini** or **GPT-4.o**"*

Neither `GPT-4-o-mini` nor `GPT-4.o` is a valid identifier. Checked against the Azure
model-lifecycle API (324 models): no match. The real names are `gpt-4o-mini` and `gpt-4o` —
no dots or hyphens inside "4o". A learner searching the catalog for the printed strings
finds nothing.

**Fix.** `gpt-4.1-mini`, `gpt-4o-mini`, `gpt-4o` — though note **G-08**: none of these can
actually be deployed, so this section needs retargeting regardless.

*Static analysis only — Lab 05 has not been walked.*

### G-10 🟠 "the root folder" is not a path, and three different templates exist

**Instruction** — *"Find the .env.example file that is supplied as the template. You can
find it in the root folder provided within the lab VM."* No path is given, and no such
"root folder" exists.

A recursive search finds **three divergent copies**, none at a drive root:

| Path | Size | Date |
|---|---|---|
| `C:\Users\Admin\Desktop\LABS\.env.example` | 2,859 B | 25 Jan 2026 — newest, and the only one a learner would plausibly find |
| `C:\Archive\New folder\1-8-2026\WPLUS-...-main\.env.example` | 2,770 B | 19 Dec 2025 |
| `C:\Archive\New folder\WPLUS-...-main\.env.example` | 2,762 B | 28 Aug 2025 |

They differ in size, so they differ in content — a learner who opens the wrong one gets a
stale variable list, and **every later lab silently depends on that choice**. `C:\Archive`
also holds three unopened zips (`Lab_1122025.zip`, `LABS.zip`,
`WPLUS-Azure-AI-Platform-and-Services.zip`).

**Fix.** Name the exact path (`C:\Users\Admin\Desktop\LABS`) and delete or clearly archive
the stale copies.

*Evidence: run 003 seq 393.*

### G-11 🟠 Step 5 pastes the embedding URI into the chat variable

The section is headed *"Set the values for the `AZURE_OPENAI_EMBEDDING_ENDPOINT` and
`AZURE_OPENAI_EMBEDDING_API_KEY` variables"*, but its body says, verbatim:

> *"Copy Endpoint Target URI and paste into .env file as the value for
> `AZURE_OPENAI_ENDPOINT`"*

`AZURE_OPENAI_ENDPOINT` is the **chat** model endpoint, set in step 4. Following step 5
literally **overwrites the chat endpoint with an embedding endpoint** and leaves
`AZURE_OPENAI_EMBEDDING_ENDPOINT` unset — breaking every notebook that does chat
completion. Step 5 appears to be step 4 copy-pasted without renaming the variable.

**Fix.** Name `AZURE_OPENAI_EMBEDDING_ENDPOINT` in the body, as the heading already does.

*Evidence: run 003 seq 419.*

### G-12 🟠 Four required variables are never mentioned

`.env.example` carries a dedicated ada-002 block:

```
AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT
AZURE_OPENAI_EMBEDDING_ADA_API_KEY
EMBEDDING_ADA_MODEL_DEPLOYMENT_NAME
EMBEDDING_ADA_MODEL_API_VERSION
```

Step 5 says only *"Similar steps as above. Follow for both text-embedding-3-large and
text-embedding-ada-002 models"*, and then names just the four **non-ADA** variables. A
learner doing exactly as told writes ada-002's values over 3-large's, and leaves all four
`ADA_` variables as the `xxxxxxx` placeholder.

**Fix.** Enumerate both variable sets explicitly.

*Evidence: run 003 seq 420.*

### G-13 🟠 `SQL_PWD` is required but no step ever sets it

`.env.example` declares `SQL_PWD=xxxxxxx` directly under `SQL_SERVER`, yet step 10 covers
only `SQL_SERVER` and **no step anywhere mentions a SQL password**. The value appears to
come from `C:\Users\Admin\Desktop\LABS\sqlcredentials.txt` — a file the instructions never
reference either.

**Fix.** Add a step naming both the variable and `sqlcredentials.txt`.

*Evidence: run 003 seq 421.*

### G-17 🟠 The resource inventory does not match the instructions

**Present** in `azureaiworkshoprg` but never accounted for: `myopai-<n>` (an empty,
unreferenced Azure OpenAI resource in West US), plus pre-provisioned `aisearch-<n>`,
`cosmosaivector-<n>`, `gw-bing-<n>`, `pgaivector-<n>`, `sqlaivector-<n>` and its `vectordb`
database.

**Absent**, but referenced by later labs: **any Computer Vision / Face resource** and **any
Logic App**. The Vision and Language labs depend on them.

Also, the `.env` instructions use example names from an earlier provisioning generation
(`ai-search-…`, `cosmos-…`, `sqlserver-…`) that no longer match the actual pattern
(`aisearch-…`, `cosmosaivector-…`, `sqlaivector-…`), and describe resources the learner
"created" when in this edition they are all pre-provisioned.

> **Uncertain:** whether the Vision/Language resources are meant to be learner-created
> later in those labs, or are genuinely missing from the image. Those labs were not
> reached, so this cannot be settled from run 003.

*Evidence: run 003 seq 660, 891.*

### G-20 🟠 The requirements notebook is not where the instruction says

**Instruction** — *"Open the LABS folder, if not opened already. Select
`06-pip-install-requirements.ipynb` to open the notebook"* — which reads as though the
notebook sits at the root of `LABS`. It does not.

There is exactly one copy, two levels down:

```
C:\Users\Admin\Desktop\LABS\Lab 00 - Prequisite - AI Foundry Resource Creation\06-pip-install-requirements.ipynb
```

…inside a folder whose name is misspelled (*"Prequisite"*, see G-16). A learner following
the instruction literally sees only `Lab 00`…`Lab 10` folders plus `.env.example`,
`requirements.txt` and `sqlcredentials.txt` at the root, and has to go hunting.

**Fix.** Give the full relative path.

*Evidence: run 003 seq 938.*

### G-21 🟠 The agent cell swallows a failed run and shows a green tick

In `quick_start.ipynb` Task 4 (*Create a Simple Agent*), `create_and_process()` returned
`RunStatus.FAILED`. The notebook **never inspects `run.status` or `run.last_error`** — it
iterates messages and prints only assistant turns. With no assistant turn, the cell:

- completes with a **green tick** in 15.1 s,
- prints **nothing**,
- saves no PNG,
- and raises nothing (the `try/except` never fires, because no exception occurred).

The learner is given a successful-looking cell with zero output and no way to tell success
from failure. This directly contradicts the lab's own *Laboratory Features → Error
Handling*: *"Comprehensive error messages and troubleshooting guidance."*

**This is model-independent** — the defect is the missing status check, not the model.

**Fix.** After `create_and_process`, assert `run.status != FAILED` and print
`run.last_error`.

*Evidence: run 003 seq 1248.*

### G-22 🟠 Choosing a replacement model: chat capability is not enough

Directly relevant to fixing **G-08**. Established from three tested observations, not one:

1. The Foundry account exposes **163 models**; **50** declare the `assistants` capability;
   only **26** of those are `GenerallyAvailable` and therefore deployable here — the rest
   are `Deprecating` and refused (G-08).
2. Of those 26, the only **non-OpenAI** options (`mistral-small-2503`, `cohere-command-a`)
   cannot be deployed at all:
   > *"Marketplace purchases are disabled for this subscription `<subscription-id>` due to
   > policy restrictions."*

   So the lab subscription is restricted to **first-party Azure OpenAI models**.
3. Within the first-party set, **the newest family is not a safe pick**. `gpt-5.6-sol`
   fails every Agents run with `invalid_prompt: "Unsupported parameter: 'top_p' is not
   supported with this model"` — the service injects `top_p`, and passing
   `top_p=None`/`temperature=None` to `create_agent` does not suppress it.
   **`gpt-5-mini` (2025-08-07) returns `RunStatus.COMPLETED`** with an assistant message on
   the same resource.

**Consequence for the lab author.** When this workshop is refreshed off `gpt-4o`, the
replacement must be validated **against the Agents API specifically**, not just chat
completions. A model can pass Lab 01 Task 3 and still fail Lab 01 Task 4 and all six Lab 02
notebooks. `gpt-5-mini` is a working choice today; `gpt-5.6-*` is not; Marketplace models
are not an option under current subscription policy.

*Evidence: run 003 seq 1404.*

### G-24 🟠 The Relevance evaluator fails 404 using exactly the documented values

100 % failure, from a fresh kernel with outputs cleared:

```
{"f1_score":  {"status":"Completed", "completed_lines":3, "failed_lines":0},
 "relevance": {"status":"Failed",    "completed_lines":0, "failed_lines":3}}
```

> `openai.NotFoundError: Error code: 404 - {'error': {'code': '404', 'message':
> 'Resource not found'}}`
> raised from `azure/ai/evaluation/_legacy/prompty/_prompty.py:382 _send_with_retries`,
> wrapped as `BatchEngineRunFailedError: (InternalError) 100% of the batch run failed`

**Root cause — a shape mismatch, not a missing value.** Setup step 4 says *"Copy Endpoint
Target URI and paste into .env file as the value for `AZURE_OPENAI_ENDPOINT`"*. The Target
URI that Foundry shows for a chat deployment is a **full operation path**:

```
AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
```

`azure-ai-evaluation` expects a **base** endpoint and appends
`/openai/deployments/<name>/chat/completions` itself — so the composed URL is nonsense and
the service returns 404.

The **correctly shaped value is already present in the same `.env`** under a different
name, `AZURE_OPENAI_BASE_URL_ENDPOINT=https://<resource>.openai.azure.com/`, but the
notebook does not read it and Setup never explains that the two variables want different
shapes. Contributing: neither `AOAI_API_VERSION` nor `API_VERSION` exists in `.env`
(verified count 0 for each), so `api_version` silently falls back to a hard-coded
`"2024-02-15-preview"`.

**Proven by a controlled A/B** — same cell, same data, same deployment, fresh kernel each
time; the **only** change was the value of `AZURE_OPENAI_ENDPOINT`:

| Run | `AZURE_OPENAI_ENDPOINT` | Result |
|---|---|---|
| A | as Setup step 4 instructs (Target URI) | `404 Resource not found` |
| B | base endpoint + `AOAI_API_VERSION=2024-12-01-preview` | `400 Unsupported parameter: 'max_tokens'` |

The **change of error class** is the proof: run A never reached a model; run B did. See
**G-26** for the second blocker that run B exposed.

**Impact.** Relevance is a headline Objective of Lab 01 Evaluations and is named in the
notebook's Key Features. **No learner following the instructions can obtain a relevance
score.**

**Fix.** Have Setup step 4 ask for the base resource endpoint, or point the notebook at
`AZURE_OPENAI_BASE_URL_ENDPOINT`; and add `AOAI_API_VERSION` to the template.

*Evidence: run 003 seq 1626, 1709.*

### G-25 🟠 The evaluation cell reports success while an evaluator failed completely

With `relevance` at status `Failed` and 3 of 3 lines failed, the cell still prints:

```
Local evaluation completed!
f1_score.f1_score          0.1870
f1_score.f1_threshold      0.5000
f1_score.binary_aggregate  0.0000
```

Nothing in the summary says `relevance` produced no result — the failure is visible only
inside a wall of promptflow logging above it. A learner skimming for the green tick
concludes both evaluators ran and the model simply scored badly.

This is **the same class of defect as G-21**: the notebooks treat *"the call returned"* as
*"the step succeeded"*.

**Fix.** Inspect the per-evaluator status block and fail loudly, or at minimum print a
warning naming the evaluator that failed and its error class.

*Evidence: run 003 seq 1627.*

### G-26 🟠 `requirements.txt` uses floors, so the documented setup keeps a stale SDK

Exposed by run B of the G-24 A/B: with the endpoint corrected, the error becomes

> `openai.BadRequestError: 400 - Unsupported parameter: 'max_tokens' is not supported with
> this model.`

`azure-ai-evaluation` **1.10.0** — the version on the VM image — drives its AI-assisted
evaluators through a legacy prompty path that sends `max_tokens`. Reasoning-family models
require `max_completion_tokens` and reject `max_tokens`. (Same pattern as the Agents
service rejecting `top_p` in G-22.)

**Why the documented setup does not fix it.** `requirements.txt` specifies **floors, not
pins**: `azure-identity>=1.24.0`, `azure-ai-projects>=1.1.0b2`, `azure-ai-evaluation>=1.10.0`,
`openai`. The image ships exactly 1.10.0 while **1.18.3** is available — and because
`>=1.10.0` is already satisfied, the documented `pip install` step in Lab 00 **will not
upgrade it**. The stale version persists through the documented setup.

**Why this compounds G-08.** The measured option space: 88 GA chat-capable models, but the
deployable first-party set is **entirely gpt-5 / o-series reasoning families** — every
non-reasoning `gpt-4o`/`gpt-4.1` model is refused (G-08), and every third-party model is
Marketplace-blocked (G-22). So the workshop is forced onto exactly the model families that
this stale SDK cannot call.

> **Untested hypothesis, stated as such.** A newer `azure-ai-evaluation` may emit
> `max_completion_tokens` and unblock this. Not tested during run 003, because upgrading
> the SDK mid-run risks destabilising Labs 02–10. `model-router` was also not tried.
> **Recommended for the lab author to verify before shipping a fix.**

*Evidence: run 003 seq 1709.*

### G-29 🟠 "Compare local vs. cloud evaluation results" is impossible as shipped

Verified in the Foundry portal (*firstProject → Protect and govern → Evaluation →
Automated evaluations*): run `health-fitness-eval-…`, status **Completed**. Its **Test
criteria lists exactly one entry — `bleu_score`** — and the metric dashboard has a single
"AI quality (NLP)" tab showing `bleu_score` 0.00 %, 0/3 passed. The "AI Quality
(AI Assisted) Metrics" column is empty.

Meanwhile the **local** run in the same notebook computes `f1_score` (and attempts
`relevance`). **Local produces F1, cloud produces BLEU — there is no overlapping metric**,
so Task 3's stated goal cannot be met.

This also contradicts the *Laboratory Features* section, which promises *"Quality metrics:
F1 Score, Relevance, Groundedness, Coherence, Fluency"* and *"Risk and safety evaluators"* —
the cloud run surfaces none of those, and no Risk and Safety tab is produced.

Separately: the only cloud result the learner sees is a red **0.00 % / 0-of-3-passed**
panel, with no explanation that the shipped sample data **deliberately contains a wrong
answer** (*"What is the capital of France?"* → *"London."*). A correct run therefore reads
as a total failure.

**Fix.** Configure the cloud evaluation with at least one evaluator in common with the
local run, and add a note that the synthetic data is intentionally imperfect.

*Evidence: run 003 seq 1763.*

### Minor findings

**G-04 🔵 "Click firstProject inside the All resources section" — no such view.**
*Go to Foundry portal* lands directly on `…/firstProject/home`, already scoped to the
project. There is no "All resources" section on that page; "All resources" is a top-right
dropdown. *Fix:* delete the step, or reword to *"You should land on firstProject. If not,
pick it from the All resources dropdown, top right."*

**G-05 🔵 The contents list shows "Lab 07- RAI" twice; the second is Lab 08.** The link
target is correct (`#lab-08---rag-patterns---graph-rag`); only the label is a copy-paste
error, so no content is unreachable. Related and cosmetic: contents say
*"Lab 10 - VectorDB"* while the body heading says *"Lab 10 - Vector-DB"*.

**G-06 🔵 "East US 2" is not where the instruction implies.** The Region dropdown's
**Recommended** group (~20 regions) does not include East US 2; it appears only under
**Other**, after typing to filter. *Fix:* *"Type East US 2 into the region filter (it
appears under Other)."*

**G-07 🔵 Three names for the same product.** *"Microsoft Foundry"*, *"Azure AI Foundry"*
and *"Foundry"* all appear in one corpus. The portal is inconsistent too — the services
tile reads "Foundry", the service page "Microsoft Foundry", the button "Go to Foundry
portal". Worth one consistency pass; note that screenshots will age faster than the text.

**G-14 🔵 The embedding Target URI shape is wrong.** Both step 5 and the template show the
embedding endpoint as `…/openai/deployments/<name>/chat/completions?api-version=…`. An
embedding deployment's Target URI ends **`/embeddings`**. Step 5 repeats step 4's chat
wording verbatim.

**G-15 🔵 Template host and instruction host disagree.** `.env.example` shows
`https://xxxxxxx.openai.azure.com/…`, while step 4 describes the Target URI as
`https://<AI-FOUNDRY-NAME>.cognitiveservices.azure.com/…`. A Foundry resource created today
issues `.cognitiveservices.azure.com` (and `.services.ai.azure.com` for the project
endpoint), so the **template** carries the stale host. Harmless if the learner pastes the
real URI; confusing if they pattern-match the template.

**G-16 🔵 Typos shipped in the lab assets.** `.env.example` line 3 ends
`/api/projects/deafultProject` (*deafult*); the do-not-modify block declares
`EMBEDDING_MODEL_DIMNESIONS=1536` (*DIMNESIONS*) — which the lab code must therefore also
misspell; and the lab root folder is named *"Lab 00 - Prequisite - AI Foundry Resource
Creation"* (*Prequisite*).

**G-18 🔵 "Azure AI Search" has been rebranded.** The portal now shows **"AI Search
(Foundry IQ)"** in global search, the service list header reads *"Microsoft Foundry | AI
Search"*, and the resource Type column reads *"Search service (Foundry IQ)"*. A learner
searching for the exact string *"Azure AI Search"* gets Marketplace offers rather than the
service blade.

**G-19 🔵 "SQL Servers" is not a label the portal offers.** Step 10 says *"Select SQL
Servers from the search results"*; the portal offers *"SQL server"* (singular), *"SQL
elastic pool"*, *"SQL Server databases"* and *"SQL Server instances"*. A learner scanning
for the exact string has to guess.

**G-23 🔵 Two contents links land on a repeated title, not the lab.** The anchors
`#evaluations-with-azure-ai-foundry` (Lab 01 Evaluations) and
`#lab-08---rag-patterns---graph-rag` are each **shadowed by a duplicate title heading**: the
instruction HTML emits the section title twice — once as a level-2 heading, once as the
level-1 section — both carrying the same `id`. A browser resolves to whichever comes first,
which is the level-2 duplicate. All 23 sections were checked; only these two are affected.
*Fix:* emit the title once, or give the duplicate a distinct id.

**G-27 🔵 Task 1 describes four activities the notebook does not implement.** Task 1
*"Environment Setup and Basic Configuration"* lists (a) initialise `AIProjectClient` with
browser-based auth, (b) perform basic LLM calls, (c) list and inspect project connections,
(d) verify model deployments and connectivity. `1-evaluation.ipynb` has eight cells — three
markdown headers plus Setup, Local Evaluation and Cloud Evaluation. Cell 4 loads environment
variables but constructs no `AIProjectClient`; that happens only in the Cloud Evaluation
cell, with `DefaultAzureCredential`. Nothing performs a basic LLM call, lists connections,
or verifies deployments. Those three **are** implemented — in the *previous* lab's
`setup and quick_start.ipynb` — which suggests Task 1 was copy-pasted. Non-blocking, but had
(b) and (d) existed here they would have surfaced **G-24** immediately instead of letting it
appear as an opaque 404 inside a batch runner.

**G-28 🔵 The notebook misdescribes its own auth model.** The Key Features cell claims
*"Browser Authentication — Uses `InteractiveBrowserCredential`"*, and Task 1 says the same.
The shipped code imports and uses **`DefaultAzureCredential`**; `InteractiveBrowserCredential`
is never imported. Cosmetic in effect, but a learner troubleshooting an auth failure would
go looking for a browser prompt that never appears.

---

## Standing risks — not defects today, but scheduled to become them

### R-01 ⚠️ Every lab depends on a legacy UI that is being retired

The workshop requires the **legacy Microsoft Foundry UI**, reached with the **New Foundry**
toggle.

**Verified working today.** The portal opens in New Foundry with the toggle on; the switch
is present top-right; toggling produces the legacy UI with the left-hand menu (`Model
catalog`, `Playgrounds`, `Agents`, `Fine-tuning`, …) that Labs 01–10 navigate by. The
feedback popup appears exactly as documented and *Continue without feedback* is present.

**But** New Foundry is the default and the page carries a permanent *"Try the new Microsoft
Foundry experience"* banner. **When that toggle is removed, every lab in this workshop
breaks at the same moment**, because all navigation is written against the legacy menu.

**Recommendation.** Treat this as the workshop's single point of failure. Re-check it on
every validation run — it is the cheapest high-value assertion available — and plan a
rewrite against New Foundry navigation before the toggle is withdrawn.

### R-02 ⚠️ Superseded by G-08

Run 002 recorded the `gpt-4o` family as *on a published retirement path, still deployable
today*. Run 003 showed that on a Skillable subscription **the risk has already
materialised** — see **G-08**. Kept here only so the change of state is visible.

**Not** a defect: `text-embedding-ada-002` (11 references) *looks* legacy, but the
lifecycle API reports it `GenerallyAvailable` until **2028-02-09**, and it deploys
successfully. Left alone deliberately.

---

## Verified correct

Recorded so that "checked and fine" is never confused with "not checked". 1,529 steps
passed; this is the representative set.

| Instruction | Result |
|---|---|
| Search "Microsoft Foundry" in the portal search bar | ✅ top **Services** result |
| "Under Overview, click Create a resource" | ✅ present |
| Resource group `azureaiworkshoprg` pre-exists and is selectable | ✅ |
| Foundry resource name accepted; default project name deletable; `firstProject` accepted | ✅ default was `proj-default` |
| "In less than 2 minutes your deployment should complete" | ✅ ~1 min 20 s |
| "click Go to resource" → "Go to Foundry Portal" | ✅ (renders "Go to Foundry portal") |
| "If the feedback popup is displayed, click Continue without feedback" | ✅ exact match |
| "In the left side menu, Click Model catalog" | ✅ present in legacy UI |
| Deploy `text-embedding-3-large` and `text-embedding-ada-002` | ✅ both succeed |
| Create the **Bing** connection (Setup §3) | ✅ as documented |
| Create the **Azure AI Search** connection (Setup §4) | ✅ as documented, once past the G-18 rename |
| `06-pip-install-requirements.ipynb` installs cleanly | ✅ once found (G-20) |
| Lab 01 Quick Start Tasks 1–3 (config, LLM call, connections) | ✅ |
| Lab 01 Evaluations Task 2 — `f1_score` evaluator | ✅ computes (0.1870 — low **by design**, see G-29) |
| Lab 01 Evaluations Task 3 — cloud evaluation submits and completes | ✅ 12.9 s; verified **Completed** in the portal |

---

## Withdrawn — recorded so they are never re-reported

Six findings were retracted after re-checking. Keeping them visible is the point: a
validator that never withdraws anything is not checking itself.

| What was claimed | Why it was wrong |
|---|---|
| `AZURE_OPENAI_ENDPOINT` missing from `.env` (and a consequent model-config finding) | The evidence was a **scrolled terminal**, not the whole file. An exhaustive per-key count showed it present exactly once. *Lesson: a negative claim needs an exhaustive read.* |
| Sign-in failure — *"We couldn't find an account with that username"*, twice, minutes apart | **Entra replication lag** on a freshly provisioned Cloud Slice user. Succeeded on the third try with a byte-identical username; the lab's own dialog reported the credentials valid for another 7 h 39 m. Clicking *Refresh Credentials* would have destroyed a valid credential set. |
| A step timing out | Recovered on retry — a transient, not a defect. |
| An agent-failure finding superseded by a better-evidenced one | Replaced by G-21/G-22, which identify the actual cause. |
| A deployment failure attributed to the wrong cause | Superseded by G-08 once the subscription-level root cause was proven. |

Telling *"the lab is wrong"* apart from *"the cloud is still catching up"* is the hardest
part of validating these labs, and the reason every finding above cites either an oracle or
a repeated observation.

Also **not a gap**: the deliberately-wrong sample data in Lab 01 Evaluations
(*"capital of France"* → *"London."*). The low F1 and 0 % BLEU are **by design**. It is
recorded under G-29 only because nothing tells the learner that, so a correct run reads as
a failure.

---

## Still to check

15 of 23 sections were never reached. Highest value first:

1. **Lab 02 – Agents** (6 notebooks). Expected to work under a `gpt-5-mini` substitution;
   guaranteed to fail as written because of G-08.
2. **Lab 09 – Security** — the largest module. Red-teaming scan (the instructions
   themselves say 30–45 min), `pip install azure-ai-evaluation[redteam]`, pinned
   `MODEL_API_VERSION="2024-12-01-preview"`.
3. **Lab 10 – Vector-DB** — three sub-labs (Cosmos DB, PostgreSQL, Azure SQL) with
   `pg_restore` from on-disk backups and hardcoded paths under
   `C:\Users\Admin\Desktop\LABS\`. **G-09 lands here** — expect the vector lab to fail on
   `CSV_PATH`.
4. **Labs 03 (Language) and 04 (Vision)** — G-17 predicts missing Computer Vision / Face /
   Logic App resources. Confirm whether they are learner-created or genuinely absent.
5. **Lab 05 – Fine-Tuning** — confirm **G-03** in the running catalog, and note that the
   section title references *GPT-4.1-mini*, which G-08 says cannot be deployed.
6. **Preview API versions** — `2024-05-01-preview`, `2024-12-01-preview` are referenced but
   there is **no machine-readable lifecycle feed for Azure OpenAI API versions**, so these
   can only be validated by execution. Currently the largest oracle blind spot.
7. **`azure-ai-evaluation` ≥ 1.18** — test the G-26 hypothesis on a disposable instance.
