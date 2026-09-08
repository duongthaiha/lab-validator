# 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model

*Section* `s13-steps-fine-tuning-the-gpt-41`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#🛠️-steps-fine-tuning-the-gpt-41-mini-model`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 136 recorded step(s), 20 heartbeat(s), 7 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## What the lab asks the learner to do

- 1. Sign in to Azure Portal
- 2. Open the Azure AI Foundry Portal
- 3. Start Fine-Tuning
- 4. Configure Fine-Tuning Job
- 5. Review Results
- 6. Deploy and Test

## Findings

**LAB003** ×4 · **LAB004** ×3

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Moved navigation (`LAB004`)
- **#2** Moved navigation (`LAB004`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)
- **#4** Changed UI label or inconsistent structure (`LAB003`)
- **#5** Moved navigation (`LAB004`)
- **#6** Changed UI label or inconsistent structure (`LAB003`)
- **#7** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!] Moved navigation — `LAB004`

*Instruction:* `#5-review-results`  
*Severity:* major · *At fault:* instruction · *Step:* `2929` · *2026-09-07T23:15:14Z*

Step 5 says 'Once complete, go to the Metrics tab' and 'Click Use this model to deploy'. Neither control exists under the current Foundry experience. The completed job wplus-ft-64827025 (ftjob-af929589ec224665b7cdc8357449101c) opens with tabs Details, Monitor, Logs, Checkpoints, Deployments - there is no tab named Metrics. Summary metrics appear inline on Details as two tiles (Final train loss, Final train mean token accuracy) with a 'View all metrics' link, and the loss/accuracy charts live under Monitor (whose route is .../metrics, so the label moved but the URL did not). There is likewise no 'Use this model to deploy' control: deployment is a 'Deploy' button in the job command bar, next to 'Continuous fine-tuning'.

### 2. [!] Moved navigation — `LAB004`

*Instruction:* `#6-deploy-and-test`  
*Severity:* major · *At fault:* instruction · *Step:* `3120` · *2026-09-08T00:01:08Z*

Step 6 routes the learner to 'My assets > Models + endpoints', which is the classic Azure AI Foundry left-nav and does not exist in the current experience. There is no 'My assets' grouping; deployments live at Build > Models > Deployments (tabs Deployments / Models / Batch jobs, split into Serverless deployments and Managed compute deployments). 'Open in playground' does still exist, but as a button on the deployment's details pane rather than the classic location, and the deployment page's own first tab is called Playground. A learner searching the current portal for 'My assets' finds nothing.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#🛠️-steps-fine-tuning-the-gpt-41-mini-model`  
*Severity:* minor · *At fault:* instruction · *Step:* `1754` · *2026-09-07T17:40:55Z*

Step 3 and step 4 name controls the current portal does not have. The lab says 'Click + Fine-tune model'; the empty Fine-tuning page offers 'Start fine-tuning' and the populated list offers 'Fine-tune'. The lab says 'Add a suffix name for your model'; the wizard's field is 'Display name' and it arrives pre-filled with a generated name (fast-reef-s44f), so a learner looking for the word suffix will not find it. The lab also has the learner choose the model first and then 'Select Supervised method', while the wizard asks for Customization method first and Model second. All observed on the live 'Fine-tune a model' wizard.

### 4. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#🛠️-steps-fine-tuning-the-gpt-41-mini-model`  
*Severity:* minor · *At fault:* instruction · *Step:* `1755` · *2026-09-07T17:40:56Z*

The Basic details step carries a third required field, 'Training type', defaulting to 'Data Zone', which step 4's value list does not mention. It is pre-filled so it does not block submission, but it is a required choice with cost and data-residency consequences that the learner is never told they are making.

### 5. [~] Moved navigation — `LAB004`

*Instruction:* `#2-open-the-azure-ai-foundry-portal`  
*Severity:* minor · *At fault:* instruction · *Step:* `2066` · *2026-09-07T18:36:48Z*

The step says only 'Launch the Azure AI Foundry Resource created in the pre-requisites lab', which no longer names a real control. https://ai.azure.com now lands on an unauthenticated marketing page ('The AI app and agent factory') with a Sign in button and no route into the resource. The working destination is https://ai.azure.com/nextgen, which opens All resources and lists firstProject under parent resource ai-foundry-64827025 in East US 2; opening that reaches the project home. The learner gets there, but not by anything the step describes.

### 6. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#3-start-fine-tuning`  
*Severity:* minor · *At fault:* instruction · *Step:* `2067` · *2026-09-07T18:36:48Z*

The destination exists but neither control is called what the step calls it. 'Navigate to the Fine-tuning section' is Build > Fine-tune in the current left navigation, and 'Click + Fine-tune model' is 'Start fine-tuning' on the empty state (and 'Fine-tune' once at least one job exists). The model choice the step offers does hold up: opening the Model dropdown showed gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, Llama-3.3-70B-Instruct, gpt-oss-20b, gpt-4o and gpt-4o-mini, so all three of GPT-4.1-mini, GPT-4o-mini and GPT-4o are still selectable.

### 7. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#5-review-results`  
*Severity:* minor · *At fault:* instruction · *Step:* `2931` · *2026-09-07T23:15:39Z*

Step 5 is 'Review Results' but gives the learner no criterion for what a good result looks like, and the two headline numbers the portal puts first are misleading on this lab's own configuration. Details shows Final train loss 0 and Final train mean token accuracy 1, which reads as a flawless fine-tune. The Monitor curves say otherwise: train loss falls to 0 by roughly step 40 while validation loss climbs from about 1.5 to about 3.5 and stays there, and validation mean token accuracy plateaus near 0.65 while train accuracy saturates at 1.0. That is textbook overfitting, and it is what 10 training samples over 10 epochs with a learning rate multiplier of 2 - the values the lab itself specifies in step 4 - will produce. A learner following the text will read the two tiles, see perfection, and deploy a memorised model without ever being pointed at the divergence.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `2930`** · instruction `#5-review-results` — Elapsed time is worth flagging for scheduling: the estimate shown while the job was queued was ~52 minutes and it actually took 1h 25m, so a learner on a fixed-length delivery will be waiting considerably longer than the portal predicts.
  <br>outcome: The job configured in step 4 does complete and does produce reviewable results. wplus-ft-64827025: base gpt-4.1-mini-2025-04-14, Supervised, created 10:39:57, training completed 12:05:37, duration 1h 25m, 5,000 training tokens billed, batch size 1, 10 epochs, learning rate multiplier 2, seed 298089851, with training_set_10samples.jsonl, validation_set_10samples.jsonl and a downloadable results.csv all linked from Details. The Monitor tab renders real per-step curves over 100 steps (Train loss, Valid loss, Full valid loss; Train/Valid/Full valid mean token accuracy), not placeholder tiles.

## Verified correct

- Steps 1-4 complete on the current Foundry UX. Reached Build > Fine-tune in the New Foundry portal (ai.azure.com/nextgen, New Foundry toggle on) for firstProject under ai-foundry-64827025, started a job, chose Supervised, and gpt-4.1-mini is present in the model list along with gpt-4o and gpt-4o-mini, so all three models the lab offers are still selectable. Both files uploaded from C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning: training_set_10samples.jsonl and validation_set_10samples.jsonl, each 2.6 KB and each previewed by the portal as 'Total rows: 10' with real content ('Clippy is a factual chatbot that is also sarcastic'), so the datasets are genuine and accepted, not silently empty. Hyperparameters left at Default as instructed. Submit produced a real job: wplus-ft-64827025, base model gpt-4.1-mini-2025-04-14, Customization method Supervised, status Queued, created 9/7/26 10:39:57 AM.
- portal.azure.com was already signed in as User1-64827025 in the lab VM's browser from earlier sections; no re-authentication was required and the portal rendered normally.
- The job configures and submits as described. Customization method Supervised, both files uploaded from C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning (training_set_10samples.jsonl and validation_set_10samples.jsonl, 2.6 KB each), each previewed by the portal as 'Total rows: 10' with real content, hyperparameters left at Default, and Submit created job wplus-ft-64827025 on base model gpt-4.1-mini-2025-04-14 at 10:39:57. Caveats recorded separately: the suffix field is now 'Display name' and arrives pre-filled, and a required 'Training type' field (Data Zone) is not mentioned by the step.
- poll fine-tune job status
- open completed SFT job wplus-ft-64827025
- open Monitor tab for training curves
- click Deploy on the completed fine-tuned model
- confirm deployment of fine-tuned model
- wait for deployment provisioning
- check deployment status of the fine-tuned model
- open the fine-tuned deployment in playground
- send a prompt to the fine-tuned deployment
- Deploy and test works end to end. Deploy from the completed job opened a 'Customize ... deployment' panel (Deployment name prefilled, Deployment type Global Standard, TPM rate limit 10000/500000, Guardrails DefaultV2); the deployment went Creating at 16:11 and reached Succeeded, appearing in Build > Models > Deployments as gpt-4.1-mini-2025-04-14.ft-af929589ec224665b7cdc8357449101c-wp, Global Standard, v2025-04-14. The details pane exposes Project endpoint and a masked API Key exactly as step 6 asks the learner to review, plus a ready-made Python snippet. 'Open in playground' loaded the deployment and a prompt returned a real completion attributed to the fine-tuned deployment name (352 tokens, 5s), so this is served inference from the fine-tuned model and not a stale base-model chat.
- Section 13 complete: all six steps judged; job completed, deployed and tested.

## Withdrawn judgements

- step `1694` — Not a lab defect. The quiet probe never settled because https://ai.azure.com/home is the unauthenticated Microsoft Foundry marketing page, which autoplays a looping hero video; capture 0215 shows a fully loaded, healthy page with a cookie banner and a Sign in button. This measures the probe against an animation, not a timing or quota problem in the lab. Withdrawn.

## Evidence

29 capture(s), in the order the learner would have seen them.

- [`0214-s13-steps-fine-tunin-open-foundry-timeout.jpg`](../images/0214-s13-steps-fine-tunin-open-foundry-timeout.jpg)
- [`0215-s13-steps-fine-tunin-open-foundry.jpg`](../images/0215-s13-steps-fine-tunin-open-foundry.jpg)
- [`0216-s13-steps-fine-tunin-open-foundry-nextgen.jpg`](../images/0216-s13-steps-fine-tunin-open-foundry-nextgen.jpg)
- [`0217-s13-steps-fine-tunin-open-project.jpg`](../images/0217-s13-steps-fine-tunin-open-project.jpg)
- [`0218-s13-steps-fine-tunin-open-build-menu.jpg`](../images/0218-s13-steps-fine-tunin-open-build-menu.jpg)
- [`0219-s13-steps-fine-tunin-open-finetune.jpg`](../images/0219-s13-steps-fine-tunin-open-finetune.jpg)
- [`0220-s13-steps-fine-tunin-start-finetuning.jpg`](../images/0220-s13-steps-fine-tunin-start-finetuning.jpg)
- [`0221-s13-steps-fine-tunin-ft-model-dropdown.jpg`](../images/0221-s13-steps-fine-tunin-ft-model-dropdown.jpg)
- [`0222-s13-steps-fine-tunin-ft-select-model.jpg`](../images/0222-s13-steps-fine-tunin-ft-select-model.jpg)
- [`0223-s13-steps-fine-tunin-ft-next-datasets.jpg`](../images/0223-s13-steps-fine-tunin-ft-next-datasets.jpg)
- [`0224-s13-steps-fine-tunin-ft-upload-training.jpg`](../images/0224-s13-steps-fine-tunin-ft-upload-training.jpg)
- [`0225-s13-steps-fine-tunin-ft-pick-training.jpg`](../images/0225-s13-steps-fine-tunin-ft-pick-training.jpg)
- [`0226-s13-steps-fine-tunin-ft-upload-validation.jpg`](../images/0226-s13-steps-fine-tunin-ft-upload-validation.jpg)
- [`0227-s13-steps-fine-tunin-ft-optional-settings.jpg`](../images/0227-s13-steps-fine-tunin-ft-optional-settings.jpg)
- [`0228-s13-steps-fine-tunin-ft-set-name.jpg`](../images/0228-s13-steps-fine-tunin-ft-set-name.jpg)
- [`0229-s13-steps-fine-tunin-ft-submit.jpg`](../images/0229-s13-steps-fine-tunin-ft-submit.jpg)
- [`0253-s13-steps-fine-tunin-ft-status-check.jpg`](../images/0253-s13-steps-fine-tunin-ft-status-check.jpg)
- [`0285-s13-steps-fine-tunin-step.jpg`](../images/0285-s13-steps-fine-tunin-step.jpg)
- [`0286-s13-steps-fine-tunin-step.jpg`](../images/0286-s13-steps-fine-tunin-step.jpg)
- [`0287-s13-steps-fine-tunin-step.jpg`](../images/0287-s13-steps-fine-tunin-step.jpg)
- [`0441-s13-steps-fine-tunin-step.jpg`](../images/0441-s13-steps-fine-tunin-step.jpg)
- [`0442-s13-steps-fine-tunin-step.jpg`](../images/0442-s13-steps-fine-tunin-step.jpg)
- [`0443-s13-steps-fine-tunin-step.jpg`](../images/0443-s13-steps-fine-tunin-step.jpg)
- [`0444-s13-steps-fine-tunin-step.jpg`](../images/0444-s13-steps-fine-tunin-step.jpg)
- [`0445-s13-steps-fine-tunin-step.jpg`](../images/0445-s13-steps-fine-tunin-step.jpg)
- [`0446-s13-steps-fine-tunin-step.jpg`](../images/0446-s13-steps-fine-tunin-step.jpg)
- [`0476-s13-steps-fine-tunin-step.jpg`](../images/0476-s13-steps-fine-tunin-step.jpg)
- [`0477-s13-steps-fine-tunin-step.jpg`](../images/0477-s13-steps-fine-tunin-step.jpg)
- [`0478-s13-steps-fine-tunin-step.jpg`](../images/0478-s13-steps-fine-tunin-step.jpg)
