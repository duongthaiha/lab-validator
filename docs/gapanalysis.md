# Gap analysis — WorkshopPLUS: Azure AI Platform and Services

What a learner is told to expect, versus what is actually in front of them.

**Lab** 79233, edition 2026031B · **Validated** 2026-07-29/30
**Runs** 002 (shallow) + 003 (deep, 8 sections) + 004 (deep, 16 sections) +
**005 (deep, all 23 sections — corpus complete, + Lab 08 config deep-dive)**
**Instruction corpus** 2,264 lines / 109,703 chars · 23 sections across 12 modules
**81 gaps** recorded, plus 2 standing risks

This is the **learner- and author-facing** output. Engineering notes live in
[`docs/approach.md`](approach.md); raw per-run evidence lives in `runs/<timestamp>/`
(gitignored — screenshots contain live API keys).

Resource names and subscription IDs are redacted to `<...>` throughout.

---

## Read this first

> **Two structural defects gate the entire workshop. Everything else is downstream.**
>
> **1 — The models the workshop names cannot be deployed.** `gpt-4o`, `gpt-4o-mini` and
> `gpt-4.1` are all refused with `ServiceModelDeprecating` on a Skillable lab subscription.
> Not quota, not region, not transient (**G-08**).
>
> **2 — The deployments that *do* exist are lying about what they are.** The lab image ships
> deployments **named** `gpt-4o` and `gpt-4o-mini` that actually serve
> **`gpt-5-mini-2025-08-07`** (**G-30**). Proven three independent ways: the portal's
> *Models + endpoints* blade, `response.model` from a live completion, and
> `az cognitiveservices account deployment list`.
>
> G-30 is the more dangerous of the two, because it does not announce itself. The lab appears
> to work, and then fails obliquely — `temperature` rejected, `max_tokens` rejected, DRIFT
> search refused — in five different labs, each of which reads as an unrelated bug.
>
> **3 — The one file every notebook depends on is wrong in two independent ways
> (G-71, G-70).** The shipped `.env` sets `AZURE_OPENAI_ENDPOINT` to a full
> `/openai/responses?api-version=…` **operation** URL where an SDK needs a **base** URL, and
> the three notebooks that read it each load it from a **different wrong relative path** —
> none of the three correct. Together these break Lab 06, Lab 09, Lab 10's SQL module and
> both optional labs. Neither defect is visible in the lab text; both are one-line fixes.

**Suggested order of repair**

| Priority | Fix | Why first |
|---|---|---|
| 1 | **G-08 + G-30** — pick a model that (a) deploys and (b) is what the deployment is named after | Nothing downstream can be validated until this clears, and the silent substitution makes every other failure unreadable. Bumping to `gpt-4.1` does **not** work — it is already refused. **`model-router` v2025-11-18 is a proven candidate — see *A tested way out* below.** |
| 2 | **G-31** — reconcile the substituted model's parameter surface | `gpt-5-mini` rejects `temperature` and `max_tokens`. Lab 06 has 22 `temperature` call sites; Lab 08's DRIFT search sends `temperature=0`. |
| 3 | **G-22** — validate the replacement against the **Agents** API, not just chat completions | A model can pass Lab 01 Task 3 and still fail Lab 01 Task 4 and all six Lab 02 notebooks. |
| 4 | **G-09, G-11, G-12, G-13, G-24, G-32, G-71, G-70, G-54** | The `.env` chain — now **nine** defects in one file. Every notebook in the workshop reads it. The endpoint **shape** (G-71) alone breaks Labs 01, 06, 09, 10 and both optional labs; a single mistyped variable name (G-54) is a hard blocker for Lab 10 Cosmos. |
| 5 | **G-69, G-62** — materials the learner cannot obtain | Three labs point at files that are not on the VM and not reachable: both optional notebooks are absent from the image, and Azure SQL's only instruction is a link that 404s. No amount of fixing the text helps until the assets exist. |
| 6 | **G-21, G-25, G-33** — cells that report success while failing | These hide every other defect from the learner. G-33 is the worst: a red-team scan that prints `Scan completed successfully!` having scored nothing. |
| 7 | **G-34, G-35** — dependency pins | `pyrit`/`duckdb` and `azure-ai-evaluation`/`graphrag` are all resolved by floor, so the image drifts away from the docs. |
| 8 | Everything else | Navigation, labels, typos. |

---

## Coverage — the corpus is now complete

| | Sections | Status |
|---|---|---|
| **Walked hands-on**, doing the work — notebook cells executed, results inspected | **23 of 23** | Every section of the corpus has been reached and exercised |
| of which **completed** | 20 | |
| of which **blocked** by a defect | 3 | Deploy models (G-08), Responsible AI (G-39), Graph RAG (G-40 — now decomposed into G-76…G-81) |
| **Never reached** | **0 of 23** | — |
| **Statically analysed** — model IDs vs the Azure model-lifecycle API, TOC/anchor structure, resource inventory | 23 of 23 | 100 % |

Runs 004 + 005 together recorded **5,880+ steps**, **111 heartbeats** and **980+ evidence
images** against instance `f469219f-…`. **220+ findings stand** — 40 critical, 85 major,
84 minor, 13 informational; **7 were retracted** after re-checking (see *Withdrawn*).

> **Every section now has positive or negative evidence behind it.** Where a section is
> marked blocked, the block itself is the finding and the material *behind* the block was
> still verified by applying the fix on a scratch copy — so "blocked" here means *a learner
> cannot proceed*, not *we do not know what is there*.
>
> **"Blocked" is a status, not a finding.** Lab 08 sat as a single blocker (G-40) until it
> was re-examined against the GraphRAG version `pip install` actually resolves to today;
> that turned one vague blocker into **six** further independently fixable defects (G-76…G-81)
> and corrected G-40's own factual claim. Any section left at *blocked* should be assumed
> to be hiding findings in the same way.
>
> **G-09 landed exactly where it was predicted to.** The run-004 note said `CSV_PATH` would
> surface in Lab 10; it did, and it is confirmed live (G-65).

---

## Findings

🔴 critical · 🟠 major · 🔵 minor

Findings **G-01 – G-29** come from runs 002/003 (Required Lab Setup + Lab 01) and are listed
first. Findings **G-30 onward** are new in run 004 (Labs 02–09) and are grouped by lab
below.

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

### New in run 004 — Labs 02 to 09

| ID | Sev | Module | Gap |
|---|---|---|---|
| **G-30** | 🔴 | All labs | **Deployments named `gpt-4o` / `gpt-4o-mini` actually serve `gpt-5-mini-2025-08-07`** |
| **G-31** | 🔴 | Labs 06, 08 | The substituted model **rejects `temperature` and `max_tokens`** — 22 call sites in Lab 06 alone |
| **G-33** | 🔴 | Lab 09 – Security | **Red-team scans score nothing** and still print `Scan completed successfully! Overall ASR: 0.0%` |
| G-36 | 🔴 | Lab 02 – Agents | Three of six exercises cannot be completed: Bing grounding, AI Search tool, multi-agent |
| G-37 | 🔴 | Lab 03 – Language | Bonus section dead: **Actions / `+ Add` is greyed out** on the classic agent, and the "new agents" surface does not restore it |
| G-38 | 🔴 | Lab 04 – Vision | OCR returns **410 Gone** on the documented `api-version`; Video Indexer needs four settings the lab never creates |
| G-39 | 🔴 | Lab 07 – RAI | The storage account and container the setup step depends on **do not exist**; *Manual evaluations* has been removed from the portal |
| G-40 | 🔴 | Lab 08 – Graph RAG | Lab points at `myopai-<id>`, which has **zero deployments** — indexing aborts in ~30 s |
| G-41 | 🔴 | Lab 09 – Security | `AZURE_OPENAI_ENDPOINT` is a Responses URL → every model-target attack is a **404** |
| **G-32** | 🟠 | Setup `.env` | `AZURE_OPENAI_ENDPOINT` **shape** is documented three different ways; all three disagree |
| **G-34** | 🟠 | Lab 09 – Security | `pyrit` 0.8.1 vs `duckdb` 1.4.0 → `unhashable type: DuckDBPyType` → 0 conversations persisted |
| **G-35** | 🟠 | Lab 08 – Graph RAG | `graphrag` 3.1.1 vs the lab's 2.7.0 — **three** copy-paste CLI breaks |
| G-42 | 🟠 | Labs 02, 09 | `az login` is an **undocumented prerequisite**, and the account's **TAP expires** mid-lab |
| G-43 | 🟠 | Lab 02 – Agents | Notebooks load `.env` from a path that does not exist; several ship **pre-populated output** |
| G-44 | 🟠 | Labs 03, 07 | **Agent Deprecation Notice** modal blocks `+ New agent`; the lab never mentions it |
| G-45 | 🟠 | Lab 04 – Vision | Five sections ship **un-set placeholder image paths**; `LabFiles` has no assets for them |
| G-46 | 🟠 | Lab 08 – Graph RAG | "Estimated Time: 30 minutes" — measured **60–90 min** |
| G-47 | 🟠 | Lab 09 – Security | Markdown tells learners to **ignore HTTP 400s** "as it is triggering the model's security filter" |
| G-48 | 🟠 | Lab 09 – Security | The advanced callback **swallows every exception** and returns a canned safe reply |
| G-49 | 🟠 | Lab 07 – RAI | Hub-era navigation throughout: *"Underneath Hub, select Connected resources"* |
| G-50 | 🔵 | Lab 09 – Security | The notebook is **never named** anywhere in the 99-line section |
| G-51 | 🔵 | Lab 09 – Security | Notebook prescribes a `.venv` + `uv pip install`; the lab text and the machine both say otherwise |
| G-52 | 🔵 | Several | Broken links: `ai-studio/concepts/evaluation-approach` → 404 after the Foundry rename |
| G-53 | 🟠 | Lab 09 – Security | The notebook promises a **link to your results in Azure AI Foundry**; no URL is ever printed |

*Plus 130 further minor and informational findings recorded in the run trace — labels,
typos, stale screenshots, and step-level inconsistencies too granular to list here.*

### New in run 005 — Lab 10 and the optional labs

| ID | Sev | Module | Gap |
|---|---|---|---|
| **G-71** | 🔴 | Setup `.env` / all labs | **`AZURE_OPENAI_ENDPOINT` is a Responses *operation* URL, not a base URL** — breaks Labs 01, 06, 09, 10 and both optional labs |
| **G-70** | 🔴 | Labs 06 + both optional | **Three notebooks load `.env` from three *different* wrong relative paths** — none correct |
| **G-54** | 🔴 | Lab 10 – Cosmos DB | `.env.example` ships `EMBEDDING_MODEL_DIMNESIONS`; the notebook reads `..._DIMENSIONS` → `KeyError` at **cell 2** |
| **G-62** | 🔴 | Lab 10 – Azure SQL | The lab's **only** actionable instruction is a `SQL folder` hyperlink that **404s** |
| **G-65** | 🔴 | Lab 10 – Vector-DB | **G-09 confirmed live**: `CSV_PATH` points at a folder that does not exist, and step 16 forbids fixing it |
| **G-66** | 🔴 | Lab 10 – Vector-DB | `4_SQLEmbeddings.py` carries a **four-defect chain**; steps 23 and 25 both die as shipped |
| **G-69** | 🔴 | Both optional labs | **Neither optional notebook is on the lab VM**, and neither section gives a path or repo |
| **G-57** | 🟠 | Lab 10 – PostgreSQL | The script the lab tells you to open, `VectoryQuery.sql`, **does not exist** — confirmed live in pgAdmin |
| **G-58** | 🟠 | Lab 10 – PostgreSQL | `create extension azure_ai` ships **without a terminating semicolon** — the script fails as shipped |
| **G-59** | 🟠 | Lab 10 – PostgreSQL | The endpoint template `https://<your-endpoint>.openai.azure.com/` has the **wrong domain** for this lab's resource |
| **G-60** | 🟠 | Lab 10 – PostgreSQL / SQL | "Open your Azure OpenAI resource" — **two** exist and only one has the deployments |
| **G-63** | 🟠 | Lab 10 – Azure SQL | The entire lab body is **26 lines with no steps**: no file list, no connection details, no expected output |
| **G-67** | 🟠 | Lab 10 – Vector-DB | Step 23 calls a **mandatory** script "optional"; skipping it makes step 25 fail |
| **G-72** | 🟠 | Both optional labs | The sections contain **no executable steps at all**, and the TMS section name does not match the repo folder |
| **G-73** | 🟠 | Optional Lab – RAG | "Configure Azure AI Search for vector search" is **never delivered** — Exercise 8 defines a function and never runs it |
| **G-75** | 🟠 | Lab 06 – Prompt Engineering | The broken `.env` path is **masked by VS Code**, so the learner debugs the wrong error |
| **G-55** | 🔵 | Lab 10 – Cosmos DB | The dimension value is wrong too — `1536` against a `text-embedding-3-large` deployment (`3072`) |
| **G-56** | 🔵 | Lab 10 – Cosmos DB | "The database has been pre-created for you" — the notebook creates it itself |
| **G-61** | 🔵 | Lab 10 – PostgreSQL | Ordering inversion, unlocated `sqlcredentials.txt`, moved *Server parameters*, renamed *Go to Foundry portal*, "consine", L2-vs-cosine |
| **G-64** | 🔵 | Lab 10 – Azure SQL | `2_LoadMovideData.py` (real name `2_LoadMovieData.py`); Objectives say "using **PostgreSQL**" |
| **G-68** | 🔵 | Lab 10 – Vector-DB | SSMS pre-fills a **stale server name** from the image; `Options >>` is now `Options <<`; `.env.example` ships a real password in clear text |
| **G-74** | 🔵 | Both optional labs | `%pip install azure-search` — abandoned 2019 package, and both notebooks re-install what `requirements.txt` already provides |

### New in run 005 addendum — Lab 08 Graph RAG, config-level deep dive

Lab 08 was previously recorded only as blocked (G-40), with G-35 noting that its GraphRAG
commands had drifted. Re-examining it against the version `pip install graphrag` actually
resolves to today (**3.1.1**) turned one vague blocker into six further, individually fixable
defects — plus a correction to G-40 itself.

| ID | Sev | Module | Gap |
|---|---|---|---|
| **G-76** | 🔴 | Lab 08 – Graph RAG | The `init` prompts' **defaults are `gpt-4.1` / `text-embedding-3-large`** — a model G-08 proves cannot be deployed, and neither matches the lab's own prerequisites |
| **G-77** | 🔴 | Lab 08 – Graph RAG | **No `sed` ever sets `model:`**, so even a correctly-deployed learner gets `DeploymentNotFound` |
| **G-78** | 🟠 | Lab 08 – Graph RAG | **`pip install graphrag` cannot succeed off Linux** — `litellm==1.92.0` ships manylinux wheels only; the prerequisite states no OS |
| **G-79** | 🟠 | Lab 08 – Graph RAG | The stated floor **"Python 3.10 to 3.12"** is wrong — graphrag 3.1.1 requires `>=3.11` |
| **G-80** | 🟠 | Lab 08 – Graph RAG | `export AZURE_OPENAI_ENDPOINT=<instance>.openai.azure.com` — **no `https://` scheme**; httpx rejects it |
| **G-81** | 🔵 | Lab 08 – Graph RAG | `api_version: 2024-05-01-preview` is pinned here but the workshop `.env` uses `2025-04-01-preview` |

> **G-35 already flagged that `graphrag init` is interactive** — that is not re-reported here.
> What is new is *why it matters*: the prompt's defaults are actively wrong (G-76), and
> nothing later in the lab corrects them (G-77).

---

### G-30 🔴 The deployment named `gpt-4o` is not `gpt-4o`

**The defect that makes every other defect unreadable.** The lab image pre-creates two chat
deployments. Their **names** are `gpt-4o` and `gpt-4o-mini`. The **models behind them** are
`gpt-5-mini`, version `2025-08-07`.

Three independent confirmations, deliberately taken from three different planes:

| Surface | Evidence |
|---|---|
| Portal | *My assets → Models + endpoints* lists deployment `gpt-4o` with **Model name `gpt-5-mini`, version `2025-08-07`** |
| SDK | A successful chat completion against deployment `gpt-4o` returns `response.model = "gpt-5-mini-2025-08-07"` |
| ARM | `az cognitiveservices account deployment list -n ai-foundry-<id>` reports `gpt-4o → gpt-5-mini (2025-08-07)` |

**Why it matters more than G-08.** G-08 is loud: the deployment is refused and the learner
stops. G-30 is silent. The learner proceeds, and then meets a scatter of unrelated-looking
failures across Labs 06, 08 and 09 — every one of which is really this.

**Suggested fix.** Either deploy the model the labs are written against, or rename the
deployments to match what they serve and update every notebook's parameter usage (G-31).
Naming a deployment after a model it does not serve is the worst of both.

---

### G-31 🔴 The substituted model rejects the parameters the labs use

Direct consequence of G-30. `gpt-5-mini` does not accept `temperature` or `max_tokens`.

| Lab | Call | Result |
|---|---|---|
| Lab 06 – Prompt Engineering | `max_tokens=50` | **HTTP 400** — `Unsupported parameter: 'max_tokens' is not supported with this model` |
| Lab 06 – Prompt Engineering | `temperature=…` | **HTTP 400** — only the default (1) is supported |
| Lab 08 – Graph RAG | DRIFT search sends `temperature=0` | `litellm.BadRequestError: … Only the default (1) value is supported` |

**Blast radius, counted statically over `Prompt Engineering.ipynb`:** 18 ×
`client.chat.completions.create`, 22 × `temperature`. The first practical cell
(Zero-Shot Prompting) fails, so **no** subsequent cell in that notebook produces output.

**A misdiagnosis this causes.** Lab 08 comments its DRIFT block out with *"not working as of
GraphRAG v2.7.0"*. That is wrong — the DRIFT code path is fine; it is the substituted model
refusing `temperature=0`. The lab author has attributed a local environment defect to an
upstream project.

---

### G-33 🔴 The red-team scan reports success having measured nothing

**Lab 09 exists to teach Attack Success Rate. ASR cannot be produced on this image.**

**All four scans in the notebook were run to completion.** Every one ends the same way:

| Cell | Scan | Attack strategies | Result | Wall clock |
|---|---|---|---|---|
| 14 | Basic-Callback-Scan | 1 | `0/0`, empty scorecard | 26.7 s |
| 18 | Intermediary (model target) | 1 | `0/0`, empty scorecard | 26.8 s |
| 24 | Advanced-Callback-Scan | 13 groups × 4 risk categories = **52 tasks** | `0/0`, empty scorecard | **41 m 41 s** |
| 28 | Custom-Prompt-Scan (bring-your-own objectives) | EASY + MODERATE + DIFFICULT = 24 tasks | `0/0`, empty scorecard | 4 m 6 s |

The output in each case:

```
Overall ASR: 0.0%
Attack Success: 0/0 attacks were successful
Risk Category      | Baseline ASR  | Easy-Complexity Attacks ASR | ...
-------------------------------------------------------------------
📁 All scan files saved to: .\scan_…
✅ Scan completed successfully!
```

Note **0/0**, and a scorecard header with no rows.

**What is actually happening** (from `redteam.log`):

1. `pyrit\memory\duckdb_memory.py:167 _insert_entries` raises
   `TypeError: unhashable type: '_duckdb.typing.DuckDBPyType'`
2. `Successfully wrote 0 conversations to …jsonl` *(sic)*
3. `WARNING – No valid conversations found in …jsonl, skipping evaluation`
4. `Processed 0 conversations from all data files`
5. `No evaluation results available or no data found, creating default scorecard`

That default scorecard is what the learner reads as "0.0% ASR". Every conversation
`.jsonl` file across all four scans is **0 bytes**; `final_results.json` carries
`overall_total: 0`, `joint_risk_attack_summary: []`, `techniques_used: {baseline: [], easy: []}`.

**Why this is the worst kind of defect.** The notebook's own markdown tells the learner to
*expect* 0 % ASR for the first example. A completely broken pipeline is therefore
indistinguishable from the documented happy path. The attacks *are* dispatched — the
progress bars reach 4/4, 52/52 and 24/24, and the Azure inference spend is real — so
nothing on screen suggests a problem.

**And it is expensive to discover.** The advanced scan ran for **41 minutes 41 seconds**,
inside the lab's own "30–45 minutes" estimate, dispatching 52 batches of attacks, before
printing an empty table. A learner has no reason to doubt it: the run took exactly as long
as the instructions said it would.

Root cause is a dependency floor, not the lab's code: see **G-34**.
See also **G-53** for the learner-facing consequence.

---

### G-53 🟠 The promised link to results in Foundry never appears

The notebook's markdown, immediately after the advanced scan, says:

> The data and results used in this attack will be saved to the `output_path` specified.
> **The URL printed out at the end of the scorecard will provide a link to where you
> results are uploaded and logged to your Azure AI Foundry project.**

No such URL is printed. All four scans end with exactly two lines after the scorecard:

```
📁 All scan files saved to: .\.scan_<name>_<timestamp>
✅ Scan completed successfully!
```

There is no link, and nothing appears under the project in Foundry. This is a downstream
consequence of G-33 — the upload happens inside the evaluation step, which is skipped —
but it is worth listing separately because it is what the *learner* experiences: the lab
directs them to look for something that does not exist, and offers no alternative route to
view results. A learner following the text will conclude they configured `azure_ai_project`
incorrectly and go looking for a mistake they did not make.

**Fix.** Resolve G-34 first. If the upload is genuinely no longer part of the SDK's
behaviour, delete the sentence rather than leaving learners hunting for a phantom URL.

---

### G-34 🟠 `pyrit` / `duckdb` version skew (root cause of G-33)

| Package | Installed on the image | Notes |
|---|---|---|
| `azure-ai-evaluation` | 1.10.0 | PyPI is at 1.18.3 — **8 minor versions ahead** |
| `pyrit` | 0.8.1 | PyPI is at 1.0.1 |
| `duckdb` | 1.4.0 | Post-dates `pyrit` 0.8.1 |
| `SQLAlchemy` | 2.0.43 | |

`pyrit` 0.8.1's SQLAlchemy type registration is no longer hashable under `duckdb` 1.4.
The lab's own instruction — `pip install azure-ai-evaluation[redteam]` — **cannot** fix
this: without `-U`, pip treats an already-installed distribution as satisfied and does
nothing (≈2 minutes of *"Requirement already satisfied"*).

**Suggested fix.** Pin (`duckdb<1.1` for `pyrit` 0.8.1) or upgrade to
`azure-ai-evaluation` 1.18.x / `pyrit` 1.x. Either way, **pin — do not floor**. This is
the same class of defect as G-26.

*Untested hypothesis, labelled as such:* upgrading is expected to clear G-33, but we did
not upgrade mid-run because it would have destabilised the remaining labs.

---

### G-35 🟠 Lab 08's GraphRAG commands do not exist any more

The lab is written against GraphRAG **2.7.0**; the environment installs **3.1.1**. Three
documented commands fail as copy-pasted:

| Line | Documented | Actual in 3.1.1 |
|---|---|---|
| ~L95 | `graphrag init --root ragtest` runs unattended | **Interactive** — prompts for default chat model and embedding model |
| L113–116 | `graphrag query … --query "…"` | `Error: No such option: --query` — the query is now **positional** |
| L134–138 | `graphrag prompt-tune … --config …` | `Error: No such option: --config` — removed in 3.x |

Corroborated against upstream `microsoft.github.io/graphrag/get_started/`, which documents
interactive `init` and positional `query` as intended behaviour.

Two further problems found by executing rather than reading:

- `prompt-tune` crashes with `KeyError: 'entity_types'` when entity discovery returns empty.
  **Workaround verified:** add `--no-discover-entity-types` → exits 0 in ~4 min.
- The lab never sets the documented `azure_deployment_name` in `settings.yaml`. It works here
  only because the deployment names happen to equal the model names.

---

### G-41 🔴 Lab 09's model-target scan 404s on every attack

`redteam.log`:

```
httpx.HTTPStatusError: Client error '404 Resource Not Found' for url
'https://ai-foundry-<id>.cognitiveservices.azure.com/openai/responses?api-version=2024-06-01'
```

Chain of causation:

1. Required Lab Setup writes `AZURE_OPENAI_ENDPOINT` as a **Responses-API URL**, complete
   with its own `api-version`.
2. The notebook passes that string to `azure_oai_model_config["azure_endpoint"]`.
3. PyRIT treats it as a **base** URL and rewrites `api-version` to `2024-06-01`.
4. The resulting path does not exist.

So the exercise that is meant to demonstrate red-teaming a real Azure OpenAI deployment
reaches the model **zero** times — and still reports a clean 0 % ASR, because of G-33.

See **G-32**: the same variable is documented with three mutually incompatible shapes.

---

### G-32 🟠 One variable, three contradictory definitions

`AZURE_OPENAI_ENDPOINT` is specified differently in three places a learner will read:

| Source | Value shape |
|---|---|
| Required Lab Setup §5 / Lab 09 line 28 | `https://<name>.openai.azure.com/openai/deployments/<dep>/chat/completions` |
| `AI_RedTeaming.ipynb` markdown, immediately above the cell that consumes it | `https://<name>.cognitiveservices.azure.com/` — bare host |
| The `.env` the lab image actually ships | `https://<name>.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview` |

The **bare host** is what the `openai` SDK's `AzureOpenAI(azure_endpoint=…)` wants. The
notebook is right and the lab text is wrong. Nothing validates the value at load time — the
`os.environ.get` cell runs in 0.0 s and reports nothing — so the failure surfaces many cells
later, disguised as a model problem.

This is the same root cause as G-24 (Lab 01's Relevance evaluator 404) and the Lab 06
blocker, which makes it the single highest-leverage `.env` fix.

---

### G-42 🟠 `az login` is required, undocumented, and expires mid-lab

Two separate problems that compound.

**It is never documented.** Lab 01, Lab 02 and Lab 09 all fail on their first credential
call unless the learner has run `az login`. No section says to. In Lab 09 the requirement
is buried as a bare `!az login` shell escape inside notebook cell 4.

**The credential expires before the lab does.** The lab account signs in with a **Temporary
Access Pass**. The instance is provisioned for **96 hours**; a TAP lives for a few. Every
CLI-derived token inherits the TAP's lifetime, so any learner who takes a long enough break
is locked out.

The failure mode is unusually bad:

- `!az login` does not error — it **hangs indefinitely** behind the Windows WAM broker
  (observed to 3 m 46 s with zero output, no pending auth prompt anywhere).
- Interrupting the cell makes it complete **green** in 4 m 18 s with output `^C`, because
  the next statement, `credential = AzureCliCredential()`, succeeds against the stale cache.
- The real error appears **four cells later**, as a 13-second scan failure:
  `AADSTS130504: Your Temporary Access Pass has expired.`

**Recovery that works** (worth adding to the lab as a troubleshooting note):

```powershell
az config set core.enable_broker_on_windows=false
az account clear
az login --use-device-code --scope https://ai.azure.com/.default
```

then open `https://login.microsoft.com/device` **in the browser on the lab VM** — the
interactive session is still valid even though the TAP is not. Note `az login` then blocks
on an interactive *"Select a subscription and tenant"* prompt.

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

---

## Run 005 write-ups — Lab 10 and the optional labs

### G-71 🔴 The endpoint in `.env` is an operation URL where a base URL is required

**One character of shape, five broken labs.** The `.env` on the lab VM ships:

```
AZURE_OPENAI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/responses?api-version=2025-04-01-preview
```

Every Azure OpenAI SDK — `AzureOpenAI(azure_endpoint=…)`, Semantic Kernel's
`AzureChatCompletion`, AutoGen's `AzureOpenAIChatCompletionClient`, and raw
`sp_invoke_external_rest_endpoint` from T-SQL — expects the **resource base**
(`https://<resource>.cognitiveservices.azure.com/`) and appends its own path. Given an
operation URL it concatenates, and the request lands somewhere that does not exist.

What the learner actually sees depends on which lab they are in, and none of it points at
the endpoint:

| Lab | Symptom |
|---|---|
| Lab 01 Evaluations | `404` from the Relevance evaluator (already filed as G-24) |
| Lab 06 Prompt Engineering | `400` on the first chat call |
| Lab 09 Red Teaming | every model-target attack `404`s (G-41) |
| Optional RAG | `400 Unsupported parameter: 'messages'. In the Responses API, this parameter has moved to 'input'` on chat, and `400 The requested operation is unsupported` on embeddings |
| Lab 10 Azure SQL | `Msg 31609 … failed to parse url` (compounded by G-66) |

The same shape defect is present on the **embedding** variables too —
`AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT` is templated as a full `/chat/completions` URL — so
this is not one bad line but a systemic misunderstanding of the field across the file.

**Fix.** Set all `*_ENDPOINT` variables to the resource base URL and let the SDKs build the
path. Where a lab genuinely needs a full operation URL (only the raw T-SQL call does), give
it a distinct, clearly named variable. Note that **a correctly shaped value already exists
in the same file** — `AZURE_OPENAI_BASE_URL_ENDPOINT` — so for most of these labs the fix is
to read the variable that is already there.

**Relationship to earlier findings.** G-24 and G-41 each describe this defect as it appears
in one lab (Evaluations' 404, Red Teaming's 404). G-71 is the same root cause seen from
above, once five more labs had been walked: it is not five bugs, it is one field whose
required shape is documented three different ways (G-32) and supplied wrongly everywhere.
Fixing G-71 closes G-24 and G-41 with it.

*Evidence: run 005 seq 5781, 5902; images 0966, 0967.*

### G-70 🔴 Three notebooks, three different wrong `.env` paths, none correct

| Notebook | Ships | Needs | Resolves to |
|---|---|---|---|
| `Lab 06 - Prompt Engineering/Prompt Engineering.ipynb` | `../../../.env` | `../.env` | `C:\Users\Admin\` |
| `Optional Lab - AI Fundamentals/RAG/RAG.ipynb` | `../.env` | `../../.env` | the lab's own folder |
| `Optional Lab - AI Fundamentals/SK and AutoGen/SK and AutoGen.ipynb` | `../../../.env` | `../../.env` | `C:\Users\Admin\Desktop\` |

Two of the three are wrong in **opposite directions**. That is only possible if none of
these notebooks was ever executed from the location it ships in — which makes the shipped
env-loading code untested across the whole workshop rather than a single slip.

Measured on the VM with `Test-Path` from each notebook's own directory, and proven by
execution: run as shipped under `jupyter nbconvert`, Prompt Engineering fails at **cell 2**
with `OpenAIError: Missing credentials` and takes cells 3–11 down with
`NameError: name 'client' is not defined` — **10 of 11 code cells**. RAG loses **8 of 12**.
SK and AutoGen loses **4 of 9**.

**Fix.** Resolve the path from the notebook's own location rather than a hand-counted
prefix — `load_dotenv(Path(__file__).resolve().parents[N] / ".env")`, or simply
`load_dotenv(find_dotenv())`, which walks upward until it finds the file and is immune to
where the notebook is opened from.

*Evidence: run 005 seq 5673, 5901, and the Lab 06 record; images 0973, 0975, 0979, 0984.*

### G-75 🟠 VS Code hides the broken path, so the learner debugs the wrong thing

The lab tells the learner to open the `LABS` folder in VS Code. The VS Code Python
extension automatically loads `${workspaceFolder}/.env` into the kernel environment. So
`os.getenv` returns values **even though `load_dotenv` found nothing**, and G-70 never
announces itself. Instead the learner meets G-71's `400` several cells later and starts
debugging their endpoint, their key, or their deployment name.

The identical file run under plain Jupyter, `nbconvert`, `papermill`, or any CI harness
fails immediately at the first client construction. This is why the defect survived
authoring, and it is a good argument for validating lab notebooks headlessly rather than in
the IDE they ship for.

*Evidence: the same notebook failing at cell 7 with `400` inside VS Code and at cell 2 with
`Missing credentials` under `nbconvert`; run 005 image 0984.*

### G-54 🔴 One mistyped variable name stops Lab 10 Cosmos DB at cell 2

`.env.example` ships `EMBEDDING_MODEL_DIMNESIONS` (letters transposed).
`Python-Samples.ipynb` cell 2 reads `config["EMBEDDING_MODEL_DIMENSIONS"]`. The result is
an immediate `KeyError` on the **second** code cell — before anything in the lab has run.

The value is wrong as well as the name: it is `1536`, but
`EMBEDDING_MODEL_DEPLOYMENT_NAME` points at a `text-embedding-3-large` deployment, whose
native dimensionality is `3072` (G-55). Fixing only the spelling silently builds an index
at the wrong width.

**Fix.** Correct the spelling in `.env.example`, set the value to match the deployment, and
read it with `config.get(...)` plus an explicit error naming the missing variable.

*Evidence: run 005 seq 4800, 4915.*

### G-66 🔴 `4_SQLEmbeddings.py` — four defects in one file, each hiding the next

Lab 10's Azure SQL module cannot be completed as shipped. Walking it produced a chain in
which every fix revealed the next failure:

1. **L67** builds `CREATE DATABASE SCOPED CREDENTIAL [{endpoint}]` from
   `AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT`. With the shipped 145-character operation URL
   (G-71) that is an over-long identifier → `Msg 103 … identifier that starts with … is too
   long. Maximum length is 128.` **Step 23 dies here.**
2. With a base URL, step 23 passes and **L106** fails instead: it emits
   `@url = ' https://…'` — a stray leading space inside the literal → `Msg 31609 … failed
   to parse url … HRESULT 0x80072ee6`. **Step 25 dies here.**
3. Remove the space and a **name mismatch** fires: L67 creates the credential as
   `[{endpoint}]` but L93 references `[{endpoint.rstrip('/')}]` →
   `Msg 15151 … Cannot find the credential`.
4. Throughout, **L71** calls `print(sql)` on the `CREATE DATABASE SCOPED CREDENTIAL`
   statement, echoing the Azure OpenAI **API key in clear text** to the console — and into
   any screenshot the learner takes.

The script is also **not re-runnable**: `create_database_credential()` has no `IF EXISTS`
guard, so a second attempt after a partial failure fails again for a new reason.

**Verified fixed.** With all four corrected, `5_query.sql` returns 11 rows and ranks
*"Houston, we have a problem."* (Apollo 13, distance 0.1649) top for the query *"texas
city"* — so the underlying lab design is sound.

*Evidence: run 005 seq 5647–5650, 5653; images 0941, 0944, 0947, 0949.*

### G-69 🔴 Neither optional lab's notebook is on the lab VM

Both optional sections reduce to a single sentence — *"Run through steps in RAG.ipynb
file"* and *"Open the SK and AutoGen.ipynb notebook and run through the steps"* — with no
path, no repository and no branch. `Desktop\LABS` contains `Lab 00` … `Lab 10` and nothing
else; a recursive search of the whole Desktop for `RAG.ipynb` returns nothing.

The files do exist publicly, at
`Optional Lab - AI Fundamentals/{RAG,SK and AutoGen}/` on the `AugRelease` branch — but the
TMS section is titled *"Optional Lab - RAG, SK and Autogen Frameworks"* while the folder is
*"AI Fundamentals"* (G-72), so even a resourceful learner searching the repo by section
name will not find it.

**Fix.** Add the folder to the golden image, and give both sections a concrete path.

*Evidence: run 005 seq 5669, 5900; images 0955, 0956.*

### G-62 🔴 Azure SQL's only instruction is a link that 404s

The Azure SQL lab body is 26 lines. It contains one actionable sentence: go to the
**SQL folder** to get the files and the order to run them. That hyperlink returns **404**
— the path does not exist on the branch it points at. There is no file list, no connection
detail, no expected output and no fallback anywhere in the section, so the 404 is total:
the lab has no content a learner can act on.

The Objectives of the same section also read *"Perform similarity searches using
**PostgreSQL**"* — copy-paste residue from the preceding module (G-64).

*Evidence: run 005 seq 5288, 5291, 5293.*

### G-57 🟠 `VectoryQuery.sql` does not exist

Lab 10's PostgreSQL module tells the learner to press `Ctrl+O` in pgAdmin and open
`…\Lab 10 - Vector-DB\PostgreSQL\VectoryQuery.sql`, and the heading above it repeats the
name. The file on disk is `VectorQuery.sql`. Confirmed live: pasting the published path
into pgAdmin's Open dialog fails.

In the same module, `VectorQuery.sql` line 1 is `create extension azure_ai` **with no
terminating semicolon** (G-58), so running the script as shipped fails on the first
statement; and the endpoint template on line 163 is
`https://<your-endpoint>.openai.azure.com/` when this lab's resource is on
`cognitiveservices.azure.com` (G-59).

*Evidence: run 005 seq 4962, 5146, 5147, 5244, 5285.*

### G-73 🟠 The RAG lab's headline objective is never delivered

*"Configure Azure AI Search for vector search capabilities"* is a stated objective, and
Exercise 8 is titled *"RAG with Azure AI Search (Real Example)"*. The cell **defines** a
function and then prints *"To use this code you need: 1. Create an index…"*. It never runs,
no index is ever created, and every other exercise searches an in-memory Python list. A
learner finishes the lab having done no Azure AI Search work at all.

*Evidence: run 005 seq 5855.*

## Lab 08 write-ups — what "blocked" was actually hiding

G-40 recorded Lab 08 as blocked and stopped there. That was a mistake worth naming: *blocked*
is a status, not a finding, and it hid six further defects that a lab author can fix
independently. Everything below was verified against **graphrag 3.1.1** — the version
`pip install graphrag` resolves to today — reading the package's own source at tag `v3.1.1`,
plus live checks on the lab subscription.

### G-35 corroborated from source

G-35 already recorded that `graphrag init --root ragtest` (`all.md#L1437`) is **interactive**
at 3.1.1. That is now confirmed from the package source rather than observed behaviour —
`packages/graphrag/graphrag/cli/main.py` at tag `v3.1.1`:

```python
model: str = typer.Option(
    DEFAULT_COMPLETION_MODEL, "--model", "-m",
    prompt="Specify the default chat model to use",
),
embedding_model: str = typer.Option(
    DEFAULT_EMBEDDING_MODEL, "--embedding", "-e",
    prompt="Specify the default embedding model to use",
),
```

A Typer option carrying `prompt=` **asks** when the flag is absent — it does not quietly take
the default. The lab's next line is `find ./ragtest`, asserting `settings.yaml` already exists.

This matters more than "the command changed shape", which is what G-35 captured. Whatever the
learner types becomes `model:` in `settings.yaml`, and on Azure GraphRAG resolves `model:` to a
**deployment name**. An undocumented prompt is silently deciding whether the rest of the lab
can work — which is what G-76 and G-77 below are about.

### G-76 🔴 Pressing Enter at those prompts guarantees failure

`packages/graphrag/graphrag/config/defaults.py` at `v3.1.1`:

```python
DEFAULT_COMPLETION_MODEL = "gpt-4.1"
DEFAULT_EMBEDDING_MODEL  = "text-embedding-3-large"
DEFAULT_MODEL_PROVIDER   = "openai"
```

Two independent problems:

1. **`gpt-4.1` is one of the exact models G-08 proves cannot be deployed** on a
   Skillable-minted subscription. The default path dead-ends on the workshop's own blocker.
2. Even on a healthy subscription the defaults **contradict the lab's own prerequisites**,
   which at `all.md#L1419-L1420` tell the learner to deploy `text-embedding-ada-002` *or*
   `text-embedding-3-small`, and `gpt-4o-mini`. Neither default matches either instruction.

### G-77 🔴 Nothing in the lab ever points `settings.yaml` at the learner's deployments

The four `sed` commands at `all.md#L1466-L1471` add `api_base`, add `api_version`, flip
`model_provider` and flip `graphml`. **None of them touches `model:`.** So a diligent learner
who deploys exactly what the prerequisites asked for still ends up with a config requesting a
deployment called `gpt-4.1`, and indexing dies with `DeploymentNotFound`.

The fix is one line, and it repairs G-35's prompt, G-76 and G-77 simultaneously:

```bash
graphrag init --root ragtest -m <chat-deployment> -e <embedding-deployment>
```

Supplying both flags removes the interactive prompt *and* writes real deployment names.

### G-78 🟠 `pip install graphrag` cannot succeed anywhere except Linux

Reproduced on the lab VM in a clean venv on Python 3.12.10 — `install_exit=1`, failing in
`Preparing metadata (pyproject.toml)` with `metadata-generation-failed`.

The chain is `graphrag 3.1.1` → `graphrag-llm==3.1.1` → **`litellm==1.92.0`** (a hard pin).
PyPI publishes litellm 1.92.0 as:

```
litellm-1.92.0-cp310..cp313-manylinux_2_28_{x86_64,aarch64}.whl
litellm-1.92.0.tar.gz
```

— **manylinux wheels only.** No `win_amd64`, no `macosx`. Off Linux, pip falls back to the
sdist and the build fails.

The lab's happy path is Cloud Shell, where the manylinux wheel matches and this never bites.
But the prerequisite at `all.md#L1416` says only *"Python 3.10 to 3.12 environment"* with no
OS constraint, and **Lab 08 is the only lab in this workshop not run on the VM** — a fact
stated once, at `all.md#L1400`, and never repeated. A learner who does what every other lab
trained them to do gets an error naming neither GraphRAG nor the platform.

### G-79 🟠 The stated Python floor is below what the package allows

`all.md#L1416` sanctions **Python 3.10**. PyPI reports `graphrag 3.1.1` as
`requires_python = "<3.14,>=3.11"`. On 3.10, pip cannot install 3.1.1 and silently back-solves
to an older GraphRAG whose `settings.yaml` schema these `sed` commands were never written for
— so the failure surfaces much later and looks like a config bug. The floor should read 3.11.

### G-80 🟠 The endpoint export is missing its scheme

`all.md#L1461`:

```bash
export AZURE_OPENAI_ENDPOINT=<instance>.openai.azure.com
```

A bare hostname. The next `sed` writes it straight into `settings.yaml` as
`api_base: ${AZURE_OPENAI_ENDPOINT}`; GraphRAG hands that to litellm and on to httpx, which
requires an absolute URL and rejects a scheme-less host. This is the **same class of defect as
G-71** — the second place in this workshop where an Azure OpenAI endpoint is written in a shape
no SDK accepts. Should read `https://<instance>.openai.azure.com`.

### ✅ What still works — the `sed` mechanics themselves

Worth recording, because it is the part most likely to have rotted. Checked against
`init_content.py` at `v3.1.1`:

| Lab command | Still matches? | Why |
|---|---|---|
| append `api_base` after `api_key:` | ✅ | `api_key:` appears twice, both at 4-space indent under `completion_models` / `embedding_models` — the appended line lands at correct depth |
| append `api_version` after `api_base:` | ✅ | follows from the above |
| `s/model_provider: openai/model_provider: azure/g` | ✅ | `model_provider:` appears twice and `DEFAULT_MODEL_PROVIDER = "openai"`, so both match |
| `s/graphml: false/graphml: true/` | ✅ | appears exactly once, under `snapshots:` — unambiguous |

The `sed` scripting is sound. What is missing is a *fifth* command — the one that sets `model:`.

### G-40 corrected — and a verified repair for Lab 08

**The original claim was overstated.** G-40 said `myopai-<id>` has *zero* deployments. It does
not:

```
az cognitiveservices account deployment list -g azureaiworkshoprg -n myopai-<id>
  -> text-embedding-ada-002          (deps_exit=0)
```

That is exactly the embedding model `all.md#L1419` asks for, so **the embedding half of Lab 08
is correctly pre-provisioned**. What is genuinely absent is a **chat** deployment — the lab
tells the learner to create `gpt-4o-mini` themselves at `all.md#L1418-L1420`, and G-08 proves
that is refused. Recording the correction because an overstated finding is worse than none.

**And that gap is closable.** Tested end to end on the lab's own resource:

1. `model-router` v2025-11-18 deployed into `myopai-<id>` — **exit 0**.
2. Called at `https://myopai-<id>.openai.azure.com/openai/deployments/model-router/chat/completions`
   using **the lab's own `api-version=2024-05-01-preview`** → `OK model=gpt-5-nano-2025-08-07`.

So the 2024-05-01-preview pin still functions — G-81 is a consistency nit, not a breakage.
The complete repair for Lab 08 is therefore:

- deploy `model-router` into `myopai-<id>`;
- change `all.md#L1437` to `graphrag init --root ragtest -m model-router -e text-embedding-ada-002`
  (fixes G-35's prompt, G-76 and G-77 in one line);
- add `https://` at `all.md#L1461` (G-80);
- correct the Python floor to 3.11 and state that Cloud Shell is required (G-79, G-78);
- adopt G-35's other two corrections (positional `query`, no `--config` on `prompt-tune`).

**Not yet verified:** that indexing and the global/local queries then succeed. That needs Cloud
Shell and was out of budget for this run. The test deployment was deleted afterwards and
`myopai-<id>` returned to its single `text-embedding-ada-002` (`del=0`).

---

### A tested way out of G-08 and G-31 — `model-router`
The two blocking defects have between them no obvious fix: the models the workshop names
cannot be deployed (G-08), and the only thing that *can* be deployed rejects the parameters
the workshop's code passes (G-31). One candidate was tested end to end on the lab
subscription and clears both.

**It deploys.** `model-router` version **2025-11-18** is `GenerallyAvailable` in `eastus2`
(2025-05-19 and 2025-08-07 are Preview). Creating it succeeded — exit code 0:

```powershell
az cognitiveservices account deployment create -g <rg> -n <foundry> `
  --deployment-name model-router --model-name model-router `
  --model-version 2025-11-18 --model-format OpenAI `
  --sku-name GlobalStandard --sku-capacity 50
```

This is the first chat-capable deployment proven to succeed on a Skillable-minted
subscription other than the pre-baked aliases, and it confirms G-08's root cause: the block
tracks a model's **deprecation date**, not its being a chat model.

**It accepts the workshop's existing parameters.** Four REST calls against the new
deployment all returned **200**:

| Request | Result |
|---|---|
| `max_tokens: 50` | ✅ 200 |
| `temperature: 0.7` | ✅ 200 |
| `max_completion_tokens: 50` | ✅ 200 |
| neither | ✅ 200 |

A direct `gpt-5-mini` deployment rejects the first two. That difference is the whole of
G-31: Lab 06's 20 `temperature` call sites, Lab 08's DRIFT search and the optional RAG
notebook would run **unmodified** against `model-router`.

**Three caveats, so this is not adopted blindly.** Every response reported
`model = gpt-5-nano-2025-08-07`, so the router serves the **gpt-5 family**:

1. `response.model` will never say `gpt-4o`. Any step or assertion that reads the model name
   back must be updated.
2. Output quality and token accounting differ from `gpt-4o`; the lab prose should stop
   naming `gpt-4o` as what the learner is using.
3. **Name the deployment `model-router`.** Naming it `gpt-4o` to avoid editing the notebooks
   would recreate G-30 exactly — a deployment whose name lies about what serves it — which
   is the single defect that made every other failure in this workshop unreadable.

*Evidence: run 005 images 0992, 0993, 0997, 0998. The test deployment was deleted
afterwards and the resource returned to its prior five deployments (image 0999).*

### Verified sound once configured
Three modules were blocked by configuration rather than by their own content. Applying the
fixes above on scratch copies proved the material itself is current:

| Module | Result after fixes |
|---|---|
| Lab 06 – Prompt Engineering | **11 of 11** code cells clean; 12,163 chars of output with zero error strings; zero-shot, few-shot, chain-of-thought and role prompting all correct |
| Optional Lab – RAG | **12 of 12** code cells clean |
| Optional Lab – SK and AutoGen | **9 of 9** code cells clean; unaffected by G-31 because it pins neither `temperature` nor `max_tokens` |
| Lab 10 – Azure SQL vector search | 11 rows, semantically correct nearest-neighbour ranking |

This matters for triage: these are **cheap** fixes with large coverage gains, not rewrites.

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

Recorded so that "checked and fine" is never confused with "not checked". Over **5,600
steps passed** across runs 003, 004 and 005; this is the representative set.

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
| Lab 08 — `graphrag index` builds a full index once the endpoint is corrected | ✅ ~28 min, all workflows green |
| Lab 08 — Global search returns a cited community answer | ✅ ~3 min |
| Lab 08 — Local search returns the Scrooge profile with seven relationships and `[Data: Entities/Sources/Reports …]` citations | ✅ ~90 s |
| Lab 08 — both *Additional Resources* links resolve | ✅ 200 |
| Lab 09 — `RedTeam(...)` constructs against the Foundry project endpoint | ✅ 5.8 s |
| Lab 09 — scan dispatches all attacks and reaches 4/4 | ✅ *(but scores none — see G-33)* |
| Lab 10 – PostgreSQL — `pg_restore` of the books database, `azure_ai` extension, pgvector `<->` query | ✅ once G-57/G-58 are worked around |
| Lab 10 – Azure SQL — 732 rows loaded and embedded; `5_query.sql` returns 11 correctly ranked rows | ✅ once G-66's four defects are fixed |
| Lab 06 – Prompt Engineering — all 11 code cells, zero error strings in 12,163 chars of output | ✅ once G-70/G-71 are fixed |
| Optional Lab – RAG — all 12 code cells | ✅ once G-69/G-70/G-71 and the pinned parameters are fixed |
| Optional Lab – SK and AutoGen — all 9 code cells, incl. AutoGen `RoundRobinGroupChat` | ✅ once G-69/G-70/G-71 are fixed |

---

## Withdrawn — recorded so they are never re-reported

**Seven** findings were retracted after re-checking. Keeping them visible is the point: a
validator that never withdraws anything is not checking itself.

| What was claimed | Why it was wrong |
|---|---|
| `AZURE_OPENAI_ENDPOINT` missing from `.env` (and a consequent model-config finding) | The evidence was a **scrolled terminal**, not the whole file. An exhaustive per-key count showed it present exactly once. *Lesson: a negative claim needs an exhaustive read.* |
| Sign-in failure — *"We couldn't find an account with that username"*, twice, minutes apart | **Entra replication lag** on a freshly provisioned Cloud Slice user. Succeeded on the third try with a byte-identical username; the lab's own dialog reported the credentials valid for another 7 h 39 m. Clicking *Refresh Credentials* would have destroyed a valid credential set. |
| A step timing out | Recovered on retry — a transient, not a defect. |
| An agent-failure finding superseded by a better-evidenced one | Replaced by G-21/G-22, which identify the actual cause. |
| A deployment failure attributed to the wrong cause | Superseded by G-08 once the subscription-level root cause was proven. |
| `graphrag prompt-tune --output` is root-relative, so the lab's `./ragtest/prompts-tuned` lands in the wrong place | The **help text** says root-relative; the **behaviour** is CWD-relative. Executed and checked: the lab's path is correct. The upstream help string is the wrong thing, not the lab. *Lesson: run it, don't read it.* |
| `pip install azure-ai-evaluation[redteam]` upgrades the SDK mid-lab | It does nothing. Without `-U`, pip treats an already-installed distribution as satisfied. Versions were byte-identical before and after. *Lesson: verify, don't predict.* |

Telling *"the lab is wrong"* apart from *"the cloud is still catching up"* is the hardest
part of validating these labs, and the reason every finding above cites either an oracle or
a repeated observation.

Also **not a gap**: the deliberately-wrong sample data in Lab 01 Evaluations
(*"capital of France"* → *"London."*). The low F1 and 0 % BLEU are **by design**. It is
recorded under G-29 only because nothing tells the learner that, so a correct run reads as
a failure.

---

## Still to check

**All 23 sections have now been walked.** What remains is not coverage but verification of
hypotheses that need a disposable instance or a fixed image:

1. **Preview API versions** — `2024-12-01-preview` is referenced but there is **no
   machine-readable lifecycle feed for Azure OpenAI API versions**, so these can only be
   validated by execution. Currently the largest oracle blind spot. (`2024-05-01-preview`
   is now *known good* — it served a live completion during the Lab 08 check.)
2. **`azure-ai-evaluation` ≥ 1.18** — one upgrade would test both the G-26 and G-34
   hypotheses. Needs a disposable instance, because it would destabilise a run in progress.
3. **Does `model-router` accept `max_tokens`?** — **answered.** It does, and it deploys.
   See *A tested way out of G-08 and G-31* above.
4. **Re-run Labs 06–09 after a G-30 fix.** Several findings in those labs are downstream of
   the substitution and should be re-checked, not assumed, once the right model is deployed.
5. **Lab 08 indexing and queries** — the *configuration* is now fully analysed (G-35, G-76…
   G-81) and a working chat deployment is proven available, but `graphrag index` and the
   global/local queries have **not** been executed. That needs Cloud Shell, because
   `pip install graphrag` cannot succeed off Linux (G-78). This is the single largest
   remaining piece of unexercised lab content.
6. **The two still-blocked sections** — Deploy models (G-08) and Responsible AI (G-39) are
   blocked by missing platform capability or missing resources, not by text. They need a
   corrected lab image before they can be completed as a learner would. (Graph RAG is no
   longer merely "blocked" — see G-40 corrected.)
7. **Setup line 152** — the claim that *Endpoints* and *Manage keys* "both go to the same
   place" is still unverified.
