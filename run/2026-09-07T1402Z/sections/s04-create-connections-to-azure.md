# Create connections to Azure AI Search at AI Foundry resource level

*Section* `s04-create-connections-to-azure`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#create-connections-to-azure-ai-search-at-ai-foundry-resource-level`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 18 recorded step(s), 3 finding(s)

**Can a learner finish this section?** **YES** — a learner following the instructions can complete this

## What the lab asks the learner to do

- 1. Go to the Connected Resources section

## Findings

**LAB003** ×2 · **LAB004** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Moved navigation (`LAB004`)
- **#2** Changed UI label or inconsistent structure (`LAB003`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)

### 1. [~] Moved navigation — `LAB004`

*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction · *Step:* `212` · *2026-09-07T14:28:26Z*

New Foundry uses Manage > Project details > Connected resources instead of the documented legacy Management center > Resource route.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction · *Step:* `213` · *2026-09-07T14:28:27Z*

The current control is Add connection, not the documented +New connection.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction · *Step:* `228` · *2026-09-07T14:29:49Z*

New Foundry returns directly to the resources table after Connect; the documented green Connected label and Close button are absent.

## Verified correct

- Connected resources lists aisearch64827025ectup5 as CognitiveSearch with API Key authentication and its search.windows.net target. Screenshot 0044 verifies the resulting artifact.

## Evidence

4 capture(s), in the order the learner would have seen them.

- [`0041-s04-create-connectio-open-search-chooser.jpg`](../images/0041-s04-create-connectio-open-search-chooser.jpg)
- [`0042-s04-create-connectio-choose-ai-search.jpg`](../images/0042-s04-create-connectio-choose-ai-search.jpg)
- [`0043-s04-create-connectio-search-resource-picker.jpg`](../images/0043-s04-create-connectio-search-resource-picker.jpg)
- [`0044-s04-create-connectio-connect-ai-search.jpg`](../images/0044-s04-create-connectio-connect-ai-search.jpg)
