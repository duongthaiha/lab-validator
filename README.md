# Lab Validator

Validates Microsoft Learning Campus hands-on lab instructions against live
product state, and reports where a lab has drifted from reality — retired
models, renamed navigation, moved features, stale screenshots.

Learning Campus is a **Skillable TMS** tenant hosted for Microsoft, so the
validator drives the platform's supported APIs rather than scraping the UI.

**Current findings:** [`docs/gapanalysis.md`](docs/gapanalysis.md) — the
learner-facing gap list for *WorkshopPLUS: Azure AI Platform and Services*,
including how much of the lab has actually been walked. Read the coverage table
first: an absence of findings in a module means *not yet checked*, not *correct*.

## Credentials — read this first

**This project never stores your Learning Campus password.** Sign-in goes
through Entra ID / MSA with MFA, and Skillable adds device registration on top,
so a stored password could not log in even if we kept one.

### Preferred: attach to a browser you're already signed into

A dedicated Edge/Chrome profile under `.browser-profile/`, cloned from one of
your real Edge profiles, that **you sign into by hand once**. Playwright then
attaches to it over CDP.

```powershell
python scripts/browser_session.py --list-profiles          # see your Edge profiles
python scripts/browser_session.py --launch --profile "Profile 2"
python scripts/browser_session.py --signin msa             # walk the sign-in chooser
python scripts/browser_session.py --status                 # confirm it's reachable
```

`--signin` drives the Learning Campus chooser as far as it can and stops at the
interactive challenge. Both Entra ID and personal Microsoft Accounts land on a
**Windows Hello / FIDO passkey** prompt, which is hardware-bound and cannot be
automated — by design. You complete that one gesture in the visible window and
the session then persists in the profile for every subsequent run.

Why this is the best option:

- **Zero credentials stored** — not even an encrypted session file.
- **MFA is never re-prompted** — the profile persists.
- **Skillable device registration stays satisfied.** Registration keys off a
  browser-cookie GUID plus IP and geolocation
  ([docs](https://docs.skillable.com/docs/device-registration)). Reusing one
  profile means the same fingerprint every run, so no email challenge.
- The browser is visible, so you can watch or take over at any point.

Notes:

- Chrome/Edge 136+ refuse `--remote-debugging-port` on the *default* profile,
  which is why a dedicated profile directory is required.
- The clone is an allow-list copy (cookies, preferences, local storage): ~6 MB
  versus ~1.6 GB for a full mirror. Saved passwords are deliberately not copied.
  Use `--full-profile` only if you need a complete mirror.

### Fallback: encrypted session capture (headless CI)

Where no interactive profile exists, capture a Playwright `storageState` and
encrypt it to your Windows account with DPAPI:

```powershell
python scripts/bootstrap_auth.py            # sign in, capture, encrypt
python scripts/bootstrap_auth.py --status
python scripts/bootstrap_auth.py --clear
```

### The other two credentials

| Credential | Where it lives | How it gets there |
|---|---|---|
| Skillable API key | `.env` locally · GitHub Actions secret in CI | Copy `.env.example` → `.env` |
| Azure access for model/lifecycle oracles | Nothing stored | `az login` locally · OIDC federation in CI |

Rules:

- `.env`, `.auth/`, `.browser-profile/`, `artifacts/`, `*.har`, `trace.zip`,
  `test-results/` are all gitignored **and** blocked by a pre-commit hook.
  Playwright traces embed cookies, request headers and response bodies — they
  are as sensitive as the password itself.
- A `storageState` file can impersonate your account until it expires
  ([Playwright docs](https://playwright.dev/docs/auth)). Treat it accordingly.
- Config uses `pydantic.SecretStr`, so printing settings shows `**********`.
- DPAPI blobs are bound to your Windows user *and* machine. Copying `.auth/`
  to another machine yields an unreadable file — by design.

## Driving the browser

```powershell
python scripts/browser_session.py --goto <url>    # navigate a tab
python scripts/browser_session.py --links         # enumerate (text, href) pairs
python scripts/browser_session.py --click <text>  # click by accessible name or text
python scripts/browser_session.py --dump          # forms/controls/frames as JSON
python scripts/browser_session.py --shot          # screenshot → artifacts/recon/
python scripts/browser_session.py --probe         # detect window.api.v1, iframes, canvases
python scripts/browser_session.py --all-tabs      # applies to every tab
```

`--probe` is the reconnaissance command: it reports whether the Skillable
[Lab Client API](https://docs.skillable.com/docs/lab-client-api-for-lab-delivery-customization)
is exposed on the page, enumerates `window.api.v1` methods, and records iframe
and `<canvas>` geometry — which is what distinguishes a DOM-automatable Cloud
Slice lab from a pixel-only virtualization lab.

`--links` and `--dump` exist because the two things you most need during recon
are *"what can I reach from here"* and *"what is on this page that I can't
see"*. The Learning Campus nav is built from dropdown parents whose children are
`display:none`, so clicking a visible nav label does nothing — link enumeration
is the only reliable way to discover routes. Likewise `--dump` surfaces controls
that exist but are hidden, such as a lab launch button gated by a client-side
countdown rather than a server-side lock.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
python -m playwright install chromium

Copy-Item .env.example .env     # then fill in LV_SKILLABLE_API_KEY
pre-commit install              # blocks credentials from reaching git

python scripts/browser_session.py --list-profiles
python scripts/browser_session.py --launch --profile "<your profile>"
```

## Layout

```
docs/approach.md                    architecture, findings and reuse guide
docs/gapanalysis.md                 learner-facing gaps found in the target lab
scripts/browser_session.py          attach to a signed-in browser; recon commands
scripts/lab_drive.py                drive a running lab: instructions, creds, VM
scripts/bootstrap_auth.py           fallback: sign-in → encrypted session
src/lab_validator/browser.py        CDP launch/attach, profile management
src/lab_validator/labclient.py      lab frames, window.api.v1, VM screen/click/type
src/lab_validator/config.py         typed settings, SecretStr-backed
src/lab_validator/secrets_store.py  DPAPI protect/unprotect helpers
src/lab_validator/auth.py           storageState load/save, session health
```

## Design

See the research report for the full architecture. In brief — *oracle-first,
API-second, DOM-third, vision-last*:

1. **Static claim checking.** Parse a lab's IDLx instruction source, extract
   claims (model, region, SKU, API version, portal label), and cross-check them
   against authoritative APIs. This catches every "model retired" defect with no
   browser at all.
2. **Instrumented launch.** Launch via the Skillable Connect LAB API, drive the
   lab client's supported `window.api.v1` surface, and read back the lab
   author's own automated-activity results.
3. **Cloud Slice DOM automation.** Azure portal labs open a second window with a
   full DOM, so Playwright locators work.
4. **Canvas vision.** Only for virtualization labs, where the VM is delivered as
   pixels over a WebSocket.