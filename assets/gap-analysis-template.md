# Gap analysis

**Lab.** {{lab_name}} — instance `{{instance_id}}`  
**Run.** `{{run_id}}` started {{started_utc}}, status **{{run_status}}**  
**Instructions.** `{{instruction_sha256_prefix}}…` ({{instruction_line_count}} lines)

This report is what a simulated learner encountered while doing the lab. It
records what was verified correct as well as what was wrong, because a list of
failures alone cannot distinguish a checked step from a skipped one.

This is the run-level roll-up. Each linked section report follows
[`section-report-template.md`](section-report-template.md), including any
deviation the simulated learner took from the written instructions.

## Can a learner complete this lab?

{{YES | NO | PARTIALLY | UNKNOWN}} — {{completion_summary}}

> {{Include when scoped: selected and unselected section counts, and state that
> this does not answer whether the whole lab is completable.}}

## Blockers

{{Omit this section when there are no blockers.}}

- **{{finding_name}}** `{{verdict_code}}` *({{section}})* — {{observed_blocker}}
  <br>evidence: step `{{trace_sequence}}`, instruction `{{task_anchor}}`

## Coverage

**{{completed_sections}} of {{selected_sections}} selected sections completed
({{coverage_percent}}%)** across {{recorded_steps}} recorded steps and
{{heartbeats}} heartbeats.

**{{unselected_sections}} of {{total_sections}} sections were not selected for
this run.**

| Section | Module | Status | Steps | Findings | Report |
|---|---|---|---|---|---|
| {{section_title}} | {{module}} | {{done / blocked / part / not reached / not selected}} | {{count}} | {{count_or_dash}} | [section]({{relative_report_path}}) |

> **{{never_reached_count}} sections were never reached.** They are unknown, not
> correct.

### What the setup preflight could not check

{{Omit when the preflight has no unchecked items.}}

- {{unchecked_condition}}

## Findings

{{verdict_code}} ×{{count}}

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** —
lab profile / image / subscription owner

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

**Instruction defects — the lab text is wrong** — lab author

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

**Unattributed — the evidence does not yet say which side is wrong** — needs
one more observation before it can be routed

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

Findings are grouped by lab below. Numbering is global and ordered by severity,
so a finding keeps its number wherever it is read.

| ID | Sev | Lab | Gap |
|---|---|---|---|
| #{{finding_number}} | {{critical / major / minor / info}} | {{lab_name}} | {{finding_name}} |

### {{lab_name}}

{{One `###` heading per lab, in the order the labs' first findings appear. A
section's lab is its module title; a single-lab document uses the section title.
Repeat the block below for every finding in that lab.}}

#### {{finding_number}}. {{severity_icon}} {{finding_name}} — `{{verdict_code}}`

*Section:* {{section_title}}  
*Instruction:* `{{task_anchor}}`  
*Severity:* {{critical / major / minor / info}} · *At fault:* {{instruction / setup / undetermined}}

**The lab says**

> {{instruction_text}}

**Actually observed:** `{{observation}}`

{{Evidence-backed explanation, reproduction detail, impact, and the evidence
that would settle an undetermined owner.}}

![evidence]({{relative_image_path}})

## Structural problems in the instruction content

{{Omit when no parser anomalies were found.}}

- {{severity_icon}} **`{{anomaly_code}}`** {{anomaly_message}}

## Ageing guidance (works today)

{{Omit when no superseded or retiring path was observed. Placed immediately
before the passes it qualifies: every entry here is a step that succeeded, so a
report can be entirely green and still describe a lab the product has moved on
from. Numbers are the same global finding numbers used above.}}

- **#{{finding_number}}** {{finding_name}} *({{section}})* — {{observed}}
  <br>instruction: `{{task_anchor}}`

## Verified correct

{{confirmation_count}} instruction(s) were checked and matched reality:

- **{{section_title}}** — {{positive_evidence}}

## Deferred

{{Omit when no work was deliberately postponed.}}

- **{{section_title}}** — {{reason}}

## Environment transients (recorded, not reported as defects)

{{Omit when there were no recovered transient failures.}}

- {{transient_observation}}

## Withdrawn judgements

{{Omit when no finding or confirmation was retracted.}}

- `{{original_verdict}}` on `{{original_action}}` — {{retraction_reason}}

## Run events

{{Omit when the run manifest has no events.}}

- `{{timestamp}}` **{{event_kind}}** — {{event_detail}}
