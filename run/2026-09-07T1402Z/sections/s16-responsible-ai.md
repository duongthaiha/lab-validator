# Responsible AI

*Section* `s16-responsible-ai`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#responsible-ai`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 44 recorded step(s), 4 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB004** ×3 · **LAB005** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Removed feature (`LAB005`)
- **#2** Moved navigation (`LAB004`)
- **#3** Moved navigation (`LAB004`)
- **#4** Moved navigation (`LAB004`)

### 1. [!] Removed feature — `LAB005`

*Instruction:* `#responsible-ai`  
*Severity:* major · *At fault:* instruction · *Step:* `2053` · *2026-09-07T18:35:31Z*

The Manual Evaluation exercise has no surface in the current portal. The lab says 'go to the Protect and govern section, select Evaluation, at the top choose Manual evaluations, select New Manual Evaluation', then rate results with thumbs up/down. There is no 'Protect and govern' section in the current left navigation, and the Evaluations page (Build > Evaluations) exposes exactly three tabs - Evaluations, Evaluator catalog, Red team - with two sub-tabs, Runs and Recurring configs. None of them is 'Manual evaluations' and there is no New Manual Evaluation control anywhere on the page. Every step of that sub-exercise, including the thumbs-up rating, the Temperature and Search type comparison and saving iterations, is therefore unfollowable.

### 2. [!] Moved navigation — `LAB004`

*Instruction:* `#responsible-ai`  
*Severity:* major · *At fault:* instruction · *Step:* `2055` · *2026-09-07T18:35:32Z*

None of the four Content Safety and Prompt Shields exercises has a route in the current portal. The lab asks for 'On the left, select AI Services. On the right, choose Content Safety' and then Moderate text content, Protected material detection for text, and Moderate image content; and separately for 'Guardrails + controls tab on the left navigation, then choose the Try it out button' followed by a Prompt Shields panel. Measured rather than glanced at: the Build left navigation has exactly ten entries (Agents, Models, Fine-tune, Services, Tools, Knowledge, Memory, Data, Evaluations, Guardrails) and none is AI Services; Build > Services > Playgrounds lists 18 of 18 playgrounds (six Content Understanding, five Speech, two Translator, five Language) and none is Content Safety; Build > Guardrails has three tabs (Guardrails, Blocklists, Integrations Preview) with a filter list and a Create button, and no 'Try it out' control and no Prompt Shields panel; Operate offers only Overview, Assets and Compliance; Discover is the model catalogue. The three CSV/ZIP bulk-test datasets the lab ships under Files/Content_Safety therefore have nowhere to be uploaded.

### 3. [~] Moved navigation — `LAB004`

*Instruction:* `#responsible-ai`  
*Severity:* minor · *At fault:* instruction · *Step:* `2052` · *2026-09-07T18:35:31Z*

The PII exercise's route and control names are all from the previous Foundry. The lab says: resource group > Azure AI project > Press Launch Studio > Playgrounds on the left > 'Try the Language playground' card > scroll the carousel > 'Extract PII from text' > Press Run. The current portal has no Playgrounds left-nav entry, no Language playground card and no carousel; the destination is Build > Services > Playgrounds > 'Azure Language - Text PII Redaction', and the action button is 'Detect', not 'Run'. The exercise still completes, so this costs the learner navigation time rather than the outcome.

### 4. [~] Moved navigation — `LAB004`

*Instruction:* `#responsible-ai`  
*Severity:* minor · *At fault:* instruction · *Step:* `2054` · *2026-09-07T18:35:32Z*

The Automated Evaluation exercise survives but under different names and a different shape. 'Automated evaluations' is now just the Evaluations tab, 'Click Create a new Evaluation' is a 'Create' button, and the wizard is six steps (Target, Scope, Frequency, Data, Criteria, Review) rather than the lab's dataset-then-evaluators pair. The lab's 'Evaluate an existing query-response dataset' choice is present as 'Dataset - Evaluate an existing dataset', alongside two options the lab does not know about, Agent and Model.

## Verified correct

- The PII Detection and Masking exercise works, and was verified from its output rather than from the page loading. Reached the current equivalent at ai.azure.com/nextgen > Build > Services > Playgrounds > 'Azure Language - Text PII Redaction', chose the 'Legal (NDA)' sample the lab names, and pressed Detect. The service returned nine real entities with types, confidences and offsets: Date 100% (offset 15), PersonType 99% (offset 40), Organization 'Contoso Restaurant' 100% (offset 52), Person 'Mateo Gomez' 98% (offset 75), Address '1234 Hollywood Boulevard Los Angeles CA' 97% (offset 100), USSocialSecurityNumber '123-45-6788' 100% (offset 170), a second Organization at offset 265, a second Person at offset 420 and Email 'mateo@contosorestaurant.com' 80% (offset 602). The masking control the lab calls the 'Hide PII slider' is present as a 'Redact PII' toggle and was on, with the input text shown masked; the 'Edit (crayon) icon' is present as an 'Edit' button.
- Coverage limit for this section, stated so it is not read as clean: the Evaluations Setup sub-exercise (uploading Files/Contoso to the -azureml-blobstore container and building a vector index over it with text-embedding-3-large), the end-to-end Manual Evaluation run, the full Automated Evaluation submission with its ten evaluators, the three Content Safety bulk tests and the System Message / Agents Playground exercise were not executed. The first was not attempted because its consumer, Manual Evaluation, no longer exists; the Content Safety ones have no route to attempt; the rest were left unrun to keep the remaining eight sections moving. They are unknown, not correct.
- Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.

## Evidence

10 capture(s), in the order the learner would have seen them.

- [`0254-s16-responsible-ai-open-guardrails.jpg`](../images/0254-s16-responsible-ai-open-guardrails.jpg)
- [`0255-s16-responsible-ai-open-services.jpg`](../images/0255-s16-responsible-ai-open-services.jpg)
- [`0256-s16-responsible-ai-search-content-safety.jpg`](../images/0256-s16-responsible-ai-search-content-safety.jpg)
- [`0257-s16-responsible-ai-open-pii-playground.jpg`](../images/0257-s16-responsible-ai-open-pii-playground.jpg)
- [`0258-s16-responsible-ai-pii-sample.jpg`](../images/0258-s16-responsible-ai-pii-sample.jpg)
- [`0259-s16-responsible-ai-pii-run.jpg`](../images/0259-s16-responsible-ai-pii-run.jpg)
- [`0260-s16-responsible-ai-check-top-nav.jpg`](../images/0260-s16-responsible-ai-check-top-nav.jpg)
- [`0261-s16-responsible-ai-check-operate.jpg`](../images/0261-s16-responsible-ai-check-operate.jpg)
- [`0262-s16-responsible-ai-open-evaluations.jpg`](../images/0262-s16-responsible-ai-open-evaluations.jpg)
- [`0263-s16-responsible-ai-eval-create-flow.jpg`](../images/0263-s16-responsible-ai-eval-create-flow.jpg)
