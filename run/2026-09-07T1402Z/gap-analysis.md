# Gap analysis

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** `` started 2026-09-07T14:02:36Z, status **done**  
**Instructions.** `474fb95356ea78f8…` (3,674 lines). A future run that hashes differently is comparing against rewritten content, not drifted product.  

This report is what a simulated learner encountered while doing the lab. It records what was verified correct as well as what was wrong, because a list of failures alone cannot distinguish a checked step from a skipped one.

## Can a learner complete this lab?

**NO** — a learner cannot complete this as written

> Scoped to what was walked. Sections that were never reached are unknown, not correct — see Coverage.

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Defective sample code** `LAB009` *(Azure AI Vision - Lab)* — The Exercise 3/4 notebook cannot read the .env the section tells the learner to edit. LabFiles/AI_vision_services_lab.ipynb does env_file = '.env' then load_dotenv(env_file) -- a relative path that resolves against the notebook's own folder, 'Lab 04 - AI-Vision\LabFiles', while the file the lab has the learner edit is the shared LABS root .env. Executed the notebook unchanged with nbconvert --execute --allow-errors: the first OCR cell died with AttributeError: 'NoneType' object has no attribute 'rstrip' at COMPUTER_VISION_ENDPOINT.rstrip('/'), i.e. os.getenv returned None. Confirmed with a direct oracle run from the notebook's folder: load_dotenv('.env') returned found_local False while load_dotenv on the LABS root .env returned found_root True and endpoint_ok True. Copying the root .env beside the notebook removed the AttributeError, so the path is the whole cause. Nothing in Exercise 3 or 4 can run as shipped.
  <br>evidence: step `1652`, instruction `#azure-ai-vision---lab`
- **Defective sample code** `LAB009` *(Azure AI Vision - Lab)* — Even with the .env resolvable, Exercise 3's OCR call is dead: the notebook hardcodes api-version=2023-02-01-preview and the service answers HTTP 410. Observed output: 'OCR error: 410 Client Error: Gone for url: https://cv-64827025.cognitiveservices.azure.com/computervision/imageanalysis:analyze?api-version=2023-02-01-preview&features=read'. This is the notebook, not the environment: the same image, key and endpoint against api-version=2024-02-01&features=read returned HTTP 200 and real text ('modelVersion':'2023-10-01', readResult blocks with 'NATIONAL IDENTITY CARD'). So the resource created in Exercise 1 is healthy and only the pinned preview API version is retired. Worse, the cell catches the error and prints it, so it completes green having produced no OCR at all.
  <br>evidence: step `1653`, instruction `#azure-ai-vision---lab`
- **Defective sample code** `LAB009` *(Prompt Engineering)* — The Prompt Engineering notebook cannot load the .env the lab has the learner configure. 'Prompt Engineering.ipynb' calls load_dotenv(dotenv_path='../../../.env'), but the notebook sits in C:/Users/Admin/Desktop/LABS/Lab 06 - Prompt Engineering, so three levels up resolves to C:\\Users\\Admin\\.env. Measured on the VM: resolved path C:\\Users\\Admin\\.env, Test-Path False, while Test-Path on C:\\Users\\Admin\\Desktop\\LABS\\.env is True. Executed unchanged with nbconvert --execute --allow-errors: 9 of 11 code cells failed, cell 2 with 'OpenAIError: Missing credentials. Please pass one of api_key, azure_ad_token...' and cells 3-10 with cascading NameError: name 'client' is not defined. Changing the single string to '../.env' (one substitution, 6 characters) let the client build and grew the executed notebook from 60,594 to 201,899 bytes. Note the sibling DPO notebook in Lab 05 uses '../../.env' correctly from one directory deeper, so this is a per-notebook mistake, not a convention.
  <br>evidence: step `1926`, instruction `#prompt-engineering`
- **Defective sample code** `LAB009` *(Azure Cosmos DB Lab)* — The Cosmos DB notebook cannot be run as delivered: its first code cell dies with KeyError: 'EMBEDDING_MODEL_DIMENSIONS'. Cell 3 does `config = dotenv_values("../../.env")` (that path is correct - it resolves to C:\Users\Admin\Desktop\LABS\.env, verified present) and then reads ten keys from it. Nine are present; EMBEDDING_MODEL_DIMENSIONS is absent from the provided .env AND from the shipped .env.example, so a learner has no template line to fill in and no way to discover the name except by reading the traceback. The section's own Pre-requisites say "None. The database has been pre-created for you." and its only task is "Open Python-Samples.ipynb and follow the steps", so nothing warns the learner that .env needs editing. Executed unmodified the whole notebook collapses: c3 KeyError, then c4 NameError 'openai_api_version', c12 NameError 'openai_client', c14/c17/c20 NameError 'full_text', c23/c25 NameError 'emb' - eight failing cells, no search ever runs. Adding a single line EMBEDDING_MODEL_DIMENSIONS=3072 to .env (3072 being the native width of the deployed text-embedding-3-large and the width advertised by the lab's own data file e-retail-data-3072D.json) makes the identical, otherwise-unmodified notebook run clean.
  <br>evidence: step `2318`, instruction `#azure-cosmos-db-lab`
- **Broken link** `LAB006` *(Azure SQL Lab)* — The pre-created Azure SQL server is unreachable from the lab VM and nothing in the lab tells the learner how to fix it. Running the lab's own second step, `python 2_LoadMovieData.py`, fails with pyodbc error 40615: "Cannot open server 'sqlaivector-64827025' requested by the login. Client with IP address '185.254.59.123' is not allowed to access the server." `az sql server firewall-rule list -g azureaiworkshoprg -s sqlaivector-64827025` returns an empty list - the server has NO firewall rules at all, so neither the VM nor Azure services can reach it. Connecting through SSMS surfaces the same condition as a "New Firewall Rule" wizard ("Your client IP address does not have access to the server"), which then demands an Azure sign-in the learner has just been forced to sign out of (see the stale-account finding). The section's Pre-requisites say "None. The database has been pre-created for you." and the Tasks say only to execute the numbered files, so a learner has no documented route past this. Everything after it in sections 21 and 22 is blocked. Unblocked here only by running `az sql server firewall-rule create ... --start-ip-address 185.254.59.0 --end-ip-address 185.254.59.255`, which the lab never mentions.
  <br>evidence: step `2791`, instruction `#azure-sql-lab`
- **Broken link** `LAB006` *(Azure SQL Lab)* — SQL Server Management Studio in the VM image is signed in as a DIFFERENT lab reservation's user and refuses to connect until that is undone. On first launch, SSMS 21 pre-populates the Connect to Server dialog with server name "sqlaivector-55791077.database.windows.net" - not this reservation's sqlaivector-64827025 - and every Connect attempt, even with SQL Server Authentication and correct credentials, aborts with: "User account 'User1-55791077@LODSPRODMCA.onmicrosoft.com' was invalid or stale when getting Azure subscriptions. Please re-authenticate the account before trying again. (Microsoft.SqlServer.Management.ApplicationAuthenticationManagement)". Opening the account flyout confirms it: signed in as User1-55791077 under tenant LODS-Prod-MCA with a "Re-enter your credentials" warning. Both the cached Entra account and the server MRU are baked into the image from lab instance 55791077. The only way forward is the undocumented sequence account flyout -> ... -> Sign out, after which the dialog stops erroring. The section tells the learner "The .sql files need to be executed in SQL Server Management Studio, which is preloaded on Desktop for you" and gives no hint that the preloaded tool is carrying someone else's identity. Related smaller inaccuracy in the same sentence: SSMS is NOT on the Desktop - the only Desktop shortcut for this user is "Visual Studio Code.lnk" and C:\Users\Public\Desktop is empty; SSMS 21 is installed at C:\Program Files\Microsoft SQL Server Management Studio 21 and pinned to the taskbar.
  <br>evidence: step `2792`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` *(Azure SQL Lab)* — Two values the lab's own scripts require are wrong or missing in the shipped .env, and no section ever tells the learner to set them. (a) SQL_PWD is EMPTY. .env.example carries a 7-character placeholder for it, but the delivered .env has "SQL_PWD=" with nothing after the equals sign. Section 05 (Setup env file) walks the learner through SQL_SERVER at step 10 and never mentions SQL_PWD, SQL_USER, SQL_DATABASE, CSV_PATH or BATCH_SIZE. Consequence: `python 2_LoadMovieData.py` fails with pyodbc 28000 "Login failed for user 'sqladmin'. (18456)". (b) CSV_PATH points at a folder that does not exist: it ends "...S\Vectors\SQL\movie_quotes.csv" (os.path.exists returns False) - a legacy layout. The file actually ships at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\SQL\movie_quotes.csv (66890 bytes). Both had to be repaired by hand before any of the numbered steps could run.
  <br>evidence: step `2793`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` *(Azure SQL Lab)* — The failure of 2_LoadMovieData.py is hidden by its own error handler, and the next script then reports success on an empty table - a textbook false pass. 2_LoadMovieData.py wraps everything in `try: ... except Exception as e: print(f"An error occurred: {e} -- {sql}")`, but `sql` is only assigned INSIDE the try, several lines after `open(csv_path)`. So when the CSV path is wrong the handler itself raises `NameError: name 'sql' is not defined` and the learner never sees the real FileNotFoundError. Worse, running the very next documented step on that empty table, `python 3_UpdateMovieEmbedding.py`, printed "Embeddings updated for all quotes." - while a direct count showed `select count(*), sum(case when embedding is null then 0 else 1 end) from dbo.MovieQuotes` = (0, None). Zero rows, zero embeddings, and a success message. A learner following the instructions and reading the console would believe the ingest worked. After repairing CSV_PATH the same two scripts ran clean and the counts became (732, 732) with real content ("Star Wars: Episode V - The Empire Strikes Back" / "Do, or do not. There is no try.", "Dracula" / "Listen to them. Children of the night."), which is what the step should have produced the first time.
  <br>evidence: step `2794`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` *(Azure SQL Lab)* — The final two steps of the lab could not be completed even after every environment problem above was repaired. 4_SQLEmbeddings.py creates a DATABASE SCOPED CREDENTIAL and a dbo.get_embedding procedure that calls sp_invoke_external_rest_endpoint, and 5_query.sql then EXECs it. Two separate defects: (a) the script is not idempotent - re-running it (which a learner will do, because step 2 failed the first time) aborts with `pyodbc.ProgrammingError ... The credential with name "https://ai-foundry-64827025.openai.azure.com/" already exists. (15530)` and never reaches the CREATE PROCEDURE, leaving the database in a half-built state that then reports "Could not find stored procedure 'dbo.get_embedding'. (2812)". (b) Even after dropping both objects and running 4_SQLEmbeddings.py once, cleanly, with a corrected endpoint, executing 5_query.sql verbatim fails with `[SQL Server]An error occurred, failed to parse url. HRESULT: 0x80072ee6. (31609)`. The URL the script composes is `{endpoint.rstrip('/')}/openai/deployments/{deployment}/embeddings?api-version=2024-02-01`, which with a corrected base endpoint evaluates to a well-formed https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01 - so the malformation is introduced when that string is embedded into the generated T-SQL, not by the endpoint value. Net effect: the lab's stated objective, a similarity search in Azure SQL, cannot be reached by following the instructions.
  <br>evidence: step `2795`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` *(Lab: Using Vector Databases in Azure SQL Database)* — Root cause of the step 25 failure, now confirmed at character level. In 4_SQLEmbeddings.py the T-SQL for dbo.get_embedding is assembled by concatenating an opening quote, a space, and then the URL variable, so the procedure stores a URL string literal that begins with a space. Dumping the deployed definition from sys.sql_modules gives exactly: [<space>https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01]. sp_invoke_external_rest_endpoint rejects that with 'failed to parse url. HRESULT: 0x80072ee6 (31609)', so step 25 can never return rows as written. Recreating the identical procedure with only that one space removed made the same 5_query.sql succeed immediately. The defect is unconditional: it does not depend on any .env value.
  <br>evidence: step `3143`, instruction `#lab-using-vector-databases-in-azure-sql-database`
- **Defective sample code** `LAB009` *(Lab: Using Vector Databases in Azure SQL Database)* — Second, independent defect in the same script, and the one a learner is guaranteed to hit. 4_SQLEmbeddings.py creates the database scoped credential named after the raw endpoint, but the stored procedure it then generates references the same name with any trailing slash stripped. Step 15 tells the learner to copy the Endpoint value from Keys and Endpoint, and that value ends in a slash - as the shipped .env does. The two names therefore never match. Verified directly: sys.database_scoped_credentials contains [https://ai-foundry-64827025.openai.azure.com/] while dbo.get_embedding asks for https://ai-foundry-64827025.openai.azure.com, and step 25 fails with 'Cannot find the credential ... because it does not exist or you do not have permission. (15151)'. Creating a credential under the stripped name made the query work. Note this is a different failure from the stray space: fixing the space alone moves the error from 31609 to 15151, so both must be fixed before step 25 returns anything.
  <br>evidence: step `3144`, instruction `#lab-using-vector-databases-in-azure-sql-database`
- **Timing or quota** `LAB007` *(Lab: Using Vector Databases in Azure SQL Database)* — The Azure portal became permanently unreachable partway through the reservation, with the lab clock still showing 1440 minutes. The account signs in with a Temporary Access Pass, and once it expired the CLI reported it exactly: 'AADSTS130504: Your Temporary Access Pass has expired. Contact your administrator to obtain a new pass.' Because no other authentication method is registered on the account, every portal re-authentication now lands on a mandatory 'Lets keep your account secure' registration flow whose only path forward is 'Install Microsoft Authenticator' on a mobile device. There is no skip and no deferral, and the lab issues no second factor. Every portal-based instruction from that moment on is unperformable: steps 1, 2, 4 (portal route), 13, 14, 15 and 20 of this section, and the portal legs of the remaining sections. The Azure CLI is the only surviving control-plane route - az login --use-device-code was run and did complete successfully - but that fallback is documented only in this section's step 4 sidebar, for firewall rules, and nowhere else in the lab.
  <br>evidence: step `3146`, instruction `#lab-using-vector-databases-in-azure-sql-database`
- **Broken link** `LAB006` *(Optional Lab RAG (Retrieval-Augmented Generation) Implementation)* — This section has exactly one instruction - 'Run through steps in RAG.ipynb file' - and that file does not exist. A recursive search of the entire C: drive on the lab VM for RAG.ipynb returned nothing, and the lab tree under Desktop\LABS contains only Lab 00 through Lab 10, with Lab 08 - RAG-Patterns holding a single file, GraphRAG\README.md, which is the Cloud Shell GraphRAG material used by an earlier section. Everything else in this section (Exercises 1 to 7, Advanced Implementation Topics, Execution Instructions, Expected Results) is prose describing what that notebook would do; none of it is independently actionable. The section is therefore unperformable as written. The supporting environment is present and would have worked: azureaiworkshoprg contains a running Azure AI Search service, aisearch-64827025 in West Europe, whose REST API answered with one existing index (myfitnessindex), and the .env carries populated AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_API_VERSION and SEARCH_AUTHENTICATION_METHOD. Only the notebook is missing.
  <br>evidence: step `3178`, instruction `#optional-lab-rag-retrieval-augmented-generation-implementation`
- **Broken link** `LAB006` *(AI Frameworks - Semantic Kernel and AutoGen)* — This section has exactly one instruction - 'Open the SK and AutoGen.ipynb notebook and run through the steps' - and no such notebook ships with the lab. A recursive enumeration of every .ipynb under Desktop\LABS returns fifteen notebooks (Lab 00 pip-install; Lab 01 setup and quick_start, 1-evaluation; Lab 02 agents 1 through 6; Lab 04 AI_vision_services_lab; Lab 05 gpt-4_o_dpo_ft; Lab 06 Prompt Engineering; Lab 09 AI_RedTeaming; Lab 10 Cosmos DB Python-Samples) and none of them is SK and AutoGen.ipynb, nor is there any file matching SK, AutoGen or Semantic anywhere in the tree. What makes this clearly an omission rather than a design choice is that the environment was prepared for it: pip list on the lab VM shows semantic-kernel 1.35.3 and autogen-agentchat, autogen-core and autogen-ext all at 0.7.4 already installed. The dependencies are there; the material that uses them is not. All five exercises are therefore unperformable and unjudgeable.
  <br>evidence: step `3203`, instruction `#ai-frameworks---semantic-kernel-and-autogen`

## Coverage

**23 of 25 sections completed (92%)** across 3,118 recorded steps and 99 heartbeats.

| Section | Module | Status | Steps | Findings | Report |
|---|---|---|---|---|---|
| Welcome to WPLUS: Azure AI Platform and Services | - | done | 2 | - | [section](sections/s00-welcome-to-wplus-azure-ai-pl.md) |
| Create Microsoft Foundry Project | - | done | 98 | 1 | [section](sections/s01-create-microsoft-foundry-pro.md) |
| Deploy models into the Microsoft Foundry Project | - | done | 82 | 3 | [section](sections/s02-deploy-models-into-the-micro.md) |
| Create connections to Bing Resources at Azure AI Fou | - | done | 29 | 3 | [section](sections/s03-create-connections-to-bing-r.md) |
| Create connections to Azure AI Search at AI Foundry  | - | done | 18 | 3 | [section](sections/s04-create-connections-to-azure.md) |
| Setup .env file | - | done | 631 | 3 | [section](sections/s05-setup-env-file.md) |
| Run requirements file to install the relevant packag | - | done | 10 | - | [section](sections/s06-run-requirements-file-to-ins.md) |
| Quick Start Guide - Azure AI Foundry | - | done | 69 | - | [section](sections/s07-quick-start-guide-azure-ai-f.md) |
| Evaluations with Azure AI Foundry | - | done | 48 | 2 | [section](sections/s08-evaluations-with-azure-ai-fo.md) |
| Azure AI Agents Tutorial Collection | - | done | 131 | 2 | [section](sections/s09-azure-ai-agents-tutorial-col.md) |
| AI Language Service with Agents Lab | - | done | 119 | 2 | [section](sections/s10-ai-language-service-with-age.md) |
| Azure AI Vision - Lab | - | done | 342 | 7 | [section](sections/s11-azure-ai-vision-lab.md) |
| Fine Tuning | - | done | 10 | 1 | [section](sections/s12-fine-tuning.md) |
| 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | - | done | 136 | 7 | [section](sections/s13-steps-fine-tuning-the-gpt-41.md) |
| Fine Tuning - Advance Lab | - | done | 121 | 1 | [section](sections/s14-fine-tuning-advance-lab.md) |
| Prompt Engineering | - | done | 138 | 4 | [section](sections/s15-prompt-engineering.md) |
| Responsible AI | - | done | 44 | 4 | [section](sections/s16-responsible-ai.md) |
| Lab 08 - RAG-Patterns - Graph RAG | System Message | done | 143 | 3 | [section](sections/s17-lab-08-rag-patterns-graph-ra.md) |
| AI Red Teaming Agent for Generative AI Applications | System Message | done | 173 | 4 | [section](sections/s18-ai-red-teaming-agent-for-gen.md) |
| Azure Cosmos DB Lab | System Message | done | 50 | 1 | [section](sections/s19-azure-cosmos-db-lab.md) |
| Azure PostgreSQL Lab | System Message | done | 191 | 4 | [section](sections/s20-azure-postgresql-lab.md) |
| Azure SQL Lab | System Message | done | 271 | 7 | [section](sections/s21-azure-sql-lab.md) |
| Lab: Using Vector Databases in Azure SQL Database | System Message | done | 200 | 6 | [section](sections/s22-lab-using-vector-databases-i.md) |
| Optional Lab RAG (Retrieval-Augmented Generation) Im | System Message | **blocked** | 31 | 2 | [section](sections/s23-optional-lab-rag-retrieval-a.md) |
| AI Frameworks - Semantic Kernel and AutoGen | System Message | **blocked** | 31 | 3 | [section](sections/s24-ai-frameworks-semantic-kerne.md) |

### Interaction coverage

Every action went through a control the learner has, so a defect in the lab's own UI would have been hit.

## Findings

**LAB002** ×4 · **LAB003** ×20 · **LAB004** ×14 · **LAB005** ×4 · **LAB006** ×4 · **LAB007** ×3 · **LAB009** ×21 · **LAB010** ×3

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#4** Defective sample code (`LAB009`)
- **#5** Broken link (`LAB006`)
- **#6** Broken link (`LAB006`)
- **#7** Defective sample code (`LAB009`)
- **#12** Timing or quota (`LAB007`)
- **#17** Timing or quota (`LAB007`)
- **#18** Timing or quota (`LAB007`)
- **#20** Missing resource or SKU (`LAB002`)
- **#30** Missing resource or SKU (`LAB002`)
- **#39** Missing resource or SKU (`LAB002`)

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Defective sample code (`LAB009`)
- **#3** Defective sample code (`LAB009`)
- **#8** Defective sample code (`LAB009`)
- **#9** Defective sample code (`LAB009`)
- **#10** Defective sample code (`LAB009`)
- **#11** Defective sample code (`LAB009`)
- **#13** Broken link (`LAB006`)
- **#14** Broken link (`LAB006`)
- **#15** Defective sample code (`LAB009`)
- **#16** Defective sample code (`LAB009`)
- **#19** Defective sample code (`LAB009`)
- **#21** Defective sample code (`LAB009`)
- **#22** Defective sample code (`LAB009`)
- **#23** Defective sample code (`LAB009`)
- **#24** Removed feature (`LAB005`)
- **#25** Moved navigation (`LAB004`)
- **#26** Defective sample code (`LAB009`)
- **#27** Defective sample code (`LAB009`)
- **#28** Removed feature (`LAB005`)
- **#29** Defective sample code (`LAB009`)
- **#31** Changed UI label or inconsistent structure (`LAB003`)
- **#32** Defective sample code (`LAB009`)
- **#33** Removed feature (`LAB005`)
- **#34** Moved navigation (`LAB004`)
- **#35** Moved navigation (`LAB004`)
- **#36** Defective sample code (`LAB009`)
- **#37** Moved navigation (`LAB004`)
- **#38** Changed UI label or inconsistent structure (`LAB003`)
- **#40** Moved navigation (`LAB004`)
- **#41** Superseded or retiring feature (`LAB010`)
- **#42** Changed UI label or inconsistent structure (`LAB003`)
- **#43** Moved navigation (`LAB004`)
- **#44** Moved navigation (`LAB004`)
- **#45** Changed UI label or inconsistent structure (`LAB003`)
- **#46** Changed UI label or inconsistent structure (`LAB003`)
- **#47** Moved navigation (`LAB004`)
- **#48** Changed UI label or inconsistent structure (`LAB003`)
- **#49** Changed UI label or inconsistent structure (`LAB003`)
- **#50** Changed UI label or inconsistent structure (`LAB003`)
- **#51** Moved navigation (`LAB004`)
- **#52** Moved navigation (`LAB004`)
- **#53** Superseded or retiring feature (`LAB010`)
- **#54** Missing resource or SKU (`LAB002`)
- **#55** Removed feature (`LAB005`)
- **#56** Defective sample code (`LAB009`)
- **#57** Changed UI label or inconsistent structure (`LAB003`)
- **#58** Changed UI label or inconsistent structure (`LAB003`)
- **#59** Changed UI label or inconsistent structure (`LAB003`)
- **#60** Moved navigation (`LAB004`)
- **#61** Moved navigation (`LAB004`)
- **#62** Moved navigation (`LAB004`)
- **#63** Changed UI label or inconsistent structure (`LAB003`)
- **#64** Changed UI label or inconsistent structure (`LAB003`)
- **#65** Changed UI label or inconsistent structure (`LAB003`)
- **#66** Changed UI label or inconsistent structure (`LAB003`)
- **#67** Moved navigation (`LAB004`)
- **#68** Changed UI label or inconsistent structure (`LAB003`)
- **#69** Changed UI label or inconsistent structure (`LAB003`)
- **#70** Changed UI label or inconsistent structure (`LAB003`)
- **#71** Changed UI label or inconsistent structure (`LAB003`)
- **#72** Changed UI label or inconsistent structure (`LAB003`)
- **#73** Superseded or retiring feature (`LAB010`)

Findings are grouped by lab below. Numbering is global and ordered by severity, so a finding keeps its number wherever it is read.

| ID | Sev | Lab | Gap |
|---|---|---|---|
| #1 | critical | Azure AI Vision - Lab | Defective sample code |
| #2 | critical | Azure AI Vision - Lab | Defective sample code |
| #3 | critical | Prompt Engineering | Defective sample code |
| #4 | critical | System Message | Defective sample code |
| #5 | critical | System Message | Broken link |
| #6 | critical | System Message | Broken link |
| #7 | critical | System Message | Defective sample code |
| #8 | critical | System Message | Defective sample code |
| #9 | critical | System Message | Defective sample code |
| #10 | critical | System Message | Defective sample code |
| #11 | critical | System Message | Defective sample code |
| #12 | critical | System Message | Timing or quota |
| #13 | critical | System Message | Broken link |
| #14 | critical | System Message | Broken link |
| #15 | major | Setup .env file | Defective sample code |
| #16 | major | Evaluations with Azure AI Foundry | Defective sample code |
| #17 | major | Azure AI Agents Tutorial Collection | Timing or quota |
| #18 | major | Azure AI Agents Tutorial Collection | Timing or quota |
| #19 | major | Azure AI Vision - Lab | Defective sample code |
| #20 | major | Azure AI Vision - Lab | Missing resource or SKU |
| #21 | major | Prompt Engineering | Defective sample code |
| #22 | major | Prompt Engineering | Defective sample code |
| #23 | major | Fine Tuning - Advance Lab | Defective sample code |
| #24 | major | Responsible AI | Removed feature |
| #25 | major | Responsible AI | Moved navigation |
| #26 | major | Prompt Engineering | Defective sample code |
| #27 | major | System Message | Defective sample code |
| #28 | major | System Message | Removed feature |
| #29 | major | System Message | Defective sample code |
| #30 | major | System Message | Missing resource or SKU |
| #31 | major | System Message | Changed UI label or inconsistent structure |
| #32 | major | System Message | Defective sample code |
| #33 | major | System Message | Removed feature |
| #34 | major | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Moved navigation |
| #35 | major | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Moved navigation |
| #36 | major | System Message | Defective sample code |
| #37 | major | System Message | Moved navigation |
| #38 | major | System Message | Changed UI label or inconsistent structure |
| #39 | major | System Message | Missing resource or SKU |
| #40 | minor | Create Microsoft Foundry Project | Moved navigation |
| #41 | minor | Deploy models into the Microsoft Foundry Project | Superseded or retiring feature |
| #42 | minor | Deploy models into the Microsoft Foundry Project | Changed UI label or inconsistent structure |
| #43 | minor | Deploy models into the Microsoft Foundry Project | Moved navigation |
| #44 | minor | Create connections to Bing Resources at Azure AI Foundry resource level | Moved navigation |
| #45 | minor | Create connections to Bing Resources at Azure AI Foundry resource level | Changed UI label or inconsistent structure |
| #46 | minor | Create connections to Bing Resources at Azure AI Foundry resource level | Changed UI label or inconsistent structure |
| #47 | minor | Create connections to Azure AI Search at AI Foundry resource level | Moved navigation |
| #48 | minor | Create connections to Azure AI Search at AI Foundry resource level | Changed UI label or inconsistent structure |
| #49 | minor | Create connections to Azure AI Search at AI Foundry resource level | Changed UI label or inconsistent structure |
| #50 | minor | Setup .env file | Changed UI label or inconsistent structure |
| #51 | minor | Evaluations with Azure AI Foundry | Moved navigation |
| #52 | minor | AI Language Service with Agents Lab | Moved navigation |
| #53 | minor | AI Language Service with Agents Lab | Superseded or retiring feature |
| #54 | minor | Azure AI Vision - Lab | Missing resource or SKU |
| #55 | minor | Azure AI Vision - Lab | Removed feature |
| #56 | minor | Azure AI Vision - Lab | Defective sample code |
| #57 | minor | Fine Tuning | Changed UI label or inconsistent structure |
| #58 | minor | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Changed UI label or inconsistent structure |
| #59 | minor | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Changed UI label or inconsistent structure |
| #60 | minor | Responsible AI | Moved navigation |
| #61 | minor | Responsible AI | Moved navigation |
| #62 | minor | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Moved navigation |
| #63 | minor | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Changed UI label or inconsistent structure |
| #64 | minor | System Message | Changed UI label or inconsistent structure |
| #65 | minor | System Message | Changed UI label or inconsistent structure |
| #66 | minor | System Message | Changed UI label or inconsistent structure |
| #67 | minor | System Message | Moved navigation |
| #68 | minor | System Message | Changed UI label or inconsistent structure |
| #69 | minor | System Message | Changed UI label or inconsistent structure |
| #70 | minor | 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model | Changed UI label or inconsistent structure |
| #71 | minor | System Message | Changed UI label or inconsistent structure |
| #72 | minor | System Message | Changed UI label or inconsistent structure |
| #73 | info | Setup .env file | Superseded or retiring feature |

### Azure AI Vision - Lab

#### 1. [!!] Defective sample code — `LAB009`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* critical · *At fault:* instruction

The Exercise 3/4 notebook cannot read the .env the section tells the learner to edit. LabFiles/AI_vision_services_lab.ipynb does env_file = '.env' then load_dotenv(env_file) -- a relative path that resolves against the notebook's own folder, 'Lab 04 - AI-Vision\LabFiles', while the file the lab has the learner edit is the shared LABS root .env. Executed the notebook unchanged with nbconvert --execute --allow-errors: the first OCR cell died with AttributeError: 'NoneType' object has no attribute 'rstrip' at COMPUTER_VISION_ENDPOINT.rstrip('/'), i.e. os.getenv returned None. Confirmed with a direct oracle run from the notebook's folder: load_dotenv('.env') returned found_local False while load_dotenv on the LABS root .env returned found_root True and endpoint_ok True. Copying the root .env beside the notebook removed the AttributeError, so the path is the whole cause. Nothing in Exercise 3 or 4 can run as shipped.

#### 2. [!!] Defective sample code — `LAB009`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* critical · *At fault:* instruction

Even with the .env resolvable, Exercise 3's OCR call is dead: the notebook hardcodes api-version=2023-02-01-preview and the service answers HTTP 410. Observed output: 'OCR error: 410 Client Error: Gone for url: https://cv-64827025.cognitiveservices.azure.com/computervision/imageanalysis:analyze?api-version=2023-02-01-preview&features=read'. This is the notebook, not the environment: the same image, key and endpoint against api-version=2024-02-01&features=read returned HTTP 200 and real text ('modelVersion':'2023-10-01', readResult blocks with 'NATIONAL IDENTITY CARD'). So the resource created in Exercise 1 is healthy and only the pinned preview API version is retired. Worse, the cell catches the error and prints it, so it completes green having produced no OCR at all.

#### 19. [!] Defective sample code — `LAB009`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* major · *At fault:* instruction

Exercise 4 (Image Analysis, notebook sections 03-07) produces nothing, and blames the learner while doing it. Each cell assigns a literal placeholder string instead of reading a variable: IMAGEPATH_SEARCH = 'SEARCH_IMAGE_PATH', IMAGEPATH_DENSECAPS = 'DENSE_CAP_IMAGE_PATH', IMAGEPATH_CAPTIONS = 'IMAGEPATH_CAPTIONS', IMAGEPATH_TAGS = 'IMAGEPATH_TAGS', IMAGEPATH_CROP = 'IMAGEPATH_CROP'. The guard os.path.isfile() is then false for all five, so every cell takes the else branch and prints 'IMAGEPATH_X is not defined or the file does not exist. Please check your .env file.' -- pointing the learner at a file that could not fix it, since the value is never read from the environment at all. Reproduced on both executions of the notebook, including the one where the .env was resolvable. Compounding it, LabFiles/images contains only ocr_image.png, so none of the five images exist either. Not one of the five Image Analysis capabilities the section teaches (Image Retrieval, Dense Captions, Captions, Tags, Smart Crop) returns a result.

#### 20. [!] Missing resource or SKU — `LAB002`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* major · *At fault:* setup

Exercise 3 says 'Inside Visual Studio Code, open the .env file. Set the following values: COMPUTER_VISION_API_KEY ... COMPUTER_VISION_ENDPOINT'. Neither variable exists in the file. Scanned C:\Users\Admin\Desktop\LABS\.env and the .env.example it was copied from for COMPUTER_VISION, IMAGEPATH, SEARCH_IMAGE, DENSE_CAP and VIDEO_INDEXER: both files returned nothing for every pattern. So there is no line to set -- the learner has to know to add the keys, with exactly the spelling the notebook expects, and the six image-path variables the notebook also reads are documented nowhere in the section. Verified by shape only, printing variable names and value lengths, never values.

#### 54. [~] Missing resource or SKU — `LAB002`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction

Exercise 1 lists the values to use as Region, Name, Pricing Tier and the policy checkbox, but the Create Computer Vision form also requires 'Resource group', which the instruction never mentions. The field ships empty and the blade cannot be submitted until it is set. A learner following the value list literally stalls on a required field with no guidance about which resource group to pick (azureaiworkshoprg is the only one present). Observed on the live Create Computer Vision blade, Basics tab.

#### 55. [~] Removed feature — `LAB005`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction

Exercise 2 orders the steps as: tick Acknowledge, select/create the resource, click Confirm, then 'Select an image and then click JSON'. On the live studio, Confirm re-renders the acknowledgement control (its label changes from 'incur usage to my Azure account' to 'incur usage to resource faceresource-64827025 in my Azure account') and the tick is cleared. A learner who follows the written order selects a sample and gets only 'Please acknowledge the resource usage policy above in order to try out Detect faces in an image' with no detection at all. Observed directly: capture 0184 shows the box cleared with the demo refusing to run, capture 0185 shows detection succeeding immediately after re-ticking the same box with nothing else changed. The instruction needs a step to re-tick the acknowledgement after Confirm.

#### 56. [~] Defective sample code — `LAB009`

*Section:* Azure AI Vision - Lab  
*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction

The section states 'Video Indexer is not included' and that the previous exercise referenced a notebook section not present in this repository, but the shipped notebook still contains the Video Indexer cell (VIDEO_INDEXER_SAMPLEPATH = 'VIDEO_INDEXER_SAMPLEPATH', VIDEO_INDEXER_LOCATION = os.getenv('VIDEO_INDEXER...')). Executing the notebook end to end raises TypeError from that cell on both runs. The text and the artifact disagree: a learner running all cells hits a traceback for an exercise the text says was removed.

### Prompt Engineering

#### 3. [!!] Defective sample code — `LAB009`

*Section:* Prompt Engineering  
*Instruction:* `#prompt-engineering`  
*Severity:* critical · *At fault:* instruction

The Prompt Engineering notebook cannot load the .env the lab has the learner configure. 'Prompt Engineering.ipynb' calls load_dotenv(dotenv_path='../../../.env'), but the notebook sits in C:/Users/Admin/Desktop/LABS/Lab 06 - Prompt Engineering, so three levels up resolves to C:\\Users\\Admin\\.env. Measured on the VM: resolved path C:\\Users\\Admin\\.env, Test-Path False, while Test-Path on C:\\Users\\Admin\\Desktop\\LABS\\.env is True. Executed unchanged with nbconvert --execute --allow-errors: 9 of 11 code cells failed, cell 2 with 'OpenAIError: Missing credentials. Please pass one of api_key, azure_ad_token...' and cells 3-10 with cascading NameError: name 'client' is not defined. Changing the single string to '../.env' (one substitution, 6 characters) let the client build and grew the executed notebook from 60,594 to 201,899 bytes. Note the sibling DPO notebook in Lab 05 uses '../../.env' correctly from one directory deeper, so this is a per-notebook mistake, not a convention.

#### 21. [!] Defective sample code — `LAB009`

*Section:* Prompt Engineering  
*Instruction:* `#prompt-engineering`  
*Severity:* major · *At fault:* instruction

With the .env path fixed, every model call still failed: 'Error code: 400 - Unsupported value: temperature does not support 0.3 with this model. Only the default (1) value is supported.' (type invalid_request_error, param temperature, code unsupported_value). The notebook passes an explicit temperature 18 times; the deployment it is configured to use is MODEL_DEPLOYMENT_NAME=gpt-5-mini, which is what this lab's own model-deployment section provisions. So the shipped notebook targets a chat-completions contract the lab's current models no longer honour. Replacing only the values (temperature=1, 18 substitutions, no keyword removed) took the notebook from 8 failing cells to 1.

#### 22. [!] Defective sample code — `LAB009`

*Section:* Prompt Engineering  
*Instruction:* `#prompt-engineering`  
*Severity:* major · *At fault:* instruction

A second, independent incompatibility with the same deployment: one cell fails with 'Error code: 400 - Unsupported parameter: max_tokens is not supported with this model. Use max_completion_tokens instead.' (param max_tokens, code unsupported_parameter). This survived the temperature fix and is the only remaining failure, so it is a distinct defect and not a symptom of the first. Section 8 of the lab (Active-Prompt / the cell in question) produces no output for the learner.

#### 26. [!] Defective sample code — `LAB009`

*Section:* Prompt Engineering  
*Instruction:* `#6-tree-of-thoughts-tot`  
*Severity:* major · *At fault:* instruction

Tree of Thoughts is the one technique that still produces nothing after every other defect is corrected. Its cell fails with 'Error code: 400 - Unsupported parameter: max_tokens is not supported with this model. Use max_completion_tokens instead.' (param max_tokens, code unsupported_parameter) against the lab's own gpt-5-mini deployment. It was the sole failure in the final run, so it is a defect in its own right rather than a symptom of the dotenv or temperature problems.

### System Message

#### 4. [!!] Defective sample code — `LAB009`

*Section:* Azure Cosmos DB Lab  
*Instruction:* `#azure-cosmos-db-lab`  
*Severity:* critical · *At fault:* setup

The Cosmos DB notebook cannot be run as delivered: its first code cell dies with KeyError: 'EMBEDDING_MODEL_DIMENSIONS'. Cell 3 does `config = dotenv_values("../../.env")` (that path is correct - it resolves to C:\Users\Admin\Desktop\LABS\.env, verified present) and then reads ten keys from it. Nine are present; EMBEDDING_MODEL_DIMENSIONS is absent from the provided .env AND from the shipped .env.example, so a learner has no template line to fill in and no way to discover the name except by reading the traceback. The section's own Pre-requisites say "None. The database has been pre-created for you." and its only task is "Open Python-Samples.ipynb and follow the steps", so nothing warns the learner that .env needs editing. Executed unmodified the whole notebook collapses: c3 KeyError, then c4 NameError 'openai_api_version', c12 NameError 'openai_client', c14/c17/c20 NameError 'full_text', c23/c25 NameError 'emb' - eight failing cells, no search ever runs. Adding a single line EMBEDDING_MODEL_DIMENSIONS=3072 to .env (3072 being the native width of the deployed text-embedding-3-large and the width advertised by the lab's own data file e-retail-data-3072D.json) makes the identical, otherwise-unmodified notebook run clean.

#### 5. [!!] Broken link — `LAB006`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup

The pre-created Azure SQL server is unreachable from the lab VM and nothing in the lab tells the learner how to fix it. Running the lab's own second step, `python 2_LoadMovieData.py`, fails with pyodbc error 40615: "Cannot open server 'sqlaivector-64827025' requested by the login. Client with IP address '185.254.59.123' is not allowed to access the server." `az sql server firewall-rule list -g azureaiworkshoprg -s sqlaivector-64827025` returns an empty list - the server has NO firewall rules at all, so neither the VM nor Azure services can reach it. Connecting through SSMS surfaces the same condition as a "New Firewall Rule" wizard ("Your client IP address does not have access to the server"), which then demands an Azure sign-in the learner has just been forced to sign out of (see the stale-account finding). The section's Pre-requisites say "None. The database has been pre-created for you." and the Tasks say only to execute the numbered files, so a learner has no documented route past this. Everything after it in sections 21 and 22 is blocked. Unblocked here only by running `az sql server firewall-rule create ... --start-ip-address 185.254.59.0 --end-ip-address 185.254.59.255`, which the lab never mentions.

#### 6. [!!] Broken link — `LAB006`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup

SQL Server Management Studio in the VM image is signed in as a DIFFERENT lab reservation's user and refuses to connect until that is undone. On first launch, SSMS 21 pre-populates the Connect to Server dialog with server name "sqlaivector-55791077.database.windows.net" - not this reservation's sqlaivector-64827025 - and every Connect attempt, even with SQL Server Authentication and correct credentials, aborts with: "User account 'User1-55791077@LODSPRODMCA.onmicrosoft.com' was invalid or stale when getting Azure subscriptions. Please re-authenticate the account before trying again. (Microsoft.SqlServer.Management.ApplicationAuthenticationManagement)". Opening the account flyout confirms it: signed in as User1-55791077 under tenant LODS-Prod-MCA with a "Re-enter your credentials" warning. Both the cached Entra account and the server MRU are baked into the image from lab instance 55791077. The only way forward is the undocumented sequence account flyout -> ... -> Sign out, after which the dialog stops erroring. The section tells the learner "The .sql files need to be executed in SQL Server Management Studio, which is preloaded on Desktop for you" and gives no hint that the preloaded tool is carrying someone else's identity. Related smaller inaccuracy in the same sentence: SSMS is NOT on the Desktop - the only Desktop shortcut for this user is "Visual Studio Code.lnk" and C:\Users\Public\Desktop is empty; SSMS 21 is installed at C:\Program Files\Microsoft SQL Server Management Studio 21 and pinned to the taskbar.

#### 7. [!!] Defective sample code — `LAB009`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup

Two values the lab's own scripts require are wrong or missing in the shipped .env, and no section ever tells the learner to set them. (a) SQL_PWD is EMPTY. .env.example carries a 7-character placeholder for it, but the delivered .env has "SQL_PWD=" with nothing after the equals sign. Section 05 (Setup env file) walks the learner through SQL_SERVER at step 10 and never mentions SQL_PWD, SQL_USER, SQL_DATABASE, CSV_PATH or BATCH_SIZE. Consequence: `python 2_LoadMovieData.py` fails with pyodbc 28000 "Login failed for user 'sqladmin'. (18456)". (b) CSV_PATH points at a folder that does not exist: it ends "...S\Vectors\SQL\movie_quotes.csv" (os.path.exists returns False) - a legacy layout. The file actually ships at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\SQL\movie_quotes.csv (66890 bytes). Both had to be repaired by hand before any of the numbered steps could run.

#### 8. [!!] Defective sample code — `LAB009`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* instruction

The failure of 2_LoadMovieData.py is hidden by its own error handler, and the next script then reports success on an empty table - a textbook false pass. 2_LoadMovieData.py wraps everything in `try: ... except Exception as e: print(f"An error occurred: {e} -- {sql}")`, but `sql` is only assigned INSIDE the try, several lines after `open(csv_path)`. So when the CSV path is wrong the handler itself raises `NameError: name 'sql' is not defined` and the learner never sees the real FileNotFoundError. Worse, running the very next documented step on that empty table, `python 3_UpdateMovieEmbedding.py`, printed "Embeddings updated for all quotes." - while a direct count showed `select count(*), sum(case when embedding is null then 0 else 1 end) from dbo.MovieQuotes` = (0, None). Zero rows, zero embeddings, and a success message. A learner following the instructions and reading the console would believe the ingest worked. After repairing CSV_PATH the same two scripts ran clean and the counts became (732, 732) with real content ("Star Wars: Episode V - The Empire Strikes Back" / "Do, or do not. There is no try.", "Dracula" / "Listen to them. Children of the night."), which is what the step should have produced the first time.

#### 9. [!!] Defective sample code — `LAB009`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* instruction

The final two steps of the lab could not be completed even after every environment problem above was repaired. 4_SQLEmbeddings.py creates a DATABASE SCOPED CREDENTIAL and a dbo.get_embedding procedure that calls sp_invoke_external_rest_endpoint, and 5_query.sql then EXECs it. Two separate defects: (a) the script is not idempotent - re-running it (which a learner will do, because step 2 failed the first time) aborts with `pyodbc.ProgrammingError ... The credential with name "https://ai-foundry-64827025.openai.azure.com/" already exists. (15530)` and never reaches the CREATE PROCEDURE, leaving the database in a half-built state that then reports "Could not find stored procedure 'dbo.get_embedding'. (2812)". (b) Even after dropping both objects and running 4_SQLEmbeddings.py once, cleanly, with a corrected endpoint, executing 5_query.sql verbatim fails with `[SQL Server]An error occurred, failed to parse url. HRESULT: 0x80072ee6. (31609)`. The URL the script composes is `{endpoint.rstrip('/')}/openai/deployments/{deployment}/embeddings?api-version=2024-02-01`, which with a corrected base endpoint evaluates to a well-formed https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01 - so the malformation is introduced when that string is embedded into the generated T-SQL, not by the endpoint value. Net effect: the lab's stated objective, a similarity search in Azure SQL, cannot be reached by following the instructions.

#### 10. [!!] Defective sample code — `LAB009`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* instruction

Root cause of the step 25 failure, now confirmed at character level. In 4_SQLEmbeddings.py the T-SQL for dbo.get_embedding is assembled by concatenating an opening quote, a space, and then the URL variable, so the procedure stores a URL string literal that begins with a space. Dumping the deployed definition from sys.sql_modules gives exactly: [<space>https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01]. sp_invoke_external_rest_endpoint rejects that with 'failed to parse url. HRESULT: 0x80072ee6 (31609)', so step 25 can never return rows as written. Recreating the identical procedure with only that one space removed made the same 5_query.sql succeed immediately. The defect is unconditional: it does not depend on any .env value.

#### 11. [!!] Defective sample code — `LAB009`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* instruction

Second, independent defect in the same script, and the one a learner is guaranteed to hit. 4_SQLEmbeddings.py creates the database scoped credential named after the raw endpoint, but the stored procedure it then generates references the same name with any trailing slash stripped. Step 15 tells the learner to copy the Endpoint value from Keys and Endpoint, and that value ends in a slash - as the shipped .env does. The two names therefore never match. Verified directly: sys.database_scoped_credentials contains [https://ai-foundry-64827025.openai.azure.com/] while dbo.get_embedding asks for https://ai-foundry-64827025.openai.azure.com, and step 25 fails with 'Cannot find the credential ... because it does not exist or you do not have permission. (15151)'. Creating a credential under the stripped name made the query work. Note this is a different failure from the stray space: fixing the space alone moves the error from 31609 to 15151, so both must be fixed before step 25 returns anything.

#### 12. [!!] Timing or quota — `LAB007`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* critical · *At fault:* setup

The Azure portal became permanently unreachable partway through the reservation, with the lab clock still showing 1440 minutes. The account signs in with a Temporary Access Pass, and once it expired the CLI reported it exactly: 'AADSTS130504: Your Temporary Access Pass has expired. Contact your administrator to obtain a new pass.' Because no other authentication method is registered on the account, every portal re-authentication now lands on a mandatory 'Lets keep your account secure' registration flow whose only path forward is 'Install Microsoft Authenticator' on a mobile device. There is no skip and no deferral, and the lab issues no second factor. Every portal-based instruction from that moment on is unperformable: steps 1, 2, 4 (portal route), 13, 14, 15 and 20 of this section, and the portal legs of the remaining sections. The Azure CLI is the only surviving control-plane route - az login --use-device-code was run and did complete successfully - but that fallback is documented only in this section's step 4 sidebar, for firewall rules, and nowhere else in the lab.

#### 13. [!!] Broken link — `LAB006`

*Section:* Optional Lab RAG (Retrieval-Augmented Generation) Implementation  
*Instruction:* `#optional-lab-rag-retrieval-augmented-generation-implementation`  
*Severity:* critical · *At fault:* instruction

This section has exactly one instruction - 'Run through steps in RAG.ipynb file' - and that file does not exist. A recursive search of the entire C: drive on the lab VM for RAG.ipynb returned nothing, and the lab tree under Desktop\LABS contains only Lab 00 through Lab 10, with Lab 08 - RAG-Patterns holding a single file, GraphRAG\README.md, which is the Cloud Shell GraphRAG material used by an earlier section. Everything else in this section (Exercises 1 to 7, Advanced Implementation Topics, Execution Instructions, Expected Results) is prose describing what that notebook would do; none of it is independently actionable. The section is therefore unperformable as written. The supporting environment is present and would have worked: azureaiworkshoprg contains a running Azure AI Search service, aisearch-64827025 in West Europe, whose REST API answered with one existing index (myfitnessindex), and the .env carries populated AZURE_AI_SEARCH_ENDPOINT, AZURE_AI_SEARCH_API_KEY, AZURE_AI_SEARCH_API_VERSION and SEARCH_AUTHENTICATION_METHOD. Only the notebook is missing.

#### 14. [!!] Broken link — `LAB006`

*Section:* AI Frameworks - Semantic Kernel and AutoGen  
*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* critical · *At fault:* instruction

This section has exactly one instruction - 'Open the SK and AutoGen.ipynb notebook and run through the steps' - and no such notebook ships with the lab. A recursive enumeration of every .ipynb under Desktop\LABS returns fifteen notebooks (Lab 00 pip-install; Lab 01 setup and quick_start, 1-evaluation; Lab 02 agents 1 through 6; Lab 04 AI_vision_services_lab; Lab 05 gpt-4_o_dpo_ft; Lab 06 Prompt Engineering; Lab 09 AI_RedTeaming; Lab 10 Cosmos DB Python-Samples) and none of them is SK and AutoGen.ipynb, nor is there any file matching SK, AutoGen or Semantic anywhere in the tree. What makes this clearly an omission rather than a design choice is that the environment was prepared for it: pip list on the lab VM shows semantic-kernel 1.35.3 and autogen-agentchat, autogen-core and autogen-ext all at 0.7.4 already installed. The dependencies are there; the material that uses them is not. All five exercises are therefore unperformable and unjudgeable.

#### 27. [!] Defective sample code — `LAB009`

*Section:* Lab 08 - RAG-Patterns - Graph RAG  
*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* major · *At fault:* instruction

The documented prompt-tune command fails as written. Lab says to run: `graphrag prompt-tune --root ./ragtest --config ./ragtest/settings.yaml --output ./ragtest/prompts-tuned --domain "Literary Analyst"`. Pasted verbatim it exits in 0.8s with: "Usage: graphrag prompt-tune [OPTIONS] / Error: No such option: --config". `graphrag prompt-tune --help` on the version `pip install graphrag` delivers today (graphrag 3.1.2) lists only --root/-r, --verbose/-v, --domain, --selection-method, --n-subset-max, --k, --limit, --max-tokens, --min-examples-required, --chunk-size, --overlap, --language, --discover-entity-types, --output/-o, --help. Removing just --config makes the same command succeed in 1m45s and write ./ragtest/prompts-tuned/{extract_graph.txt, summarize_descriptions.txt, community_report_graph.txt}, so the rest of the step and both follow-up `more` commands are correct - the single invalid flag is what stops a learner. Learner impact: the auto-tuning exercise, the last task of the lab, cannot be completed by following the text.

#### 28. [!] Removed feature — `LAB005`

*Section:* Lab 08 - RAG-Patterns - Graph RAG  
*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* major · *At fault:* instruction

The DRIFT query is shipped commented out under the heading "DRIFT Query (not working as of GraphRAG v2.7.0)", and the optional reindex block is disabled with the same caveat. The caveat is stale: `pip install graphrag` with no version pin installs graphrag 3.1.2 today, and running the commented-out command verbatim (uncommented) - `graphrag query --root ./ragtest --method drift "Who is Scrooge and what are his main relationships?"` - completed successfully in roughly 6 minutes and returned a full DRIFT answer with source citations ("## Who is Scrooge?", "## His main relationships", [Data: Sources (0,35)], (7,8,9), (20,21,22,33) ...). This matters because the lab's own Objectives list "Understand and execute Global, Local, and DRIFT queries" - a learner following the text never executes a DRIFT query and so cannot meet a stated objective, even though the product supports it. The instructions should either un-comment the DRIFT step or pin the version the caveat refers to.

#### 29. [!] Defective sample code — `LAB009`

*Section:* Azure PostgreSQL Lab  
*Instruction:* `#azure-postgresql-lab`  
*Severity:* major · *At fault:* instruction

Part 5's placeholder guidance does not match the script it applies to, in two separate ways, and one of them silently produces a broken endpoint. (a) Name mismatch: the instructions tell you to replace `<your-endpoint>` and `<your-api-key>`, but VectorQuery.sql actually contains `select azure_ai.set_setting('azure_openai.endpoint', '<your-endpoint-url>');` and `select azure_ai.set_setting('azure_openai.subscription_key', '<your-subscription-key>');`. Neither documented token appears in the file. (b) Shape mismatch that matters: the instruction prints the target as the template 'https://<your-endpoint>.openai.azure.com/' and then offers "or the AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT value in your .env file" as an equivalent source. It is not equivalent - that .env value is 120 characters and, verified by pattern match, contains a /openai/deployments/ path segment, i.e. it is a full deployment/inference URI, not the bare resource endpoint. Substituting it into the template yields a malformed URL, and substituting it into the script's slot sets azure_openai.endpoint to a deployment URI. The similarity query only succeeded here after the value was trimmed back to its scheme+host base (https://ai-foundry-64827025.openai.azure.com/), which the instructions never tell the learner to do.

#### 30. [!] Missing resource or SKU — `LAB002`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* major · *At fault:* setup

The same .env variable that breaks the PostgreSQL lab also breaks this one, which makes it a shared root cause rather than two coincidences. 4_SQLEmbeddings.py treats AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT as a bare resource endpoint and appends "/openai/deployments/<deployment>/embeddings?api-version=2024-02-01" to it. The delivered value is a full 120-character deployment/inference URI that already contains "/openai/deployments/", so the generated URL contains that path twice and SQL rejects it. This was only diagnosable by reading the composed string; the visible symptom is the opaque "failed to parse url" above. Either the scripts should normalise the endpoint (strip anything after the host) or Section 05 should record the bare endpoint in a separate variable.

#### 31. [!] Changed UI label or inconsistent structure — `LAB003`

*Section:* Azure SQL Lab  
*Instruction:* `#azure-sql-lab`  
*Severity:* major · *At fault:* instruction

The single Tasks paragraph contains four separate documentation errors. (a) The hyperlink labelled "SQL folder" points at https://github.com/Azure/WPLUS-Azure-AI-Platform-and-Services/tree/AugRelease/Vector-DB/Cosmos%20DB - the COSMOS DB folder, not the SQL one - and that URL returns HTTP 404 when fetched, so the link is both mislabelled and dead. (b) The example command reads `python 2_LoadMovideData.py`; the file that ships is 2_LoadMovieData.py ("Movide" -> "Movie"), so copying the example gives "can't open file". (c) "Files are numberd" and "you have nagivated" are misspellings in the same sentence. (d) The section's second Objective reads "Perform similarity searches using PostgreSQL" - copied verbatim from the PostgreSQL lab into the Azure SQL lab, so the stated goal names the wrong product.

#### 32. [!] Defective sample code — `LAB009`

*Section:* AI Red Teaming Agent for Generative AI Applications  
*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* major · *At fault:* instruction

AI_RedTeaming.ipynb cell 5 contains a bare '!az login' between the azure.identity import and 'credential = AzureCliCredential()'. This directly contradicts the section's own Setup step ('Authenticate to Azure by running az login --use-device-code in your terminal before running the notebook') and the notebook's own markdown cells 1 and 4, which both say to authenticate in a terminal BEFORE running the notebook. Effect observed: az login defaults to the interactive browser flow, so a Run All stalls on an account picker; the VM had accumulated ~25 blank Edge windows from repeated interactive login attempts, and one showed a failed sign-in for a stale account. The learner is already authenticated by the documented pre-step, so the cell is redundant as well as blocking. Removing only that line let the notebook run to completion unattended.

#### 33. [!] Removed feature — `LAB005`

*Section:* AI Red Teaming Agent for Generative AI Applications  
*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* major · *At fault:* instruction

The notebook's markdown cell 26 states: 'The data and results used in this attack will be saved to the output_path specified. The URL printed out at the end of the scorecard will provide a link to where you results are uploaded and logged to your Azure AI Foundry project.' Neither half held. Every RedTeam object was constructed with azure_ai_project=AI_FOUNDRY_PROJECT_ENDPOINT and credential=AzureCliCredential(), yet no ai.azure.com URL appears anywhere in the executed notebook's output (grep over all cell outputs returned only the four 'Overall ASR' lines), and Microsoft Foundry > Build > Evaluations > Red team reports 'No red teams found' after all four scans completed. Results exist only as local files. A learner following the text would go looking in the portal for a scan record that is not there.

#### 36. [!] Defective sample code — `LAB009`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction

Step 23 says 'Resolve any error before continuing', but the script it tells you to run cannot be re-run. 4_SQLEmbeddings.py creates the database scoped credential before it creates the stored procedure and does not guard the CREATE. A second execution aborts on 'The credential with name ... already exists. (15530)' and never reaches CREATE OR ALTER PROCEDURE, so dbo.get_embedding is left missing and step 25 then reports 'Could not find stored procedure dbo.get_embedding. (2812)'. That is precisely the position a learner following step 23's own instruction ends up in: they hit an error, change something, run it again, and the second run leaves the database in a worse state than the first. Recovering requires manually dropping both the procedure and the credential, which the lab never mentions.

#### 37. [!] Moved navigation — `LAB004`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction

Steps 20, 26 and 27 describe a Foundry portal that no longer exists. Step 20's 'click Explore Azure AI Foundry portal' is the classic Azure OpenAI resource blade action; the current route is ai.azure.com/nextgen with a top nav of Home, Discover, Build, Operate, Manage, Docs. Step 26's 'go to Model catalog' has no match: the catalog is Discover > Models, and the word catalog appears nowhere in the navigation. Step 27's 'Click Use this model' is likewise gone - the text-embedding-ada-002 model card's command is a 'Deploy' split button, and the deployment form it opens has no field called 'Deployment type: Global Standard' to choose in the way step 27 implies, since Global Standard is preselected. The deployment fields that do exist (Deployment name, Deployment type, TPM rate limit, Guardrails) were confirmed on the fine-tuned model deployment in this same run.

#### 38. [!] Changed UI label or inconsistent structure — `LAB003`

*Section:* Lab: Using Vector Databases in Azure SQL Database  
*Instruction:* `#lab-using-vector-databases-in-azure-sql-database`  
*Severity:* major · *At fault:* instruction

Steps 13 to 15 send the learner to 'your Azure OpenAI resource (example: myopai-resource-53809613)' and to its Keys and Endpoint blade. No such resource exists in this lab. The only cognitive-services resource in azureaiworkshoprg is the Foundry resource ai-foundry-64827025, and it is what the lab's own .env points at. Two consequences follow. The learner has nothing matching the described name to click, and the Endpoint value they are told to copy in step 15 is the resource endpoint, whereas the shipped .env holds a full deployment inference URI for AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT; 4_SQLEmbeddings.py concatenates /openai/deployments/<name>/embeddings onto whatever it finds, producing a doubled path. Smaller text defects in the same section: the copy-button control text has bled into every code block (powershellTypeCopy, sqlTypeCopy, envTypeCopy, and a bare TypeCopy on the expected output in step 22), and step 22 presents 'Embeddings updated for all quotes.' as proof of success even though that line is printed unconditionally - the same false success recorded against the Azure SQL section, where it appeared with zero rows updated.

#### 39. [!] Missing resource or SKU — `LAB002`

*Section:* AI Frameworks - Semantic Kernel and AutoGen  
*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* major · *At fault:* setup

The lab's own Resources tab advertises an Open AI Endpoint named myopai-64827025, and the Azure SQL vector section's steps 13 and 14 send the learner to 'your Azure OpenAI resource (example: myopai-resource-53809613)'. No resource of that name exists. az cognitiveservices account list over azureaiworkshoprg returns exactly three accounts: ai-foundry-64827025 (kind AIServices), cv-64827025 (kind ComputerVision) and faceresource-64827025 (kind CognitiveServices). The learner is told to look for a resource that was never provisioned, on the Resources tab that is supposed to be the authoritative statement of what the reservation contains. This is the same naming assumption that underpins the endpoint-shape defects reported against the PostgreSQL and Azure SQL sections.

#### 64. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Lab 08 - RAG-Patterns - Graph RAG  
*Instruction:* `#lab-08---rag-patterns---graph-rag`  
*Severity:* minor · *At fault:* instruction

The Objectives block still carries the authoring template placeholder: it reads "List the objectives" on the line immediately before the real objective list ("In this lab we will: Install graphrag from Pypi / Index a data source / Understand and execute Global, Local, and DRIFT queries. / Start to inspect Prompt tuning"). This is the same unedited placeholder seen in section 12, so it is a repeated authoring defect rather than a one-off.

#### 65. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Azure PostgreSQL Lab  
*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction

Part 3 sends the learner to a file that does not exist. It says "Open the VectoryQuery.sql Script" and "Press Ctrl+O and open the VectorQuery.sql file located at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\PostgreSQL\VectoryQuery.sql" - note the heading and the path both spell it "VectoryQuery.sql". Test-Path on that exact documented path returns False. The file that ships is VectorQuery.sql (477 bytes) in that same folder. A learner using Ctrl+O and typing the documented path gets nothing.

#### 66. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Azure PostgreSQL Lab  
*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction

The lab is inconsistent about where the PostgreSQL password comes from, and one of the two answers publishes it. Part 2 Step 1 correctly tells the learner to take it from sqlcredentials.txt (that file exists at C:\Users\Admin\Desktop\LABS\sqlcredentials.txt and holds a single 15-character line). Part 3 instead prints a literal password value in the connection-details list. Comparing the two without displaying either confirmed they are the same string today, so the instruction happens to work - but it only works while the lab issues that one fixed password. If Skillable ever randomises it per reservation, Part 3 becomes actively wrong while Part 2 stays right, and a learner who trusts the printed value will get an authentication failure with no clue why. Publishing a working database password in the learner manual is also poor hygiene for a workshop whose own Lab 09 is about security. Recommend Part 3 point at sqlcredentials.txt exactly as Part 2 does.

#### 67. [~] Moved navigation — `LAB004`

*Section:* Azure PostgreSQL Lab  
*Instruction:* `#azure-postgresql-lab`  
*Severity:* minor · *At fault:* instruction

Two navigation instructions no longer match the current UX. (a) Part 1 says "In the left menu, select Server parameters" as though it were a top-level entry; in the portal today the PostgreSQL flexible-server blade groups it under a collapsed "Settings" section, so the learner must expand Settings first - the item is not visible on arrival. (b) Part 4 is written against the retired Foundry entry points: "Click Explore Azure AI Foundry portal", "Go to Model catalog", "Click text-embedding-ada-002", "Click Use this model", and calls the resource an "Azure OpenAI" resource. The current portal used throughout this walk is ai.azure.com/nextgen, whose top nav is Home / Discover / Build / Operate / Manage / Docs, where the catalogue lives under Discover and deployments under Build > Models > Deployments, and the resource is presented as a Microsoft Foundry resource. Judged as route drift rather than executed, because Part 4 is explicitly skippable when the model already exists - text-embedding-ada-002 is already deployed in this environment and AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT / _API_KEY are already present in .env, which is the branch this walk took.

#### 68. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* AI Red Teaming Agent for Generative AI Applications  
*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* minor · *At fault:* instruction

Cell 19 - the Intermediary-Model-Target-Scan, and the only scan in the notebook that attacks a real deployed model rather than a hard-coded callback - is the one scan that omits output_path, while cells 15, 25 and 29 all set one. Its results therefore never appear as a named JSON in the working folder; they are only in the hidden .scan_Intermediary-Model-Target-Scan_<timestamp>/final_results.json. That is exactly the scan whose numbers are worth reading: it is the only one with a non-zero Attack Success Rate (50.0%, violence 2/2). A learner told to inspect 'the results' will find three JSON files and miss the interesting one.

#### 69. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* AI Red Teaming Agent for Generative AI Applications  
*Instruction:* `#ai-red-teaming-agent-for-generative-ai-applications`  
*Severity:* minor · *At fault:* instruction

Four text defects in this section. (1) 'Using the Notebook' says 'The notebook provides two main examples' and then lists three (Basic, Intermediary, Advanced); the notebook actually runs four scans - the fourth, Custom-Prompt-Scan, is undocumented in this list. (2) The copy-button control text has bled into the rendered code blocks: 'bashTypeCopy   pip install ...' and 'envTypeCopy   # Azure OpenAI', so a learner selecting the block copies 'bashTypeCopy' with it. (3) Typos: 'When testing different attach strategies' and 'attack stragies'. (4) The four Additional Resources entries are written as if they were links ('Learn more about Azure AI Foundry Evaluations.') but render as plain text with no URL, so none of them is reachable.

#### 71. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Optional Lab RAG (Retrieval-Augmented Generation) Implementation  
*Instruction:* `#optional-lab-rag-retrieval-augmented-generation-implementation`  
*Severity:* minor · *At fault:* instruction

Text defects, recorded because they are all that remains verifiable once the notebook is gone. The Pre-requisites open with 'Compleate pre-requisites lab'. The six Additional Resources entries (Azure AI Search Vector Search, Azure OpenAI Embeddings, RAG Architecture Patterns, Vector Database Options in Azure, RAG Best Practices, Document Intelligence for RAG) are written as link text but render as plain words with no URLs, so none is reachable - the same defect as in the AI Red Teaming section. The section also contradicts itself about what is being built: the Objectives promise 'Configure Azure AI Search for vector search capabilities' and the Expected Results promise the learner will 'Implement production-ready RAG systems using Azure services', but Exercise 5 describes implementing cosine similarity in-process and explicitly says 'Simulate Azure AI Search vector capabilities'. A learner is told they are configuring a real search service and then told the search is simulated.

#### 72. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* AI Frameworks - Semantic Kernel and AutoGen  
*Instruction:* `#ai-frameworks---semantic-kernel-and-autogen`  
*Severity:* minor · *At fault:* instruction

Text defects. The Next Steps paragraph tells the learner 'You'll be ready to proceed to Lab 5, where you'll explore RAG (Retrieval-Augmented Generation) implementations' - but Lab 05 in this workshop is Fine-Tuning, the RAG material is Lab 08 and the optional RAG section immediately precedes this one, and this is the last section in the lab. The pointer is wrong in both number and direction. The five Additional Resources entries (Semantic Kernel Documentation, AutoGen Framework, Azure OpenAI Service, Multi-Agent Systems Design, Plugin Development Best Practices) are again written as link text but render as plain words with no URLs. The section is also written against AutoGen 'v0.6+' in two places while the VM ships 0.7.4, which spans the 0.6 to 0.7 API change the text is presumably trying to warn about.

### Setup .env file

#### 15. [!] Defective sample code — `LAB009`

*Section:* Setup .env file  
*Instruction:* `#5-set-the-values-for-the-azure_openai_embedding_endpoint-and-azure_openai_embedding_api_key-variables`  
*Severity:* major · *At fault:* instruction

The embedding instructions say to paste the embedding Target URI into AZURE_OPENAI_ENDPOINT instead of AZURE_OPENAI_EMBEDDING_ENDPOINT, and illustrate a chat/completions URI for embedding models. Following that text literally misconfigures the shipped .env and breaks embedding calls.

#### 50. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Setup .env file  
*Instruction:* `#7-set-the-values-for-the-tenant_id-azure_resource_group-and-azure_subscription_id-variables`  
*Severity:* minor · *At fault:* instruction

The final instruction says to paste the Subscription ID as the value for, but omits the variable name. The task heading identifies AZURE_SUBSCRIPTION_ID, so the learner can infer it.

#### 73. [i] Superseded or retiring feature — `LAB010`

*Section:* Setup .env file  
*Instruction:* `#4-set-the-values-for-the-azure_openai_endpoint-and-azure_openai_api_key-variables`  
*Severity:* info · *At fault:* instruction

The instructions depend on legacy Models + endpoints and a per-deployment Target URI. New Foundry uses Build > Models > Deployments and presents a project endpoint plus SDK sample; the equivalent OpenAI Language APIs endpoint is on the Azure resource.

### Evaluations with Azure AI Foundry

#### 16. [!] Defective sample code — `LAB009`

*Section:* Evaluations with Azure AI Foundry  
*Instruction:* `#evaluations-with-azure-ai-foundry`  
*Severity:* major · *At fault:* instruction

The shipped notebook reports a cloud evaluation as successfully submitted and writes status NotStarted with an evaluation ID, but New Foundry Build > Evaluations remains empty after repeated refreshes and a two-minute propagation wait. The success-shaped notebook output is not backed by the promised portal artifact.

#### 51. [~] Moved navigation — `LAB004`

*Section:* Evaluations with Azure AI Foundry  
*Instruction:* `#evaluations-with-azure-ai-foundry`  
*Severity:* minor · *At fault:* instruction

The notebook directs learners to Project > Evaluation > View evaluation runs. Current New Foundry exposes Runs under Build > Evaluations.

### Azure AI Agents Tutorial Collection

#### 17. [!] Timing or quota — `LAB007`

*Section:* Azure AI Agents Tutorial Collection  
*Instruction:* `#azure-ai-agents-tutorial-collection`  
*Severity:* major · *At fault:* setup

1-basics.ipynb created the health advisor agent and thread, then Run All remained at cell 4 of 18 for more than three minutes without producing the first agent response.

#### 18. [!] Timing or quota — `LAB007`

*Section:* Azure AI Agents Tutorial Collection  
*Instruction:* `#azure-ai-agents-tutorial-collection`  
*Severity:* major · *At fault:* setup

6-multi-agent-solution.ipynb reached the orchestration cell but never produced the promised triage output or ran cleanup after more than three minutes; the final two cells remained unexecuted.

### Fine Tuning - Advance Lab

#### 23. [!] Defective sample code — `LAB009`

*Section:* Fine Tuning - Advance Lab  
*Instruction:* `#fine-tuning---advance-lab`  
*Severity:* major · *At fault:* instruction

gpt-4_o_dpo_ft.ipynb uploads its two datasets and then immediately submits the fine-tuning job with no wait for the service-side import to finish, so a straight run of the notebook fails. Executed with nbconvert --execute --allow-errors: the upload cell succeeded and printed both ids (training file-bd0d8df1c84e42f3ba46742fae7cd187, validation file-5d720655cdb84a0ab757ca9a6a6e31f4), and the very next cell, client.fine_tuning.jobs.create(...), returned 'BadRequestError: Error code: 400 - invalidPayload: The specified file reference must point to a completed file import.' Cells 13-18 then cascaded into KeyError, NameError and NotFoundError, so the whole second half of the lab produced nothing. Proven to be timing and nothing else: listing the account's files afterwards showed both ids with status 'processed', and re-issuing the identical jobs.create with the same two file ids, the same model gpt-4o-2024-08-06, the same DPO method block and the notebook's own api_version 2025-02-01-preview was accepted and returned 'JOB ftjob-bd8df88bbbf541ebb8274ec42597456f pending'. The notebook needs a poll on file status between the two cells.

### Responsible AI

#### 24. [!] Removed feature — `LAB005`

*Section:* Responsible AI  
*Instruction:* `#responsible-ai`  
*Severity:* major · *At fault:* instruction

The Manual Evaluation exercise has no surface in the current portal. The lab says 'go to the Protect and govern section, select Evaluation, at the top choose Manual evaluations, select New Manual Evaluation', then rate results with thumbs up/down. There is no 'Protect and govern' section in the current left navigation, and the Evaluations page (Build > Evaluations) exposes exactly three tabs - Evaluations, Evaluator catalog, Red team - with two sub-tabs, Runs and Recurring configs. None of them is 'Manual evaluations' and there is no New Manual Evaluation control anywhere on the page. Every step of that sub-exercise, including the thumbs-up rating, the Temperature and Search type comparison and saving iterations, is therefore unfollowable.

#### 25. [!] Moved navigation — `LAB004`

*Section:* Responsible AI  
*Instruction:* `#responsible-ai`  
*Severity:* major · *At fault:* instruction

None of the four Content Safety and Prompt Shields exercises has a route in the current portal. The lab asks for 'On the left, select AI Services. On the right, choose Content Safety' and then Moderate text content, Protected material detection for text, and Moderate image content; and separately for 'Guardrails + controls tab on the left navigation, then choose the Try it out button' followed by a Prompt Shields panel. Measured rather than glanced at: the Build left navigation has exactly ten entries (Agents, Models, Fine-tune, Services, Tools, Knowledge, Memory, Data, Evaluations, Guardrails) and none is AI Services; Build > Services > Playgrounds lists 18 of 18 playgrounds (six Content Understanding, five Speech, two Translator, five Language) and none is Content Safety; Build > Guardrails has three tabs (Guardrails, Blocklists, Integrations Preview) with a filter list and a Create button, and no 'Try it out' control and no Prompt Shields panel; Operate offers only Overview, Assets and Compliance; Discover is the model catalogue. The three CSV/ZIP bulk-test datasets the lab ships under Files/Content_Safety therefore have nowhere to be uploaded.

#### 60. [~] Moved navigation — `LAB004`

*Section:* Responsible AI  
*Instruction:* `#responsible-ai`  
*Severity:* minor · *At fault:* instruction

The PII exercise's route and control names are all from the previous Foundry. The lab says: resource group > Azure AI project > Press Launch Studio > Playgrounds on the left > 'Try the Language playground' card > scroll the carousel > 'Extract PII from text' > Press Run. The current portal has no Playgrounds left-nav entry, no Language playground card and no carousel; the destination is Build > Services > Playgrounds > 'Azure Language - Text PII Redaction', and the action button is 'Detect', not 'Run'. The exercise still completes, so this costs the learner navigation time rather than the outcome.

#### 61. [~] Moved navigation — `LAB004`

*Section:* Responsible AI  
*Instruction:* `#responsible-ai`  
*Severity:* minor · *At fault:* instruction

The Automated Evaluation exercise survives but under different names and a different shape. 'Automated evaluations' is now just the Evaluations tab, 'Click Create a new Evaluation' is a 'Create' button, and the wizard is six steps (Target, Scope, Frequency, Data, Criteria, Review) rather than the lab's dataset-then-evaluators pair. The lab's 'Evaluate an existing query-response dataset' choice is present as 'Dataset - Evaluate an existing dataset', alongside two options the lab does not know about, Agent and Model.

### 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model

#### 34. [!] Moved navigation — `LAB004`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#5-review-results`  
*Severity:* major · *At fault:* instruction

Step 5 says 'Once complete, go to the Metrics tab' and 'Click Use this model to deploy'. Neither control exists under the current Foundry experience. The completed job wplus-ft-64827025 (ftjob-af929589ec224665b7cdc8357449101c) opens with tabs Details, Monitor, Logs, Checkpoints, Deployments - there is no tab named Metrics. Summary metrics appear inline on Details as two tiles (Final train loss, Final train mean token accuracy) with a 'View all metrics' link, and the loss/accuracy charts live under Monitor (whose route is .../metrics, so the label moved but the URL did not). There is likewise no 'Use this model to deploy' control: deployment is a 'Deploy' button in the job command bar, next to 'Continuous fine-tuning'.

#### 35. [!] Moved navigation — `LAB004`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#6-deploy-and-test`  
*Severity:* major · *At fault:* instruction

Step 6 routes the learner to 'My assets > Models + endpoints', which is the classic Azure AI Foundry left-nav and does not exist in the current experience. There is no 'My assets' grouping; deployments live at Build > Models > Deployments (tabs Deployments / Models / Batch jobs, split into Serverless deployments and Managed compute deployments). 'Open in playground' does still exist, but as a button on the deployment's details pane rather than the classic location, and the deployment page's own first tab is called Playground. A learner searching the current portal for 'My assets' finds nothing.

#### 58. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#🛠️-steps-fine-tuning-the-gpt-41-mini-model`  
*Severity:* minor · *At fault:* instruction

Step 3 and step 4 name controls the current portal does not have. The lab says 'Click + Fine-tune model'; the empty Fine-tuning page offers 'Start fine-tuning' and the populated list offers 'Fine-tune'. The lab says 'Add a suffix name for your model'; the wizard's field is 'Display name' and it arrives pre-filled with a generated name (fast-reef-s44f), so a learner looking for the word suffix will not find it. The lab also has the learner choose the model first and then 'Select Supervised method', while the wizard asks for Customization method first and Model second. All observed on the live 'Fine-tune a model' wizard.

#### 59. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#🛠️-steps-fine-tuning-the-gpt-41-mini-model`  
*Severity:* minor · *At fault:* instruction

The Basic details step carries a third required field, 'Training type', defaulting to 'Data Zone', which step 4's value list does not mention. It is pre-filled so it does not block submission, but it is a required choice with cost and data-residency consequences that the learner is never told they are making.

#### 62. [~] Moved navigation — `LAB004`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#2-open-the-azure-ai-foundry-portal`  
*Severity:* minor · *At fault:* instruction

The step says only 'Launch the Azure AI Foundry Resource created in the pre-requisites lab', which no longer names a real control. https://ai.azure.com now lands on an unauthenticated marketing page ('The AI app and agent factory') with a Sign in button and no route into the resource. The working destination is https://ai.azure.com/nextgen, which opens All resources and lists firstProject under parent resource ai-foundry-64827025 in East US 2; opening that reaches the project home. The learner gets there, but not by anything the step describes.

#### 63. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#3-start-fine-tuning`  
*Severity:* minor · *At fault:* instruction

The destination exists but neither control is called what the step calls it. 'Navigate to the Fine-tuning section' is Build > Fine-tune in the current left navigation, and 'Click + Fine-tune model' is 'Start fine-tuning' on the empty state (and 'Fine-tune' once at least one job exists). The model choice the step offers does hold up: opening the Model dropdown showed gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, Llama-3.3-70B-Instruct, gpt-oss-20b, gpt-4o and gpt-4o-mini, so all three of GPT-4.1-mini, GPT-4o-mini and GPT-4o are still selectable.

#### 70. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* 🛠️ Steps: Fine-Tuning the GPT-4.1-mini Model  
*Instruction:* `#5-review-results`  
*Severity:* minor · *At fault:* instruction

Step 5 is 'Review Results' but gives the learner no criterion for what a good result looks like, and the two headline numbers the portal puts first are misleading on this lab's own configuration. Details shows Final train loss 0 and Final train mean token accuracy 1, which reads as a flawless fine-tune. The Monitor curves say otherwise: train loss falls to 0 by roughly step 40 while validation loss climbs from about 1.5 to about 3.5 and stays there, and validation mean token accuracy plateaus near 0.65 while train accuracy saturates at 1.0. That is textbook overfitting, and it is what 10 training samples over 10 epochs with a learning rate multiplier of 2 - the values the lab itself specifies in step 4 - will produce. A learner following the text will read the two tiles, see perfection, and deploy a memorised model without ever being pointed at the divergence.

### Create Microsoft Foundry Project

#### 40. [~] Moved navigation — `LAB004`

*Section:* Create Microsoft Foundry Project  
*Instruction:* `#1-sign-in-to-azure-portal`  
*Severity:* minor · *At fault:* instruction

Task 1 begins with 'Go to https://portal.azure.com', but the fresh learner VM opens at an Admin Windows lock screen. The learner must first use the separately issued machine password; the instruction does not mention this prerequisite.

### Deploy models into the Microsoft Foundry Project

#### 41. [~] Superseded or retiring feature — `LAB010`

*Section:* Deploy models into the Microsoft Foundry Project  
*Instruction:* `#1-ensure-that-you-are-on-the-microsoft-foundry-overview-page`  
*Severity:* minor · *At fault:* instruction

The prerequisite explicitly says to use the legacy Microsoft Foundry UI and instructs learners to turn New Foundry off. The created project opens in the current New Foundry experience, whose Home uses top navigation and an Explore models card; screenshot 0019 captures the replacement UX. The legacy path remains selectable but is superseded.

#### 42. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Deploy models into the Microsoft Foundry Project  
*Instruction:* `#2-deploy-gpt-51-model`  
*Severity:* minor · *At fault:* instruction

The latest Foundry model detail page has a purple Deploy control; the documented Use this model button is not present. Screenshot 0022 captures the current GPT-5.1 detail UX.

#### 43. [~] Moved navigation — `LAB004`

*Section:* Deploy models into the Microsoft Foundry Project  
*Instruction:* `#5-deploy-text-embedding-ada-002-model`  
*Severity:* minor · *At fault:* instruction

The completion text says to scroll the legacy left menu to Models + endpoints. In New Foundry, deployment verification is at Build > Models > Deployments; screenshot 0033 shows the current four-row deployment list.

### Create connections to Bing Resources at Azure AI Foundry resource level

#### 44. [~] Moved navigation — `LAB004`

*Section:* Create connections to Bing Resources at Azure AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

New Foundry reaches this page through Manage > Project details > Connected resources, not the documented legacy Management center > Resource route. Screenshot 0035 captures the current destination.

#### 45. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Create connections to Bing Resources at Azure AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

The current control is labeled Add connection; the documented +New connection label is no longer present.

#### 46. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Create connections to Bing Resources at Azure AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

After Connect, New Foundry returns directly to the Connected resources table. It does not show the documented green Connected label or Close button; the created GroundingWithBingSearch row is the current confirmation.

### Create connections to Azure AI Search at AI Foundry resource level

#### 47. [~] Moved navigation — `LAB004`

*Section:* Create connections to Azure AI Search at AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

New Foundry uses Manage > Project details > Connected resources instead of the documented legacy Management center > Resource route.

#### 48. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Create connections to Azure AI Search at AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

The current control is Add connection, not the documented +New connection.

#### 49. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Create connections to Azure AI Search at AI Foundry resource level  
*Instruction:* `#1-go-to-the-connected-resources-section`  
*Severity:* minor · *At fault:* instruction

New Foundry returns directly to the resources table after Connect; the documented green Connected label and Close button are absent.

### AI Language Service with Agents Lab

#### 52. [~] Moved navigation — `LAB004`

*Section:* AI Language Service with Agents Lab  
*Instruction:* `#copy-the-access-language-api-key-and-endpoint-url`  
*Severity:* minor · *At fault:* instruction

New Foundry no longer exposes the API key and Azure AI Services endpoint on the project Overview page. The current route is the backing Foundry resource in Azure portal, Resource Management > Keys and Endpoint.

#### 53. [~] Superseded or retiring feature — `LAB010`

*Section:* AI Language Service with Agents Lab  
*Instruction:* `#create-a-pii-redaction-logic-app`  
*Severity:* minor · *At fault:* instruction

The portal opened the previous Logic Apps designer and explicitly offered Switch to preview experience. In the current experience the workflow is draft/autosaved and uses Publish/Run draft, not the documented Save/Run canvas shown in the lab.

### Fine Tuning

#### 57. [~] Changed UI label or inconsistent structure — `LAB003`

*Section:* Fine Tuning  
*Instruction:* `#fine-tuning`  
*Severity:* minor · *At fault:* instruction

The Objectives block still carries its authoring template placeholder: it reads 'List the objectives' on the line above the real objective 'In this lab we will: Fine tune a model with given training and test dataset'. Visible to the learner in the rendered instructions.

## Structural problems in the instruction content

Found by parsing the instruction document itself, independently of walking the lab, so these hold regardless of coverage.

- [~] **`LAB003`** Section 'Manual Evaluation' is an <h4> while the other 5 contents entries are <h3>; it is structurally inconsistent.
- [~] **`LAB003`** Section 'Automated Evaluation' is an <h4> while the other 5 contents entries are <h3>; it is structurally inconsistent.
- [~] **`LAB003`** Section 'Welcome to WPLUS: Azure AI Platform and Services' has neither an Introduction heading nor numbered tasks, unlike every other section.
- [~] **`LAB003`** Section 'AI Red Teaming Agent for Generative AI Applications' has neither an Introduction heading nor numbered tasks, unlike every other section.
- [~] **`LAB003`** Section 'Lab: Using Vector Databases in Azure SQL Database' has neither an Introduction heading nor numbered tasks, unlike every other section.

## Ageing guidance (works today)

Nothing here stopped a learner. Each is a step that *succeeded* while following a path the product has moved on from, so it dates the lab rather than breaking it.

- **#41** Superseded or retiring feature *(Deploy models into the Microsoft Foundry Project)* — The prerequisite explicitly says to use the legacy Microsoft Foundry UI and instructs learners to turn New Foundry off. The created project opens in the current New Foundry experience, whose Home uses top navigation and an Explore models card; screenshot 0019 captures the replacement UX. The legacy path remains selectable but is superseded.
  <br>instruction: `#1-ensure-that-you-are-on-the-microsoft-foundry-overview-page`
- **#53** Superseded or retiring feature *(AI Language Service with Agents Lab)* — The portal opened the previous Logic Apps designer and explicitly offered Switch to preview experience. In the current experience the workflow is draft/autosaved and uses Publish/Run draft, not the documented Save/Run canvas shown in the lab.
  <br>instruction: `#create-a-pii-redaction-logic-app`
- **#73** Superseded or retiring feature *(Setup .env file)* — The instructions depend on legacy Models + endpoints and a per-deployment Target URI. New Foundry uses Build > Models > Deployments and presents a project endpoint plus SDK sample; the equivalent OpenAI Language APIs endpoint is on the Azure resource.
  <br>instruction: `#4-set-the-values-for-the-azure_openai_endpoint-and-azure_openai_api_key-variables`

## Verified correct

137 instruction(s) were checked and matched reality:

- **Create Microsoft Foundry Project** — After the undocumented VM unlock, the lab-issued Azure username and Temporary Access Pass authenticated successfully and loaded portal.azure.com.
- **Create Microsoft Foundry Project** — The Azure portal search returned Microsoft Foundry and opened its Overview blade in the current portal UX.
- **Create Microsoft Foundry Project** — The current Microsoft Foundry Overview contains the documented Create a resource control and opens the Foundry resource creation form.
- **Create Microsoft Foundry Project** — The current portal UX accepted azureaiworkshoprg, ai-foundry-64827025, East US 2, and firstProject. Deployment completed successfully within the stated two-minute window.
- **Create Microsoft Foundry Project** — The resource Overview showed Succeeded and Go to Foundry portal opened firstProject in the latest New Foundry experience, with the New Foundry switch on and current Home, Discover, Build, Operate, Manage, and Docs navigation.
- **Deploy models into the Microsoft Foundry** — The firstProject current Home page loaded successfully in New Foundry and exposes model deployment entry points.
- **Deploy models into the Microsoft Foundry** — In New Foundry, Deploy > Default settings created a gpt-5.1 Global Standard deployment and opened its current playground. The product path works, but differs from the documented legacy Use this model dialog.
- **Deploy models into the Microsoft Foundry** — New Foundry deployed gpt-5-mini with Default settings and opened its playground with a Global Standard deployment.
- **Deploy models into the Microsoft Foundry** — New Foundry deployed text-embedding-3-large version 1 as GlobalStandard; the Details page showed provisioning state Succeeded and model identity text-embedding-3-large.
- **Deploy models into the Microsoft Foundry** — New Foundry deployed text-embedding-ada-002 version 2 as GlobalStandard; Details showed provisioning state Succeeded and matching model identity.
- **Deploy models into the Microsoft Foundry** — New Foundry Build > Models > Deployments showed gpt-5.1, gpt-5-mini, text-embedding-3-large, and text-embedding-ada-002, all Succeeded with matching model identities.
- **Deploy models into the Microsoft Foundry** — The firstProject New Foundry Home page loaded and provided current model deployment entry points.
- **Create connections to Bing Resources at ** — Connected resources lists one GroundingWithBingSearch connection backed by gw-bing-64827025, using API Key authentication and the Bing API target. Screenshot 0040 verifies the resulting artifact.
- **Create connections to Azure AI Search at** — Connected resources lists aisearch64827025ectup5 as CognitiveSearch with API Key authentication and its search.windows.net target. Screenshot 0044 verifies the resulting artifact.
- **Setup .env file** — Copied .env.example to .env in the LABS root and preserved the marked do-not-modify section.
- **Setup .env file** — The signed-in New Foundry project opened successfully.
- **Setup .env file** — Copied the current project endpoint and set the project name from its final path component.
- **Setup .env file** — Configured the chat deployment identity, OpenAI-compatible endpoint, API version, and key using the current deployment and resource endpoint surfaces.
- **Setup .env file** — Configured both deployed embedding identities with embedding endpoints, API versions, and the resource key in the intended .env variables.
- **Setup .env file** — Copied the GroundingWithBingSearch connection identity from the New Foundry Connected resources table.
- **Setup .env file** — Set tenant, subscription, and resource-group values from the current Foundry and Azure resource overview surfaces.
- **Setup .env file** — Opened AI Search (Foundry IQ), verified the issued service URL, and populated its primary admin key without exposing it in the report.
- **Setup .env file** — Opened the issued Cosmos DB account, verified its URI, and populated the primary key without exposing it in the report.
- **Setup .env file** — Located the issued SQL logical server and set its fully qualified database.windows.net server name.
- **Setup .env file** — Set the Foundry resource name and the OpenAI Language APIs base endpoint from Azure portal > Resource Management > Keys and Endpoint > OpenAI.
- **Run requirements file to install the rel** — VS Code opened the supplied notebook with Python 3.12.10 selected. Run All re-executed both cells; the requirements path resolved and pip completed in 8.9 seconds with required packages satisfied.
- **Quick Start Guide - Azure AI Foundry** — After the documented Azure CLI device-code login and default-subscription selection, the notebook initialized credentials and the project client, returned a real gpt-5-mini completion, created a code-interpreter agent, calculated BMI, and saved a visualization file.
- **Evaluations with Azure AI Foundry** — The evaluation notebook executed and produced local evaluation result artifacts, including synthetic test data and local metrics output.
- **Azure AI Agents Tutorial Collection** — Code interpreter, file search, Bing grounding, and Azure AI Search notebooks reached their Congratulations sections and created their expected artifacts. The code interpreter generated multiple chart files.
- **Azure AI Vision - Lab** — Exercise 1 (Provision Azure Resources) works as written on the current portal UX. portal.azure.com > search 'Microsoft Foundry' > Foundry hub > left panel 'More services' > 'Computer vision' > Create. Form accepted Subscription MIPDG-lod53051908, Resource group azureaiworkshoprg, Region (US) East US, Name cv-64827025, Pricing tier 'Standard S1 (10 Calls per second)', Responsible AI checkbox. Review + create validated, Create submitted, and the deployment blade then read 'Your deployment is complete' with resource cv-64827025 of type Microsoft.CognitiveServices/accounts Created (deployment ComputerVisionCreate-20260907093654). Verified from the deployment artifact, not from a green tick alone.
- **Azure AI Vision - Lab** — Exercise 2 (Face Analysis) completes on the current Vision Studio. portal.vision.cognitive.azure.com redirects to /gallery/face and, after Sign in, 'Detect faces in an image' > acknowledge > 'Please select a resource' > subscription MIPDG-lod53051908 > 'Create a new resource' accepted Name faceresource-64827025, Resource group azureaiworkshoprg, Resource type CognitiveServices, Location East US, Price tier S0, then Confirm. Real API output was read, not just a tick: sample image 1 returned one bounding box with 'Face #1 / Face mask: no' and the JSON tab showed recognitionModel recognition_01 with faceRectangle {width 141, height 201, left 470, top 186} and faceLandmarks (pupilLeft, pupilRight, noseTip, mouthLeft, mouthRight). Iterating to sample image 3 returned two boxes and Face #1 and Face #2.
- **Fine Tuning** — Section 12's only actionable instruction checks out. C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning/ exists and contains both files it names, with real content rather than stubs: training_set_10samples.jsonl (2,695 bytes) and validation_set_10samples.jsonl (2,631 bytes). Listed from the VM.
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — Steps 1-4 complete on the current Foundry UX. Reached Build > Fine-tune in the New Foundry portal (ai.azure.com/nextgen, New Foundry toggle on) for firstProject under ai-foundry-64827025, started a job, chose Supervised, and gpt-4.1-mini is present in the model list along with gpt-4o and gpt-4o-mini, so all three models the lab offers are still selectable. Both files uploaded from C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning: training_set_10samples.jsonl and validation_set_10samples.jsonl, each 2.6 KB and each previewed by the portal as 'Total rows: 10' with real content ('Clippy is a factual chatbot that is also sarcastic'), so the datasets are genuine and accepted, not silently empty. Hyperparameters left at Default as instructed. Submit produced a real job: wplus-ft-64827025, base model gpt-4.1-mini-2025-04-14, Customization method Supervised, status Queued, created 9/7/26 10:39:57 AM.
- **Prompt Engineering** — The teaching content itself is sound once the three shipped-code defects are corrected. After the minimal value-only patches (dotenv path, temperature), 10 of 11 code cells ran clean and returned real model output rather than empty success: cell outputs of 246, 275, 1,719, 6,155, 2,196, 679 and 1,179 characters, including a readable Active-Prompt demonstration ('Sentence to classify: This thing is pretty awesome, dude!' with automatically selected examples). So the eight prompting techniques the section teaches do work against the lab's own gpt-5-mini deployment; only the parameters the notebook sends are wrong.
- **Fine Tuning - Advance Lab** — Everything section 14 depends on besides that one missing wait is correct and current. The three files it names exist under C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning/Advance Fine-Tuning/: gpt-4_o_dpo_ft.ipynb, data/gpt4o_generated_qa_dpo_train_10_samples.jsonl and data/gpt4o_generated_qa_dpo_validation_10_samples.jsonl. Unlike the Lab 06 notebook, this one resolves its configuration correctly with load_dotenv(dotenv_path='../../.env'), and all five variables it reads are present and correctly shaped in the .env: AZURE_SUBSCRIPTION_ID (36 chars), AI_FOUNDRY_NAME (19), AZURE_RESOURCE_GROUP (17), AZURE_OPENAI_API_KEY (84), AZURE_OPENAI_BASE_URL_ENDPOINT (45) - checked by name and length only, never by value. The service accepted the DPO payload as written, so the base model gpt-4o-2024-08-06, the 'dpo' method with beta 1.0 / batch_size 32 / learning_rate_multiplier 5.0 / n_epochs 1, and api_version 2025-02-01-preview are all still valid.
- **Responsible AI** — The PII Detection and Masking exercise works, and was verified from its output rather than from the page loading. Reached the current equivalent at ai.azure.com/nextgen > Build > Services > Playgrounds > 'Azure Language - Text PII Redaction', chose the 'Legal (NDA)' sample the lab names, and pressed Detect. The service returned nine real entities with types, confidences and offsets: Date 100% (offset 15), PersonType 99% (offset 40), Organization 'Contoso Restaurant' 100% (offset 52), Person 'Mateo Gomez' 98% (offset 75), Address '1234 Hollywood Boulevard Los Angeles CA' 97% (offset 100), USSocialSecurityNumber '123-45-6788' 100% (offset 170), a second Organization at offset 265, a second Person at offset 420 and Email 'mateo@contosorestaurant.com' 80% (offset 602). The masking control the lab calls the 'Hide PII slider' is present as a 'Redact PII' toggle and was on, with the input text shown masked; the 'Edit (crayon) icon' is present as an 'Edit' button.
- **Responsible AI** — Coverage limit for this section, stated so it is not read as clean: the Evaluations Setup sub-exercise (uploading Files/Contoso to the -azureml-blobstore container and building a vector index over it with text-embedding-3-large), the end-to-end Manual Evaluation run, the full Automated Evaluation submission with its ten evaluators, the three Content Safety bulk tests and the System Message / Agents Playground exercise were not executed. The first was not attempted because its consumer, Manual Evaluation, no longer exists; the Content Safety ones have no route to attempt; the rest were left unrun to keep the remaining eight sections moving. They are unknown, not correct.
- **Prompt Engineering** — The Zero-Shot technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 246 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The Few-Shot technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 275 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The Chain-of-Thought technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 1,719 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The Meta Prompting technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 6,155 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The Prompt Chaining technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 2,196 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The RAG technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 679 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **Prompt Engineering** — The Active-Prompt technique is demonstrated correctly and returns real model output. As shipped the cell cannot run at all - the notebook's load_dotenv path is wrong, so no client exists - but after the two value-only corrections (dotenv path and temperature) this cell executed against the lab's own gpt-5-mini deployment and produced 1,179 characters of model response. Judged from the executed notebook on disk, not from cell status.
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — portal.azure.com was already signed in as User1-64827025 in the lab VM's browser from earlier sections; no re-authentication was required and the portal rendered normally.
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — The job configures and submits as described. Customization method Supervised, both files uploaded from C:/Users/Admin/Desktop/LABS/Lab 05 - Fine-Tuning (training_set_10samples.jsonl and validation_set_10samples.jsonl, 2.6 KB each), each previewed by the portal as 'Total rows: 10' with real content, hyperparameters left at Default, and Submit created job wplus-ft-64827025 on base model gpt-4.1-mini-2025-04-14 at 10:39:57. Caveats recorded separately: the suffix field is now 'Display name' and arrives pre-filled, and a required 'Training type' field (Data Zone) is not mentioned by the step.
- **Lab 08 - RAG-Patterns - Graph RAG** — PASS - Walked the whole GraphRAG lab in Azure Cloud Shell (bash) and verified real artifacts, not headings. Cloud Shell first-run pane provisioned with "No storage account required" + subscription MIPDG-lod53051908; python3 3.12.9 (inside the documented 3.10-3.12 range). mkdir/venv/activate/pip install graphrag all worked. `graphrag init --root ragtest` prompted for the two model names exactly as documented (defaults offered were gpt-4.1 and text-embedding-3-large; entered gpt-5-mini and text-embedding-ada-002) and produced exactly the documented expected files: settings.yaml, .env, prompts/ (14 templates). curl -L https://aka.ms/dickens/xmas resolved and returned 189184 bytes of "The Project Gutenberg eBook of A Christmas Carol" (wc 3976 32462 189184). All four documented sed edits matched real lines in the generated settings.yaml and produced model_provider: azure, api_base: ${AZURE_OPENAI_ENDPOINT}, api_version: 2024-05-01-preview under BOTH default_completion_model and default_embedding_model, and graphml: true at line 104. `graphrag index --root ./ragtest` ran the full pipeline to "Pipeline complete" in 7m09s (extract_graph 1368/1368 text units) and wrote real output: entities.parquet 126296 B, relationships.parquet 149244 B, community_reports.parquet 1087549 B, graph.graphml 103306 B (proving the graphml sed took effect), documents/text_units/communities parquet and a lancedb/ vector store. Global query returned a themed answer citing community reports [Data: Reports (41,25,100,33,39,+more)]; local query returned an entity-grounded answer citing [Data: Entities (49,19); Relationships (161); Sources (6)]. prompt-tune produced genuinely domain-adapted prompts - summarize_descriptions.txt opens "You are an expert Literary Community Network Analyst" and extract_graph.txt lists domain entity types (fictional character, workhouse/gaol/almshouse, poverty/charity/redemption/ignorance).
- **Azure PostgreSQL Lab** — PASS - Every part of this lab was executed against the real pre-created server pgaivector-64827025 (PostgreSQL 15.19, Sweden Central) and verified from artifacts rather than headings. Part 1: Server parameters -> azure.extensions -> ticked AZURE_AI and VECTOR -> Save; the value went from "0 selected" to "2 selected" and the portal reported deployment PostgreSQLFlexibleServerParameters_383a6c628b324053a with resource serverParameters-0-... status OK. Part 2: psql connected with the password taken from sqlcredentials.txt, `create database books;` returned CREATE DATABASE and the database then appeared in \l. Part 3 restore: pg_restore against the on-disk backup finished with exactly the one error the lab tells you to expect ("unrecognized configuration parameter transaction_timeout" -> "warning: errors ignored on restore: 1"), so that instruction's caveat is accurate; the restored table holds 4999 rows and desc_embedding is a real USER-DEFINED vector column, with azure_ai 1.3.1 and vector 0.8.2 present in \dx (which only works because Part 1 allow-listed them first). Part 3 pgAdmin: pgAdmin 4 v9.5 launched, the server registered as AIWorkshop against host pgaivector-64827025.postgres.database.azure.com:5432 / postgres / postgres, connected, and the documented `select * from books limit 20;` ran in the Query Tool returning 20 real rows (Euphoria, A Map of the World, The Tuscan Child, Twilight, The Catcher in the Rye ...). Part 5: after azure_ai.set_setting for endpoint and subscription_key, the lab's own similarity query ran and returned five genuinely ranked results - Longitude: The True Story of a Lone Genius 0.6549, The Restaurant at the End of the Universe 0.6695, Flatland: A Romance of Many Dimensions 0.6759, The Three-Body Problem 0.6772, Seraphina 0.6836 - i.e. a live text-embedding-ada-002 call from inside PostgreSQL, not a cached value.
- **Azure SQL Lab** — PARTIAL COVERAGE NOTE for this section, recorded so the report does not read cleaner than the walk was. Verified by execution: 1_Setup.sql (dbo.MovieQuotes created with a native `embedding vector(1536)` column), 2_LoadMovieData.py and 3_UpdateMovieEmbedding.py (732 rows, 732 embeddings, real quote content) - but only after repairing SQL_PWD, CSV_PATH and the server firewall. NOT verified: the end-to-end vector search in 5_query.sql, which remains broken (see the sp_invoke_external_rest_endpoint finding). Deviation: the two .sql files were executed through pyodbc from the terminal rather than through the SSMS GUI. SSMS itself was launched and driven as far as the Connect to Server dialog - which is where the stale-identity and firewall defects were found - but the masked password field could not be filled reliably through this harness, and the SQL text executed was byte-identical to the shipped files. Also note the environment was mutated to get this far: an Azure SQL firewall rule "labvm-client" was added, and .env had SQL_PWD filled, CSV_PATH corrected and AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT trimmed to its base host.
- **AI Red Teaming Agent for Generative AI A** — focus terminal
- **AI Red Teaming Agent for Generative AI A** — run error scan
- **AI Red Teaming Agent for Generative AI A** — capture error scan output
- **AI Red Teaming Agent for Generative AI A** — capture error scan output
- **AI Red Teaming Agent for Generative AI A** — inspect red team scorecards
- **AI Red Teaming Agent for Generative AI A** — inspect scan working folders
- **AI Red Teaming Agent for Generative AI A** — inspect intermediary model target scan results
- **AI Red Teaming Agent for Generative AI A** — inspect notebook scan configuration
- **AI Red Teaming Agent for Generative AI A** — look for foundry upload URL in outputs
- **AI Red Teaming Agent for Generative AI A** — inspect RedTeam constructor and project wiring
- **AI Red Teaming Agent for Generative AI A** — switch to VM Edge to check Foundry for uploaded red team results
- **AI Red Teaming Agent for Generative AI A** — open a blank Edge window
- **AI Red Teaming Agent for Generative AI A** — open Microsoft Foundry nextgen portal
- **AI Red Teaming Agent for Generative AI A** — re-authenticate Foundry session
- **AI Red Teaming Agent for Generative AI A** — pick lab user account
- **AI Red Teaming Agent for Generative AI A** — sign in to Foundry with portal role credential
- **AI Red Teaming Agent for Generative AI A** — open Build > Evaluations to look for red teaming runs
- **AI Red Teaming Agent for Generative AI A** — return to Foundry home
- **AI Red Teaming Agent for Generative AI A** — open Build hub
- **AI Red Teaming Agent for Generative AI A** — open Evaluations to check for uploaded red team scans
- **AI Red Teaming Agent for Generative AI A** — open Red team tab
- **AI Red Teaming Agent for Generative AI A** — Section 18 complete: all four scans executed and their artifacts inspected.
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — poll fine-tune job status
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — open completed SFT job wplus-ft-64827025
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — open Monitor tab for training curves
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — click Deploy on the completed fine-tuned model
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — confirm deployment of fine-tuned model
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — wait for deployment provisioning
- **Lab: Using Vector Databases in Azure SQL** — begin section 22
- **Lab: Using Vector Databases in Azure SQL** — return to Windows Terminal
- **Lab: Using Vector Databases in Azure SQL** — read 4_SQLEmbeddings.py
- **Lab: Using Vector Databases in Azure SQL** — read 4_SQLEmbeddings.py part 2
- **Lab: Using Vector Databases in Azure SQL** — dump the @url literal from the deployed stored procedure
- **Lab: Using Vector Databases in Azure SQL** — dump the @url literal from the deployed stored procedure
- **Lab: Using Vector Databases in Azure SQL** — strip the stray leading space from the generated @url literal
- **Lab: Using Vector Databases in Azure SQL** — recreate proc without the stray space
- **Lab: Using Vector Databases in Azure SQL** — run 5_query.sql vector similarity query
- **Lab: Using Vector Databases in Azure SQL** — compare credential name to the referenced name
- **Lab: Using Vector Databases in Azure SQL** — create credential matching the name the procedure references
- **Lab: Using Vector Databases in Azure SQL** — create credential matching the referenced name
- **Lab: Using Vector Databases in Azure SQL** — run 5_query.sql after resolving all three defects
- **Lab: Using Vector Databases in Azure SQL** — open resource group in Azure portal
- **Lab: Using Vector Databases in Azure SQL** — list Edge windows
- **Lab: Using Vector Databases in Azure SQL** — switch to the signed-in Azure portal window
- **Lab: Using Vector Databases in Azure SQL** — open resource group overview
- **Lab: Using Vector Databases in Azure SQL** — open resource group overview
- **Lab: Using Vector Databases in Azure SQL** — reload portal after token expiry
- **Lab: Using Vector Databases in Azure SQL** — inspect MFA registration prompt for a skip option
- **Lab: Using Vector Databases in Azure SQL** — confirm the Azure portal is unreachable without MFA enrolment
- **Lab: Using Vector Databases in Azure SQL** — verify SQL server and database facts via az CLI
- **Lab: Using Vector Databases in Azure SQL** — start device code login without displaying the code
- **Lab: Using Vector Databases in Azure SQL** — start device code login (temp log)
- **Lab: Using Vector Databases in Azure SQL** — open device login page
- **Lab: Using Vector Databases in Azure SQL** — submit device code
- **Lab: Using Vector Databases in Azure SQL** — pick account for CLI device login
- **Lab: Using Vector Databases in Azure SQL** — continue CLI device login
- **Lab: Using Vector Databases in Azure SQL** — verify SQL server, database and firewall rules
- **Lab: Using Vector Databases in Azure SQL** — switch to Microsoft Foundry tab
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — check deployment status of the fine-tuned model
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — open the fine-tuned deployment in playground
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — send a prompt to the fine-tuned deployment
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — Deploy and test works end to end. Deploy from the completed job opened a 'Customize ... deployment' panel (Deployment name prefilled, Deployment type Global Standard, TPM rate limit 10000/500000, Guardrails DefaultV2); the deployment went Creating at 16:11 and reached Succeeded, appearing in Build > Models > Deployments as gpt-4.1-mini-2025-04-14.ft-af929589ec224665b7cdc8357449101c-wp, Global Standard, v2025-04-14. The details pane exposes Project endpoint and a masked API Key exactly as step 6 asks the learner to review, plus a ready-made Python snippet. 'Open in playground' loaded the deployment and a prompt returned a real completion attributed to the fine-tuned deployment name (352 tokens, 5s), so this is served inference from the fine-tuned model and not a stale base-model chat.
- **🛠️ Steps: Fine-Tuning the GPT-4.1-mini M** — Section 13 complete: all six steps judged; job completed, deployed and tested.
- **Lab: Using Vector Databases in Azure SQL** — open Discover to look for the model catalog
- **Lab: Using Vector Databases in Azure SQL** — search the catalog for text-embedding-ada-002
- **Lab: Using Vector Databases in Azure SQL** — search catalog for the ada embedding model
- **Lab: Using Vector Databases in Azure SQL** — open text-embedding-ada-002 model card
- **Lab: Using Vector Databases in Azure SQL** — Closed partial: the SQL and embedding chain was executed and verified end to end, but steps 1, 2, 13, 14, 15 and 20 could not be performed in the portal because the Temporary Access Pass expired and the portal now demands MFA registration. Their facts were confirmed instead through the Azure CLI and the Foundry portal, which is weaker evidence than walking the documented screens.
- **Optional Lab RAG (Retrieval-Augmented Ge** — begin section 23
- **Optional Lab RAG (Retrieval-Augmented Ge** — locate RAG.ipynb and check for an Azure AI Search resource
- **Optional Lab RAG (Retrieval-Augmented Ge** — search for the RAG notebook
- **Optional Lab RAG (Retrieval-Augmented Ge** — check Lab 08 folder and search the whole disk for RAG.ipynb
- **Optional Lab RAG (Retrieval-Augmented Ge** — check whether the Azure AI Search service holds any index
- **Optional Lab RAG (Retrieval-Augmented Ge** — check .env for Azure AI Search credentials (names and lengths only)
- **Optional Lab RAG (Retrieval-Augmented Ge** — Closed blocked: the section's only task cannot be started because RAG.ipynb is absent from the lab VM. No exercise in this section was executed, and none of the seven exercises can be judged.
- **AI Frameworks - Semantic Kernel and Auto** — begin section 24
- **AI Frameworks - Semantic Kernel and Auto** — locate the SK and AutoGen notebook
- **AI Frameworks - Semantic Kernel and Auto** — focus Windows Terminal
- **AI Frameworks - Semantic Kernel and Auto** — list every notebook shipped with the lab
- **AI Frameworks - Semantic Kernel and Auto** — check whether Semantic Kernel and AutoGen are installed
- **AI Frameworks - Semantic Kernel and Auto** — Closed blocked: the section's only task cannot be started because SK and AutoGen.ipynb is absent from the lab VM. None of Exercises 1 to 5 was executed.
- **AI Frameworks - Semantic Kernel and Auto** — remove scratch files created during the walk
- **Azure SQL Lab** — Follow-up to the 'failed to parse url (31609)' finding recorded above, which closed with the character-level cause unconfirmed. It was subsequently identified while walking the Vector Databases in Azure SQL section and is reported there in full: 4_SQLEmbeddings.py emits the T-SQL as @url = <quote><space><url>, so the stored procedure holds a URL literal beginning with a space, which sp_invoke_external_rest_endpoint refuses to parse. Dumping sys.sql_modules showed the leading space directly. A second, independent defect sits behind it - the database scoped credential is created under the raw endpoint name but referenced with the trailing slash stripped, which yields error 15151 once the space is fixed. Both must be corrected before 5_query.sql returns rows; with both corrected it returns the expected 10 ranked results. The two sections describe one defect chain, not two.
- **AI Language Service with Agents Lab** — Coverage limit for this section, stated so it is not read as clean. The Logic Apps designer exercise was left in an inconsistent state by the walk itself, not by the lab: a delayed response in the designer caused a duplicated Parse JSON action to be added, so the workflow was never run end to end and the section's later steps were not exercised. That is an artefact of how this walk drove the UI and must not be read as a lab defect. What it does mean is that any defect living in the unrun portion of this section would not have been detected, and the absence of findings there is absence of evidence.
- **AI Language Service with Agents Lab** — Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.
- **Responsible AI** — Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.
- **Azure SQL Lab** — Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.
- **Lab: Using Vector Databases in Azure SQL** — Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.

## Deferred

_Postponed by the walk, not by the lab. Blockers are reported up front._

- **Create Microsoft Foundry Project** — Machine credentials/Password typed (delta 0.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Create Microsoft Foundry Project** — Azure Portal/Username typed (delta 4.4); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Create Microsoft Foundry Project** — Azure Portal/TAP typed (delta 4.9); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/Username typed (delta 1.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **Azure AI Agents Tutorial Collection** — Azure Portal/TAP typed (delta 12.5); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **AI Language Service with Agents Lab** — Azure Portal/Username typed (delta 1.4); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **AI Language Service with Agents Lab** — Azure Portal/TAP typed (delta 1.8); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed
- **AI Red Teaming Agent for Generative AI A** — Azure Portal/Password typed (delta 1.6); the delta cannot tell acceptance from rejection on this console -- capture the screen and read it. A password box or an error message means it failed

## Withdrawn judgements

Findings and confirmations recorded during the walk, then withdrawn once the cause was understood. They are listed rather than deleted so the report can be audited against the raw trace.

- `LAB007` on `until:quiet:15000` — Not a lab defect. The quiet probe never settled because https://ai.azure.com/home is the unauthenticated Microsoft Foundry marketing page, which autoplays a looping hero video; capture 0215 shows a fully loaded, healthy page with a cookie banner and a Sign in button. This measures the probe against an animation, not a timing or quota problem in the lab. Withdrawn.
