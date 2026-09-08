# Azure AI Agents Tutorial Collection

*Section* `s09-azure-ai-agents-tutorial-col`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#azure-ai-agents-tutorial-collection`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 131 recorded step(s), 2 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB007** ×2

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#1** Timing or quota (`LAB007`)
- **#2** Timing or quota (`LAB007`)

### 1. [!] Timing or quota — `LAB007`

*Instruction:* `#azure-ai-agents-tutorial-collection`  
*Severity:* major · *At fault:* setup · *Step:* `1115` · *2026-09-07T16:14:48Z*

1-basics.ipynb created the health advisor agent and thread, then Run All remained at cell 4 of 18 for more than three minutes without producing the first agent response.

### 2. [!] Timing or quota — `LAB007`

*Instruction:* `#azure-ai-agents-tutorial-collection`  
*Severity:* major · *At fault:* setup · *Step:* `1116` · *2026-09-07T16:14:48Z*

6-multi-agent-solution.ipynb reached the orchestration cell but never produced the promised triage output or ran cleanup after more than three minutes; the final two cells remained unexecuted.

## Verified correct

- Code interpreter, file search, Bing grounding, and Azure AI Search notebooks reached their Congratulations sections and created their expected artifacts. The code interpreter generated multiple chart files.

## Deferred

_Postponed by the walk, not by the lab. These say nothing about the lab._

- Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed

## Evidence

20 capture(s), in the order the learner would have seen them.

- [`0111-s09-azure-ai-agents-run-agent-basics.jpg`](../images/0111-s09-azure-ai-agents-run-agent-basics.jpg)
- [`0112-s09-azure-ai-agents-run-agent-basics-vscode.jpg`](../images/0112-s09-azure-ai-agents-run-agent-basics-vscode.jpg)
- [`0113-s09-azure-ai-agents-select-notebook-window.jpg`](../images/0113-s09-azure-ai-agents-select-notebook-window.jpg)
- [`0114-s09-azure-ai-agents-open-agent-notebook-window.jpg`](../images/0114-s09-azure-ai-agents-open-agent-notebook-window.jpg)
- [`0115-s09-azure-ai-agents-approve-agent-auth.jpg`](../images/0115-s09-azure-ai-agents-approve-agent-auth.jpg)
- [`0116-s09-azure-ai-agents-agent-basics-result.jpg`](../images/0116-s09-azure-ai-agents-agent-basics-result.jpg)
- [`0117-s09-azure-ai-agents-wait-agent-basics.jpg`](../images/0117-s09-azure-ai-agents-wait-agent-basics.jpg)
- [`0118-s09-azure-ai-agents-run-code-interpreter.jpg`](../images/0118-s09-azure-ai-agents-run-code-interpreter.jpg)
- [`0119-s09-azure-ai-agents-code-interpreter-auth.jpg`](../images/0119-s09-azure-ai-agents-code-interpreter-auth.jpg)
- [`0120-s09-azure-ai-agents-code-interpreter-result.jpg`](../images/0120-s09-azure-ai-agents-code-interpreter-result.jpg)
- [`0121-s09-azure-ai-agents-run-file-search.jpg`](../images/0121-s09-azure-ai-agents-run-file-search.jpg)
- [`0122-s09-azure-ai-agents-file-search-auth.jpg`](../images/0122-s09-azure-ai-agents-file-search-auth.jpg)
- [`0123-s09-azure-ai-agents-run-bing-grounding.jpg`](../images/0123-s09-azure-ai-agents-run-bing-grounding.jpg)
- [`0124-s09-azure-ai-agents-bing-notebook-auth.jpg`](../images/0124-s09-azure-ai-agents-bing-notebook-auth.jpg)
- [`0125-s09-azure-ai-agents-run-ai-search-agent.jpg`](../images/0125-s09-azure-ai-agents-run-ai-search-agent.jpg)
- [`0126-s09-azure-ai-agents-ai-search-notebook-auth.jpg`](../images/0126-s09-azure-ai-agents-ai-search-notebook-auth.jpg)
- [`0127-s09-azure-ai-agents-run-multi-agent.jpg`](../images/0127-s09-azure-ai-agents-run-multi-agent.jpg)
- [`0128-s09-azure-ai-agents-multi-agent-auth.jpg`](../images/0128-s09-azure-ai-agents-multi-agent-auth.jpg)
- [`0129-s09-azure-ai-agents-inspect-multi-agent-result.jpg`](../images/0129-s09-azure-ai-agents-inspect-multi-agent-result.jpg)
- [`0130-s09-azure-ai-agents-multi-agent-output.jpg`](../images/0130-s09-azure-ai-agents-multi-agent-output.jpg)
