# AGENTS.md

Working notes for coding agents live in
[`.github/copilot-instructions.md`](.github/copilot-instructions.md).

Read it before changing anything. The short version:

- `python -m pytest -q` and `python -m ruff check .` must both pass. The suite
  is offline; no test needs a browser or a live lab.
- Edited `skills/lab-validator/`? Run `python -m lab_validator.cli install-skill`.
- Edited `src/` or `scripts/`? Run `python -m lab_validator.cli prepare-skill`,
  then `install-skill`.
- Docs are tested against the code — rename a module or add a CLI flag and you
  must update `README.md`, `SKILL.md` and `docs/agent.md` in the same change.
- Never commit anything under `runs/`, `artifacts/`, `.auth/` or
  `.browser-profile/`; they carry real lab credentials.
