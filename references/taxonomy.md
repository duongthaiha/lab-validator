# Verdict taxonomy

Generated from `src/lab_validator/taxonomy.py`, which is the single source of
truth. If this file and the module disagree, the module wins — regenerate with:

```powershell
python -c "import sys; sys.path.insert(0,'src'); from lab_validator import taxonomy as t; [print(f'| `{c}` | {v.name} | {v.typical_domain} | {v.default_severity} | {v.definition} |') for c,v in t.BY_CODE.items()]"
```

> Why this file is generated rather than written: the codes previously lived in
> three places that disagreed. One module accepted `LAB009`, the renderer's name
> table stopped at `LAB008`, and no document defined either. Nothing failed —
> and **40 findings, the second-largest category in the run, printed as
> `LAB009 — LAB009` in the delivered report.**

## Codes

| Code | Name | Typical domain | Severity | Definition |
|---|---|---|---|---|
| `PASS` | Verified correct | instruction | — | The instruction was followed and the product behaved as described. As important as any failure code: a differ with no positive evidence cannot tell 'verified correct' from 'never reached'. |
| `LAB000` | Environment transient | setup | — | A failure that did not reproduce, or that resolved on retry. Recorded so the trace stays honest, never reported as a finding. |
| `LAB001` | Retired or renamed model | either | major | A model the instructions name cannot be used. An instruction defect when the text names a model that is gone; a setup defect when the model is alive but this subscription or region refuses it. |
| `LAB002` | Missing resource or SKU | either | major | Something the learner is told to find is not there. An instruction defect when the text names a SKU that never existed; a setup defect when the lab was supposed to provision it and did not. |
| `LAB003` | Changed UI label or inconsistent structure | instruction | minor | The control exists but is not called what the instructions call it, or the instructions contradict themselves. |
| `LAB004` | Moved navigation | instruction | minor | The destination exists but is not reached the way the instructions describe. |
| `LAB005` | Removed feature | instruction | major | A capability the instructions depend on no longer exists in the product at all. |
| `LAB006` | Broken link | instruction | minor | A URL the instructions offer does not resolve, or resolves to something other than what it promises. |
| `LAB007` | Timing or quota | setup | major | The step cannot complete in the time or capacity available — including 'this never finishes'. Usually the environment, not the text, unless the text promises a duration it cannot honour. |
| `LAB008` | Undocumented mandatory step | instruction | major | Something the learner must do to proceed that the instructions never mention. Found by doing the lab, never by reading it. |
| `LAB009` | Defective sample code | either | major | Code or configuration shipped with the lab is wrong — it swallows failure, produces no output, or reports success having done nothing. The most dangerous class, because it hides every other defect from the learner. |
| `LAB010` | Superseded or retiring feature | instruction | info | The instructions teach a path the product has moved on from — a 'classic' experience, a superseded API version, a feature with an announced retirement. Unique among the codes in that the step *succeeds*: it is a defect with a deadline rather than a defect today, and the only one that has to be looked for rather than tripped over. An instruction defect, because the newer path working here is what makes the older one superseded; if the environment cannot offer the newer path, that is LAB002 or LAB007 instead. |
| `BLOCKED` | Could not be attempted | undetermined | — | A dependency failed, so this was never reached. A status, not a finding: the blocker itself is the finding, and the walk should carry on reading rather than stop here. |
| `DEFERRED` | Deliberately not attempted | undetermined | — | Skipped on purpose, and requires a justification that survives review. Distinct from BLOCKED: nothing prevented it. |

**Statuses, not findings:** `PASS`, `LAB000`, `BLOCKED`, `DEFERRED`. These never
appear in the findings list and never count toward a severity roll-up.

**Domains:** `instruction`, `setup`, `undetermined`.
**Severities:** `critical`, `major`, `minor`, `info`.

## Choosing between neighbours

These are the pairs that get confused, and the question that separates them.

| Confusion | Ask |
|---|---|
| `LAB003` vs `LAB004` | Is the *control* misnamed, or is the *route to it* wrong? Label → 003. Path → 004. |
| `LAB004` vs `LAB005` | Can you reach it by *any* route? Yes → 004 (moved). No → 005 (removed). |
| `LAB002` vs `LAB005` | Is the thing absent *here* or absent *from the product*? This environment → 002. Everywhere → 005. |
| `LAB001` vs `LAB007` | Is the model gone, or is it present-but-refused? Gone → 001. Refused for capacity/quota → 007. |
| `LAB008` vs `LAB003` | Did the text describe the step *badly*, or *not at all*? Badly → 003. Not at all → 008. |
| `LAB009` vs `LAB000` | Does it reproduce? Reproducible defect in shipped code → 009. Did not reproduce → 000. |
| `LAB010` vs `LAB005` | Does the old path still work? Yes → 010 (superseded). No → 005 (removed). 010 is what 005 was a year ago. |
| `LAB010` vs `LAB003` | Is the *name* stale, or the *approach*? A renamed button on the current path → 003. The current path is elsewhere entirely → 010. |
| `LAB010` vs `PASS` | Both apply — the step worked. Record the `PASS` for what you verified, and `LAB010` separately for the ageing. One does not displace the other. |
| `BLOCKED` vs `DEFERRED` | Were you *prevented*, or did you *choose*? Prevented → BLOCKED. Chose → DEFERRED, and justify it. |

## Severity

Severity is about **the learner's experience**, not about how annoying the
defect is to fix.

| Severity | Test |
|---|---|
| `critical` | The lab cannot be completed. A learner following the text hits a wall with no route past it. |
| `major` | A section cannot be completed, or the learner completes it believing something false. |
| `minor` | The learner is slowed or confused but gets there. |
| `info` | Worth telling the author; costs the learner nothing. |

Note that **"the learner completes it believing something false" is major, not
minor.** A step that silently does nothing and prints a success message is more
damaging than one that fails loudly, because it propagates.

`LAB010` defaults to `info` because the severity scale measures *this* learner's
experience, and a superseded path costs them nothing — it works. Raise it when
the cost has a date attached: `minor` when the product labels the path legacy or
classic, `major` when a retirement date is published and the lab will stop
working on it. Severity is the only place that distinction can be recorded, so
leaving everything at `info` makes an ageing lab indistinguishable from a
pristine one.

## Completability

A report opens with one structural answer, derived — never written by hand:

| Verdict | Rule |
|---|---|
| `no` | Any `BLOCKED` section, or any `critical` finding. |
| `partially` | No blockers, but at least one `major` finding. |
| `unknown` | No blockers and no majors, but not every section was walked. |
| `yes` | Every section walked, no blockers, nothing above `minor`. |

Two deliberate choices in that table:

- **`DEFERRED` is never a blocker.** It is a fact about the walk, not about the lab.
- **Absence of evidence is never a `yes`.** An unwalked lab is `unknown`,
  because the alternative lets a run that did almost nothing report success.
