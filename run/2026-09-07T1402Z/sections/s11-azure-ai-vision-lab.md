# Azure AI Vision - Lab

*Section* `s11-azure-ai-vision-lab`

**Lab.** WorkshopPLUS - Azure AI Platform and Services — instance `3ef430fc-3d4a-4e16-a6fa-a0f6c3805712`  
**Run.** ``  
**Status.** walked to the end  
**Instructions.** `#azure-ai-vision---lab`  
**Lab clock.** 1,440 min at start → 1,440 min at end  
**Evidence.** 342 recorded step(s), 46 heartbeat(s), 7 finding(s)

**Can a learner finish this section?** **NO** — a learner cannot complete this as written

## Blockers

These stop a learner outright. Everything after this point was observed either before the block or around it.

- **Defective sample code** `LAB009` — The Exercise 3/4 notebook cannot read the .env the section tells the learner to edit. LabFiles/AI_vision_services_lab.ipynb does env_file = '.env' then load_dotenv(env_file) -- a relative path that resolves against the notebook's own folder, 'Lab 04 - AI-Vision\LabFiles', while the file the lab has the learner edit is the shared LABS root .env. Executed the notebook unchanged with nbconvert --execute --allow-errors: the first OCR cell died with AttributeError: 'NoneType' object has no attribute 'rstrip' at COMPUTER_VISION_ENDPOINT.rstrip('/'), i.e. os.getenv returned None. Confirmed with a direct oracle run from the notebook's folder: load_dotenv('.env') returned found_local False while load_dotenv on the LABS root .env returned found_root True and endpoint_ok True. Copying the root .env beside the notebook removed the AttributeError, so the path is the whole cause. Nothing in Exercise 3 or 4 can run as shipped.
  <br>evidence: step `1652`, instruction `#azure-ai-vision---lab`
- **Defective sample code** `LAB009` — Even with the .env resolvable, Exercise 3's OCR call is dead: the notebook hardcodes api-version=2023-02-01-preview and the service answers HTTP 410. Observed output: 'OCR error: 410 Client Error: Gone for url: https://cv-64827025.cognitiveservices.azure.com/computervision/imageanalysis:analyze?api-version=2023-02-01-preview&features=read'. This is the notebook, not the environment: the same image, key and endpoint against api-version=2024-02-01&features=read returned HTTP 200 and real text ('modelVersion':'2023-10-01', readResult blocks with 'NATIONAL IDENTITY CARD'). So the resource created in Exercise 1 is healthy and only the pinned preview API version is retired. Worse, the cell catches the error and prints it, so it completes green having produced no OCR at all.
  <br>evidence: step `1653`, instruction `#azure-ai-vision---lab`

## Findings

**LAB002** ×2 · **LAB005** ×1 · **LAB009** ×4

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** — lab profile / image / subscription owner

- **#4** Missing resource or SKU (`LAB002`)

**Instruction defects — the lab text is wrong** — lab author

- **#1** Defective sample code (`LAB009`)
- **#2** Defective sample code (`LAB009`)
- **#3** Defective sample code (`LAB009`)
- **#5** Missing resource or SKU (`LAB002`)
- **#6** Removed feature (`LAB005`)
- **#7** Defective sample code (`LAB009`)

### 1. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* critical · *At fault:* instruction · *Step:* `1652` · *2026-09-07T17:22:49Z*

The Exercise 3/4 notebook cannot read the .env the section tells the learner to edit. LabFiles/AI_vision_services_lab.ipynb does env_file = '.env' then load_dotenv(env_file) -- a relative path that resolves against the notebook's own folder, 'Lab 04 - AI-Vision\LabFiles', while the file the lab has the learner edit is the shared LABS root .env. Executed the notebook unchanged with nbconvert --execute --allow-errors: the first OCR cell died with AttributeError: 'NoneType' object has no attribute 'rstrip' at COMPUTER_VISION_ENDPOINT.rstrip('/'), i.e. os.getenv returned None. Confirmed with a direct oracle run from the notebook's folder: load_dotenv('.env') returned found_local False while load_dotenv on the LABS root .env returned found_root True and endpoint_ok True. Copying the root .env beside the notebook removed the AttributeError, so the path is the whole cause. Nothing in Exercise 3 or 4 can run as shipped.

### 2. [!!] Defective sample code — `LAB009`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* critical · *At fault:* instruction · *Step:* `1653` · *2026-09-07T17:22:50Z*

Even with the .env resolvable, Exercise 3's OCR call is dead: the notebook hardcodes api-version=2023-02-01-preview and the service answers HTTP 410. Observed output: 'OCR error: 410 Client Error: Gone for url: https://cv-64827025.cognitiveservices.azure.com/computervision/imageanalysis:analyze?api-version=2023-02-01-preview&features=read'. This is the notebook, not the environment: the same image, key and endpoint against api-version=2024-02-01&features=read returned HTTP 200 and real text ('modelVersion':'2023-10-01', readResult blocks with 'NATIONAL IDENTITY CARD'). So the resource created in Exercise 1 is healthy and only the pinned preview API version is retired. Worse, the cell catches the error and prints it, so it completes green having produced no OCR at all.

### 3. [!] Defective sample code — `LAB009`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* major · *At fault:* instruction · *Step:* `1654` · *2026-09-07T17:23:11Z*

Exercise 4 (Image Analysis, notebook sections 03-07) produces nothing, and blames the learner while doing it. Each cell assigns a literal placeholder string instead of reading a variable: IMAGEPATH_SEARCH = 'SEARCH_IMAGE_PATH', IMAGEPATH_DENSECAPS = 'DENSE_CAP_IMAGE_PATH', IMAGEPATH_CAPTIONS = 'IMAGEPATH_CAPTIONS', IMAGEPATH_TAGS = 'IMAGEPATH_TAGS', IMAGEPATH_CROP = 'IMAGEPATH_CROP'. The guard os.path.isfile() is then false for all five, so every cell takes the else branch and prints 'IMAGEPATH_X is not defined or the file does not exist. Please check your .env file.' -- pointing the learner at a file that could not fix it, since the value is never read from the environment at all. Reproduced on both executions of the notebook, including the one where the .env was resolvable. Compounding it, LabFiles/images contains only ocr_image.png, so none of the five images exist either. Not one of the five Image Analysis capabilities the section teaches (Image Retrieval, Dense Captions, Captions, Tags, Smart Crop) returns a result.

### 4. [!] Missing resource or SKU — `LAB002`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* major · *At fault:* setup · *Step:* `1655` · *2026-09-07T17:23:11Z*

Exercise 3 says 'Inside Visual Studio Code, open the .env file. Set the following values: COMPUTER_VISION_API_KEY ... COMPUTER_VISION_ENDPOINT'. Neither variable exists in the file. Scanned C:\Users\Admin\Desktop\LABS\.env and the .env.example it was copied from for COMPUTER_VISION, IMAGEPATH, SEARCH_IMAGE, DENSE_CAP and VIDEO_INDEXER: both files returned nothing for every pattern. So there is no line to set -- the learner has to know to add the keys, with exactly the spelling the notebook expects, and the six image-path variables the notebook also reads are documented nowhere in the section. Verified by shape only, printing variable names and value lengths, never values.

### 5. [~] Missing resource or SKU — `LAB002`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `1339` · *2026-09-07T16:41:08Z*

Exercise 1 lists the values to use as Region, Name, Pricing Tier and the policy checkbox, but the Create Computer Vision form also requires 'Resource group', which the instruction never mentions. The field ships empty and the blade cannot be submitted until it is set. A learner following the value list literally stalls on a required field with no guidance about which resource group to pick (azureaiworkshoprg is the only one present). Observed on the live Create Computer Vision blade, Basics tab.

### 6. [~] Removed feature — `LAB005`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `1425` · *2026-09-07T16:48:59Z*

Exercise 2 orders the steps as: tick Acknowledge, select/create the resource, click Confirm, then 'Select an image and then click JSON'. On the live studio, Confirm re-renders the acknowledgement control (its label changes from 'incur usage to my Azure account' to 'incur usage to resource faceresource-64827025 in my Azure account') and the tick is cleared. A learner who follows the written order selects a sample and gets only 'Please acknowledge the resource usage policy above in order to try out Detect faces in an image' with no detection at all. Observed directly: capture 0184 shows the box cleared with the demo refusing to run, capture 0185 shows detection succeeding immediately after re-ticking the same box with nothing else changed. The instruction needs a step to re-tick the acknowledgement after Confirm.

### 7. [~] Defective sample code — `LAB009`

*Instruction:* `#azure-ai-vision---lab`  
*Severity:* minor · *At fault:* instruction · *Step:* `1656` · *2026-09-07T17:23:12Z*

The section states 'Video Indexer is not included' and that the previous exercise referenced a notebook section not present in this repository, but the shipped notebook still contains the Video Indexer cell (VIDEO_INDEXER_SAMPLEPATH = 'VIDEO_INDEXER_SAMPLEPATH', VIDEO_INDEXER_LOCATION = os.getenv('VIDEO_INDEXER...')). Executing the notebook end to end raises TypeError from that cell on both runs. The text and the artifact disagree: a learner running all cells hits a traceback for an exercise the text says was removed.

## Deviations from the written instructions

These are actions the simulated learner took by a route the lab did not describe. They are reported whether or not the alternate route revealed a defect.

- **Step `1446`** · no instruction anchor recorded — Navigated straight to the cv-64827025 Keys and Endpoint blade by URL rather than re-walking Foundry > More services > Computer vision; that navigation path was already exercised and verified earlier in this section for Exercise 1.
- **Step `1554`** · no instruction anchor recorded — Wrote the two COMPUTER_VISION values into .env from the VS Code integrated terminal instead of typing them into the open .env editor, so no key value was ever rendered on screen or captured in evidence. Same file, same values, same learner-available tool.

## Verified correct

- Exercise 1 (Provision Azure Resources) works as written on the current portal UX. portal.azure.com > search 'Microsoft Foundry' > Foundry hub > left panel 'More services' > 'Computer vision' > Create. Form accepted Subscription MIPDG-lod53051908, Resource group azureaiworkshoprg, Region (US) East US, Name cv-64827025, Pricing tier 'Standard S1 (10 Calls per second)', Responsible AI checkbox. Review + create validated, Create submitted, and the deployment blade then read 'Your deployment is complete' with resource cv-64827025 of type Microsoft.CognitiveServices/accounts Created (deployment ComputerVisionCreate-20260907093654). Verified from the deployment artifact, not from a green tick alone.
- Exercise 2 (Face Analysis) completes on the current Vision Studio. portal.vision.cognitive.azure.com redirects to /gallery/face and, after Sign in, 'Detect faces in an image' > acknowledge > 'Please select a resource' > subscription MIPDG-lod53051908 > 'Create a new resource' accepted Name faceresource-64827025, Resource group azureaiworkshoprg, Resource type CognitiveServices, Location East US, Price tier S0, then Confirm. Real API output was read, not just a tick: sample image 1 returned one bounding box with 'Face #1 / Face mask: no' and the JSON tab showed recognitionModel recognition_01 with faceRectangle {width 141, height 201, left 470, top 186} and faceLandmarks (pupilLeft, pupilRight, noseTip, mouthLeft, mouthRight). Iterating to sample image 3 returned two boxes and Face #1 and Face #2.

## Evidence

52 capture(s), in the order the learner would have seen them.

- [`0161-s11-azure-ai-vision-search-computer-vision.jpg`](../images/0161-s11-azure-ai-vision-search-computer-vision.jpg)
- [`0162-s11-azure-ai-vision-open-foundry-resource-list.jpg`](../images/0162-s11-azure-ai-vision-open-foundry-resource-list.jpg)
- [`0163-s11-azure-ai-vision-s11-read-instructions.jpg`](../images/0163-s11-azure-ai-vision-s11-read-instructions.jpg)
- [`0164-s11-azure-ai-vision-expand-more-services.jpg`](../images/0164-s11-azure-ai-vision-expand-more-services.jpg)
- [`0165-s11-azure-ai-vision-open-computer-vision.jpg`](../images/0165-s11-azure-ai-vision-open-computer-vision.jpg)
- [`0166-s11-azure-ai-vision-cv-create-click.jpg`](../images/0166-s11-azure-ai-vision-cv-create-click.jpg)
- [`0167-s11-azure-ai-vision-cv-rg-dropdown.jpg`](../images/0167-s11-azure-ai-vision-cv-rg-dropdown.jpg)
- [`0168-s11-azure-ai-vision-cv-rg-select.jpg`](../images/0168-s11-azure-ai-vision-cv-rg-select.jpg)
- [`0169-s11-azure-ai-vision-cv-pricing-dropdown.jpg`](../images/0169-s11-azure-ai-vision-cv-pricing-dropdown.jpg)
- [`0170-s11-azure-ai-vision-cv-tier-and-terms.jpg`](../images/0170-s11-azure-ai-vision-cv-tier-and-terms.jpg)
- [`0171-s11-azure-ai-vision-cv-accept-terms.jpg`](../images/0171-s11-azure-ai-vision-cv-accept-terms.jpg)
- [`0172-s11-azure-ai-vision-cv-create-submit.jpg`](../images/0172-s11-azure-ai-vision-cv-create-submit.jpg)
- [`0173-s11-azure-ai-vision-cv-create-verify.jpg`](../images/0173-s11-azure-ai-vision-cv-create-verify.jpg)
- [`0174-s11-azure-ai-vision-open-vision-studio.jpg`](../images/0174-s11-azure-ai-vision-open-vision-studio.jpg)
- [`0175-s11-azure-ai-vision-vision-studio-signin.jpg`](../images/0175-s11-azure-ai-vision-vision-studio-signin.jpg)
- [`0176-s11-azure-ai-vision-detect-faces-open.jpg`](../images/0176-s11-azure-ai-vision-detect-faces-open.jpg)
- [`0177-s11-azure-ai-vision-face-ack-select-resource.jpg`](../images/0177-s11-azure-ai-vision-face-ack-select-resource.jpg)
- [`0178-s11-azure-ai-vision-face-choose-subscription.jpg`](../images/0178-s11-azure-ai-vision-face-choose-subscription.jpg)
- [`0179-s11-azure-ai-vision-face-sub-and-newres.jpg`](../images/0179-s11-azure-ai-vision-face-sub-and-newres.jpg)
- [`0180-s11-azure-ai-vision-face-create-new-resource.jpg`](../images/0180-s11-azure-ai-vision-face-create-new-resource.jpg)
- [`0181-s11-azure-ai-vision-face-fill-name-rg.jpg`](../images/0181-s11-azure-ai-vision-face-fill-name-rg.jpg)
- [`0182-s11-azure-ai-vision-face-rg-tier.jpg`](../images/0182-s11-azure-ai-vision-face-rg-tier.jpg)
- [`0183-s11-azure-ai-vision-face-create-resource.jpg`](../images/0183-s11-azure-ai-vision-face-create-resource.jpg)
- [`0184-s11-azure-ai-vision-face-confirm-and-sample.jpg`](../images/0184-s11-azure-ai-vision-face-confirm-and-sample.jpg)
- [`0185-s11-azure-ai-vision-face-reack-and-detect.jpg`](../images/0185-s11-azure-ai-vision-face-reack-and-detect.jpg)
- [`0186-s11-azure-ai-vision-face-json-view.jpg`](../images/0186-s11-azure-ai-vision-face-json-view.jpg)
- [`0187-s11-azure-ai-vision-face-sample-iterate.jpg`](../images/0187-s11-azure-ai-vision-face-sample-iterate.jpg)
- [`0188-s11-azure-ai-vision-open-vscode.jpg`](../images/0188-s11-azure-ai-vision-open-vscode.jpg)
- [`0189-s11-azure-ai-vision-portal-keys-endpoint.jpg`](../images/0189-s11-azure-ai-vision-portal-keys-endpoint.jpg)
- [`0190-s11-azure-ai-vision-focus-vscode-windows.jpg`](../images/0190-s11-azure-ai-vision-focus-vscode-windows.jpg)
- [`0191-s11-azure-ai-vision-check-taskbar-state.jpg`](../images/0191-s11-azure-ai-vision-check-taskbar-state.jpg)
- [`0192-s11-azure-ai-vision-focus-env-window.jpg`](../images/0192-s11-azure-ai-vision-focus-env-window.jpg)
- [`0193-s11-azure-ai-vision-env-shape-check.jpg`](../images/0193-s11-azure-ai-vision-env-shape-check.jpg)
- [`0194-s11-azure-ai-vision-env-vision-scan.jpg`](../images/0194-s11-azure-ai-vision-env-vision-scan.jpg)
- [`0195-s11-azure-ai-vision-labfiles-listing.jpg`](../images/0195-s11-azure-ai-vision-labfiles-listing.jpg)
- [`0196-s11-azure-ai-vision-nb-env-names.jpg`](../images/0196-s11-azure-ai-vision-nb-env-names.jpg)
- [`0197-s11-azure-ai-vision-nb-env-names2.jpg`](../images/0197-s11-azure-ai-vision-nb-env-names2.jpg)
- [`0198-s11-azure-ai-vision-nb-env-names3.jpg`](../images/0198-s11-azure-ai-vision-nb-env-names3.jpg)
- [`0199-s11-azure-ai-vision-env-template-scan.jpg`](../images/0199-s11-azure-ai-vision-env-template-scan.jpg)
- [`0200-s11-azure-ai-vision-nb-dotenv-usage.jpg`](../images/0200-s11-azure-ai-vision-nb-dotenv-usage.jpg)
- [`0201-s11-azure-ai-vision-nb-source-dump.jpg`](../images/0201-s11-azure-ai-vision-nb-source-dump.jpg)
- [`0202-s11-azure-ai-vision-env-set-vision.jpg`](../images/0202-s11-azure-ai-vision-env-set-vision.jpg)
- [`0203-s11-azure-ai-vision-nb-run-start.jpg`](../images/0203-s11-azure-ai-vision-nb-run-start.jpg)
- [`0204-s11-azure-ai-vision-nb-execute.jpg`](../images/0204-s11-azure-ai-vision-nb-execute.jpg)
- [`0205-s11-azure-ai-vision-nb-parse-1.jpg`](../images/0205-s11-azure-ai-vision-nb-parse-1.jpg)
- [`0206-s11-azure-ai-vision-nb-parse-2.jpg`](../images/0206-s11-azure-ai-vision-nb-parse-2.jpg)
- [`0207-s11-azure-ai-vision-nb-ocr-traceback.jpg`](../images/0207-s11-azure-ai-vision-nb-ocr-traceback.jpg)
- [`0208-s11-azure-ai-vision-dotenv-path-oracle.jpg`](../images/0208-s11-azure-ai-vision-dotenv-path-oracle.jpg)
- [`0209-s11-azure-ai-vision-nb-rerun-fixed.jpg`](../images/0209-s11-azure-ai-vision-nb-rerun-fixed.jpg)
- [`0210-s11-azure-ai-vision-nb-parse-fixed.jpg`](../images/0210-s11-azure-ai-vision-nb-parse-fixed.jpg)
- [`0211-s11-azure-ai-vision-ocr-current-api-probe.jpg`](../images/0211-s11-azure-ai-vision-ocr-current-api-probe.jpg)
- [`0212-s11-azure-ai-vision-cleanup-scratch.jpg`](../images/0212-s11-azure-ai-vision-cleanup-scratch.jpg)
