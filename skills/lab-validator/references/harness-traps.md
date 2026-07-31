# Harness traps

The expensive ones. Every item below cost real time to learn during runs that
executed lab content rather than checking that pages load. Most silently produce
*wrong results* rather than errors, which is why they are worth reading before
a walk rather than during one.

---

## Reading results

**"No error output" is not success.** Cells wrapped in `try/except` report clean
while printing an error string. Always follow an execution step with a text scan:

```powershell
[regex]::Matches($allText, 'Error|Traceback|Exception|400').Count
```

**Green does not mean worked.** The single highest-value finding of one lab was
a scan printing `Scan completed successfully!` and `Overall ASR: 0.0%` having
evaluated **zero** attacks. Look past the exit status to the artefact: file
sizes, row counts, the actual numbers in the JSON. `0/0` and `0/4` render almost
identically to a human and mean opposite things.

**Read tracebacks from the saved notebook file, not from the screen.** VS Code
truncates long cell output behind a *"Output is truncated. View as a scrollable
element"* link that cannot be scraped, and a screenshot of a wrapped 200-column
traceback is close to unreadable. `Ctrl+S`, then parse:

```powershell
$nb = Get-Content $path -Raw | ConvertFrom-Json
$nb.cells[$N].outputs | ForEach-Object { $_.text -join ''; $_.traceback -join "`n" }
```

**Redirect rich-console tools to a file.** Anything using `rich` repaints and
then *clears* the terminal, so a failure leaves an empty screen. `cmd > run.log
2>&1`, then tail the log. This turned an unexplainable blank screen into a
one-line diagnosis twice.

## Executing notebooks

Use `nbconvert`, not the VS Code UI:

```powershell
python -m jupyter nbconvert --to notebook --execute --allow-errors `
  --ExecutePreprocessor.timeout=240 --output out.ipynb in.ipynb
```

It runs **every** cell, keeps going past failures, and stores each traceback in
the output file — which removes the *failed* vs *never reached* ambiguity that
"Run All" creates.

- **`jupyter` may not be on `PATH`** even when installed. Use `python -m jupyter`.
- **PowerShell 5.1's `Set-Content -Encoding UTF8` writes a BOM**, and `nbformat`
  rejects it: `NotJSONError: Notebook does not appear to be JSON: '\ufeff{…'`.
  Write with `[System.IO.File]::WriteAllText($path, $json)` — UTF-8, no BOM.

## Prove a defect by fixing it on a scratch copy

The most valuable output is not "this lab is broken" but "this lab is broken
**for exactly these N reasons**, and here is the run proving nothing else is
wrong." Copy the artifact, apply one minimal fix per known defect, re-run, and
record both results. It separates *configuration* defects from *content rot* —
three modules that looked dead turned out sound once two `.env` lines were fixed.

Keep patches minimal and mechanical so the diff itself is the finding. Patch
**values**, not keyword arguments — removing a kwarg changes the code shape and
invites a `TypeError` that is your fault, not the lab's.

## Driving a VM console

- **Clicking the taskbar button of the already-foreground app minimises it**, and
  every keystroke in the same action chain then goes to whatever was behind it.
  This silently redirected an entire command sequence once. Screenshot to
  establish focus before switching windows, or make the switch its own step.
  A blind taskbar click at the head of a chain is **not idempotent**.
- **Keep typed lines short.** Long payloads wrap in the console and can pick up a
  stray Enter, leaving PowerShell at a `>>` continuation prompt that swallows
  everything after it. Split into several short lines — session variables persist
  between them, so build a pipeline up incrementally and read it back at the end.
- **Multi-line text loses its trailing newline.** Follow with an explicit Enter.
- **Interactive prompts eat queued keystrokes.** Keys typed while a long command
  runs are tty-buffered and execute afterwards — usually convenient, occasionally
  destructive. `az login` blocking on *"Select a subscription and tenant"*
  consumed a queued command as its answer. Screenshot before typing into a
  terminal that might be mid-prompt.
- **A new editor window can be poisoned while the existing one is fine.** Opening
  a file spawned a second VS Code window that failed with *"Could not register
  service worker"*; the pre-existing window was healthy. Open files from inside
  the window that already works. Do not assume one process per app.
- **Terminal output prints at column 0**, outside the crop used for portal
  screenshots. Crop from `x=0` when reading a shell, or the evidence is blank.
- **Recompute coordinate scaling per crop.** The view→VM factor is a property of
  *that* crop, not of the harness: ×1.157 for one size, ×1.333 for another.
  Getting it wrong produces clicks 100 px off that look like flaky UI.
- **`until:quiet` is not a completion probe.** A terminal that is thinking is
  visually quiet, so it returned immediately after a `clear` and repeatedly
  mid-install. For long shell operations use a fixed wait plus a screenshot, and poll.
- **`C:\` may not be writable.** Scratch files go to `$env:USERPROFILE`.

## Credentials

**Credential lifetime is shorter than lab lifetime, and that is itself a
finding.** Lab accounts often sign in with a **Temporary Access Pass** that
expires long before the instance does, taking every CLI-derived token with it.
The failure does not look like an auth failure — `az login` simply hangs forever
behind the Windows WAM broker, and the real error surfaces several steps later.
Recovery that works unattended:

```powershell
az config set core.enable_broker_on_windows=false
az account clear
az login --use-device-code --scope <resource>/.default
```

then complete the device code **in the browser on the VM**, where the
interactive session is still valid even though the TAP is not.

## Evidence hygiene

**Capture secrets by shape, never by value.** To audit a config file, print key
names and value *lengths*:

```powershell
$p[0] + " = <" + $v.Length + " chars>"
```

That is enough to prove a variable is present, populated, and the **wrong
shape** — which was exactly one of the highest-value findings — without ever
writing the secret to the trace.

**Screenshots are pixels and redactors are text-only.** Evidence images will
contain live keys. Keep the run folder out of version control, and secret-scan
anything derived from it before committing.

## Discipline

**Verify, do not predict.** Two findings had to be retracted for predicting an
outcome instead of observing one: `pip install X` without `-U` is a **no-op**
for an already-installed distribution, and one tool's `--output` resolved
against CWD despite its own `--help` claiming otherwise. Run the command, then
write the finding.

**A retraction is cheap; a wrong finding is not.** Use the retract command the
moment evidence contradicts a recorded verdict.
