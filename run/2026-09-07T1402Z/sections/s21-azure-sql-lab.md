# Azure SQL Lab

*Section* `s21-azure-sql-lab` · *Module* System Message

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#azure-sql-lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 271 recorded step(s), 7 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Broken link** `LAB006` — The pre-created Azure SQL server is unreachable from the lab VM and nothing in the lab tells the learner how to fix it. Running the lab's own second step, `python 2_LoadMovieData.py`, fails with pyodbc error 40615: "Cannot open server 'sqlaivector-64827025' requested by the login. Client with IP address '185.254.59.123' is not allowed to access the server." `az sql server firewall-rule list -g azureaiworkshoprg -s sqlaivector-64827025` returns an empty list - the server has NO firewall rules at all, so neither the VM nor Azure services can reach it. Connecting through SSMS surfaces the same condition as a "New Firewall Rule" wizard ("Your client IP address does not have access to the server"), which then demands an Azure sign-in the learner has just been forced to sign out of (see the stale-account finding). The section's Pre-requisites say "None. The database has been pre-created for you." and the Tasks say only to execute the numbered files, so a learner has no documented route past this. Everything after it in sections 21 and 22 is blocked. Unblocked here only by running `az sql server firewall-rule create ... --start-ip-address 185.254.59.0 --end-ip-address 185.254.59.255`, which the lab never mentions.
  <br>evidence: step `2791`, instruction `#azure-sql-lab`
- **Broken link** `LAB006` — SQL Server Management Studio in the VM image is signed in as a DIFFERENT lab reservation's user and refuses to connect until that is undone. On first launch, SSMS 21 pre-populates the Connect to Server dialog with server name "sqlaivector-55791077.database.windows.net" - not this reservation's sqlaivector-64827025 - and every Connect attempt, even with SQL Server Authentication and correct credentials, aborts with: "User account 'User1-55791077@LODSPRODMCA.onmicrosoft.com' was invalid or stale when getting Azure subscriptions. Please re-authenticate the account before trying again. (Microsoft.SqlServer.Management.ApplicationAuthenticationManagement)". Opening the account flyout confirms it: signed in as User1-55791077 under tenant LODS-Prod-MCA with a "Re-enter your credentials" warning. Both the cached Entra account and the server MRU are baked into the image from lab instance 55791077. The only way forward is the undocumented sequence account flyout -> ... -> Sign out, after which the dialog stops erroring. The section tells the learner "The .sql files need to be executed in SQL Server Management Studio, which is preloaded on Desktop for you" and gives no hint that the preloaded tool is carrying someone else's identity. Related smaller inaccuracy in the same sentence: SSMS is NOT on the Desktop - the only Desktop shortcut for this user is "Visual Studio Code.lnk" and C:\Users\Public\Desktop is empty; SSMS 21 is installed at C:\Program Files\Microsoft SQL Server Management Studio 21 and pinned to the taskbar.
  <br>evidence: step `2792`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` — Two values the lab's own scripts require are wrong or missing in the shipped .env, and no section ever tells the learner to set them. (a) SQL_PWD is EMPTY. .env.example carries a 7-character placeholder for it, but the delivered .env has "SQL_PWD=" with nothing after the equals sign. Section 05 (Setup env file) walks the learner through SQL_SERVER at step 10 and never mentions SQL_PWD, SQL_USER, SQL_DATABASE, CSV_PATH or BATCH_SIZE. Consequence: `python 2_LoadMovieData.py` fails with pyodbc 28000 "Login failed for user 'sqladmin'. (18456)". (b) CSV_PATH points at a folder that does not exist: it ends "...S\Vectors\SQL\movie_quotes.csv" (os.path.exists returns False) - a legacy layout. The file actually ships at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\SQL\movie_quotes.csv (66890 bytes). Both had to be repaired by hand before any of the numbered steps could run.
  <br>evidence: step `2793`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` — The failure of 2_LoadMovieData.py is hidden by its own error handler, and the next script then reports success on an empty table - a textbook false pass. 2_LoadMovieData.py wraps everything in `try: ... except Exception as e: print(f"An error occurred: {e} -- {sql}")`, but `sql` is only assigned INSIDE the try, several lines after `open(csv_path)`. So when the CSV path is wrong the handler itself raises `NameError: name 'sql' is not defined` and the learner never sees the real FileNotFoundError. Worse, running the very next documented step on that empty table, `python 3_UpdateMovieEmbedding.py`, printed "Embeddings updated for all quotes." - while a direct count showed `select count(*), sum(case when embedding is null then 0 else 1 end) from dbo.MovieQuotes` = (0, None). Zero rows, zero embeddings, and a success message. A learner following the instructions and reading the console would believe the ingest worked. After repairing CSV_PATH the same two scripts ran clean and the counts became (732, 732) with real content ("Star Wars: Episode V - The Empire Strikes Back" / "Do, or do not. There is no try.", "Dracula" / "Listen to them. Children of the night."), which is what the step should have produced the first time.
  <br>evidence: step `2794`, instruction `#azure-sql-lab`
- **Defective sample code** `LAB009` — The final two steps of the lab could not be completed even after every environment problem above was repaired. 4_SQLEmbeddings.py creates a DATABASE SCOPED CREDENTIAL and a dbo.get_embedding procedure that calls sp_invoke_external_rest_endpoint, and 5_query.sql then EXECs it. Two separate defects: (a) the script is not idempotent - re-running it (which a learner will do, because step 2 failed the first time) aborts with `pyodbc.ProgrammingError ... The credential with name "https://ai-foundry-64827025.openai.azure.com/" already exists. (15530)` and never reaches the CREATE PROCEDURE, leaving the database in a half-built state that then reports "Could not find stored procedure 'dbo.get_embedding'. (2812)". (b) Even after dropping both objects and running 4_SQLEmbeddings.py once, cleanly, with a corrected endpoint, executing 5_query.sql verbatim fails with `[SQL Server]An error occurred, failed to parse url. HRESULT: 0x80072ee6. (31609)`. The URL the script composes is `{endpoint.rstrip('/')}/openai/deployments/{deployment}/embeddings?api-version=2024-02-01`, which with a corrected base endpoint evaluates to a well-formed https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01 - so the malformation is introduced when that string is embedded into the generated T-SQL, not by the endpoint value. Net effect: the lab's stated objective, a similarity search in Azure SQL, cannot be reached by following the instructions.
  <br>evidence: step `2795`, instruction `#azure-sql-lab`

## Findings

**LAB002** ×1 · **LAB003** ×1 · **LAB006** ×2 · **LAB009** ×3

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#1** Broken link (`LAB006`)
- **#2** Broken link (`LAB006`)
- **#3** Defective sample code (`LAB009`)
- **#6** Missing resource or SKU (`LAB002`)

**Instruction defects — the lab text is wrong** — lab author

- **#4** Defective sample code (`LAB009`)
- **#5** Defective sample code (`LAB009`)
- **#7** Changed UI label or inconsistent structure (`LAB003`)

### 1. [!!] Broken link — `LAB006`

*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup · *Step:* `2791` · *2026-09-07T22:43:27Z*

The pre-created Azure SQL server is unreachable from the lab VM and nothing in the lab tells the learner how to fix it. Running the lab's own second step, `python 2_LoadMovieData.py`, fails with pyodbc error 40615: "Cannot open server 'sqlaivector-64827025' requested by the login. Client with IP address '185.254.59.123' is not allowed to access the server." `az sql server firewall-rule list -g azureaiworkshoprg -s sqlaivector-64827025` returns an empty list - the server has NO firewall rules at all, so neither the VM nor Azure services can reach it. Connecting through SSMS surfaces the same condition as a "New Firewall Rule" wizard ("Your client IP address does not have access to the server"), which then demands an Azure sign-in the learner has just been forced to sign out of (see the stale-account finding). The section's Pre-requisites say "None. The database has been pre-created for you." and the Tasks say only to execute the numbered files, so a learner has no documented route past this. Everything after it in sections 21 and 22 is blocked. Unblocked here only by running `az sql server firewall-rule create ... --start-ip-address 185.254.59.0 --end-ip-address 185.254.59.255`, which the lab never mentions.

### 2. [!!] Broken link — `LAB006`

*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup · *Step:* `2792` · *2026-09-07T22:43:46Z*

SQL Server Management Studio in the VM image is signed in as a DIFFERENT lab reservation's user and refuses to connect until that is undone. On first launch, SSMS 21 pre-populates the Connect to Server dialog with server name "sqlaivector-55791077.database.windows.net" - not this reservation's sqlaivector-64827025 - and every Connect attempt, even with SQL Server Authentication and correct credentials, aborts with: "User account 'User1-55791077@LODSPRODMCA.onmicrosoft.com' was invalid or stale when getting Azure subscriptions. Please re-authenticate the account before trying again. (Microsoft.SqlServer.Management.ApplicationAuthenticationManagement)". Opening the account flyout confirms it: signed in as User1-55791077 under tenant LODS-Prod-MCA with a "Re-enter your credentials" warning. Both the cached Entra account and the server MRU are baked into the image from lab instance 55791077. The only way forward is the undocumented sequence account flyout -> ... -> Sign out, after which the dialog stops erroring. The section tells the learner "The .sql files need to be executed in SQL Server Management Studio, which is preloaded on Desktop for you" and gives no hint that the preloaded tool is carrying someone else's identity. Related smaller inaccuracy in the same sentence: SSMS is NOT on the Desktop - the only Desktop shortcut for this user is "Visual Studio Code.lnk" and C:\Users\Public\Desktop is empty; SSMS 21 is installed at C:\Program Files\Microsoft SQL Server Management Studio 21 and pinned to the taskbar.

### 3. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* setup · *Step:* `2793` · *2026-09-07T22:44:09Z*

Two values the lab's own scripts require are wrong or missing in the shipped .env, and no section ever tells the learner to set them. (a) SQL_PWD is EMPTY. .env.example carries a 7-character placeholder for it, but the delivered .env has "SQL_PWD=" with nothing after the equals sign. Section 05 (Setup env file) walks the learner through SQL_SERVER at step 10 and never mentions SQL_PWD, SQL_USER, SQL_DATABASE, CSV_PATH or BATCH_SIZE. Consequence: `python 2_LoadMovieData.py` fails with pyodbc 28000 "Login failed for user 'sqladmin'. (18456)". (b) CSV_PATH points at a folder that does not exist: it ends "...S\Vectors\SQL\movie_quotes.csv" (os.path.exists returns False) - a legacy layout. The file actually ships at C:\Users\Admin\Desktop\LABS\Lab 10 - Vector-DB\SQL\movie_quotes.csv (66890 bytes). Both had to be repaired by hand before any of the numbered steps could run.

### 4. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* instruction · *Step:* `2794` · *2026-09-07T22:44:10Z*

The failure of 2_LoadMovieData.py is hidden by its own error handler, and the next script then reports success on an empty table - a textbook false pass. 2_LoadMovieData.py wraps everything in `try: ... except Exception as e: print(f"An error occurred: {e} -- {sql}")`, but `sql` is only assigned INSIDE the try, several lines after `open(csv_path)`. So when the CSV path is wrong the handler itself raises `NameError: name 'sql' is not defined` and the learner never sees the real FileNotFoundError. Worse, running the very next documented step on that empty table, `python 3_UpdateMovieEmbedding.py`, printed "Embeddings updated for all quotes." - while a direct count showed `select count(*), sum(case when embedding is null then 0 else 1 end) from dbo.MovieQuotes` = (0, None). Zero rows, zero embeddings, and a success message. A learner following the instructions and reading the console would believe the ingest worked. After repairing CSV_PATH the same two scripts ran clean and the counts became (732, 732) with real content ("Star Wars: Episode V - The Empire Strikes Back" / "Do, or do not. There is no try.", "Dracula" / "Listen to them. Children of the night."), which is what the step should have produced the first time.

### 5. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-sql-lab`  
*Severity:* critical · *At fault:* instruction · *Step:* `2795` · *2026-09-07T22:44:34Z*

The final two steps of the lab could not be completed even after every environment problem above was repaired. 4_SQLEmbeddings.py creates a DATABASE SCOPED CREDENTIAL and a dbo.get_embedding procedure that calls sp_invoke_external_rest_endpoint, and 5_query.sql then EXECs it. Two separate defects: (a) the script is not idempotent - re-running it (which a learner will do, because step 2 failed the first time) aborts with `pyodbc.ProgrammingError ... The credential with name "https://ai-foundry-64827025.openai.azure.com/" already exists. (15530)` and never reaches the CREATE PROCEDURE, leaving the database in a half-built state that then reports "Could not find stored procedure 'dbo.get_embedding'. (2812)". (b) Even after dropping both objects and running 4_SQLEmbeddings.py once, cleanly, with a corrected endpoint, executing 5_query.sql verbatim fails with `[SQL Server]An error occurred, failed to parse url. HRESULT: 0x80072ee6. (31609)`. The URL the script composes is `{endpoint.rstrip('/')}/openai/deployments/{deployment}/embeddings?api-version=2024-02-01`, which with a corrected base endpoint evaluates to a well-formed https://ai-foundry-64827025.openai.azure.com/openai/deployments/text-embedding-ada-002/embeddings?api-version=2024-02-01 - so the malformation is introduced when that string is embedded into the generated T-SQL, not by the endpoint value. Net effect: the lab's stated objective, a similarity search in Azure SQL, cannot be reached by following the instructions.

### 6. [!] Missing resource or SKU — `LAB002`

*Instruction:* `#azure-sql-lab`  
*Severity:* major · *At fault:* setup · *Step:* `2796` · *2026-09-07T22:44:35Z*

The same .env variable that breaks the PostgreSQL lab also breaks this one, which makes it a shared root cause rather than two coincidences. 4_SQLEmbeddings.py treats AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT as a bare resource endpoint and appends "/openai/deployments/<deployment>/embeddings?api-version=2024-02-01" to it. The delivered value is a full 120-character deployment/inference URI that already contains "/openai/deployments/", so the generated URL contains that path twice and SQL rejects it. This was only diagnosable by reading the composed string; the visible symptom is the opaque "failed to parse url" above. Either the scripts should normalise the endpoint (strip anything after the host) or Section 05 should record the bare endpoint in a separate variable.

### 7. [!] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#azure-sql-lab`  
*Severity:* major · *At fault:* instruction · *Step:* `2797` · *2026-09-07T22:44:58Z*

The single Tasks paragraph contains four separate documentation errors. (a) The hyperlink labelled "SQL folder" points at https://github.com/Azure/WPLUS-Azure-AI-Platform-and-Services/tree/AugRelease/Vector-DB/Cosmos%20DB - the COSMOS DB folder, not the SQL one - and that URL returns HTTP 404 when fetched, so the link is both mislabelled and dead. (b) The example command reads `python 2_LoadMovideData.py`; the file that ships is 2_LoadMovieData.py ("Movide" -> "Movie"), so copying the example gives "can't open file". (c) "Files are numberd" and "you have nagivated" are misspellings in the same sentence. (d) The section's second Objective reads "Perform similarity searches using PostgreSQL" - copied verbatim from the PostgreSQL lab into the Azure SQL lab, so the stated goal names the wrong product.

## Verified correct

- PARTIAL COVERAGE NOTE for this section, recorded so the report does not read cleaner than the walk was. Verified by execution: 1_Setup.sql (dbo.MovieQuotes created with a native `embedding vector(1536)` column), 2_LoadMovieData.py and 3_UpdateMovieEmbedding.py (732 rows, 732 embeddings, real quote content) - but only after repairing SQL_PWD, CSV_PATH and the server firewall. NOT verified: the end-to-end vector search in 5_query.sql, which remains broken (see the sp_invoke_external_rest_endpoint finding). Deviation: the two .sql files were executed through pyodbc from the terminal rather than through the SSMS GUI. SSMS itself was launched and driven as far as the Connect to Server dialog - which is where the stale-identity and firewall defects were found - but the masked password field could not be filled reliably through this harness, and the SQL text executed was byte-identical to the shipped files. Also note the environment was mutated to get this far: an Azure SQL firewall rule "labvm-client" was added, and .env had SQL_PWD filled, CSV_PATH corrected and AZURE_OPENAI_EMBEDDING_ADA_ENDPOINT trimmed to its base host.
- Follow-up to the 'failed to parse url (31609)' finding recorded above, which closed with the character-level cause unconfirmed. It was subsequently identified while walking the Vector Databases in Azure SQL section and is reported there in full: 4_SQLEmbeddings.py emits the T-SQL as @url = <quote><space><url>, so the stored procedure holds a URL literal beginning with a space, which sp_invoke_external_rest_endpoint refuses to parse. Dumping sys.sql_modules showed the leading space directly. A second, independent defect sits behind it - the database scoped credential is created under the raw endpoint name but referenced with the trailing slash stripped, which yields error 15151 once the space is fixed. Both must be corrected before 5_query.sql returns rows; with both corrected it returns the expected 10 ranked results. The two sections describe one defect chain, not two.
- Re-closed as done so the run report stops rendering this section as 'not reached'. The status 'partial' is not one the report understands, and a section that was walked for hundreds of steps and produced findings must not appear as one nobody opened. The coverage limits for this section are recorded as their own notes above and stand unchanged.

## Evidence

52 capture(s), in the order the learner would have seen them.

- [`0370-s21-azure-sql-lab-step.jpg`](../images/0370-s21-azure-sql-lab-step.jpg)
- [`0371-s21-azure-sql-lab-step.jpg`](../images/0371-s21-azure-sql-lab-step.jpg)
- [`0372-s21-azure-sql-lab-step.jpg`](../images/0372-s21-azure-sql-lab-step.jpg)
- [`0373-s21-azure-sql-lab-step.jpg`](../images/0373-s21-azure-sql-lab-step.jpg)
- [`0374-s21-azure-sql-lab-step.jpg`](../images/0374-s21-azure-sql-lab-step.jpg)
- [`0375-s21-azure-sql-lab-step.jpg`](../images/0375-s21-azure-sql-lab-step.jpg)
- [`0376-s21-azure-sql-lab-step.jpg`](../images/0376-s21-azure-sql-lab-step.jpg)
- [`0377-s21-azure-sql-lab-step.jpg`](../images/0377-s21-azure-sql-lab-step.jpg)
- [`0378-s21-azure-sql-lab-step.jpg`](../images/0378-s21-azure-sql-lab-step.jpg)
- [`0379-s21-azure-sql-lab-step.jpg`](../images/0379-s21-azure-sql-lab-step.jpg)
- [`0380-s21-azure-sql-lab-step.jpg`](../images/0380-s21-azure-sql-lab-step.jpg)
- [`0381-s21-azure-sql-lab-step.jpg`](../images/0381-s21-azure-sql-lab-step.jpg)
- [`0382-s21-azure-sql-lab-step.jpg`](../images/0382-s21-azure-sql-lab-step.jpg)
- [`0383-s21-azure-sql-lab-step.jpg`](../images/0383-s21-azure-sql-lab-step.jpg)
- [`0384-s21-azure-sql-lab-step.jpg`](../images/0384-s21-azure-sql-lab-step.jpg)
- [`0385-s21-azure-sql-lab-step.jpg`](../images/0385-s21-azure-sql-lab-step.jpg)
- [`0386-s21-azure-sql-lab-step.jpg`](../images/0386-s21-azure-sql-lab-step.jpg)
- [`0387-s21-azure-sql-lab-step.jpg`](../images/0387-s21-azure-sql-lab-step.jpg)
- [`0388-s21-azure-sql-lab-step.jpg`](../images/0388-s21-azure-sql-lab-step.jpg)
- [`0389-s21-azure-sql-lab-step.jpg`](../images/0389-s21-azure-sql-lab-step.jpg)
- [`0390-s21-azure-sql-lab-step.jpg`](../images/0390-s21-azure-sql-lab-step.jpg)
- [`0391-s21-azure-sql-lab-step.jpg`](../images/0391-s21-azure-sql-lab-step.jpg)
- [`0392-s21-azure-sql-lab-step.jpg`](../images/0392-s21-azure-sql-lab-step.jpg)
- [`0393-s21-azure-sql-lab-step.jpg`](../images/0393-s21-azure-sql-lab-step.jpg)
- [`0394-s21-azure-sql-lab-step.jpg`](../images/0394-s21-azure-sql-lab-step.jpg)
- [`0395-s21-azure-sql-lab-step.jpg`](../images/0395-s21-azure-sql-lab-step.jpg)
- [`0396-s21-azure-sql-lab-step.jpg`](../images/0396-s21-azure-sql-lab-step.jpg)
- [`0397-s21-azure-sql-lab-step.jpg`](../images/0397-s21-azure-sql-lab-step.jpg)
- [`0398-s21-azure-sql-lab-step.jpg`](../images/0398-s21-azure-sql-lab-step.jpg)
- [`0399-s21-azure-sql-lab-step.jpg`](../images/0399-s21-azure-sql-lab-step.jpg)
- [`0400-s21-azure-sql-lab-step.jpg`](../images/0400-s21-azure-sql-lab-step.jpg)
- [`0401-s21-azure-sql-lab-step.jpg`](../images/0401-s21-azure-sql-lab-step.jpg)
- [`0402-s21-azure-sql-lab-step.jpg`](../images/0402-s21-azure-sql-lab-step.jpg)
- [`0403-s21-azure-sql-lab-step.jpg`](../images/0403-s21-azure-sql-lab-step.jpg)
- [`0404-s21-azure-sql-lab-step.jpg`](../images/0404-s21-azure-sql-lab-step.jpg)
- [`0405-s21-azure-sql-lab-step.jpg`](../images/0405-s21-azure-sql-lab-step.jpg)
- [`0406-s21-azure-sql-lab-step.jpg`](../images/0406-s21-azure-sql-lab-step.jpg)
- [`0407-s21-azure-sql-lab-step.jpg`](../images/0407-s21-azure-sql-lab-step.jpg)
- [`0408-s21-azure-sql-lab-step.jpg`](../images/0408-s21-azure-sql-lab-step.jpg)
- [`0409-s21-azure-sql-lab-step.jpg`](../images/0409-s21-azure-sql-lab-step.jpg)
- [`0410-s21-azure-sql-lab-step.jpg`](../images/0410-s21-azure-sql-lab-step.jpg)
- [`0411-s21-azure-sql-lab-step.jpg`](../images/0411-s21-azure-sql-lab-step.jpg)
- [`0412-s21-azure-sql-lab-step.jpg`](../images/0412-s21-azure-sql-lab-step.jpg)
- [`0413-s21-azure-sql-lab-step.jpg`](../images/0413-s21-azure-sql-lab-step.jpg)
- [`0414-s21-azure-sql-lab-step.jpg`](../images/0414-s21-azure-sql-lab-step.jpg)
- [`0415-s21-azure-sql-lab-step.jpg`](../images/0415-s21-azure-sql-lab-step.jpg)
- [`0416-s21-azure-sql-lab-step.jpg`](../images/0416-s21-azure-sql-lab-step.jpg)
- [`0417-s21-azure-sql-lab-step.jpg`](../images/0417-s21-azure-sql-lab-step.jpg)
- [`0418-s21-azure-sql-lab-step.jpg`](../images/0418-s21-azure-sql-lab-step.jpg)
- [`0419-s21-azure-sql-lab-step.jpg`](../images/0419-s21-azure-sql-lab-step.jpg)
- [`0420-s21-azure-sql-lab-step.jpg`](../images/0420-s21-azure-sql-lab-step.jpg)
- [`0421-s21-azure-sql-lab-step.jpg`](../images/0421-s21-azure-sql-lab-step.jpg)
