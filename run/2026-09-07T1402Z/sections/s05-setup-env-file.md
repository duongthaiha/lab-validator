# Setup .env file

*Section* `s05-setup-env-file`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#setup-env-file`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 631 recorded step(s), 3 finding(s)

**Can a learner finish this section?** **PARTIALLY** — reachable, but not by following the instructions as written

## What the lab asks the learner to do

- 1. Copy .env.example as .env
- 2. Go to the Microsoft Foundry - Overview page
- 3. Set the values for the AI_FOUNDRY_PROJECT_ENDPOINT and AZURE_PROJECT_NAME variables
- 4. Set the values for the AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY variables
- 5. Set the values for the AZURE_OPENAI_EMBEDDING_ENDPOINT and AZURE_OPENAI_EMBEDDING_API_KEY variables
- 6. Set the value for the GROUNDING_WITH_BING_CONNECTION_NAME variable
- 7. Set the values for the TENANT_ID, AZURE_RESOURCE_GROUP and AZURE_SUBSCRIPTION_ID variables
- 8. Set the values for the AZURE_AI_SEARCH_ENDPOINT and AZURE_AI_SEARCH_API_KEY variables
- 9. Set the values for the COSMOS_ENDPOINT and COSMOS_KEY variables
- 10. Set the value for the SQL_SERVER variable
- 11. Set additional Microsoft Foundry Values (for Advance Fine-Tuning Lab)

## Findings

**LAB003** ×1 · **LAB009** ×1 · **LAB010** ×1

### Who fixes what

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Changed UI label or inconsistent structure (`LAB003`)
- **#3** Superseded or retiring feature (`LAB010`)

### 1. [!] Defective sample code — `LAB009`

*Instruction:* `#5-set-the-values-for-the-azure_openai_embedding_endpoint-and-azure_openai_embedding_api_key-variables`  
*Severity:* major · *At fault:* instruction · *Step:* `852` · *2026-09-07T15:04:17Z*

The embedding instructions say to paste the embedding Target URI into AZURE_OPENAI_ENDPOINT instead of AZURE_OPENAI_EMBEDDING_ENDPOINT, and illustrate a chat/completions URI for embedding models. Following that text literally misconfigures the shipped .env and breaks embedding calls.

### 2. [~] Changed UI label or inconsistent structure — `LAB003`

*Instruction:* `#7-set-the-values-for-the-tenant_id-azure_resource_group-and-azure_subscription_id-variables`  
*Severity:* minor · *At fault:* instruction · *Step:* `855` · *2026-09-07T15:04:18Z*

The final instruction says to paste the Subscription ID as the value for, but omits the variable name. The task heading identifies AZURE_SUBSCRIPTION_ID, so the learner can infer it.

### 3. [i] Superseded or retiring feature — `LAB010`

*Instruction:* `#4-set-the-values-for-the-azure_openai_endpoint-and-azure_openai_api_key-variables`  
*Severity:* info · *At fault:* instruction · *Step:* `850` · *2026-09-07T15:04:03Z*

The instructions depend on legacy Models + endpoints and a per-deployment Target URI. New Foundry uses Build > Models > Deployments and presents a project endpoint plus SDK sample; the equivalent OpenAI Language APIs endpoint is on the Azure resource.

## Ageing guidance (works today)

Nothing here stopped a learner. Each is a step that *succeeded* while following a path the product has moved on from, so it dates the lab rather than breaking it.

- **#3** Superseded or retiring feature — The instructions depend on legacy Models + endpoints and a per-deployment Target URI. New Foundry uses Build > Models > Deployments and presents a project endpoint plus SDK sample; the equivalent OpenAI Language APIs endpoint is on the Azure resource.
  <br>instruction: `#4-set-the-values-for-the-azure_openai_endpoint-and-azure_openai_api_key-variables`

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `310`** · no instruction anchor recorded — Used New Foundry Build > Models instead of the documented legacy Models + endpoints blade.
- **Step `368`** · no instruction anchor recorded — New Foundry exposes a project endpoint and SDK sample rather than the legacy per-deployment Target URI. Used the resource OpenAI Language APIs endpoint and the current deployment identity to configure the equivalent values.

## Verified correct

- Copied .env.example to .env in the LABS root and preserved the marked do-not-modify section.
- The signed-in New Foundry project opened successfully.
- Copied the current project endpoint and set the project name from its final path component.
- Configured the chat deployment identity, OpenAI-compatible endpoint, API version, and key using the current deployment and resource endpoint surfaces.
- Configured both deployed embedding identities with embedding endpoints, API versions, and the resource key in the intended .env variables.
- Copied the GroundingWithBingSearch connection identity from the New Foundry Connected resources table.
- Set tenant, subscription, and resource-group values from the current Foundry and Azure resource overview surfaces.
- Opened AI Search (Foundry IQ), verified the issued service URL, and populated its primary admin key without exposing it in the report.
- Opened the issued Cosmos DB account, verified its URI, and populated the primary key without exposing it in the report.
- Located the issued SQL logical server and set its fully qualified database.windows.net server name.
- Set the Foundry resource name and the OpenAI Language APIs base endpoint from Azure portal > Resource Management > Keys and Endpoint > OpenAI.

## Evidence

37 capture(s), in the order the learner would have seen them.

- [`0045-s05-setup-env-file-open-vscode.jpg`](../images/0045-s05-setup-env-file-open-vscode.jpg)
- [`0046-s05-setup-env-file-wait-vscode.jpg`](../images/0046-s05-setup-env-file-wait-vscode.jpg)
- [`0047-s05-setup-env-file-copy-env-template.jpg`](../images/0047-s05-setup-env-file-copy-env-template.jpg)
- [`0048-s05-setup-env-file-wait-env-open.jpg`](../images/0048-s05-setup-env-file-wait-env-open.jpg)
- [`0049-s05-setup-env-file-open-env.jpg`](../images/0049-s05-setup-env-file-open-env.jpg)
- [`0050-s05-setup-env-file-return-project-details.jpg`](../images/0050-s05-setup-env-file-return-project-details.jpg)
- [`0051-s05-setup-env-file-set-project-values.jpg`](../images/0051-s05-setup-env-file-set-project-values.jpg)
- [`0052-s05-setup-env-file-apply-project-values.jpg`](../images/0052-s05-setup-env-file-apply-project-values.jpg)
- [`0053-s05-setup-env-file-switch-vscode.jpg`](../images/0053-s05-setup-env-file-switch-vscode.jpg)
- [`0054-s05-setup-env-file-choose-env-window.jpg`](../images/0054-s05-setup-env-file-choose-env-window.jpg)
- [`0055-s05-setup-env-file-repair-project-values.jpg`](../images/0055-s05-setup-env-file-repair-project-values.jpg)
- [`0056-s05-setup-env-file-set-project-values-absolute.jpg`](../images/0056-s05-setup-env-file-set-project-values-absolute.jpg)
- [`0057-s05-setup-env-file-edit-project-values.jpg`](../images/0057-s05-setup-env-file-edit-project-values.jpg)
- [`0058-s05-setup-env-file-open-current-deployments.jpg`](../images/0058-s05-setup-env-file-open-current-deployments.jpg)
- [`0059-s05-setup-env-file-current-models.jpg`](../images/0059-s05-setup-env-file-current-models.jpg)
- [`0060-s05-setup-env-file-open-azure-portal.jpg`](../images/0060-s05-setup-env-file-open-azure-portal.jpg)
- [`0061-s05-setup-env-file-resource-endpoints.jpg`](../images/0061-s05-setup-env-file-resource-endpoints.jpg)
- [`0062-s05-setup-env-file-openai-endpoint-tab.jpg`](../images/0062-s05-setup-env-file-openai-endpoint-tab.jpg)
- [`0063-s05-setup-env-file-populate-openai-values.jpg`](../images/0063-s05-setup-env-file-populate-openai-values.jpg)
- [`0064-s05-setup-env-file-search-ai-search-resource.jpg`](../images/0064-s05-setup-env-file-search-ai-search-resource.jpg)
- [`0065-s05-setup-env-file-open-search-services.jpg`](../images/0065-s05-setup-env-file-open-search-services.jpg)
- [`0066-s05-setup-env-file-open-search-resource.jpg`](../images/0066-s05-setup-env-file-open-search-resource.jpg)
- [`0067-s05-setup-env-file-open-search-keys.jpg`](../images/0067-s05-setup-env-file-open-search-keys.jpg)
- [`0068-s05-setup-env-file-search-key-page.jpg`](../images/0068-s05-setup-env-file-search-key-page.jpg)
- [`0069-s05-setup-env-file-search-cosmos.jpg`](../images/0069-s05-setup-env-file-search-cosmos.jpg)
- [`0070-s05-setup-env-file-open-cosmos-resource.jpg`](../images/0070-s05-setup-env-file-open-cosmos-resource.jpg)
- [`0071-s05-setup-env-file-open-cosmos-settings.jpg`](../images/0071-s05-setup-env-file-open-cosmos-settings.jpg)
- [`0072-s05-setup-env-file-cosmos-keys.jpg`](../images/0072-s05-setup-env-file-cosmos-keys.jpg)
- [`0073-s05-setup-env-file-search-sql-server.jpg`](../images/0073-s05-setup-env-file-search-sql-server.jpg)
- [`0074-s05-setup-env-file-open-sql-servers.jpg`](../images/0074-s05-setup-env-file-open-sql-servers.jpg)
- [`0075-s05-setup-env-file-verify-env-placeholders.jpg`](../images/0075-s05-setup-env-file-verify-env-placeholders.jpg)
- [`0076-s05-setup-env-file-locate-search-resource.jpg`](../images/0076-s05-setup-env-file-locate-search-resource.jpg)
- [`0077-s05-setup-env-file-reopen-search-resource.jpg`](../images/0077-s05-setup-env-file-reopen-search-resource.jpg)
- [`0078-s05-setup-env-file-locate-cosmos-resource.jpg`](../images/0078-s05-setup-env-file-locate-cosmos-resource.jpg)
- [`0079-s05-setup-env-file-reopen-cosmos-keys.jpg`](../images/0079-s05-setup-env-file-reopen-cosmos-keys.jpg)
- [`0080-s05-setup-env-file-verify-env-missing-only.jpg`](../images/0080-s05-setup-env-file-verify-env-missing-only.jpg)
- [`0081-s05-setup-env-file-verify-env-complete.jpg`](../images/0081-s05-setup-env-file-verify-env-complete.jpg)
