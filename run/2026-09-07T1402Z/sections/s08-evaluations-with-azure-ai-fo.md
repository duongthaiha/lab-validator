# Evaluations with Azure AI Foundry

*Section* `s08-evaluations-with-azure-ai-fo`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#evaluations-with-azure-ai-foundry`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 48 recorded step(s), 2 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB004** ×1 · **LAB009** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Moved navigation (`LAB004`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#evaluations-with-azure-ai-foundry`  
*Severity:* major · *At fault:* instruction · *Step:* `985` · *2026-09-07T15:26:16Z*

The shipped notebook reports a cloud evaluation as successfully submitted and writes status NotStarted with an evaluation ID, but New Foundry Build > Evaluations remains empty after repeated refreshes and a two-minute propagation wait. The success-shaped notebook output is not backed by the promised portal artifact.

### 2. [~] Moved navigation — `LAB004`

*Instruction:* `#evaluations-with-azure-ai-foundry`  
*Severity:* minor · *At fault:* instruction · *Step:* `986` · *2026-09-07T15:26:17Z*

The notebook directs learners to Project > Evaluation > View evaluation runs. Current New Foundry exposes Runs under Build > Evaluations.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `969`** · no instruction anchor recorded — Used New Foundry Operate navigation to review the submitted cloud evaluation.
- **Step `976`** · no instruction anchor recorded — New Foundry exposes evaluation runs under Build > Evaluations rather than the notebook's printed Project > Evaluation route.

## Verified correct

- The evaluation notebook executed and produced local evaluation result artifacts, including synthetic test data and local metrics output.

## Evidence

10 capture(s), in the order the learner would have seen them.

- [`0101-s08-evaluations-with-inspect-evaluation-files.jpg`](../images/0101-s08-evaluations-with-inspect-evaluation-files.jpg)
- [`0102-s08-evaluations-with-run-evaluation-notebook.jpg`](../images/0102-s08-evaluations-with-run-evaluation-notebook.jpg)
- [`0103-s08-evaluations-with-evaluation-final-output.jpg`](../images/0103-s08-evaluations-with-evaluation-final-output.jpg)
- [`0104-s08-evaluations-with-cloud-evaluation-output.jpg`](../images/0104-s08-evaluations-with-cloud-evaluation-output.jpg)
- [`0105-s08-evaluations-with-cloud-evaluation-result.jpg`](../images/0105-s08-evaluations-with-cloud-evaluation-result.jpg)
- [`0106-s08-evaluations-with-inspect-cloud-result-file.jpg`](../images/0106-s08-evaluations-with-inspect-cloud-result-file.jpg)
- [`0107-s08-evaluations-with-open-current-evaluations.jpg`](../images/0107-s08-evaluations-with-open-current-evaluations.jpg)
- [`0108-s08-evaluations-with-current-evaluation-route.jpg`](../images/0108-s08-evaluations-with-current-evaluation-route.jpg)
- [`0109-s08-evaluations-with-wait-evaluation-list.jpg`](../images/0109-s08-evaluations-with-wait-evaluation-list.jpg)
- [`0110-s08-evaluations-with-recheck-cloud-evaluation.jpg`](../images/0110-s08-evaluations-with-recheck-cloud-evaluation.jpg)
