# Create connections to Bing Resources at Azure AI Foundry resource level

*Section* `s03-create-connections-to-bing-r`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#create-connections-to-bing-resources-at-azure-ai-foundry-resource-level`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 29 recorded step(s), 3 finding(s)

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
*Severity:* minor · *At fault:* instruction · *Step:* `191` · *2026-09-07T14:24:25Z*

New Foundry reaches this page through Manage > Project details > Connected resources, not the documented legacy Management center > Resource route. Screenshot 0035 captures the current destination.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction · *Step:* `192` · *2026-09-07T14:24:26Z*

The current control is labeled Add connection; the documented +New connection label is no longer present.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction · *Step:* `210` · *2026-09-07T14:26:36Z*

After Connect, New Foundry returns directly to the Connected resources table. It does not show the documented green Connected label or Close button; the created GroundingWithBingSearch row is the current confirmation.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `190`** · no instruction anchor recorded — Used New Foundry Manage > Project details > Connected resources instead of the legacy Management center > Resource > Connected resources route.
- **Step `200`** · no instruction anchor recorded — New Foundry presents a connection-type chooser with a Grounding with Bing Search card; no search step is needed.

## Verified correct

- Connected resources lists one GroundingWithBingSearch connection backed by gw-bing-64827025, using API Key authentication and the Bing API target. Screenshot 0040 verifies the resulting artifact.

## Evidence

7 capture(s), in the order the learner would have seen them.

- [`0034-s03-create-connectio-latest-manage.jpg`](../images/0034-s03-create-connectio-latest-manage.jpg)
- [`0035-s03-create-connectio-latest-connected-resources.jpg`](../images/0035-s03-create-connectio-latest-connected-resources.jpg)
- [`0036-s03-create-connectio-add-bing-connection.jpg`](../images/0036-s03-create-connectio-add-bing-connection.jpg)
- [`0037-s03-create-connectio-choose-bing.jpg`](../images/0037-s03-create-connectio-choose-bing.jpg)
- [`0038-s03-create-connectio-bing-resource-picker.jpg`](../images/0038-s03-create-connectio-bing-resource-picker.jpg)
- [`0039-s03-create-connectio-connect-issued-bing.jpg`](../images/0039-s03-create-connectio-connect-issued-bing.jpg)
- [`0040-s03-create-connectio-wait-bing-connection.jpg`](../images/0040-s03-create-connectio-wait-bing-connection.jpg)
