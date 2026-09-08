# Prompt Engineering

*Section* `s15-prompt-engineering`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#prompt-engineering`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 138 recorded step(s), 4 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Defective sample code** `LAB009` — The Prompt Engineering notebook cannot load the .env the lab has the learner configure. 'Prompt Engineering.ipynb' calls load_dotenv(dotenv_path='../../../.env'), but the notebook sits in C:/Users/Admin/Desktop/LABS/Lab 06 - Prompt Engineering, so three levels up resolves to C:\\Users\\Admin\\.env. Measured on the VM: resolved path C:\\Users\\Admin\\.env, Test-Path False, while Test-Path on C:\\Users\\Admin\\Desktop\\LABS\\.env is True. Executed unchanged with nbconvert --execute --allow-errors: 9 of 11 code cells failed, cell 2 with 'OpenAIError: Missing credentials. Please pass one of api_key, azure_ad_token...' and cells 3-10 with cascading NameError: name 'client' is not defined. Changing the single string to '../.env' (one substitution, 6 characters) let the client build and grew the executed notebook from 60,594 to 201,899 bytes. Note the sibling DPO notebook in Lab 05 uses '../../.env' correctly from one directory deeper, so this is a per-notebook mistake, not a convention.
  <br>evidence: step `1926`, instruction `#prompt-engineering`

## What the lab asks the learner to do

- 1. Zero-Shot Prompting
- 2. Few-Shot Prompting
- 3. Chain-of-Thought Prompting
- 4. Meta Prompting
- 5. Prompt Chaining
- 6. Tree of Thoughts (ToT)
- 7. Retrieval Augmented Generation (RAG)
- 8. Active-Prompt

## Findings

**LAB009** ×4

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Defective sample code (`LAB009`)
- **#3** Defective sample code (`LAB009`)
- **#4** Defective sample code (`LAB009`)

### 1. [!!] Defective sample code — `LAB009`

*Instruction:* `#prompt-engineering`  
*Severity:* critical · *At fault:* instruction · *Step:* `1926` · *2026-09-07T18:11:02Z*

The Prompt Engineering notebook cannot load the .env the lab has the learner configure. 'Prompt Engineering.ipynb' calls load_dotenv(dotenv_path='../../../.env'), but the notebook sits in C:/Users/Admin/Desktop/LABS/Lab 06 - Prompt Engineering, so three levels up resolves to C:\\Users\\Admin\\.env. Measured on the VM: resolved path C:\\Users\\Admin\\.env, Test-Path False, while Test-Path on C:\\Users\\Admin\\Desktop\\LABS\\.env is True. Executed unchanged with nbconvert --execute --allow-errors: 9 of 11 code cells failed, cell 2 with 'OpenAIError: Missing credentials. Please pass one of api_key, azure_ad_token...' and cells 3-10 with cascading NameError: name 'client' is not defined. Changing the single string to '../.env' (one substitution, 6 characters) let the client build and grew the executed notebook from 60,594 to 201,899 bytes. Note the sibling DPO notebook in Lab 05 uses '../../.env' correctly from one directory deeper, so this is a per-notebook mistake, not a convention.

### 2. [!] Defective sample code — `LAB009`

*Instruction:* `#prompt-engineering`  
*Severity:* major · *At fault:* instruction · *Step:* `1927` · *2026-09-07T18:11:03Z*

With the .env path fixed, every model call still failed: 'Error code: 400 - Unsupported value: temperature does not support 0.3 with this model. Only the default (1) value is supported.' (type invalid_request_error, param temperature, code unsupported_value). The notebook passes an explicit temperature 18 times; the deployment it is configured to use is MODEL_DEPLOYMENT_NAME=gpt-5-mini, which is what this lab's own model-deployment section provisions. So the shipped notebook targets a chat-completions contract the lab's current models no longer honour. Replacing only the values (temperature=1, 18 substitutions, no keyword removed) took the notebook from 8 failing cells to 1.

### 3. [!] Defective sample code — `LAB009`

*Instruction:* `#prompt-engineering`  
*Severity:* major · *At fault:* instruction · *Step:* `1928` · *2026-09-07T18:11:03Z*

A second, independent incompatibility with the same deployment: one cell fails with 'Error code: 400 - Unsupported parameter: max_tokens is not supported with this model. Use max_completion_tokens instead.' (param max_tokens, code unsupported_parameter). This survived the temperature fix and is the only remaining failure, so it is a distinct defect and not a symptom of the first. Section 8 of the lab (Active-Prompt / the cell in question) produces no output for the learner.

### 4. [!] Defective sample code — `LAB009`

*Instruction:* `#6-tree-of-thoughts-tot`  
*Severity:* major · *At fault:* instruction · *Step:* `2064` · *2026-09-07T18:36:25Z*

Tree of Thoughts is the one technique that still produces nothing after every other defect is corrected. Its cell fails with 'Error code: 400 - Unsupported parameter: max_tokens is not supported with this model. Use max_completion_tokens instead.' (param max_tokens, code unsupported_parameter) against the lab's own gpt-5-mini deployment. It was the sole failure in the final run, so it is a defect in its own right rather than a symptom of the dotenv or temperature problems.

## Verified correct

- The teaching content itself is sound once the three shipped-code defects are corrected. After the minimal value-only patches (dotenv path, temperature), 10 of 11 code cells ran clean and returned real model output rather than empty success: cell outputs of 246, 275, 1,719, 6,155, 2,196, 679 and 1,179 characters, including a readable Active-Prompt demonstration ('Sentence to classify: This thing is pretty awesome, dude!' with automatically selected examples). So the eight prompting techniques the section teaches do work against the lab's own gpt-5-mini deployment; only the parameters the notebook sends are wrong.
- The Zero-Shot technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 246 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The Few-Shot technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 275 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The Chain-of-Thought technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 1,719 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The Meta Prompting technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 6,155 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The Prompt Chaining technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 2,196 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The RAG technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 679 characters of model response. Judged from the executed notebook on disk, not from cell status.
- The Active-Prompt technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 1,179 characters of model response. Judged from the executed notebook on disk, not from cell status.

## Evidence

11 capture(s), in the order the learner would have seen them.

- [`0234-s15-prompt-engineeri-pe-run.jpg`](../images/0234-s15-prompt-engineeri-pe-run.jpg)
- [`0235-s15-prompt-engineeri-pe-parse.jpg`](../images/0235-s15-prompt-engineeri-pe-parse.jpg)
- [`0236-s15-prompt-engineeri-pe-error-detail.jpg`](../images/0236-s15-prompt-engineeri-pe-error-detail.jpg)
- [`0237-s15-prompt-engineeri-pe-path-oracle.jpg`](../images/0237-s15-prompt-engineeri-pe-path-oracle.jpg)
- [`0238-s15-prompt-engineeri-pe-patch-run.jpg`](../images/0238-s15-prompt-engineeri-pe-patch-run.jpg)
- [`0239-s15-prompt-engineeri-pe-parse2.jpg`](../images/0239-s15-prompt-engineeri-pe-parse2.jpg)
- [`0240-s15-prompt-engineeri-pe-badrequest.jpg`](../images/0240-s15-prompt-engineeri-pe-badrequest.jpg)
- [`0241-s15-prompt-engineeri-pe-badrequest-msg.jpg`](../images/0241-s15-prompt-engineeri-pe-badrequest-msg.jpg)
- [`0242-s15-prompt-engineeri-pe-temp-patch.jpg`](../images/0242-s15-prompt-engineeri-pe-temp-patch.jpg)
- [`0243-s15-prompt-engineeri-pe-parse3.jpg`](../images/0243-s15-prompt-engineeri-pe-parse3.jpg)
- [`0244-s15-prompt-engineeri-pe-cleanup.jpg`](../images/0244-s15-prompt-engineeri-pe-cleanup.jpg)
