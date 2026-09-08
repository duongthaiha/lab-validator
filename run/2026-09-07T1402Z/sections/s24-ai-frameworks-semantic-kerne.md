# AI Frameworks - Semantic Kernel and AutoGen

*Section* `s24-ai-frameworks-semantic-kerne` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** **blocked part-way**  
**Instructions.** `#ai-frameworks---semantic-kernel-and-autogen`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 31 recorded step(s), 3 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Broken link** `LAB006` — This section has exactly one instruction - 'Open the SK and AutoGen.ipynb notebook and run through the steps' - and no such notebook ships with the lab. A recursive enumeration of every .ipynb under Desktop\LABS returns fifteen notebooks (Lab 00 pip-install; Lab 01 setup and quick_start, 1-evaluation; Lab 02 agents 1 through 6; Lab 04 AI_vision_services_lab; Lab 05 gpt-4_o_dpo_ft; Lab 06 Prompt Engineering; Lab 09 AI_RedTeaming; Lab 10 Cosmos DB Python-Samples) and none of them is SK and AutoGen.ipynb, nor is there any file matching SK, AutoGen or Semantic anywhere in the tree. What makes this clearly an omission rather than a design choice is that the environment was prepared for it: pip list on the lab VM shows semantic-kernel 1.35.3 and autogen-agentchat, autogen-core and autogen-ext all at 0.7.4 already installed. The dependencies are there; the material that uses them is not. All five exercises are therefore unperformable and unjudgeable.
  <br>evidence: step `3203`, instruction `#ai-frameworks---semantic-kernel-and-autogen`

## Findings

**LAB002** ×1 · **LAB003** ×1 · **LAB006** ×1

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#2** Missing resource or SKU (`LAB002`)

**Instruction defects — the lab text is wrong** — lab author

- **#1** Broken link (`LAB006`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!!] Broken link — `LAB006`

*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* critical · *At fault:* instruction · *Step:* `3203` · *2026-09-08T00:22:19Z*

This section has exactly one instruction - 'Open the SK and AutoGen.ipynb notebook and run through the steps' - and no such notebook ships with the lab. A recursive enumeration of every .ipynb under Desktop\LABS returns fifteen notebooks (Lab 00 pip-install; Lab 01 setup and quick_start, 1-evaluation; Lab 02 agents 1 through 6; Lab 04 AI_vision_services_lab; Lab 05 gpt-4_o_dpo_ft; Lab 06 Prompt Engineering; Lab 09 AI_RedTeaming; Lab 10 Cosmos DB Python-Samples) and none of them is SK and AutoGen.ipynb, nor is there any file matching SK, AutoGen or Semantic anywhere in the tree. What makes this clearly an omission rather than a design choice is that the environment was prepared for it: pip list on the lab VM shows semantic-kernel 1.35.3 and autogen-agentchat, autogen-core and autogen-ext all at 0.7.4 already installed. The dependencies are there; the material that uses them is not. All five exercises are therefore unperformable and unjudgeable.

### 2. [!] Missing resource or SKU — `LAB002`

*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* major · *At fault:* setup · *Step:* `3204` · *2026-09-08T00:22:32Z*

The lab's own Resources tab advertises an Open AI Endpoint named myopai-64827025, and the Azure SQL vector section's steps 13 and 14 send the learner to 'your Azure OpenAI resource (example: myopai-resource-53809613)'. No resource of that name exists. az cognitiveservices account list over azureaiworkshoprg returns exactly three accounts: ai-foundry-64827025 (kind AIServices), cv-64827025 (kind ComputerVision) and faceresource-64827025 (kind CognitiveServices). The learner is told to look for a resource that was never provisioned, on the Resources tab that is supposed to be the authoritative statement of what the reservation contains. This is the same naming assumption that underpins the endpoint-shape defects reported against the PostgreSQL and Azure SQL sections.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* minor · *At fault:* instruction · *Step:* `3205` · *2026-09-08T00:22:46Z*

Text defects. The Next Steps paragraph tells the learner 'You'll be ready to proceed to Lab 5, where you'll explore RAG (Retrieval-Augmented Generation) implementations' - but Lab 05 in this workshop is Fine-Tuning, the RAG material is Lab 08 and the optional RAG section immediately precedes this one, and this is the last section in the lab. The pointer is wrong in both number and direction. The five Additional Resources entries (Semantic Kernel Documentation, AutoGen Framework, Azure OpenAI Service, Multi-Agent Systems Design, Plugin Development Best Practices) are again written as link text but render as plain words with no URLs. The section is also written against AutoGen 'v0.6+' in two places while the VM ships 0.7.4, which spans the 0.6 to 0.7 API change the text is presumably trying to warn about.

## Verified correct

- begin section 24
- locate the SK and AutoGen notebook
- focus Windows Terminal
- list every notebook shipped with the lab
- check whether Semantic Kernel and AutoGen are installed
- Closed blocked: the section's only task cannot be started because SK and AutoGen.ipynb is absent from the lab VM. None of Exercises 1 to 5 was executed.
- remove scratch files created during the walk

## Evidence

5 capture(s), in the order the learner would have seen them.

- [`0488-s24-ai-frameworks-se-step.jpg`](../images/0488-s24-ai-frameworks-se-step.jpg)
- [`0489-s24-ai-frameworks-se-step.jpg`](../images/0489-s24-ai-frameworks-se-step.jpg)
- [`0490-s24-ai-frameworks-se-step.jpg`](../images/0490-s24-ai-frameworks-se-step.jpg)
- [`0491-s24-ai-frameworks-se-step.jpg`](../images/0491-s24-ai-frameworks-se-step.jpg)
- [`0492-s24-ai-frameworks-se-step.jpg`](../images/0492-s24-ai-frameworks-se-step.jpg)
