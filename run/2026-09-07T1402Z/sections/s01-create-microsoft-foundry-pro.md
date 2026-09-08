# Create Microsoft Foundry Project

*Section* `s01-create-microsoft-foundry-pro`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#create-microsoft-foundry-project`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 98 recorded step(s), 1 finding(s)

**Can a learner finish this section?** **YES** — a learner following the instructions can complete this

## What the lab asks the learner to do

- 1. Sign in to Azure Portal
- 2. Search for "Microsoft Foundry"
- 3. Create "Microsoft Foundry"
- 4. Fill in the details and deploy
- 5. Verify Deployment, and Go to Microsoft Foundry portal

## Findings

**LAB004** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Moved navigation (`LAB004`)

### 1. [~] Moved navigation — `LAB004`

*Instruction:* `#1-sign-in-to-azure-portal`  
*Severity:* minor · *At fault:* instruction · *Step:* `5` · *2026-09-07T14:03:16Z*

Task 1 begins with 'Go to https://portal.azure.com', but the fresh learner VM opens at an Admin Windows lock screen. The learner must first use the separately issued machine password; the instruction does not mention this prerequisite.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `9`** · no instruction anchor recorded — Unlocked the VM with the lab-issued machine credential before the documented Azure Portal sign-in.
- **Step `23`** · no instruction anchor recorded — Dismissed Edge's first-run privacy prompt before navigation; this browser-image prerequisite is not mentioned in the lab.

## Verified correct

- After the undocumented VM unlock, the lab-issued Azure username and Temporary Access Pass authenticated successfully and loaded portal.azure.com.
- The Azure portal search returned Microsoft Foundry and opened its Overview blade in the current portal UX.
- The current Microsoft Foundry Overview contains the documented Create a resource control and opens the Foundry resource creation form.
- The current portal UX accepted azureaiworkshoprg, ai-foundry-64827025, East US 2, and firstProject. Deployment completed successfully within the stated two-minute window.
- The resource Overview showed Succeeded and Go to Foundry portal opened firstProject in the latest New Foundry experience, with the New Foundry switch on and current Home, Discover, Build, Operate, Manage, and Docs navigation.

## Deferred

_Postponed by the walk, not by the lab. These say nothing about the lab._

- Machine credentials/Password typed (delta 0.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/Username typed (delta 4.4); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 4.9); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed

## Evidence

17 capture(s), in the order the learner would have seen them.

- [`0002-s01-create-microsoft-initial-screen.jpg`](../images/0002-s01-create-microsoft-initial-screen.jpg)
- [`0003-s01-create-microsoft-vm-signin.jpg`](../images/0003-s01-create-microsoft-vm-signin.jpg)
- [`0004-s01-create-microsoft-open-portal.jpg`](../images/0004-s01-create-microsoft-open-portal.jpg)
- [`0005-s01-create-microsoft-navigate-portal.jpg`](../images/0005-s01-create-microsoft-navigate-portal.jpg)
- [`0006-s01-create-microsoft-portal-signin.jpg`](../images/0006-s01-create-microsoft-portal-signin.jpg)
- [`0007-s01-create-microsoft-portal-home.jpg`](../images/0007-s01-create-microsoft-portal-home.jpg)
- [`0008-s01-create-microsoft-search-foundry.jpg`](../images/0008-s01-create-microsoft-search-foundry.jpg)
- [`0009-s01-create-microsoft-open-foundry.jpg`](../images/0009-s01-create-microsoft-open-foundry.jpg)
- [`0010-s01-create-microsoft-correct-foundry-search.jpg`](../images/0010-s01-create-microsoft-correct-foundry-search.jpg)
- [`0011-s01-create-microsoft-foundry-overview.jpg`](../images/0011-s01-create-microsoft-foundry-overview.jpg)
- [`0012-s01-create-microsoft-create-foundry.jpg`](../images/0012-s01-create-microsoft-create-foundry.jpg)
- [`0013-s01-create-microsoft-fill-basics.jpg`](../images/0013-s01-create-microsoft-fill-basics.jpg)
- [`0014-s01-create-microsoft-review-create.jpg`](../images/0014-s01-create-microsoft-review-create.jpg)
- [`0015-s01-create-microsoft-deploy-resource.jpg`](../images/0015-s01-create-microsoft-deploy-resource.jpg)
- [`0016-s01-create-microsoft-resource-overview.jpg`](../images/0016-s01-create-microsoft-resource-overview.jpg)
- [`0017-s01-create-microsoft-latest-foundry-home.jpg`](../images/0017-s01-create-microsoft-latest-foundry-home.jpg)
- [`0018-s01-create-microsoft-latest-foundry-loaded.jpg`](../images/0018-s01-create-microsoft-latest-foundry-loaded.jpg)
