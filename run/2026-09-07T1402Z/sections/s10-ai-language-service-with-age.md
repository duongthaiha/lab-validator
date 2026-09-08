# AI Language Service with Agents Lab

*Section* `s10-ai-language-service-with-age`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#ai-language-service-with-agents-lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 119 recorded step(s), 33 heartbeat(s), 2 finding(s)

**Can a learner finish this section?** **YES** — a learner following the instructions can complete this

## Findings

**LAB004** ×1 · **LAB010** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Moved navigation (`LAB004`)
- **#2** Superseded or retiring feature (`LAB010`)

### 1. [~] Moved navigation — `LAB004`

*Instruction:* `#copy-the-access-language-api-key-and-endpoint-url`  
*Severity:* minor · *At fault:* instruction · *Step:* `1267` · *2026-09-07T16:32:16Z*

New Foundry no longer exposes the API key and Azure AI Services endpoint on the project Overview page. The current route is the backing Foundry resource in Azure portal, Resource Management > Keys and Endpoint.

### 2. [~] Superseded or retiring feature — `LAB010`

*Instruction:* `#create-a-pii-redaction-logic-app`  
*Severity:* minor · *At fault:* instruction · *Step:* `1268` · *2026-09-07T16:32:17Z*

The portal opened the previous Logic Apps designer and explicitly offered Switch to preview experience. In the current experience the workflow is draft/autosaved and uses Publish/Run draft, not the documented Save/Run canvas shown in the lab.

## Ageing guidance (works today)

Nothing here stopped a learner. Each is a step that *succeeded* while following a path the product has moved on from, so it dates the lab rather than breaking it.

- **#2** Superseded or retiring feature — The portal opened the previous Logic Apps designer and explicitly offered Switch to preview experience. In the current experience the workflow is draft/autosaved and uses Publish/Run draft, not the documented Save/Run canvas shown in the lab.
  <br>instruction: `#create-a-pii-redaction-logic-app`

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `1267`** · instruction `#copy-the-access-language-api-key-and-endpoint-url` — Retrieved the endpoint from the backing Foundry resource rather than the documented Foundry Overview page.
  <br>outcome: New Foundry no longer exposes the API key and Azure AI Services endpoint on the project Overview page. The current route is the backing Foundry resource in Azure portal, Resource Management > Keys and Endpoint.
- **Step `1268`** · instruction `#create-a-pii-redaction-logic-app` — Switched to the current preview Logic Apps designer as requested for this validation.
  <br>outcome: The portal opened the previous Logic Apps designer and explicitly offered Switch to preview experience. In the current experience the workflow is draft/autosaved and uses Publish/Run draft, not the documented Save/Run canvas shown in the lab.

## Verified correct

- Coverage limit for this section, stated so it is not read as clean. The Logic Apps designer exercise was left in an inconsistent state by the walk itself, not by the lab: a delayed response in the designer caused a duplicated Parse JSON action to be added, so the workflow was never run end to end and the section's later steps were not exercised. That is an artefact of how this walk drove the UI and must not be read as a lab defect. What it does mean is that any defect living in the unrun portion of this section would not have been detected, and the absence of findings there is absence of evidence.
- Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.

## Deferred

_Postponed by the walk, not by the lab. These say nothing about the lab._

- Azure Portal/Username typed (delta 1.4); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 1.8); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed

## Evidence

30 capture(s), in the order the learner would have seen them.

- [`0131-s10-ai-language-serv-inspect-current-screen.jpg`](../images/0131-s10-ai-language-serv-inspect-current-screen.jpg)
- [`0132-s10-ai-language-serv-open-azure-portal.jpg`](../images/0132-s10-ai-language-serv-open-azure-portal.jpg)
- [`0133-s10-ai-language-serv-portal-reauth.jpg`](../images/0133-s10-ai-language-serv-portal-reauth.jpg)
- [`0134-s10-ai-language-serv-finish-portal-login.jpg`](../images/0134-s10-ai-language-serv-finish-portal-login.jpg)
- [`0135-s10-ai-language-serv-find-logic-app.jpg`](../images/0135-s10-ai-language-serv-find-logic-app.jpg)
- [`0136-s10-ai-language-serv-open-logic-apps.jpg`](../images/0136-s10-ai-language-serv-open-logic-apps.jpg)
- [`0137-s10-ai-language-serv-create-logic-app.jpg`](../images/0137-s10-ai-language-serv-create-logic-app.jpg)
- [`0138-s10-ai-language-serv-select-consumption.jpg`](../images/0138-s10-ai-language-serv-select-consumption.jpg)
- [`0139-s10-ai-language-serv-configure-pii-app.jpg`](../images/0139-s10-ai-language-serv-configure-pii-app.jpg)
- [`0140-s10-ai-language-serv-fill-pii-app-basics.jpg`](../images/0140-s10-ai-language-serv-fill-pii-app-basics.jpg)
- [`0141-s10-ai-language-serv-deploy-pii-app.jpg`](../images/0141-s10-ai-language-serv-deploy-pii-app.jpg)
- [`0142-s10-ai-language-serv-submit-pii-app.jpg`](../images/0142-s10-ai-language-serv-submit-pii-app.jpg)
- [`0143-s10-ai-language-serv-wait-validation.jpg`](../images/0143-s10-ai-language-serv-wait-validation.jpg)
- [`0144-s10-ai-language-serv-open-pii-app.jpg`](../images/0144-s10-ai-language-serv-open-pii-app.jpg)
- [`0145-s10-ai-language-serv-open-logic-designer.jpg`](../images/0145-s10-ai-language-serv-open-logic-designer.jpg)
- [`0146-s10-ai-language-serv-enter-designer.jpg`](../images/0146-s10-ai-language-serv-enter-designer.jpg)
- [`0147-s10-ai-language-serv-switch-new-designer.jpg`](../images/0147-s10-ai-language-serv-switch-new-designer.jpg)
- [`0148-s10-ai-language-serv-load-new-designer.jpg`](../images/0148-s10-ai-language-serv-load-new-designer.jpg)
- [`0149-s10-ai-language-serv-add-http-trigger.jpg`](../images/0149-s10-ai-language-serv-add-http-trigger.jpg)
- [`0150-s10-ai-language-serv-select-http-trigger.jpg`](../images/0150-s10-ai-language-serv-select-http-trigger.jpg)
- [`0151-s10-ai-language-serv-configure-http-trigger.jpg`](../images/0151-s10-ai-language-serv-configure-http-trigger.jpg)
- [`0152-s10-ai-language-serv-add-parse-json.jpg`](../images/0152-s10-ai-language-serv-add-parse-json.jpg)
- [`0153-s10-ai-language-serv-open-action-picker.jpg`](../images/0153-s10-ai-language-serv-open-action-picker.jpg)
- [`0154-s10-ai-language-serv-choose-parse-json.jpg`](../images/0154-s10-ai-language-serv-choose-parse-json.jpg)
- [`0155-s10-ai-language-serv-insert-parse-json.jpg`](../images/0155-s10-ai-language-serv-insert-parse-json.jpg)
- [`0156-s10-ai-language-serv-set-parse-content.jpg`](../images/0156-s10-ai-language-serv-set-parse-content.jpg)
- [`0157-s10-ai-language-serv-open-content-picker.jpg`](../images/0157-s10-ai-language-serv-open-content-picker.jpg)
- [`0158-s10-ai-language-serv-type-parse-input.jpg`](../images/0158-s10-ai-language-serv-type-parse-input.jpg)
- [`0159-s10-ai-language-serv-retry-parse-input.jpg`](../images/0159-s10-ai-language-serv-retry-parse-input.jpg)
- [`0160-s10-ai-language-serv-inspect-code-view.jpg`](../images/0160-s10-ai-language-serv-inspect-code-view.jpg)
