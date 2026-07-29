# Gap analysis — WorkshopPLUS: Azure AI Platform and Services

What a learner is told to expect, versus what is actually in front of them.

**Lab** 79233, edition 2026031B · **Instance** `d211a44c-…` · **Validated** 2026-07-29
**Instruction corpus** 2,264 lines / 109,703 chars, 12 modules
**Line references** are into `artifacts/instructions/all.md` (regenerate with
`python scripts/lab_drive.py --page N`).

This is the learner-facing output. Engineering notes live in `docs/approach.md`;
per-run logs live in the session `research/validation-run-00N.md` files.

---

## Coverage — read this before trusting the "no gaps found" areas

| Depth | Scope | Coverage |
|---|---|---|
| **Walked hands-on** in the lab VM, every step compared to the instruction | Required Lab Setup (tasks 1–5); *Deploy models* prerequisites; *Lab 01* task 2 up to the model search | **~3 %** of instruction lines |
| **Statically analysed** — model IDs vs the Azure model-lifecycle API, TOC structure, anchor targets, resource names | Whole corpus | **100 %** |
| **Not executed at all** | Labs 01 (deployments) – 10, Optional Lab | **0 of 10** numbered labs completed |

So: **no, the lab has not been fully validated.** One module of twelve was executed
end-to-end. The gaps below are real and reproducible, but the absence of findings in
Labs 02–10 means *not yet checked*, **not** *verified correct*. Labs 09 and 10 are the
largest (722 and ~250 lines) and are entirely unexercised.

---

## Gaps

| ID | Sev | Module | Gap |
|---|---|---|---|
| G-01 | 🔴 | Required Lab Setup | Sign-in needs a Temporary Access Pass; no instruction says so |
| G-02 | 🔴 | Required Lab Setup | Create-wizard tab list is stale — 6 tabs, not the 4 documented |
| G-03 | 🔴 | Lab 05 – Fine-Tuning | Two model names that do not exist |
| G-04 | 🟠 | Deploy models | "Click firstProject inside All resources" — that view never appears |
| G-05 | 🟠 | Contents | Second "Lab 07- RAI" entry is really Lab 08 |
| G-06 | 🔵 | Required Lab Setup | "East US 2" is not in the Recommended region list |
| G-07 | 🔵 | Global | Product naming drifts between three variants |
| R-01 | ⚠️ | All labs | Everything depends on the "New Foundry" legacy toggle surviving |
| R-02 | ⚠️ | Several | `gpt-4o` family is on a published retirement path |

---

### G-01 🔴 The sign-in asks for something the instructions never mention

**Line 61** — "Go to https://portal.azure.com and sign in with your Azure credentials.
These credentials are present on the right hand side under resources tab below Azure Portal."

**What actually happens.** After the username, Entra does not ask for a password. It shows
**"Enter Temporary Access Pass"**. The Resources tab does carry a `TAP` value — but it sits
*below* a `Password` value, and nothing explains which is used when.

**Why it matters.** This is the very first action of the workshop and the instruction points
at the wrong field. There is a "Use your password instead" link on that screen, but a learner
has no way to know which path is intended.

**Fix.** "Sign in with the **Username** and the **TAP** from the Resources tab. The Password
is used for later prompts, not the first sign-in."

### G-02 🔴 The create wizard has six tabs, not four

**Line 75** — "we will keep all default values for all the subsequent tabs
**(Network, Identity, Encryption, Tags)**."

**What actually happens.**

> Basics | **Storage** | **Inbound Networking** | **Outbound Networking** | Identity | Encryption | Tags | Review + create

**Network** has been split into **Inbound Networking** and **Outbound Networking**, and a
**Storage** tab has been added. Confirmed by clicking through: **six** presses of *Next* to
reach Tags, not the three implied.

**Why it matters.** Defaults are still correct, so nothing breaks — but a learner counting
tabs against the instruction concludes they are in the wrong wizard.

**Fix.** Update to "(Storage, Inbound Networking, Outbound Networking, Identity, Encryption,
Tags)", or make it version-proof: "click Next through the remaining tabs, accepting defaults,
until you reach Review + create."

### G-03 🔴 Model names that do not exist

**Line 993** — "Here choose GPT-4.1-mini or **GPT-4-o-mini** or **GPT-4.o**"

Neither `GPT-4-o-mini` nor `GPT-4.o` is a valid identifier. Checked against the Azure
model-lifecycle API (324 models): no match. The real names are **`gpt-4o-mini`** and
**`gpt-4o`** — no dots or hyphens inside "4o". A learner searching the catalog for the
printed strings finds nothing.

**Fix.** `gpt-4.1-mini`, `gpt-4o-mini`, `gpt-4o`.

*(Not yet executed — found by static analysis. Lab 05 has not been walked.)*

### G-04 🟠 "Click firstProject inside the All resources section" — no such view

**Line 97** — "If this is the first Portal view in the Foundry Portal, then click
**firstProject** inside the **All resources** section."

**What actually happens.** **Go to Foundry portal** lands directly on
`…/firstProject/home`, already scoped to the project. There is no "All resources" section on
that page; "All resources" is now a top-right dropdown.

**Why it matters.** Learners hunt for a control that is not on the page they are looking at,
and cannot tell whether they have gone wrong.

**Fix.** Delete the step, or reword: "You should land on **firstProject**. If not, pick it
from the **All resources** dropdown, top right."

### G-05 🟠 The contents list shows "Lab 07- RAI" twice; the second one is Lab 08

The navigation pane lists **Lab 07- RAI** twice and never shows Lab 08:

```
Lab 07- RAI   → #lab-07--rai
Lab 07- RAI   → #lab-08---rag-patterns---graph-rag     ← wrong label, right target
```

The **link is correct** — it goes to *Lab 08 – RAG-Patterns – Graph RAG*, which does exist
(line 1398). Only the label is a copy-paste error, so no content is unreachable.

**Fix.** Rename the second entry to "Lab 08 - RAG-Patterns - Graph RAG".

Related, cosmetic: the contents say **"Lab 10 - VectorDB"**, the body heading says
**"Lab 10 - Vector-DB"**; and "Lab 01 - AI-Foundry" / "Lab 07- RAI" space their dashes
differently.

### G-06 🔵 "East US 2" is not where the instruction implies

**Line 71** — "Choose a Region (e.g. East US 2)".

The Region dropdown's **Recommended** group lists East US, West US 2, Australia East,
Southeast Asia, North Europe, Sweden Central, West Europe, UK South, Central US, … —
East US 2 appears only under **Other**, after typing it into the filter. It works, it just
is not visible where a learner will look first.

**Fix.** "Type *East US 2* into the region filter (it appears under **Other**)."

### G-07 🔵 Three different names for the same product

Within one corpus: **"Microsoft Foundry"**, **"Azure AI Foundry"**, and **"Foundry"**. The
portal itself is inconsistent too — the Azure services tile reads "Foundry", the service page
"Microsoft Foundry", the button "Go to Foundry portal". Worth one pass for consistency, and
worth noting that screenshots in the instructions will age faster than the text.

---

## Standing risks — not defects today, but scheduled to become them

### R-01 ⚠️ Every lab depends on a legacy UI that is being retired

**Lines 96–99** require the **legacy Microsoft Foundry UI**, reached with the **New Foundry**
toggle.

**Verified working today.** The portal opens in New Foundry with the toggle on; the switch is
present top-right; toggling it produces the legacy UI with the left-hand menu
(`Model catalog`, `Playgrounds`, `Agents`, `Fine-tuning`, …) that Labs 01–10 navigate by. The
feedback popup appears exactly as documented and **Continue without feedback** is present.

**But** New Foundry is the default and the page carries a permanent *"Try the new Microsoft
Foundry experience"* banner. **When that toggle is removed, every lab in this workshop breaks
at the same moment**, because all navigation is written against the legacy left-hand menu.

**Recommendation.** Treat this as the workshop's single point of failure. Re-check it on every
validation run — it is the cheapest high-value assertion available — and plan a rewrite
against New Foundry navigation before the toggle is withdrawn.

### R-02 ⚠️ The `gpt-4o` family is on a published retirement path

`gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini` are all **`Deprecating`**, retiring
**2027-04-14** (Azure model-lifecycle API). Still deployable today — both `gpt-4o` and
`gpt-4o-mini` were confirmed present in the catalog.

Context worth noting: the catalog's default view is now entirely next-generation
(`gpt-5.6-*`, `claude-opus-5`, `grok-4.x`, `DeepSeek-V4`, `MAI-*`) across 198 models. The
workshop's models are reachable only by explicit search — the labs increasingly teach against
models a learner would not otherwise encounter.

**Not** a defect: `text-embedding-ada-002` (11 references) *looks* legacy but the API reports
it `GenerallyAvailable` until **2028-02-09**. Left alone deliberately.

---

## Verified correct

Recorded so that "checked and fine" is never confused with "not checked".

| Instruction | Result |
|---|---|
| Search "Microsoft Foundry" in the portal search bar | ✅ top **Services** result |
| "Under Overview, click Create a resource" | ✅ present |
| Resource group `azureaiworkshoprg` pre-exists and is selectable | ✅ |
| Name `ai-foundry-63812580` accepted | ✅ validated |
| Default project name has a value to delete; `firstProject` accepted | ✅ default was `proj-default` |
| "In less than 2 minutes your deployment should complete" | ✅ ~1 min 20 s |
| "click Go to resource" → "Go to Foundry Portal" | ✅ (renders "Go to Foundry portal") |
| "If the feedback popups is displayed, click Continue without feedback" | ✅ exact match |
| "In the left side menu, Click Model catalog" | ✅ present in legacy UI |
| "search gpt-4o" | ✅ `gpt-4o` and `gpt-4o-mini` both present |

---

## Not a gap — recorded so it is never re-reported

Sign-in failed **twice** with *"We couldn't find an account with that username"*, minutes
apart, then succeeded on the third try with a byte-identical username. The credential was
verified clean first, and the lab's own dialog reported the credentials *"valid for another
7 Hr 39 Min"*.

That was **Entra replication lag on a freshly provisioned Cloud Slice user** — not a content
error. Reporting it would have been wrong, and "fixing" it by clicking *Refresh Credentials*
would have destroyed a valid credential set. Telling *the lab is wrong* apart from *the cloud
is still catching up* is the hardest part of validating these labs.

---

## Still to check

Highest value first — the two largest modules are entirely unexercised.

1. **Lab 01 model deployments** — deploy all four (`text-embedding-3-large`, `gpt-4o`,
   `gpt-4o-mini`, `text-embedding-ada-002`). Quota and region availability are the likely
   failure modes and cannot be checked statically.
2. **Lab 09 – Security** (722 lines, the largest module) — red-teaming notebook, `pip install
   azure-ai-evaluation[redteam]`, pinned `MODEL_API_VERSION="2024-12-01-preview"`.
3. **Lab 10 – Vector-DB** — three sub-labs (Cosmos DB, PostgreSQL, Azure SQL) with
   pre-created servers, `pg_restore` from on-disk backups, and hardcoded paths under
   `C:\Users\Admin\Desktop\LABS\`. Fragile by construction.
4. **G-03** — confirm the invalid model names in the running catalog.
5. **Preview API versions** — `2024-05-01-preview`, `2024-12-01-preview` are referenced but
   there is no machine-readable lifecycle feed for Azure OpenAI *API versions*, so these can
   only be validated by execution. Currently the largest blind spot.
