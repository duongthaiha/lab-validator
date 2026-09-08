# Fine Tuning

*Section* `s12-fine-tuning`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#fine-tuning`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 10 recorded step(s), 1 finding(s)

**Can a learner finish this section?** **YES** — a learner following the instructions can complete this

## Findings

**LAB003** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Changed UI label or inconsistent structure (`LAB003`)

### 1. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#fine-tuning`  
*Severity:* minor · *At fault:* instruction · *Step:* `1666` · *2026-09-07T17:25:27Z*

The Objectives block still carries its authoring template placeholder: it reads 'List the objectives' on the line above the real objective 'In this lab we will: Fine tune a model with given training and test dataset'. Visible to the learner in the rendered instructions.

## Verified correct

- Section 12's only actionable instruction checks out. C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning/ exists and contains both files it names, with real content rather than stubs: training_set_10samples.jsonl (2,695 bytes) and validation_set_10samples.jsonl (2,631 bytes). Listed from the VM.

## Evidence

1 capture(s), in the order the learner would have seen them.

- [`0213-s12-fine-tuning-ft-dataset-check.jpg`](../images/0213-s12-fine-tuning-ft-dataset-check.jpg)
