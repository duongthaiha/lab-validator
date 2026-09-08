# Deploy models into the Microsoft Foundry Project

*Section* `s02-deploy-models-into-the-micro`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#deploy-models-into-the-microsoft-foundry-project`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 82 recorded step(s), 3 finding(s)

**Can a learner finish this section?** **YES** — a learner following the instructions can complete this

## What the lab asks the learner to do

- 1. Ensure that you are on the Microsoft Foundry - Overview page
- 2. Deploy gpt-5.1 model
- 3. Deploy gpt-5-mini model
- 4. Deploy embedding model
- 5. Deploy text-embedding-ada-002 model

## Findings

**LAB003** ×1 · **LAB004** ×1 · **LAB010** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Superseded or retiring feature (`LAB010`)
- **#2** Changed UI label or inconsistent structure (`LAB003`)
- **#3** Moved navigation (`LAB004`)

### 1. [~] Superseded or retiring feature — `LAB010`

*Instruction:* `#1-ensure-that-you-are-on-the-microsoft-foundry-overview-page`  
*Severity:* minor · *At fault:* instruction · *Step:* `103` · *2026-09-07T14:14:35Z*

The prerequisite explicitly says to use the legacy Microsoft Foundry UI and instructs learners to turn New Foundry off. The created project opens in the current New Foundry experience, whose Home uses top navigation and an Explore models card; screenshot 0019 captures the replacement UX. The legacy path remains selectable but is superseded.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#2-deploy-gpt-51-model`  
*Severity:* minor · *At fault:* instruction · *Step:* `116` · *2026-09-07T14:16:08Z*

The latest Foundry model detail page has a purple Deploy control; the documented Use this model button is not present. Screenshot 0022 captures the current GPT-5.1 detail UX.

### 3. [~] Moved navigation — `LAB004`

*Instruction:* `#5-deploy-text-embedding-ada-002-model`  
*Severity:* minor · *At fault:* instruction · *Step:* `180` · *2026-09-07T14:22:50Z*

The completion text says to scroll the legacy left menu to Models + endpoints. In New Foundry, deployment verification is at Build > Models > Deployments; screenshot 0033 shows the current four-row deployment list.

## Ageing guidance (works today)

Nothing here stopped a learner. Each is a step that *succeeded* while following a path the product has moved on from, so it dates the lab rather than breaking it.

- **#1** Superseded or retiring feature — The prerequisite explicitly says to use the legacy Microsoft Foundry UI and instructs learners to turn New Foundry off. The created project opens in the current New Foundry experience, whose Home uses top navigation and an Explore models card; screenshot 0019 captures the replacement UX. The legacy path remains selectable but is superseded.
  <br>instruction: `#1-ensure-that-you-are-on-the-microsoft-foundry-overview-page`

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `108`** · no instruction anchor recorded — Used the latest New Foundry Home > Explore models route instead of the documented legacy left-menu Model catalog route.
- **Step `120`** · no instruction anchor recorded — Used the latest model detail Deploy control instead of the legacy Use this model flow.
- **Step `179`** · no instruction anchor recorded — Verified deployments in New Foundry Build > Models > Deployments rather than the documented legacy Models + endpoints menu.

## Verified correct

- The firstProject current Home page loaded successfully in New Foundry and exposes model deployment entry points.
- In New Foundry, Deploy > Default settings created a gpt-5.1 Global Standard deployment and opened its current playground. The product path works, but differs from the documented legacy Use this model dialog.
- New Foundry deployed gpt-5-mini with Default settings and opened its playground with a Global Standard deployment.
- New Foundry deployed text-embedding-3-large version 1 as GlobalStandard; the Details page showed provisioning state Succeeded and model identity text-embedding-3-large.
- New Foundry deployed text-embedding-ada-002 version 2 as GlobalStandard; Details showed provisioning state Succeeded and matching model identity.
- New Foundry Build > Models > Deployments showed gpt-5.1, gpt-5-mini, text-embedding-3-large, and text-embedding-ada-002, all Succeeded with matching model identities.
- The firstProject New Foundry Home page loaded and provided current model deployment entry points.

## Evidence

15 capture(s), in the order the learner would have seen them.

- [`0019-s02-deploy-models-in-latest-home.jpg`](../images/0019-s02-deploy-models-in-latest-home.jpg)
- [`0020-s02-deploy-models-in-latest-model-catalog.jpg`](../images/0020-s02-deploy-models-in-latest-model-catalog.jpg)
- [`0021-s02-deploy-models-in-search-gpt51-latest.jpg`](../images/0021-s02-deploy-models-in-search-gpt51-latest.jpg)
- [`0022-s02-deploy-models-in-gpt51-latest-detail.jpg`](../images/0022-s02-deploy-models-in-gpt51-latest-detail.jpg)
- [`0023-s02-deploy-models-in-gpt51-deploy-dialog.jpg`](../images/0023-s02-deploy-models-in-gpt51-deploy-dialog.jpg)
- [`0024-s02-deploy-models-in-gpt51-default-deploy.jpg`](../images/0024-s02-deploy-models-in-gpt51-default-deploy.jpg)
- [`0025-s02-deploy-models-in-gpt51-latest-result.jpg`](../images/0025-s02-deploy-models-in-gpt51-latest-result.jpg)
- [`0026-s02-deploy-models-in-latest-models-list.jpg`](../images/0026-s02-deploy-models-in-latest-models-list.jpg)
- [`0027-s02-deploy-models-in-deploy-base-model.jpg`](../images/0027-s02-deploy-models-in-deploy-base-model.jpg)
- [`0028-s02-deploy-models-in-deploy-gpt5-mini-latest.jpg`](../images/0028-s02-deploy-models-in-deploy-gpt5-mini-latest.jpg)
- [`0029-s02-deploy-models-in-search-embedding3-latest.jpg`](../images/0029-s02-deploy-models-in-search-embedding3-latest.jpg)
- [`0030-s02-deploy-models-in-deploy-embedding3-latest.jpg`](../images/0030-s02-deploy-models-in-deploy-embedding3-latest.jpg)
- [`0031-s02-deploy-models-in-search-ada002-latest.jpg`](../images/0031-s02-deploy-models-in-search-ada002-latest.jpg)
- [`0032-s02-deploy-models-in-deploy-ada002-latest.jpg`](../images/0032-s02-deploy-models-in-deploy-ada002-latest.jpg)
- [`0033-s02-deploy-models-in-verify-latest-deployments.jpg`](../images/0033-s02-deploy-models-in-verify-latest-deployments.jpg)
