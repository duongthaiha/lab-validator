# Skillable / Learning Campus mechanics

Platform-specific facts, all confirmed live. Everything here is *nouns*; the
transferable reasoning is in `judgement.md`.

## The launch chain

```
mslearningcampus.com/Lab/Launch/{labId}
  → labclient.labondemand.com/Setup/{instanceGuid}       (provisioning, ~2 min)
  → labclient.labondemand.com/LabClient/{instanceGuid}   (the frameset)
```

**The lab-client URL cannot be loaded directly** — it returns *Access Denied*.
It must be reached by the redirect chain, in a browser that already holds the
platform session. That session is **memory-only**, which is why restarting the
browser mid-run costs a human sign-in.

## The frameset

| Frame | URL | Contents |
|---|---|---|
| *(top)* | `/LabClient/{guid}` | shell only — **no `window.api`** |
| `#consoleIFrame` | `/VirtualizationClient/{guid}?childClient=1` | 1024×768 `<canvas>` + one `<video>` — the Hyper-V console |
| `#instructionsIFrame` | `/Instructions/{guid}` | the instructions, full DOM |
| `#contentDialogIFrame` | `about:blank` | dialog host; reaches the API via `window.parent` |

**`window.api.v1` lives in the child frames, not the top frame.** Probing only
the top page reports `window.api present: False` and would wrongly conclude the
API is unavailable. All 22 documented methods are present in both child frames.

A tab whose URL matches is **not** ready. The frameset may still be building, so
wait for `getMinutesRemaining()` to actually answer before issuing any other
call — otherwise the first real step dies for reasons nobody can reproduce.

## Useful confirmed calls

| Call | Notes |
|---|---|
| `gotoInstructionsPage(i)` | index **clamps to 0** past the end — a reliable termination signal |
| `getInstructionsPageIndex()` | current page |
| `getMinutesRemaining()` | returned `5760` = 96 h exactly; use as the readiness probe |
| `getEnvironmentConnectionStatus()` | connection state, for `until:connected` |

## Instructions extraction

`/Instructions/{guid}` is directly addressable with a full DOM, so **instruction
text can be extracted without any platform API key** — which removes what looks
at first like the project's biggest external dependency.

**Trap: the instructions frame accumulates rendered pages.** Page 4 came back at
78 KB containing labs 03–10. Extraction still captures everything, but
per-section attribution must come from the **heading structure**, never the page
index.

Segment on `<h1>`: it is where the corpus starts a new named piece of work,
which is both what a learner treats as one sitting and small enough that a crash
loses little.

## Launch gating

The Launch button is `display:none` but **`disabled === false`** — a client-side
countdown to the class start, not a server lock.

Do **not** force-click a hidden Launch. The countdown is the product saying "not
ready", and a lab instance is a real enrolment on a real clock. Report
`LAUNCH NEEDED`, ask the human, and wait.

Labels seen in the wild: `Launch Lab`, `Launch`, `Start Lab`, `Start`, `Resume`.
`Resume` appears when the instance is already running; from the learner's point
of view it is the same action.

## The Resources tab

The lab hands the learner its own credentials — usernames, passwords,
subscription ids, endpoints, keys — on a **Resources** tab in the instructions
frame. Parse it into structured rows (`scope`, `label`, `value`), not a blob.

Capture it **once, immediately after launch**, for two reasons at the same time:

1. Every value is registered with the redactor, so it can never reach the trace
   whatever a later step does. A redactor can only mask values it knows.
2. The rows are kept as **data**, so a credential can be compared against what
   the lab *ships* — which is exactly how a wrong `.env` is caught — rather than
   only typed into a VM.

After reading it, **switch back to the instructions pane**. Leaving the lab
parked on Resources means every later screenshot is of the wrong pane.

## The clock

Labs are time-boxed — 96 h for the reference workshop, `5760` minutes. Record
`getMinutesRemaining()` at the start of the run so that every later "was this
slow because the lab was expiring?" question has a zero point.

## The VM console

The console is a `<canvas>` — there is no DOM inside the VM and no OCR here.
Interaction is coordinate clicks, key events and typed text against the canvas;
observation is screenshots plus whatever the guest OS will print to a terminal.

This is rung 5 of the control-surface ladder (see `judgement.md` §1) and it is
the least reliable surface in the system. Prefer any question that can be
answered from the instructions frame, the platform API, or an out-of-band
oracle. Reach for the canvas only when the work itself is inside the VM.
