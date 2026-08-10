# {{section_title}}

*Section* `{{section_id}}` · *Module* {{module}}

**Lab.** {{lab_name}} — instance `{{instance_id}}`  
**Run.** `{{run_id}}`  
**Status.** {{walked to the end / blocked part-way / skipped / not selected / still in progress / not started}}  
**Instructions.** `{{section_anchor}}`  
**Lab clock.** {{minutes_at_start}} min at start → {{minutes_at_end}} min at end  
**Evidence.** {{recorded_steps}} recorded step(s), {{heartbeats}} heartbeat(s), {{findings}} finding(s)

**Can a learner finish this section?** **{{YES | NO | PARTIALLY | UNKNOWN}}** —
{{completion_summary}}

> {{Optional section note.}}

## Blockers

{{Omit when nothing stops a learner outright.}}

- **{{finding_name}}** `{{verdict_code}}` — {{observed_blocker}}
  <br>evidence: step `{{trace_sequence}}`, instruction `{{task_anchor}}`

## What the lab asks the learner to do

{{Omit when the instruction outline has no numbered tasks for this section.}}

- {{task_text}}

## Findings

{{When the section is finished with no findings: `No defects recorded in this
section.` When unfinished: state that no findings yet does not mean the section
is clean. Otherwise render the verdict counts and blocks below.}}

**{{verdict_code}}** ×{{count}}

### Who fixes what

**Setup defects — the environment cannot deliver what the text describes** —
lab profile / image / subscription owner

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

**Instruction defects — the lab text is wrong** — lab author

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

**Unattributed — the evidence does not yet say which side is wrong** — needs
one more observation before it can be routed

- **#{{finding_number}}** {{finding_name}} (`{{verdict_code}}`)

### {{finding_number}}. {{severity_icon}} {{finding_name}} — `{{verdict_code}}`

*Instruction:* `{{task_anchor}}`  
*Severity:* {{critical / major / minor / info}} · *At fault:* {{instruction / setup / undetermined}} · *Step:* `{{trace_sequence}}` · *{{timestamp}}*

**The lab says**

> {{instruction_text}}

**Actually observed:** `{{observation}}`

{{Evidence-backed explanation, reproduction detail, impact, and the evidence
that would settle an undetermined owner.}}

![evidence]({{relative_image_path}})

## Ageing guidance (works today)

{{Omit when no superseded or retiring path was observed. Each entry is a step
that succeeded, so it qualifies the verified passes that follow.}}

- **#{{finding_number}}** {{finding_name}} — {{observed}}
  <br>instruction: `{{task_anchor}}`

## Deviations from the written instructions

{{Omit when the simulated learner followed the written path exactly. Record
every departure, including alternate navigation, additional mandatory steps,
manual fixes, configuration changes, or workarounds used to finish a task.
A deviation is not automatically a defect: keep its verdict and severity
separate.}}

- **Step `{{trace_sequence}}`** · instruction `{{task_anchor}}` —
  {{what_the_simulated_learner_did_differently}}
  <br>outcome: {{why_it_was_needed_and_what_happened}}

  ![deviation evidence]({{relative_image_path}})

## Verified correct

{{Do not count a deviation as verification that the written instruction was
correct. If no explicit confirmations remain, say so.}}

- {{positive_evidence}}

## Deferred

{{Omit when no work was deliberately postponed.}}

_Postponed by the walk, not by the lab. These say nothing about the lab._

- {{reason}}

## Environment transients (not defects)

{{Omit when there were no recovered transient failures.}}

- {{transient_observation}}

## Withdrawn judgements

{{Omit when no finding, confirmation, or deviation was retracted.}}

- step `{{retracted_sequence}}` — {{retraction_reason}}

## Evidence

{{Omit when no captures were recorded. List captures in learner order.}}

{{capture_count}} capture(s), in the order the learner would have seen them.

- [`{{image_name}}`]({{relative_image_path}}) — {{optional_analysis_note}}
