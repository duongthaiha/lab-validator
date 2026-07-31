# Judgement

The rules that decide whether a validation report is worth reading. Every one
was paid for in a defect that was missed, overstated, or reported to the wrong
person. **Deliberately platform-agnostic** — none of this depends on any
particular lab host, and it transfers to any "walk a documented procedure and
report where it diverges" problem.

---

## 1. Take the highest rung that can answer the question

| Rung | Surface | Reliability |
|---|---|---|
| 1 | Out-of-band oracle (a product's own lifecycle/metadata API, package registry, upstream source at the pinned version) | Deterministic |
| 2 | The platform's own API | Deterministic |
| 3 | The application's client API | High |
| 4 | DOM / accessibility tree | Good |
| 5 | Vision (screenshot → model → click) | Poor |

Never answer with vision what an API can answer. Every rung down costs an order
of magnitude in reliability, and a flaky observation is worse than no
observation because it generates findings that cannot be reproduced.

A large fraction of high-value findings need **no session at all**. Package
metadata and upstream source at the exact version a procedure installs will tell
you: whether a pinned dependency can even be installed on the stated platform,
whether the documented CLI shape still matches, whether the tool's *defaults*
match what the text told you to create, whether the stated language version
range is satisfiable. Cheap, offline, and available for anything that pins a
package.

## 2. Partial runs must be valuable

Reliability maths guarantees most long runs end early. Design so that stopping
at any point leaves something worth reading:

- Write each section's report **as it is walked**, never at the end.
- Make segments resumable.
- Put coverage at the top, so a partial run cannot be misread as a complete one.

## 3. Capture first, judge later

Record raw observations; run rules over the trace afterwards. Never couple *what
did I see* to *is that wrong*. Coupling them means every rule change requires a
new run, and a run costs hours.

## 4. A defect needs an oracle or a repeated observation

Never a single transient. One reference run withdrew **6 of 36** findings on
re-check; every withdrawal came from trusting something seen once.

Corollary: **re-verify a blocker's factual claim before publishing it.** A
finding asserting "zero deployments exist" was refuted by one list command
showing one. An overstated finding costs more credibility than a missing one,
because it is precisely what the owner will check first and then use to dismiss
the rest of the report.

## 5. Negative claims need exhaustive evidence

"X is missing" is a measurement, not a glance. State where you looked. A claim
that a menu item is gone, made from one screenshot of one blade, will be
disproved by anyone who scrolls.

## 6. A green tick is not an observation

Read the artifact the step was meant to produce, not the signal that it ran.

This matters more than it sounds. The worst defect class in real labs is **code
that succeeds while failing** — a cell that catches every exception and prints
nothing, a script whose only output is its own progress bar, a command that
exits 0 having done nothing. A validator that trusts success signals reproduces
exactly the bug it was sent to find, and reports the lab as working.

Practical rule: after any execution step, grep the output for
`Error|Traceback|Exception|4\d\d|5\d\d` **and** assert that the expected artifact
exists with non-trivial content. *No error output* is not success.

## 7. Do the work; do not check reachability

Navigating to the page containing the button proves the page exists. It proves
nothing about the button, the operation behind it, or the twelve instructions
that follow. Reachability checking produces reports that look thorough and find
nothing, because every real defect is one layer below the surface it inspects.

## 8. Record what was *not* reached as loudly as what failed

An absent finding must never be readable as a pass. Coverage goes at the top of
the report, before any finding. If the run could not check a whole class of
thing — because no expectations were supplied, or a dependency was down — say
so where nobody can miss it. Silence reads as "nothing was expected and nothing
was missing", which is the opposite of the truth.

## 9. Blocked is a status, not a finding

**The most generalisable lesson here.**

A blocker terminates *the learner's* path, so it feels like it terminates *the
validator's* path too. It does not. The instructions past the blocker are still
claims about the world, and most can be checked without ever clearing the block:

| Checkable without clearing the blocker |
|---|
| Does the command still have the shape the text assumes? |
| Do the tool's **defaults** match what the text told you to create? |
| Does the config the procedure builds actually reference the things it told you to make? |
| Can the prerequisite even be installed on the stated platform? |
| Does the stated version range match the package metadata? |
| Is every URL well-formed and does it resolve? |

One section sat for two runs as a single line — *blocked* — which felt like a
complete answer. Re-opening it produced **six further independently-fixable
defects** and corrected the blocker's own factual claim.

Two operational rules:

1. **Never let a section end at `BLOCKED` with a single finding.** Treat the
   blocker as the *first* finding and keep reading. Budget a static pass over
   the remainder.
2. **A section whose only record is `BLOCKED` is incomplete, not covered.**
   Coverage counted by *sections reached* flatters the run.

And a reporting consequence: a run that finds the lab blocked has found the most
important thing there is to find. It must not render as a degraded run. Blockers
go **first**, with what the learner would actually experience.

## 10. Say which side is wrong — or say you cannot tell

Two different defects, two different owners, two different fixes:

- **Instruction defect** — the text is wrong. The environment is fine. The
  *author* edits text.
- **Setup defect** — the text is right but the environment cannot deliver. The
  *environment owner* fixes provisioning, config, image or entitlement.

The same defect *code* falls both ways, so the domain is a separate axis, not a
property of the code. "Model cannot be deployed" is an instruction defect if the
text names a dead model, and a setup defect if the model is alive but this
subscription refuses it.

`undetermined` is a **first-class, respectable answer** — but it must name the
evidence that would settle it. Ruling out "quota, region, transient" for one
finding took a deliberate experiment on a fresh environment. That is the
standard; a guess from a single error message is not.

Why this matters more than it looks: the two most damaging findings in the
reference walk were **setup** defects, and neither announced itself. Both
surfaced late, after many sections had been walked and their failures
misattributed to unrelated causes.

## 11. Match on identity, not on a name you derived

Any check that compares a generated label against a human-curated one will
silently miss, because humans shorten names.

The sharper version: **ask what a thing is, not what it is called.** A
deployment *named* `gpt-4o` can serve an entirely different model. That defect
does not announce itself; the lab appears to work and then fails obliquely, in
several places at once, each of which reads as an unrelated bug.

## 12. Never invent an expectation

A tool that generates expectations must emit what was observed and mark the rest
as unfilled. A plausible guess is worse than a blank because it will be
believed, and the run will then report a divergence that is really a typo in
your own descriptor.

Corollary: **validate types, not just key names.** `models = "gpt-4o"` where a
list belongs is not a typo a reader catches — it is six invented model names.

## 13. Keep distinct failures distinct

*Not signed in*, *page does not exist*, and *signed in with nothing there* need
three different actions, so they need three different messages. A diagnostic
that merges states sends people to debug the wrong problem.

## 14. Borrow a session, never a credential

The human proves identity; the machine does the work. This is a good boundary
because the identity challenge is hardware-bound and deliberately
un-automatable, while nothing after it is.

Credentials *issued by the environment under test* are a different category:
they are ephemeral, scoped to a throwaway tenancy, and handed to the agent by
the thing being validated. Capturing them **improves** safety, because a
redactor can only mask values it knows — capture is what makes masking exact.
Bind capture and registration together so no code path can obtain a value
without masking it.

Residual risk to state plainly rather than paper over: **screenshots are pixels
and redactors are text-only.** Evidence images will contain live secrets. Keep
them out of version control.

## 15. Version drift is a finding, not just metadata

A new content version or edition code is the strongest available prior that the
instructions moved. Record it every run.

## 16. The run log must be writable in every state the run can be in

Including "the target has disappeared". Bookkeeping that depends on observing
the thing being observed fails exactly when you need it most.

---

## Writing a finding somebody will act on

A finding is an argument. It needs:

1. **The claim, quoted.** What the text said, verbatim, with a reference to
   where. Paraphrase invites "that's not what it says".
2. **The observation.** What happened, including the exact error text. Not "it
   failed" — the message, the code, the trace id.
3. **The elimination.** Why this is not the obvious innocent explanation.
   *"Third independent observation, on a fresh instance and a new subscription,
   so it is not a stale environment."*
4. **The blast radius.** What else depends on this. A gating defect and a
   cosmetic one need different words, and the reader cannot infer which is which
   from the code alone.
5. **The domain.** Who fixes it — and if `undetermined`, what would settle it.

Length is not rigour, but neither is brevity. The test is whether the owner can
act without asking you a question.
