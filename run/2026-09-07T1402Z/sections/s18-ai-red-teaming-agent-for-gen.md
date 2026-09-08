# AI Red Teaming Agent for Generative AI Applications

*Section* `s18-ai-red-teaming-agent-for-gen` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#ai-red-teaming-agent-for-generative-ai-applications`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 173 recorded step(s), 4 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB003** ×2 · **LAB005** ×1 · **LAB009** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Removed feature (`LAB005`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)
- **#4** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* major · *At fault:* instruction · *Step:* `2898` · *2026-09-07T23:07:58Z*

AI_RedTeaming.ipynb cell 5 contains a bare '!az login' between the azure.identity import and 'credential = AzureCliCredential()'. This directly contradicts the section's own Setup step ('Authenticate to Azure by running az login --use-device-code in your terminal before running the notebook') and the notebook's own markdown cells 1 and 4, which both say to authenticate in a terminal BEFORE running the notebook. Effect observed: az login defaults to the interactive browser flow, so a Run All stalls on an account picker; the VM had accumulated ~25 blank Edge windows from repeated interactive login attempts, and one showed a failed sign-in for a stale account. The learner is already authenticated by the documented pre-step, so the cell is redundant as well as blocking. Removing only that line let the notebook run to completion unattended.

### 2. [!] Removed feature — `LAB005`

*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* major · *At fault:* instruction · *Step:* `2899` · *2026-09-07T23:08:09Z*

The notebook's markdown cell 26 states: 'The data and results used in this attack will be saved to the output_path specified. The URL printed out at the end of the scorecard will provide a link to where you results are uploaded and logged to your Azure AI Foundry project.' Neither half held. Every RedTeam object was constructed with azure_ai_project=AI_FOUNDRY_PROJECT_ENDPOINT and credential=AzureCliCredential(), yet no ai.azure.com URL appears anywhere in the executed notebook's output (grep over all cell outputs returned only the four 'Overall ASR' lines), and Microsoft Foundry > Build > Evaluations > Red team reports 'No red teams found' after all four scans completed. Results exist only as local files. A learner following the text would go looking in the portal for a scan record that is not there.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* minor · *At fault:* instruction · *Step:* `2900` · *2026-09-07T23:08:19Z*

Cell 19 - the Intermediary-Model-Target-Scan, and the only scan in the notebook that attacks a real deployed model rather than a hard-coded callback - is the one scan that omits output_path, while cells 15, 25 and 29 all set one. Its results therefore never appear as a named JSON in the working folder; they are only in the hidden .scan_Intermediary-Model-Target-Scan_<timestamp>/final_results.json. That is exactly the scan whose numbers are worth reading: it is the only one with a non-zero Attack Success Rate (50.0%, violence 2/2). A learner told to inspect 'the results' will find three JSON files and miss the interesting one.

### 4. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* minor · *At fault:* instruction · *Step:* `2901` · *2026-09-07T23:08:30Z*

Four text defects in this section. (1) 'Using the Notebook' says 'The notebook provides two main examples' and then lists three (Basic, Intermediary, Advanced); the notebook actually runs four scans - the fourth, Custom-Prompt-Scan, is undocumented in this list. (2) The copy-button control text has bled into the rendered code blocks: 'bashTypeCopy   pip install ...' and 'envTypeCopy   # Azure OpenAI', so a learner selecting the block copies 'bashTypeCopy' with it. (3) Typos: 'When testing different attach strategies' and 'attack stragies'. (4) The four Additional Resources entries are written as if they were links ('Learn more about Azure AI Foundry Evaluations.') but render as plain text with no URL, so none of them is reachable.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `2897`** · instruction `#ai-red-teaming-agent-for-generative-ai-applications` — Ran the notebook headless via nbconvert from a clean Windows Terminal rather than clicking Run All in VS Code, to avoid opening the .env-bearing workspace; the only source edit was commenting out the interactive !az login in cell 5 (see the finding below). pip install of azure-ai-evaluation[redteam] and duckdb<1.4.0 was run exactly as documented and downgraded duckdb 1.4.0 to 1.3.2.
  <br>outcome: AI_RedTeaming.ipynb executes end to end with zero cell errors (nbconvert, 13:21-14:06 = 45 min, inside the documented 30-45 min estimate). Evidence is artifact-level, not headings: four scans wrote real per-conversation JSONL plus final_results.json. Basic-Callback-Scan 4 conversations (violence 2, hate_unfairness 2) ASR 0.0; Advanced-Callback-Scan 20 conversations (5 each across violence/hate_unfairness/sexual/self_harm) ASR 0.0; Custom-Prompt-Scan 3 conversations from ../data/prompts.json ASR 0.0; Intermediary-Model-Target-Scan 4 conversations against the real gpt-5-mini deployment with overall ASR 50.0 and violence_asr 100.0 (2 of 2 successful attacks). Non-zero attack totals in every scorecard rule out the 'scan succeeded having evaluated nothing' false success.
- **Step `2902`** · instruction `#ai-red-teaming-agent-for-generative-ai-applications` — Also noted: the Setup block lists AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP and AZURE_PROJECT_NAME as required, but the notebook reads only AI_FOUNDRY_PROJECT_ENDPOINT; the three are unused here.
  <br>outcome: Corroboration for the endpoint-shape defect reported against Lab 10 (Azure SQL). This section's Setup block is where the bad shape is documented: AZURE_OPENAI_ENDPOINT is specified as 'https://endpoint-name.openai.azure.com/openai/deployments/deployment-name/chat/completions', i.e. a full inference URI rather than the bare resource endpoint that the Azure SQL and PostgreSQL labs both concatenate paths onto. The deployed .env follows this section's shape, which is why 4_SQLEmbeddings.py composed a doubled path. Recorded here as evidence of origin, not as a second finding.

## Verified correct

- focus terminal
- run error scan
- capture error scan output
- capture error scan output
- inspect red team scorecards
- inspect scan working folders
- inspect intermediary model target scan results
- inspect notebook scan configuration
- look for foundry upload URL in outputs
- inspect RedTeam constructor and project wiring
- switch to VM Edge to check Foundry for uploaded red team results
- open a blank Edge window
- open Microsoft Foundry nextgen portal
- re-authenticate Foundry session
- pick lab user account
- sign in to Foundry with portal role credential
- open Build > Evaluations to look for red teaming runs
- return to Foundry home
- open Build hub
- open Evaluations to check for uploaded red team scans
- open Red team tab
- Section 18 complete: all four scans executed and their artifacts inspected.

## Deferred

_Postponed by the walk, not by the lab. These say nothing about the lab._

- Azure Portal/Password typed (delta 1.6); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed

## Evidence

36 capture(s), in the order the learner would have seen them.

- [`0300-s18-ai-red-teaming-a-step.jpg`](../images/0300-s18-ai-red-teaming-a-step.jpg)
- [`0301-s18-ai-red-teaming-a-step.jpg`](../images/0301-s18-ai-red-teaming-a-step.jpg)
- [`0302-s18-ai-red-teaming-a-step.jpg`](../images/0302-s18-ai-red-teaming-a-step.jpg)
- [`0303-s18-ai-red-teaming-a-step.jpg`](../images/0303-s18-ai-red-teaming-a-step.jpg)
- [`0304-s18-ai-red-teaming-a-step.jpg`](../images/0304-s18-ai-red-teaming-a-step.jpg)
- [`0305-s18-ai-red-teaming-a-step.jpg`](../images/0305-s18-ai-red-teaming-a-step.jpg)
- [`0306-s18-ai-red-teaming-a-step.jpg`](../images/0306-s18-ai-red-teaming-a-step.jpg)
- [`0307-s18-ai-red-teaming-a-step.jpg`](../images/0307-s18-ai-red-teaming-a-step.jpg)
- [`0308-s18-ai-red-teaming-a-step.jpg`](../images/0308-s18-ai-red-teaming-a-step.jpg)
- [`0309-s18-ai-red-teaming-a-step.jpg`](../images/0309-s18-ai-red-teaming-a-step.jpg)
- [`0310-s18-ai-red-teaming-a-step.jpg`](../images/0310-s18-ai-red-teaming-a-step.jpg)
- [`0311-s18-ai-red-teaming-a-step.jpg`](../images/0311-s18-ai-red-teaming-a-step.jpg)
- [`0312-s18-ai-red-teaming-a-step.jpg`](../images/0312-s18-ai-red-teaming-a-step.jpg)
- [`0325-s18-ai-red-teaming-a-step.jpg`](../images/0325-s18-ai-red-teaming-a-step.jpg)
- [`0326-s18-ai-red-teaming-a-step.jpg`](../images/0326-s18-ai-red-teaming-a-step.jpg)
- [`0327-s18-ai-red-teaming-a-step.jpg`](../images/0327-s18-ai-red-teaming-a-step.jpg)
- [`0328-s18-ai-red-teaming-a-step.jpg`](../images/0328-s18-ai-red-teaming-a-step.jpg)
- [`0422-s18-ai-red-teaming-a-step.jpg`](../images/0422-s18-ai-red-teaming-a-step.jpg)
- [`0423-s18-ai-red-teaming-a-step.jpg`](../images/0423-s18-ai-red-teaming-a-step.jpg)
- [`0424-s18-ai-red-teaming-a-step.jpg`](../images/0424-s18-ai-red-teaming-a-step.jpg)
- [`0425-s18-ai-red-teaming-a-step.jpg`](../images/0425-s18-ai-red-teaming-a-step.jpg)
- [`0426-s18-ai-red-teaming-a-step.jpg`](../images/0426-s18-ai-red-teaming-a-step.jpg)
- [`0427-s18-ai-red-teaming-a-step.jpg`](../images/0427-s18-ai-red-teaming-a-step.jpg)
- [`0428-s18-ai-red-teaming-a-step.jpg`](../images/0428-s18-ai-red-teaming-a-step.jpg)
- [`0429-s18-ai-red-teaming-a-step.jpg`](../images/0429-s18-ai-red-teaming-a-step.jpg)
- [`0430-s18-ai-red-teaming-a-step.jpg`](../images/0430-s18-ai-red-teaming-a-step.jpg)
- [`0431-s18-ai-red-teaming-a-step.jpg`](../images/0431-s18-ai-red-teaming-a-step.jpg)
- [`0432-s18-ai-red-teaming-a-step.jpg`](../images/0432-s18-ai-red-teaming-a-step.jpg)
- [`0433-s18-ai-red-teaming-a-step.jpg`](../images/0433-s18-ai-red-teaming-a-step.jpg)
- [`0434-s18-ai-red-teaming-a-step.jpg`](../images/0434-s18-ai-red-teaming-a-step.jpg)
- [`0435-s18-ai-red-teaming-a-step.jpg`](../images/0435-s18-ai-red-teaming-a-step.jpg)
- [`0436-s18-ai-red-teaming-a-step.jpg`](../images/0436-s18-ai-red-teaming-a-step.jpg)
- [`0437-s18-ai-red-teaming-a-step.jpg`](../images/0437-s18-ai-red-teaming-a-step.jpg)
- [`0438-s18-ai-red-teaming-a-step.jpg`](../images/0438-s18-ai-red-teaming-a-step.jpg)
- [`0439-s18-ai-red-teaming-a-step.jpg`](../images/0439-s18-ai-red-teaming-a-step.jpg)
- [`0440-s18-ai-red-teaming-a-step.jpg`](../images/0440-s18-ai-red-teaming-a-step.jpg)
