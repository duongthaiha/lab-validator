# Fine Tuning - Advance Lab

*Section* `s14-fine-tuning-advance-lab`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#fine-tuning---advance-lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 121 recorded step(s), 1 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB009** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#fine-tuning---advance-lab`  
*Severity:* major · *At fault:* instruction · *Step:* `2005` · *2026-09-07T18:25:09Z*

gpt-4_o_dpo_ft.ipynb uploads its two datasets and then immediately submits the fine-tuning job with no wait for the service-side import to finish, so a straight run of the notebook fails. Executed with nbconvert --execute --allow-errors: the upload cell succeeded and printed both ids (training file-bd0d8df1c84e42f3ba46742fae7cd187, validation file-5d720655cdb84a0ab757ca9a6a6e31f4), and the very next cell, client.fine_tuning.jobs.create(...), returned 'BadRequestError: Error code: 400 - invalidPayload: The specified file reference must point to a completed file import.' Cells 13-18 then cascaded into KeyError, NameError and NotFoundError, so the whole second half of the lab produced nothing. Proven to be timing and nothing else: listing the account's files afterwards showed both ids with status 'processed', and re-issuing the identical jobs.create with the same two file ids, the same model gpt-4o-2024-08-06, the same DPO method block and the notebook's own api_version 2025-02-01-preview was accepted and returned 'JOB ftjob-bd8df88bbbf541ebb8274ec42597456f pending'. The notebook needs a poll on file status between the two cells.

## Verified correct

- Everything section 14 depends on besides that one missing wait is correct and current. The three files it names exist under C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning/Advance Fine-Tuning/: gpt-4_o_dpo_ft.ipynb, data/gpt4o_generated_qa_dpo_train_10_samples.jsonl and data/gpt4o_generated_qa_dpo_validation_10_samples.jsonl. Unlike the Lab 06 notebook, this one resolves its configuration correctly with load_dotenv(dotenv_path='../../.env'), and all five variables it reads are present and correctly shaped in the .env: AZURE_SUBSCRIPTION_ID (36 chars), AI_FOUNDRY_NAME (19), AZURE_RESOURCE_GROUP (17), AZURE_OPENAI_API_KEY (84), AZURE_OPENAI_BASE_URL_ENDPOINT (45) - checked by name and length only, never by value. The service accepted the DPO payload as written, so the base model gpt-4o-2024-08-06, the 'dpo' method with beta 1.0 / batch_size 32 / learning_rate_multiplier 5.0 / n_epochs 1, and api_version 2025-02-01-preview are all still valid.

## Evidence

12 capture(s), in the order the learner would have seen them.

- [`0230-s14-fine-tuning-adva-dpo-inspect.jpg`](../images/0230-s14-fine-tuning-adva-dpo-inspect.jpg)
- [`0231-s14-fine-tuning-adva-dpo-env-shape.jpg`](../images/0231-s14-fine-tuning-adva-dpo-env-shape.jpg)
- [`0232-s14-fine-tuning-adva-dpo-env-shape2.jpg`](../images/0232-s14-fine-tuning-adva-dpo-env-shape2.jpg)
- [`0233-s14-fine-tuning-adva-dpo-run-bg.jpg`](../images/0233-s14-fine-tuning-adva-dpo-run-bg.jpg)
- [`0245-s14-fine-tuning-adva-dpo-progress.jpg`](../images/0245-s14-fine-tuning-adva-dpo-progress.jpg)
- [`0246-s14-fine-tuning-adva-dpo-parse.jpg`](../images/0246-s14-fine-tuning-adva-dpo-parse.jpg)
- [`0247-s14-fine-tuning-adva-dpo-error.jpg`](../images/0247-s14-fine-tuning-adva-dpo-error.jpg)
- [`0248-s14-fine-tuning-adva-dpo-cells-78.jpg`](../images/0248-s14-fine-tuning-adva-dpo-cells-78.jpg)
- [`0249-s14-fine-tuning-adva-dpo-file-status.jpg`](../images/0249-s14-fine-tuning-adva-dpo-file-status.jpg)
- [`0250-s14-fine-tuning-adva-dpo-job-retry.jpg`](../images/0250-s14-fine-tuning-adva-dpo-job-retry.jpg)
- [`0251-s14-fine-tuning-adva-dpo-client-cfg.jpg`](../images/0251-s14-fine-tuning-adva-dpo-client-cfg.jpg)
- [`0252-s14-fine-tuning-adva-dpo-job-retry2.jpg`](../images/0252-s14-fine-tuning-adva-dpo-job-retry2.jpg)
