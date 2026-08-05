# Evaluating this skill

Test cases live in `evals.json`, in the layout the
[Agent Skills spec](https://agentskills.io/skill-creation/evaluating-skills)
describes. Generated results do not live here — see *Where results go* below.

## The problem this layout solves

The spec's loop is: run each case twice, once with the skill and once without,
and compare. That does not survive contact with this skill unmodified, for a
reason worth stating plainly.

This skill walks a **live Skillable lab** in a real browser, and a human has to
sign in. So a paired run costs two lab reservations and two sign-ins. That is
merely expensive. The disqualifying part is that **the two runs do not see the
same lab.** Lab environments drift between reservations — retired models,
changed portal labels, exhausted quota. Detecting exactly that drift is what
this tool is *for*. So a with/without delta measured across two live runs is
partly measuring the skill and partly measuring the lab moving underneath it,
with no way to separate the two. The baseline is not a baseline.

The fix is to hold the environment still. Feed the agent a **recorded walk**
instead of a live lab. `evals/files/drifted-walk/` is exactly that: a complete
run folder — the same `run.json` and `trace.jsonl` schema a real walk emits —
with the observations already made. Same input every time, for every version of
the skill, forever.

That is affordable because of what the skill actually contributes. It does not
implement browser control; the CLI does, and that has 817 offline unit tests.
What the skill contributes is two things:

- **Operating** — drive the CLI, stay in the learner's path, capture evidence
  before recording a verdict.
- **Judgement** — given what was observed, is this a defect, whose is it, what
  evidence would settle it, how bad is it.

Neither needs a browser. The part of this system with the most to get wrong is
the part that evaluates most cheaply.

## The three tiers

| Tier | What it tests | Needs a lab? | Run it |
| --- | --- | --- | --- |
| **1 — Judgement** | Verdicts, ownership, evidence standards, report shape | No | Every iteration |
| **2 — Operating** | Does the agent follow the documented commands, or improvise? | No | Every iteration |
| **3 — Live walk** | The whole thing, end to end | Yes, and a human | At release, rarely |

Tiers 1 and 2 are the loop. Eval 1 is tier 1; evals 2 and 3 are tier 2.

Tier 3 has no `without_skill` arm, because an unskilled agent cannot drive a
browser through a lab at all — the comparison would be vacuous. Compare against
the **previous skill version's** recorded walk instead, as the spec describes
for skill-to-skill comparison.

## The fixture

`evals/files/drifted-walk/` is synthetic, and deliberately so. Real run folders
are gitignored (`runs/`) because they carry `@lab.MaskedTextBox` values and
portal credentials; committing one as a fixture would put lab credentials in
git history. It is also more useful synthetic: every trap in it is planted, so
the right answer is known rather than argued about.

What is planted, and which judgement rule each one probes:

| Planted | Probes |
| --- | --- |
| A 503 and a kernel drop, each seen once and resolving on retry | A defect needs an oracle or a repeat. Reporting these is the failure. |
| A tile relabelled `AI Foundry` → `Microsoft Foundry`, seen twice | A real instruction defect, correctly evidenced. |
| A deployment *named* `gpt-4o` that serves `gpt-35-turbo` | Match on identity, not on a derived name — and this is **setup**, not instruction. |
| A notebook cell green with no output and no artifact on disk | A green tick is not an observation. The most dangerous class. |
| Quota refusal blocking a dependent step, walk continues past it | Blocked is a status; the blocker is the finding. |
| 2 of 5 sections never selected | Coverage goes at the top, before any finding. |

A skill-less run will typically report the transients, miss the model-identity
mismatch or file it against the instructions, and open with findings rather than
coverage. That is the delta these evals exist to measure.

## Assertions

`evals.json` carries prompts and expected outputs but **no assertions yet**, per
the spec: write them after seeing what the first run produces. Assertions
guessed in advance tend to encode what the author hoped for rather than what
distinguishes a good answer from a bad one.

When adding them after iteration 1, drop any assertion that passes in both arms
— it is measuring the base model, not the skill, and it inflates the with-skill
pass rate while saying nothing.

## Where results go

Alongside the skill directory, not inside it:

```
C:\Git\lab-validator\               the skill (this repo)
C:\Git\lab-validator-workspace\     generated: iteration-1/, iteration-2/, ...
```

Outside the repo on purpose. Eval outputs are model-written gap analyses derived
from run data — the same class of material as `runs/` and `artifacts/`, which
this repo already refuses to track. Keeping the workspace a sibling means it
cannot be committed by accident and cannot be swept into a package. A
`lab-validator-workspace/` inside the repo is gitignored as a fallback, for when
somebody runs it in the wrong place.

`evals/` itself is repository-only. It is developer material, like `tests/`, and
is not published by `install-skill` or `package-skill`; a guard test enforces
that.
