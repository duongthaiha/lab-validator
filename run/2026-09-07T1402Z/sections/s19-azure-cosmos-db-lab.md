# Azure Cosmos DB Lab

*Section* `s19-azure-cosmos-db-lab` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#azure-cosmos-db-lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 50 recorded step(s), 1 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Defective sample code** `LAB009` — The Cosmos DB notebook cannot be run as delivered: its first code cell dies with KeyError: 'EMBEDDING_MODEL_DIMENSIONS'. Cell 3 does `config = dotenv_values("../../.env")` (that path is correct - it resolves to C:\Users\Admin\Desktop\LABS\.env, verified present) and then reads ten keys from it. Nine are present; EMBEDDING_MODEL_DIMENSIONS is absent from the provided .env AND from the shipped .env.example, so a learner has no template line to fill in and no way to discover the name except by reading the traceback. The section's own Pre-requisites say "None. The database has been pre-created for you." and its only task is "Open Python-Samples.ipynb and follow the steps", so nothing warns the learner that .env needs editing. Executed unmodified the whole notebook collapses: c3 KeyError, then c4 NameError 'openai_api_version', c12 NameError 'openai_client', c14/c17/c20 NameError 'full_text', c23/c25 NameError 'emb' - eight failing cells, no search ever runs. Adding a single line EMBEDDING_MODEL_DIMENSIONS=3072 to .env (3072 being the native width of the deployed text-embedding-3-large and the width advertised by the lab's own data file e-retail-data-3072D.json) makes the identical, otherwise-unmodified notebook run clean.
  <br>evidence: step `2318`, instruction `#azure-cosmos-db-lab`

## Findings

**LAB009** ×1

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#1** Defective sample code (`LAB009`)

### 1. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-cosmos-db-lab`  
*Severity:* critical · *At fault:* setup · *Step:* `2318` · *2026-09-07T20:16:24Z*

The Cosmos DB notebook cannot be run as delivered: its first code cell dies with KeyError: 'EMBEDDING_MODEL_DIMENSIONS'. Cell 3 does `config = dotenv_values("../../.env")` (that path is correct - it resolves to C:\Users\Admin\Desktop\LABS\.env, verified present) and then reads ten keys from it. Nine are present; EMBEDDING_MODEL_DIMENSIONS is absent from the provided .env AND from the shipped .env.example, so a learner has no template line to fill in and no way to discover the name except by reading the traceback. The section's own Pre-requisites say "None. The database has been pre-created for you." and its only task is "Open Python-Samples.ipynb and follow the steps", so nothing warns the learner that .env needs editing. Executed unmodified the whole notebook collapses: c3 KeyError, then c4 NameError 'openai_api_version', c12 NameError 'openai_client', c14/c17/c20 NameError 'full_text', c23/c25 NameError 'emb' - eight failing cells, no search ever runs. Adding a single line EMBEDDING_MODEL_DIMENSIONS=3072 to .env (3072 being the native width of the deployed text-embedding-3-large and the width advertised by the lab's own data file e-retail-data-3072D.json) makes the identical, otherwise-unmodified notebook run clean.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `2319`** · instruction `#azure-cosmos-db-lab` — Deviation: a single line, EMBEDDING_MODEL_DIMENSIONS=3072, was appended to C:\Users\Admin\Desktop\LABS\.env so the rest of the section could be tested. The notebook itself was executed byte-for-byte unmodified. The value was left in place because it repairs the lab rather than damaging it.
  <br>outcome: PASS - With the one missing variable supplied, the notebook meets both stated objectives ("Store and retrieve vector data", "Perform similarity searches using Cosmos DB") against the real pre-created Cosmos account, with zero failing cells. Evidence from the executed output notebook (26340 bytes): the container and indexing/full-text/vector policies were created, the 15422697-byte e-retail-data-3072D.json catalogue was ingested, embeddings were generated through the deployed text-embedding-3-large, and every one of the four search styles the lab sets out to contrast returned real product documents rather than empty result sets - classic `CONTAINS` (1228 chars of results, e.g. "Hollywood Glam Vanity Mirror"), `FullTextContainsAny` (1222 chars, "Parisian Chic Scarf"), BM25 ranking with `FullTextScore` (1257 chars, "Vintage Leather Messenger Bag"), `VectorDistance` similarity (1414 chars, "Luxe Leather Handbag") and the hybrid/RRF cell (1475 chars, "Luxe Leather Handbag"). The notebook's own commentary about relevance ("Rose Gold Quartz Watch" and "Sapphire Blue Silk Scarf" being poor matches for "luxury handbags", then hybrid search fixing it) is borne out by the results actually returned, so the teaching point stands up.

## Verified correct

_No explicit confirmations recorded in this section._

## Evidence

12 capture(s), in the order the learner would have seen them.

- [`0313-s19-azure-cosmos-db-step.jpg`](../images/0313-s19-azure-cosmos-db-step.jpg)
- [`0314-s19-azure-cosmos-db-step.jpg`](../images/0314-s19-azure-cosmos-db-step.jpg)
- [`0315-s19-azure-cosmos-db-step.jpg`](../images/0315-s19-azure-cosmos-db-step.jpg)
- [`0316-s19-azure-cosmos-db-step.jpg`](../images/0316-s19-azure-cosmos-db-step.jpg)
- [`0317-s19-azure-cosmos-db-step.jpg`](../images/0317-s19-azure-cosmos-db-step.jpg)
- [`0318-s19-azure-cosmos-db-step.jpg`](../images/0318-s19-azure-cosmos-db-step.jpg)
- [`0319-s19-azure-cosmos-db-step.jpg`](../images/0319-s19-azure-cosmos-db-step.jpg)
- [`0320-s19-azure-cosmos-db-step.jpg`](../images/0320-s19-azure-cosmos-db-step.jpg)
- [`0321-s19-azure-cosmos-db-step.jpg`](../images/0321-s19-azure-cosmos-db-step.jpg)
- [`0322-s19-azure-cosmos-db-step.jpg`](../images/0322-s19-azure-cosmos-db-step.jpg)
- [`0323-s19-azure-cosmos-db-step.jpg`](../images/0323-s19-azure-cosmos-db-step.jpg)
- [`0324-s19-azure-cosmos-db-step.jpg`](../images/0324-s19-azure-cosmos-db-step.jpg)
