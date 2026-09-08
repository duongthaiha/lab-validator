# Lab 08 - RAG-Patterns - Graph RAG

*Section* `s17-lab-08-rag-patterns-graph-ra` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#lab-08---rag-patterns---graph-rag`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 143 recorded step(s), 3 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB003** ×1 · **LAB005** ×1 · **LAB009** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Removed feature (`LAB005`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* major · *At fault:* instruction · *Step:* `2218` · *2026-09-07T19:37:30Z*

The documented prompt-tune command fails as written. Lab says to run: `graphrag prompt-tune --root ./ragtest --config ./ragtest/settings.yaml --output ./ragtest/prompts-tuned --domain "Literary Analyst"`. Pasted verbatim it exits in 0.8s with: "Usage: graphrag prompt-tune [OPTIONS] / Error: No such option: --config". `graphrag prompt-tune --help` on the version `pip install graphrag` delivers today (graphrag 3.1.2) lists only --root/-r, --verbose/-v, --domain, --selection-method, --n-subset-max, --k, --limit, --max-tokens, --min-examples-required, --chunk-size, --overlap, --language, --discover-entity-types, --output/-o, --help. Removing just --config makes the same command succeed in 1m45s and write ./ragtest/prompts-tuned/{extract_graph.txt, summarize_descriptions.txt, community_report_graph.txt}, so the rest of the step and both follow-up `more` commands are correct - the single invalid flag is what stops a learner. Learner impact: the auto-tuning exercise, the last task of the lab, cannot be completed by following the text.

### 2. [!] Removed feature — `LAB005`

*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* major · *At fault:* instruction · *Step:* `2219` · *2026-09-07T19:37:41Z*

The DRIFT query is shipped commented out under the heading "DRIFT Query (not working as of GraphRAG v2.7.0)", and the optional reindex block is disabled with the same caveat. The caveat is stale: `pip install graphrag` with no version pin installs graphrag 3.1.2 today, and running the commented-out command verbatim (uncommented) - `graphrag query --root ./ragtest --method drift "Who is Scrooge and what are his main relationships?"` - completed successfully in roughly 6 minutes and returned a full DRIFT answer with source citations ("## Who is Scrooge?", "## His main relationships", [Data: Sources (0,35)], (7,8,9), (20,21,22,33) ...). This matters because the lab's own Objectives list "Understand and execute Global, Local, and DRIFT queries" - a learner following the text never executes a DRIFT query and so cannot meet a stated objective, even though the product supports it. The instructions should either un-comment the DRIFT step or pin the version the caveat refers to.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* minor · *At fault:* instruction · *Step:* `2220` · *2026-09-07T19:37:53Z*

The Objectives block still carries the authoring template placeholder: it reads "List the objectives" on the line immediately before the real objective list ("In this lab we will: Install graphrag from Pypi / Index a data source / Understand and execute Global, Local, and DRIFT queries. / Start to inspect Prompt tuning"). This is the same unedited placeholder seen in section 12, so it is a repeated authoring defect rather than a one-off.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `2220`** · instruction `#lab-08---rag-patterns---graph-rag` — Deviation recorded for transparency: rather than pasting the Azure OpenAI key into the shell in clear text as the instruction's `echo "GRAPHRAG_API_KEY=<your_api_key>"` implies, the key was captured into a shell variable via `az cognitiveservices account keys list ... --query key1 -o tsv` so it never rendered on screen or in any capture. The documented sed line itself was executed unchanged apart from substituting that variable, and ragtest/.env was verified afterwards to contain a single GRAPHRAG_API_KEY entry of the expected 84-character length. The indexing and query steps that followed all authenticated successfully, which proves the documented .env edit is functionally correct.
  <br>outcome: The Objectives block still carries the authoring template placeholder: it reads "List the objectives" on the line immediately before the real objective list ("In this lab we will: Install graphrag from Pypi / Index a data source / Understand and execute Global, Local, and DRIFT queries. / Start to inspect Prompt tuning"). This is the same unedited placeholder seen in section 12, so it is a repeated authoring defect rather than a one-off.

## Verified correct

- PASS - Walked the whole GraphRAG lab in Azure Cloud Shell (bash) and verified real artifacts, not headings. Cloud Shell first-run pane provisioned with "No storage account required" + subscription MIPDG-lod53051908; python3 3.12.9 (inside the documented 3.10-3.12 range). mkdir/venv/activate/pip install graphrag all worked. `graphrag init --root ragtest` prompted for the two model names exactly as documented (defaults offered were gpt-4.1 and text-embedding-3-large; entered gpt-5-mini and text-embedding-ada-002) and produced exactly the documented expected files: settings.yaml, .env, prompts/ (14 templates). curl -L https://aka.ms/dickens/xmas resolved and returned 189184 bytes of "The Project Gutenberg eBook of A Christmas Carol" (wc 3976 32462 189184). All four documented sed edits matched real lines in the generated settings.yaml and produced model_provider: azure, api_base: ${AZURE_OPENAI_ENDPOINT}, api_version: 2024-05-01-preview under BOTH default_completion_model and default_embedding_model, and graphml: true at line 104. `graphrag index --root ./ragtest` ran the full pipeline to "Pipeline complete" in 7m09s (extract_graph 1368/1368 text units) and wrote real output: entities.parquet 126296 B, relationships.parquet 149244 B, community_reports.parquet 1087549 B, graph.graphml 103306 B (proving the graphml sed took effect), documents/text_units/communities parquet and a lancedb/ vector store. Global query returned a themed answer citing community reports [Data: Reports (41,25,100,33,39,+more)]; local query returned an entity-grounded answer citing [Data: Entities (49,19); Relationships (161); Sources (6)]. prompt-tune produced genuinely domain-adapted prompts - summarize_descriptions.txt opens "You are an expert Literary Community Network Analyst" and extract_graph.txt lists domain entity types (fictional character, workhouse/gaol/almshouse, poverty/charity/redemption/ignorance).

## Evidence

33 capture(s), in the order the learner would have seen them.

- [`0264-s17-lab-08-rag-patte-open-cloudshell.jpg`](../images/0264-s17-lab-08-rag-patte-open-cloudshell.jpg)
- [`0265-s17-lab-08-rag-patte-cloudshell-bash.jpg`](../images/0265-s17-lab-08-rag-patte-cloudshell-bash.jpg)
- [`0266-s17-lab-08-rag-patte-cloudshell-sub.jpg`](../images/0266-s17-lab-08-rag-patte-cloudshell-sub.jpg)
- [`0267-s17-lab-08-rag-patte-step.jpg`](../images/0267-s17-lab-08-rag-patte-step.jpg)
- [`0268-s17-lab-08-rag-patte-step.jpg`](../images/0268-s17-lab-08-rag-patte-step.jpg)
- [`0269-s17-lab-08-rag-patte-step.jpg`](../images/0269-s17-lab-08-rag-patte-step.jpg)
- [`0270-s17-lab-08-rag-patte-step.jpg`](../images/0270-s17-lab-08-rag-patte-step.jpg)
- [`0271-s17-lab-08-rag-patte-step.jpg`](../images/0271-s17-lab-08-rag-patte-step.jpg)
- [`0272-s17-lab-08-rag-patte-step.jpg`](../images/0272-s17-lab-08-rag-patte-step.jpg)
- [`0273-s17-lab-08-rag-patte-step.jpg`](../images/0273-s17-lab-08-rag-patte-step.jpg)
- [`0274-s17-lab-08-rag-patte-step.jpg`](../images/0274-s17-lab-08-rag-patte-step.jpg)
- [`0275-s17-lab-08-rag-patte-step.jpg`](../images/0275-s17-lab-08-rag-patte-step.jpg)
- [`0276-s17-lab-08-rag-patte-step.jpg`](../images/0276-s17-lab-08-rag-patte-step.jpg)
- [`0277-s17-lab-08-rag-patte-step.jpg`](../images/0277-s17-lab-08-rag-patte-step.jpg)
- [`0278-s17-lab-08-rag-patte-step.jpg`](../images/0278-s17-lab-08-rag-patte-step.jpg)
- [`0279-s17-lab-08-rag-patte-step.jpg`](../images/0279-s17-lab-08-rag-patte-step.jpg)
- [`0280-s17-lab-08-rag-patte-step.jpg`](../images/0280-s17-lab-08-rag-patte-step.jpg)
- [`0281-s17-lab-08-rag-patte-step.jpg`](../images/0281-s17-lab-08-rag-patte-step.jpg)
- [`0282-s17-lab-08-rag-patte-step.jpg`](../images/0282-s17-lab-08-rag-patte-step.jpg)
- [`0283-s17-lab-08-rag-patte-step.jpg`](../images/0283-s17-lab-08-rag-patte-step.jpg)
- [`0284-s17-lab-08-rag-patte-step.jpg`](../images/0284-s17-lab-08-rag-patte-step.jpg)
- [`0288-s17-lab-08-rag-patte-step.jpg`](../images/0288-s17-lab-08-rag-patte-step.jpg)
- [`0289-s17-lab-08-rag-patte-step.jpg`](../images/0289-s17-lab-08-rag-patte-step.jpg)
- [`0290-s17-lab-08-rag-patte-step.jpg`](../images/0290-s17-lab-08-rag-patte-step.jpg)
- [`0291-s17-lab-08-rag-patte-step.jpg`](../images/0291-s17-lab-08-rag-patte-step.jpg)
- [`0292-s17-lab-08-rag-patte-step.jpg`](../images/0292-s17-lab-08-rag-patte-step.jpg)
- [`0293-s17-lab-08-rag-patte-step.jpg`](../images/0293-s17-lab-08-rag-patte-step.jpg)
- [`0294-s17-lab-08-rag-patte-step.jpg`](../images/0294-s17-lab-08-rag-patte-step.jpg)
- [`0295-s17-lab-08-rag-patte-step.jpg`](../images/0295-s17-lab-08-rag-patte-step.jpg)
- [`0296-s17-lab-08-rag-patte-step.jpg`](../images/0296-s17-lab-08-rag-patte-step.jpg)
- [`0297-s17-lab-08-rag-patte-step.jpg`](../images/0297-s17-lab-08-rag-patte-step.jpg)
- [`0298-s17-lab-08-rag-patte-step.jpg`](../images/0298-s17-lab-08-rag-patte-step.jpg)
- [`0299-s17-lab-08-rag-patte-step.jpg`](../images/0299-s17-lab-08-rag-patte-step.jpg)
