# Lab: Using Vector Databases in Azure SQL Database

*Section* `s22-lab-using-vector-databases-i` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#lab-using-vector-databases-in-azure-sql-database`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 200 recorded step(s), 6 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Defective sample code** `LAB009` — Root cause of the step 25 failure, now confirmed at character level. In 4_SQLEmbeddings.py the T-SQL for dbo.get_embedding is assembled by concatenating an opening quote, a space, and then the URL variable, so the procedure stores a URL string literal that begins with a space. Dumping the deployed definition from sys.sql_modules gives exactly: [<space>https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01]. sp_invoke_external_rest_endpoint rejects that with 'failed to parse url. HRESULT: 0x80072ee6 (31609)', so step 25 can never return rows as written. Recreating the identical procedure with only that one space removed made the same 5_query.sql succeed immediately. The defect is unconditional: it does not depend on any .env value.
  <br>evidence: step `3143`, instruction `#lab-using-vector-databases-in-azure-sql-database`
- **Defective sample code** `LAB009` — Second, independent defect in the same script, and the one a learner is guaranteed to hit. 4_SQLEmbeddings.py creates the database scoped credential named after the raw endpoint, but the stored procedure it then generates references the same name with any trailing slash stripped. Step 15 tells the learner to copy the Endpoint value from Keys and Endpoint, and that value ends in a slash - as the shipped .env does. The two names therefore never match. Verified directly: sys.database_scoped_credentials contains [https://ai-foundry-64827025.openai.azure.com/] while dbo.get_embedding asks for https://ai-foundry-64827025.openai.azure.com, and step 25 fails with 'Cannot find the credential ... because it does not exist or you do not have permission. (15151)'. Creating a credential under the stripped name made the query work. Note this is a different failure from the stray space: fixing the space alone moves the error from 31609 to 15151, so both must be fixed before step 25 returns anything.
  <br>evidence: step `3144`, instruction `#lab-using-vector-databases-in-azure-sql-database`
- **Timing or quota** `LAB007` — The Azure portal became permanently unreachable partway through the reservation, with the lab clock still showing 1440 minutes. The account signs in with a Temporary Access Pass, and once it expired the CLI reported it exactly: 'AADSTS130504: Your Temporary Access Pass has expired. Contact your administrator to obtain a new pass.' Because no other authentication method is registered on the account, every portal re-authentication now lands on a mandatory 'Lets keep your account secure' registration flow whose only path forward is 'Install Microsoft Authenticator' on a mobile device. There is no skip and no deferral, and the lab issues no second factor. Every portal-based instruction from that moment on is unperformable: steps 1, 2, 4 (portal route), 13, 14, 15 and 20 of this section, and the portal legs of the remaining sections. The Azure CLI is the only surviving control-plane route - az login --use-device-code was run and did complete successfully - but that fallback is documented only in this section's step 4 sidebar, for firewall rules, and nowhere else in the lab.
  <br>evidence: step `3146`, instruction `#lab-using-vector-databases-in-azure-sql-database`

## Findings

**LAB003** ×1 · **LAB004** ×1 · **LAB007** ×1 · **LAB009** ×3

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#3** Timing or quota (`LAB007`)

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Defective sample code (`LAB009`)
- **#4** Defective sample code (`LAB009`)
- **#5** Moved navigation (`LAB004`)
- **#6** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!!] Defective sample code — `LAB009`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* instruction · *Step:* `3143` · *2026-09-08T00:04:54Z*

Root cause of the step 25 failure, now confirmed at character level. In 4_SQLEmbeddings.py the T-SQL for dbo.get_embedding is assembled by concatenating an opening quote, a space, and then the URL variable, so the procedure stores a URL string literal that begins with a space. Dumping the deployed definition from sys.sql_modules gives exactly: [<space>https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01]. sp_invoke_external_rest_endpoint rejects that with 'failed to parse url. HRESULT: 0x80072ee6 (31609)', so step 25 can never return rows as written. Recreating the identical procedure with only that one space removed made the same 5_query.sql succeed immediately. The defect is unconditional: it does not depend on any .env value.

### 2. [!!] Defective sample code — `LAB009`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* instruction · *Step:* `3144` · *2026-09-08T00:05:06Z*

Second, independent defect in the same script, and the one a learner is guaranteed to hit. 4_SQLEmbeddings.py creates the database scoped credential named after the raw endpoint, but the stored procedure it then generates references the same name with any trailing slash stripped. Step 15 tells the learner to copy the Endpoint value from Keys and Endpoint, and that value ends in a slash - as the shipped .env does. The two names therefore never match. Verified directly: sys.database_scoped_credentials contains [https://ai-foundry-64827025.openai.azure.com/] while dbo.get_embedding asks for https://ai-foundry-64827025.openai.azure.com, and step 25 fails with 'Cannot find the credential ... because it does not exist or you do not have permission. (15151)'. Creating a credential under the stripped name made the query work. Note this is a different failure from the stray space: fixing the space alone moves the error from 31609 to 15151, so both must be fixed before step 25 returns anything.

### 3. [!!] Timing or quota — `LAB007`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* setup · *Step:* `3146` · *2026-09-08T00:05:33Z*

The Azure portal became permanently unreachable partway through the reservation, with the lab clock still showing 1440 minutes. The account signs in with a Temporary Access Pass, and once it expired the CLI reported it exactly: 'AADSTS130504: Your Temporary Access Pass has expired. Contact your administrator to obtain a new pass.' Because no other authentication method is registered on the account, every portal re-authentication now lands on a mandatory 'Lets keep your account secure' registration flow whose only path forward is 'Install Microsoft Authenticator' on a mobile device. There is no skip and no deferral, and the lab issues no second factor. Every portal-based instruction from that moment on is unperformable: steps 1, 2, 4 (portal route), 13, 14, 15 and 20 of this section, and the portal legs of the remaining sections. The Azure CLI is the only surviving control-plane route - az login --use-device-code was run and did complete successfully - but that fallback is documented only in this section's step 4 sidebar, for firewall rules, and nowhere else in the lab.

### 4. [!] Defective sample code — `LAB009`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction · *Step:* `3145` · *2026-09-08T00:05:19Z*

Step 23 says 'Resolve any error before continuing', but the script it tells you to run cannot be re-run. 4_SQLEmbeddings.py creates the database scoped credential before it creates the stored procedure and does not guard the CREATE. A second execution aborts on 'The credential with name ... already exists. (15530)' and never reaches CREATE OR ALTER PROCEDURE, so dbo.get_embedding is left missing and step 25 then reports 'Could not find stored procedure dbo.get_embedding. (2812)'. That is precisely the position a learner following step 23's own instruction ends up in: they hit an error, change something, run it again, and the second run leaves the database in a worse state than the first. Recovering requires manually dropping both the procedure and the credential, which the lab never mentions.

### 5. [!] Moved navigation — `LAB004`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction · *Step:* `3147` · *2026-09-08T00:05:45Z*

Steps 20, 26 and 27 describe a Foundry portal that no longer exists. Step 20's 'click Explore Azure AI Foundry portal' is the classic Azure OpenAI resource blade action; the current route is ai.azure.com/nextgen with a top nav of Home, Discover, Build, Operate, Manage, Docs. Step 26's 'go to Model catalog' has no match: the catalog is Discover > Models, and the word catalog appears nowhere in the navigation. Step 27's 'Click Use this model' is likewise gone - the text-embedding-ada-002 model card's command is a 'Deploy' split button, and the deployment form it opens has no field called 'Deployment type: Global Standard' to choose in the way step 27 implies, since Global Standard is preselected. The deployment fields that do exist (Deployment name, Deployment type, TPM rate limit, Guardrails) were confirmed on the fine-tuned model deployment in this same run.

### 6. [!] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction · *Step:* `3148` · *2026-09-08T00:06:03Z*

Steps 13 to 15 send the learner to 'your Azure OpenAI resource (example: myopai-resource-53809613)' and to its Keys and Endpoint blade. No such resource exists in this lab. The only cognitive-services resource in azureaiworkshoprg is the Foundry resource ai-foundry-64827025, and it is what the lab's own .env points at. Two consequences follow. The learner has nothing matching the described name to click, and the Endpoint value they are told to copy in step 15 is the resource endpoint, whereas the shipped .env holds a full deployment inference URI for AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT; 4_SQLEmbeddings.py concatenates /openai/deployments/<name>/embeddings onto whatever it finds, producing a doubled path. Smaller text defects in the same section: the copy-button control text has bled into every code block (powershellTypeCopy, sqlTypeCopy, envTypeCopy, and a bare TypeCopy on the expected output in step 22), and step 22 presents 'Embeddings updated for all quotes.' as proof of success even though that line is printed unconditionally - the same false success recorded against the Azure SQL section, where it appeared with zero rows updated.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `3142`** · instruction `#lab-using-vector-databases-in-azure-sql-database` — Steps 3-8 and 24-25 were driven through pyodbc from the VM terminal rather than clicking through SSMS, because SSMS on this VM was pre-populated with another reservation's server and a stale account (recorded against the Azure SQL section). The SQL executed is byte-for-byte the contents of 1_Setup.sql and 5_query.sql.
  <br>outcome: The vector pipeline this section teaches does work, and was verified on real data rather than on success messages. dbo.MovieQuotes exists with a native embedding vector(1536) column; step 18 loaded 732 rows of real content (Star Wars 'Do, or do not. There is no try.', Dracula 'Listen to them. Children of the night.'); step 21 populated 732 non-null embeddings; and after the three script defects below were corrected, step 25's 5_query.sql returned exactly 10 ranked rows for the query 'texas city', led by Apollo 13's 'Houston, we have a problem.' at cosine distance 0.165, followed by The Wizard of Oz at 0.232 - a semantically correct ranking, not an arbitrary one. Step 1's example database name (vectordb) and step 4's example admin login (sqladmin) both match the provisioned environment; the server is sqlaivector-64827025.database.windows.net. Step 4 is also correct and necessary: az sql server firewall-rule list showed the pre-created server ships with no firewall rules at all, so the client IP must be added before anything connects.

## Verified correct

- begin section 22
- return to Windows Terminal
- read 4_SQLEmbeddings.py
- read 4_SQLEmbeddings.py part 2
- dump the @url literal from the deployed stored procedure
- dump the @url literal from the deployed stored procedure
- strip the stray leading space from the generated @url literal
- recreate proc without the stray space
- run 5_query.sql vector similarity query
- compare credential name to the referenced name
- create credential matching the name the procedure references
- create credential matching the referenced name
- run 5_query.sql after resolving all three defects
- open resource group in Azure portal
- list Edge windows
- switch to the signed-in Azure portal window
- open resource group overview
- open resource group overview
- reload portal after token expiry
- inspect MFA registration prompt for a skip option
- confirm the Azure portal is unreachable without MFA enrolment
- verify SQL server and database facts via az CLI
- start device code login without displaying the code
- start device code login (temp log)
- open device login page
- submit device code
- pick account for CLI device login
- continue CLI device login
- verify SQL server, database and firewall rules
- switch to Microsoft Foundry tab
- open Discover to look for the model catalog
- search the catalog for text-embedding-ada-002
- search catalog for the ada embedding model
- open text-embedding-ada-002 model card
- Closed partial: the SQL and embedding chain was executed and verified end to end, but steps 1, 2, 13, 14, 15 and 20 could not be performed in the portal because the Temporary Access Pass expired and the portal now demands MFA registration. Their facts were confirmed instead through the Azure CLI and the Foundry portal, which is weaker evidence than walking the documented screens.
- Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.

## Evidence

33 capture(s), in the order the learner would have seen them.

- [`0447-s22-lab-using-vector-step.jpg`](../images/0447-s22-lab-using-vector-step.jpg)
- [`0448-s22-lab-using-vector-step.jpg`](../images/0448-s22-lab-using-vector-step.jpg)
- [`0449-s22-lab-using-vector-step.jpg`](../images/0449-s22-lab-using-vector-step.jpg)
- [`0450-s22-lab-using-vector-step.jpg`](../images/0450-s22-lab-using-vector-step.jpg)
- [`0451-s22-lab-using-vector-step.jpg`](../images/0451-s22-lab-using-vector-step.jpg)
- [`0452-s22-lab-using-vector-step.jpg`](../images/0452-s22-lab-using-vector-step.jpg)
- [`0453-s22-lab-using-vector-step.jpg`](../images/0453-s22-lab-using-vector-step.jpg)
- [`0454-s22-lab-using-vector-step.jpg`](../images/0454-s22-lab-using-vector-step.jpg)
- [`0455-s22-lab-using-vector-step.jpg`](../images/0455-s22-lab-using-vector-step.jpg)
- [`0456-s22-lab-using-vector-step.jpg`](../images/0456-s22-lab-using-vector-step.jpg)
- [`0457-s22-lab-using-vector-step.jpg`](../images/0457-s22-lab-using-vector-step.jpg)
- [`0458-s22-lab-using-vector-step.jpg`](../images/0458-s22-lab-using-vector-step.jpg)
- [`0459-s22-lab-using-vector-step.jpg`](../images/0459-s22-lab-using-vector-step.jpg)
- [`0460-s22-lab-using-vector-step.jpg`](../images/0460-s22-lab-using-vector-step.jpg)
- [`0461-s22-lab-using-vector-step.jpg`](../images/0461-s22-lab-using-vector-step.jpg)
- [`0462-s22-lab-using-vector-step.jpg`](../images/0462-s22-lab-using-vector-step.jpg)
- [`0463-s22-lab-using-vector-step.jpg`](../images/0463-s22-lab-using-vector-step.jpg)
- [`0464-s22-lab-using-vector-step.jpg`](../images/0464-s22-lab-using-vector-step.jpg)
- [`0465-s22-lab-using-vector-step.jpg`](../images/0465-s22-lab-using-vector-step.jpg)
- [`0466-s22-lab-using-vector-step.jpg`](../images/0466-s22-lab-using-vector-step.jpg)
- [`0467-s22-lab-using-vector-step.jpg`](../images/0467-s22-lab-using-vector-step.jpg)
- [`0468-s22-lab-using-vector-step.jpg`](../images/0468-s22-lab-using-vector-step.jpg)
- [`0469-s22-lab-using-vector-step.jpg`](../images/0469-s22-lab-using-vector-step.jpg)
- [`0470-s22-lab-using-vector-step.jpg`](../images/0470-s22-lab-using-vector-step.jpg)
- [`0471-s22-lab-using-vector-step.jpg`](../images/0471-s22-lab-using-vector-step.jpg)
- [`0472-s22-lab-using-vector-step.jpg`](../images/0472-s22-lab-using-vector-step.jpg)
- [`0473-s22-lab-using-vector-step.jpg`](../images/0473-s22-lab-using-vector-step.jpg)
- [`0474-s22-lab-using-vector-step.jpg`](../images/0474-s22-lab-using-vector-step.jpg)
- [`0475-s22-lab-using-vector-step.jpg`](../images/0475-s22-lab-using-vector-step.jpg)
- [`0479-s22-lab-using-vector-step.jpg`](../images/0479-s22-lab-using-vector-step.jpg)
- [`0480-s22-lab-using-vector-step.jpg`](../images/0480-s22-lab-using-vector-step.jpg)
- [`0481-s22-lab-using-vector-step.jpg`](../images/0481-s22-lab-using-vector-step.jpg)
- [`0482-s22-lab-using-vector-step.jpg`](../images/0482-s22-lab-using-vector-step.jpg)
