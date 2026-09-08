# Azure PostgreSQL Lab

*Section* `s20-azure-postgresql-lab` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#azure-postgresql-lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 191 recorded step(s), 4 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## Findings

**LAB003** ×2 · **LAB004** ×1 · **LAB009** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Changed UI label or inconsistent structure (`LAB003`)
- **#3** Changed UI label or inconsistent structure (`LAB003`)
- **#4** Moved navigation (`LAB004`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#azure-postgresql-lab`  
*Severity:* major · *At fault:* instruction · *Step:* `2527` · *2026-09-07T21:07:16Z*

Part 5's placeholder guidance does not match the script it applies to, in two separate ways, and one of them silently produces a broken endpoint. (a) Name mismatch: the instructions tell you to replace `<your-endpoint>` and `<your-api-key>`, but VectorQuery.sql actually contains `select azure_ai.set_setting('azure_openai.endpoint', '<your-endpoint-url>');` and `select azure_ai.set_setting('azure_openai.subscription_key', '<your-subscription-key>');`. Neither documented token appears in the file. (b) Shape mismatch that matters: the instruction prints the target as the template 'https://<your-endpoint>.openai.azure.com/' and then offers "or the AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT value in your .env file" as an equivalent source. It is not equivalent - that .env value is 120 characters and, verified by pattern match, contains a /openai/deployments/ path segment, i.e. it is a full deployment/inference URI, not the bare resource endpoint. Substituting it into the template yields a malformed URL, and substituting it into the script's slot sets azure_openai.endpoint to a deployment URI. The similarity query only succeeded here after the value was trimmed back to its scheme+host base (https://ai-foundry-64827025.openai.azure.com/), which the instructions never tell the learner to do.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `2526` · *2026-09-07T21:07:15Z*

Part 3 sends the learner to a file that does not exist. It says "Open the VectoryQuery.sql Script" and "Press Ctrl+O and open the VectorQuery.sql file located at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\PostgreSQL\VectoryQuery.sql" - note the heading and the path both spell it "VectoryQuery.sql". Test-Path on that exact documented path returns False. The file that ships is VectorQuery.sql (477 bytes) in that same folder. A learner using Ctrl+O and typing the documented path gets nothing.

### 3. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `2528` · *2026-09-07T21:07:38Z*

The lab is inconsistent about where the PostgreSQL password comes from, and one of the two answers publishes it. Part 2 Step 1 correctly tells the learner to take it from sqlcredentials.txt (that file exists at C:\Users\Admin\Desktop\LABS\sqlcredentials.txt and holds a single 15-character line). Part 3 instead prints a literal password value in the connection-details list. Comparing the two without displaying either confirmed they are the same string today, so the instruction happens to work - but it only works while the lab issues that one fixed password. If Skillable ever randomises it per reservation, Part 3 becomes actively wrong while Part 2 stays right, and a learner who trusts the printed value will get an authentication failure with no clue why. Publishing a working database password in the learner manual is also poor hygiene for a workshop whose own Lab 09 is about security. Recommend Part 3 point at sqlcredentials.txt exactly as Part 2 does.

### 4. [~] Moved navigation — `LAB004`

*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `2529` · *2026-09-07T21:07:39Z*

Two navigation instructions no longer match the current UX. (a) Part 1 says "In the left menu, select Server parameters" as though it were a top-level entry; in the portal today the PostgreSQL flexible-server blade groups it under a collapsed "Settings" section, so the learner must expand Settings first - the item is not visible on arrival. (b) Part 4 is written against the retired Foundry entry points: "Click Explore Azure AI Foundry portal", "Go to Model catalog", "Click text-embedding-ada-002", "Click Use this model", and calls the resource an "Azure OpenAI" resource. The current portal used throughout this walk is ai.azure.com/nextgen, whose top nav is Home / Discover / Build / Operate / Manage / Docs, where the catalogue lives under Discover and deployments under Build > Models > Deployments, and the resource is presented as a Microsoft Foundry resource. Judged as route drift rather than executed, because Part 4 is explicitly skippable when the model already exists - text-embedding-ada-002 is already deployed in this environment and AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT / _API_KEY are already present in .env, which is the branch this walk took.

## Verified correct

- PASS - Every part of this lab was executed against the real pre-created server pgaivector-64827025 (PostgreSQL 15.19, Sweden Central) and verified from artifacts rather than headings. Part 1: Server parameters -> azure.extensions -> ticked AZURE_AI and VECTOR -> Save; the value went from "0 selected" to "2 selected" and the portal reported deployment PostgreSQLFlexibleServerParameters_383a6c628b324053a with resource serverParameters-0-... status OK. Part 2: psql connected with the password taken from sqlcredentials.txt, `create database books;` returned CREATE DATABASE and the database then appeared in \l. Part 3 restore: pg_restore against the on-disk backup finished with exactly the one error the lab tells you to expect ("unrecognized configuration parameter transaction_timeout" -> "warning: errors ignored on restore: 1"), so that instruction's caveat is accurate; the restored table holds 4999 rows and desc_embedding is a real USER-DEFINED vector column, with azure_ai 1.3.1 and vector 0.8.2 present in \dx (which only works because Part 1 allow-listed them first). Part 3 pgAdmin: pgAdmin 4 v9.5 launched, the server registered as AIWorkshop against host pgaivector-64827025.postgres.database.azure.com:5432 / postgres / postgres, connected, and the documented `select * from books limit 20;` ran in the Query Tool returning 20 real rows (Euphoria, A Map of the World, The Tuscan Child, Twilight, The Catcher in the Rye ...). Part 5: after azure_ai.set_setting for endpoint and subscription_key, the lab's own similarity query ran and returned five genuinely ranked results - Longitude: The True Story of a Lone Genius 0.6549, The Restaurant at the End of the Universe 0.6695, Flatland: A Romance of Many Dimensions 0.6759, The Three-Body Problem 0.6772, Seraphina 0.6836 - i.e. a live text-embedding-ada-002 call from inside PostgreSQL, not a cached value.

## Evidence

41 capture(s), in the order the learner would have seen them.

- [`0329-s20-azure-postgresql-step.jpg`](../images/0329-s20-azure-postgresql-step.jpg)
- [`0330-s20-azure-postgresql-step.jpg`](../images/0330-s20-azure-postgresql-step.jpg)
- [`0331-s20-azure-postgresql-step.jpg`](../images/0331-s20-azure-postgresql-step.jpg)
- [`0332-s20-azure-postgresql-step.jpg`](../images/0332-s20-azure-postgresql-step.jpg)
- [`0333-s20-azure-postgresql-step.jpg`](../images/0333-s20-azure-postgresql-step.jpg)
- [`0334-s20-azure-postgresql-step.jpg`](../images/0334-s20-azure-postgresql-step.jpg)
- [`0335-s20-azure-postgresql-step.jpg`](../images/0335-s20-azure-postgresql-step.jpg)
- [`0336-s20-azure-postgresql-step.jpg`](../images/0336-s20-azure-postgresql-step.jpg)
- [`0337-s20-azure-postgresql-step.jpg`](../images/0337-s20-azure-postgresql-step.jpg)
- [`0338-s20-azure-postgresql-step.jpg`](../images/0338-s20-azure-postgresql-step.jpg)
- [`0339-s20-azure-postgresql-step.jpg`](../images/0339-s20-azure-postgresql-step.jpg)
- [`0340-s20-azure-postgresql-step.jpg`](../images/0340-s20-azure-postgresql-step.jpg)
- [`0341-s20-azure-postgresql-step.jpg`](../images/0341-s20-azure-postgresql-step.jpg)
- [`0342-s20-azure-postgresql-step.jpg`](../images/0342-s20-azure-postgresql-step.jpg)
- [`0343-s20-azure-postgresql-step.jpg`](../images/0343-s20-azure-postgresql-step.jpg)
- [`0344-s20-azure-postgresql-step.jpg`](../images/0344-s20-azure-postgresql-step.jpg)
- [`0345-s20-azure-postgresql-step.jpg`](../images/0345-s20-azure-postgresql-step.jpg)
- [`0346-s20-azure-postgresql-step.jpg`](../images/0346-s20-azure-postgresql-step.jpg)
- [`0347-s20-azure-postgresql-step.jpg`](../images/0347-s20-azure-postgresql-step.jpg)
- [`0348-s20-azure-postgresql-step.jpg`](../images/0348-s20-azure-postgresql-step.jpg)
- [`0349-s20-azure-postgresql-step.jpg`](../images/0349-s20-azure-postgresql-step.jpg)
- [`0350-s20-azure-postgresql-step.jpg`](../images/0350-s20-azure-postgresql-step.jpg)
- [`0351-s20-azure-postgresql-step.jpg`](../images/0351-s20-azure-postgresql-step.jpg)
- [`0352-s20-azure-postgresql-step.jpg`](../images/0352-s20-azure-postgresql-step.jpg)
- [`0353-s20-azure-postgresql-step.jpg`](../images/0353-s20-azure-postgresql-step.jpg)
- [`0354-s20-azure-postgresql-step.jpg`](../images/0354-s20-azure-postgresql-step.jpg)
- [`0355-s20-azure-postgresql-step.jpg`](../images/0355-s20-azure-postgresql-step.jpg)
- [`0356-s20-azure-postgresql-step.jpg`](../images/0356-s20-azure-postgresql-step.jpg)
- [`0357-s20-azure-postgresql-step.jpg`](../images/0357-s20-azure-postgresql-step.jpg)
- [`0358-s20-azure-postgresql-step.jpg`](../images/0358-s20-azure-postgresql-step.jpg)
- [`0359-s20-azure-postgresql-step.jpg`](../images/0359-s20-azure-postgresql-step.jpg)
- [`0360-s20-azure-postgresql-step.jpg`](../images/0360-s20-azure-postgresql-step.jpg)
- [`0361-s20-azure-postgresql-step.jpg`](../images/0361-s20-azure-postgresql-step.jpg)
- [`0362-s20-azure-postgresql-step.jpg`](../images/0362-s20-azure-postgresql-step.jpg)
- [`0363-s20-azure-postgresql-step.jpg`](../images/0363-s20-azure-postgresql-step.jpg)
- [`0364-s20-azure-postgresql-step.jpg`](../images/0364-s20-azure-postgresql-step.jpg)
- [`0365-s20-azure-postgresql-step.jpg`](../images/0365-s20-azure-postgresql-step.jpg)
- [`0366-s20-azure-postgresql-step.jpg`](../images/0366-s20-azure-postgresql-step.jpg)
- [`0367-s20-azure-postgresql-step.jpg`](../images/0367-s20-azure-postgresql-step.jpg)
- [`0368-s20-azure-postgresql-step.jpg`](../images/0368-s20-azure-postgresql-step.jpg)
- [`0369-s20-azure-postgresql-step.jpg`](../images/0369-s20-azure-postgresql-step.jpg)
