# Optional Lab RAG (Retrieval-Augmented Generation) Implementation

*Section* `s23-optional-lab-rag-retrieval-a` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** **blocked part-way**  
**Instructions.** `#optional-lab-rag-retrieval-augmented-generation-implementation`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 31 recorded step(s), 2 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Broken link** `LAB006` — This section has exactly one instruction - 'Run through steps in RAG.ipynb file' - and that file does not exist. A recursive search of the entire C: drive on the lab VM for RAG.ipynb returned nothing, and the lab tree under Desktop\LABS contains only Lab 00 through Lab 10, with Lab 08 - RAG-Patterns holding a single file, GraphRAG\README.md, which is the Cloud Shell GraphRAG material used by an earlier section. Everything else in this section (Exercises 1 to 7, Advanced Implementation Topics, Execution Instructions, Expected Results) is prose describing what that notebook would do; none of it is independently actionable. The section is therefore unperformable as written. The supporting environment is present and would have worked: azureaiworkshoprg contains a running Azure AI Search service, aisearch-64827025 in West Europe, whose REST API answered with one existing index (myfitnessindex), and the .env carries populated AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_API_VERSION and SEARCH_AUTHENTICATION_METHOD. Only the notebook is missing.
  <br>evidence: step `3178`, instruction `#optional-lab-rag-retrieval-augmented-generation-implementation`

## Findings

**LAB003** ×1 · **LAB006** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Broken link (`LAB006`)
- **#2** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!!] Broken link — `LAB006`

*Instruction:* `#optional-lab-rag-retrieval-augmented-generation-implementation`  
*Severity:* critical · *At fault:* instruction · *Step:* `3178` · *2026-09-08T00:16:28Z*

This section has exactly one instruction - 'Run through steps in RAG.ipynb file' - and that file does not exist. A recursive search of the entire C: drive on the lab VM for RAG.ipynb returned nothing, and the lab tree under Desktop\LABS contains only Lab 00 through Lab 10, with Lab 08 - RAG-Patterns holding a single file, GraphRAG\README.md, which is the Cloud Shell GraphRAG material used by an earlier section. Everything else in this section (Exercises 1 to 7, Advanced Implementation Topics, Execution Instructions, Expected Results) is prose describing what that notebook would do; none of it is independently actionable. The section is therefore unperformable as written. The supporting environment is present and would have worked: azureaiworkshoprg contains a running Azure AI Search service, aisearch-64827025 in West Europe, whose REST API answered with one existing index (myfitnessindex), and the .env carries populated AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_API_VERSION and SEARCH_AUTHENTICATION_METHOD. Only the notebook is missing.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#optional-lab-rag-retrieval-augmented-generation-implementation`  
*Severity:* minor · *At fault:* instruction · *Step:* `3179` · *2026-09-08T00:16:41Z*

Text defects, recorded because they are all that remains verifiable once the notebook is gone. The Pre-requisites open with 'Compleate pre-requisites lab'. The six Additional Resources entries (Azure AI Search Vector Search, Azure OpenAI Embeddings, RAG Architecture Patterns, Vector Database Options in Azure, RAG Best Practices, Document Intelligence for RAG) are written as link text but render as plain words with no URLs, so none is reachable - the same defect as in the AI Red Teaming section. The section also contradicts itself about what is being built: the Objectives promise 'Configure Azure AI Search for vector search capabilities' and the Expected Results promise the learner will 'Implement production-ready RAG systems using Azure services', but Exercise 5 describes implementing cosine similarity in-process and explicitly says 'Simulate Azure AI Search vector capabilities'. A learner is told they are configuring a real search service and then told the search is simulated.

## Verified correct

- begin section 23
- locate RAG.ipynb and check for an Azure AI Search resource
- search for the RAG notebook
- check Lab 08 folder and search the whole disk for RAG.ipynb
- check whether the Azure AI Search service holds any index
- check .env for Azure AI Search credentials (names and lengths only)
- Closed blocked: the section's only task cannot be started because RAG.ipynb is absent from the lab VM. No exercise in this section was executed, and none of the seven exercises can be judged.

## Evidence

5 capture(s), in the order the learner would have seen them.

- [`0483-s23-optional-lab-rag-step.jpg`](../images/0483-s23-optional-lab-rag-step.jpg)
- [`0484-s23-optional-lab-rag-step.jpg`](../images/0484-s23-optional-lab-rag-step.jpg)
- [`0485-s23-optional-lab-rag-step.jpg`](../images/0485-s23-optional-lab-rag-step.jpg)
- [`0486-s23-optional-lab-rag-step.jpg`](../images/0486-s23-optional-lab-rag-step.jpg)
- [`0487-s23-optional-lab-rag-step.jpg`](../images/0487-s23-optional-lab-rag-step.jpg)
